"""حراسة الحزمة المجمّدة لويندوز: كل وحدة يستوردها ترقيع يجب أن تكون متاحة بعد التحديث.

حزمة ويندوز 4.1.4 المجمّدة لا تحمل وحدة ``zoneinfo`` إطلاقًا (تحقّق من تحليل PyInstaller
لمدخل ``launcher.py``)، وويندوز لا يملك قاعدة مناطق زمنية في النظام أصلًا. لذلك يسافر
مع كل ترقيع: نسخة ``zoneinfo`` القياسية بايثون خالص، وملفات TZif للمدن المدعومة.
هذا الاختبار يمنع أي ترقية تُدخل وحدة غير موجودة في الحزمة القديمة.
"""
import ast
import importlib.util
import json
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent

# الوحدات المتاحة داخل حزمة Windows 4.1.4 المجمّدة (تحليل PyInstaller لمدخل launcher.py،
# بما فيها الوحدات المدمجة في المفسّر والوحدات الممتدة في lib-dynload).
FROZEN_BUNDLE_MODULES = frozenset(
    {
        "__future__", "_abc", "_aix_support", "_ast", "_asyncio", "_bisect", "_blake2", "_bz2",
        "_codecs", "_codecs_cn", "_codecs_hk", "_codecs_iso2022", "_codecs_jp", "_codecs_kr",
        "_codecs_tw", "_collections", "_collections_abc", "_colorize", "_compat_pickle",
        "_compression", "_contextvars", "_csv", "_ctypes", "_datetime", "_decimal", "_functools",
        "_hashlib", "_heapq", "_imp", "_io", "_json", "_locale", "_lzma", "_markupbase", "_md5",
        "_multibytecodec", "_multiprocessing", "_opcode", "_opcode_metadata", "_operator",
        "_pickle", "_posixshmem", "_posixsubprocess", "_py_abc", "_pydatetime", "_pydecimal",
        "_pyrepl", "_queue", "_random", "_sha1", "_sha2", "_sha3", "_signal", "_socket",
        "_sqlite3", "_sre", "_ssl", "_stat", "_statistics", "_string", "_strptime", "_struct",
        "_suggestions", "_symtable", "_sysconfig", "_thread", "_threading_local", "_tokenize",
        "_tracemalloc", "_typing", "_warnings", "_weakref", "_weakrefset", "abc", "argparse",
        "array", "ast", "asyncio", "atexit", "base64", "bdb", "binascii", "bisect", "builtins",
        "bz2", "calendar", "cmd", "code", "codecs", "codeop", "collections", "concurrent",
        "contextlib", "contextvars", "copy", "copyreg", "csv", "ctypes", "dataclasses", "datetime",
        "decimal", "difflib", "dis", "doctest", "email", "encodings", "enum", "errno",
        "faulthandler", "fcntl", "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc",
        "genericpath", "getopt", "getpass", "gettext", "glob", "grp", "gzip", "hashlib", "heapq",
        "hmac", "html", "http", "importlib", "inspect", "io", "ipaddress", "itertools", "json",
        "keyword", "linecache", "locale", "logging", "lzma", "marshal", "math", "mimetypes",
        "mmap", "multiprocessing", "netrc", "ntpath", "nturl2path", "numbers", "opcode",
        "operator", "os", "pathlib", "pdb", "pickle", "pkgutil", "platform", "posix", "posixpath",
        "pprint", "pwd", "py_compile", "pydoc", "pydoc_data", "pyexpat", "queue", "quopri",
        "random", "re", "readline", "reprlib", "resource", "rlcompleter", "runpy", "secrets",
        "select", "selectors", "shlex", "shutil", "signal", "socket", "socketserver", "sqlite3",
        "sre_compile", "sre_constants", "sre_parse", "ssl", "stat", "statistics", "string",
        "stringprep", "struct", "subprocess", "sys", "sysconfig", "tarfile", "tempfile", "termios",
        "textwrap", "threading", "time", "token", "tokenize", "traceback", "tracemalloc", "tty",
        "types", "typing", "unicodedata", "unittest", "urllib", "warnings", "weakref",
        "webbrowser", "xml", "xmlrpc", "zipfile", "zipimport", "zlib",
    }
)
BUNDLED_THIRD_PARTY = frozenset(
    {"PySide6", "nacl", "packaging", "miniaudio", "_miniaudio", "_cffi_backend"}
)


def local_modules(app_dir=HERE):
    return {path.stem for path in app_dir.glob("*.py")}


def required_imports(source: str):
    """أسماء الوحدات المستوردة في مسار إلزامي (خارج try/except ImportError)."""
    modules = set()

    def visit(node):
        for child in ast.iter_child_nodes(node):
            optional = isinstance(child, ast.Try) and any(
                (handler.type is None)
                or (isinstance(handler.type, ast.Name) and handler.type.id in {"ImportError", "Exception"})
                or (isinstance(handler.type, ast.Tuple) and any(
                    isinstance(item, ast.Name) and item.id in {"ImportError", "Exception"}
                    for item in handler.type.elts
                ))
                for handler in child.handlers
            )
            if optional:
                continue
            if isinstance(child, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in child.names)
            elif isinstance(child, ast.ImportFrom) and child.level == 0 and child.module:
                modules.add(child.module.split(".")[0])
            visit(child)

    visit(ast.parse(source))
    return modules


class FrozenBundleImportTests(unittest.TestCase):
    def test_patchable_modules_import_only_modules_present_in_frozen_bundle(self):
        allowed = FROZEN_BUNDLE_MODULES | BUNDLED_THIRD_PARTY | local_modules()
        offenders = {}
        for path in sorted(HERE.glob("*.py")):
            for module in sorted(required_imports(path.read_text(encoding="utf-8"))):
                if module not in allowed:
                    offenders.setdefault(path.name, []).append(module)
        self.assertEqual(offenders, {}, "وحدات غير موجودة في حزمة ويندوز المجمّدة 4.1.4")

    def test_zoneinfo_import_is_optional_in_main(self):
        source = (HERE / "main.py").read_text(encoding="utf-8")
        self.assertIn("except ImportError", source)
        self.assertIn("if zone_name and ZoneInfo is not None", source)
        self.assertIn("_bundled_tz = Path(__file__).resolve().parent / 'tzdata'", source)

    def test_vendored_zoneinfo_is_a_working_drop_in(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    """
                    import sys
                    sys.path.insert(0, {app!r})

                    class Blocker:
                        def find_spec(self, name, path=None, target=None):
                            if name == "_zoneinfo":
                                raise ImportError("no C accelerator in the frozen bundle")
                            return None

                    sys.meta_path.insert(0, Blocker())
                    import zoneinfo
                    from datetime import datetime
                    assert zoneinfo.__file__.startswith({app!r}), zoneinfo.__file__
                    london = zoneinfo.ZoneInfo("Europe/London")
                    assert datetime(2026, 7, 1, 12, tzinfo=london).utcoffset().total_seconds() == 3600
                    assert datetime(2026, 1, 1, 12, tzinfo=london).utcoffset().total_seconds() == 0
                    """
                ).format(app=str(HERE)),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bundled_tz_database_covers_every_supported_city(self):
        cities = json.loads((HERE / "data" / "prayer-cities.json").read_text(encoding="utf-8"))["cities"]
        zones = {city["tz"] for city in cities if city.get("tz")}
        self.assertGreaterEqual(len(zones), 20)
        tz_dir = HERE / "tzdata"
        self.assertTrue((tz_dir / "ATTRIBUTION.json").is_file())
        for zone in zones:
            with self.subTest(zone=zone):
                self.assertTrue((tz_dir / zone).is_file(), zone)
        # كل المناطق المطلوبة تُقرأ فعليًا من المجلد المضمّن وحده (كما في ويندوز بلا قاعدة نظام).
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    """
                    import json, os, sys
                    from datetime import datetime
                    os.environ["PYTHONTZPATH"] = {tz!r}
                    sys.path.insert(0, {app!r})
                    import zoneinfo
                    zones = {zones!r}
                    for zone in sorted(zones):
                        moment = datetime(2026, 7, 15, 12, tzinfo=zoneinfo.ZoneInfo(zone))
                        assert moment.utcoffset() is not None, zone
                    print("ok")
                    """
                ).format(tz=str(tz_dir), app=str(HERE), zones=sorted(zones)),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_signed_patch_payload_ships_zoneinfo_and_tzdata(self):
        scripts = ROOT / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        spec = importlib.util.spec_from_file_location(
            "generate_signed_patch", scripts / "generate_signed_patch.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        files = module.default_patch_files(HERE)
        self.assertIn("zoneinfo/__init__.py", files)
        self.assertIn("zoneinfo/_zoneinfo.py", files)
        self.assertIn("tzdata/Africa/Cairo", files)
        self.assertIn("tzdata/ATTRIBUTION.json", files)
        self.assertIn("main.py", files)


if __name__ == "__main__":
    unittest.main()
