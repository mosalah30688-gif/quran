"""حراسة الحزمة المجمّدة: كل وحدة يستوردها ترقيع يجب أن تكون موجودة في حزمة 4.1.1.

سبب وجود هذا الملف: ترقيع 4.3.1 استورد ``zoneinfo`` في أعلى ``main.py``، والحزمة
المجمّدة 4.1.1 لا تحمل هذه الوحدة إطلاقًا (تحقّق من تحليل PyInstaller لمدخل
``launcher.py``)، فمات التطبيق فورًا بعد التحديث بلا نافذة ولا رسالة. الاختبار
يمنع تكرار هذا الصنف من الأخطاء في أي ترقيع قادم.
"""
import ast
import importlib.util
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent

# وحدة قياسية متاحة داخل حزمة Linux المجمّدة 4.1.1 (تحليل PyInstaller لمدخل launcher.py
# مع الوحدات المدمجة في مفسّر بايثون). أي وحدة خارجها تعني تعطّلًا فوريًا بعد الترقيع.
FROZEN_BUNDLE_MODULES = frozenset(
    {
        "__future__", "_abc", "_aix_support", "_ast", "_bisect", "_blake2", "_codecs",
        "_collections", "_collections_abc", "_colorize", "_compat_pickle", "_compression",
        "_csv", "_datetime", "_functools", "_heapq", "_imp", "_io", "_json", "_locale",
        "_markupbase", "_md5", "_opcode_metadata", "_operator", "_posixsubprocess", "_py_abc",
        "_pydatetime", "_pydecimal", "_pyrepl", "_queue", "_random", "_sha1", "_sha2", "_sha3",
        "_signal", "_socket", "_sre", "_ssl", "_stat", "_string", "_strptime", "_struct",
        "_suggestions", "_symtable", "_sysconfig", "_thread", "_threading_local", "_tokenize",
        "_tracemalloc", "_typing", "_warnings", "_weakref", "_weakrefset", "abc", "argparse",
        "array", "ast", "asyncio", "atexit", "base64", "bdb", "bisect", "builtins", "bz2", "calendar",
        "cmd", "code", "codecs", "codeop", "collections", "concurrent", "contextlib",
        "contextvars", "copy", "copyreg", "csv", "ctypes", "dataclasses", "datetime", "decimal",
        "difflib", "dis", "doctest", "email", "encodings", "enum", "errno", "faulthandler",
        "fcntl", "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc", "genericpath",
        "getopt", "getpass", "gettext", "glob", "grp", "gzip", "hashlib", "heapq", "hmac",
        "html", "http", "importlib", "inspect", "io", "ipaddress", "itertools", "json",
        "keyword", "linecache", "locale", "logging", "lzma", "marshal", "math", "mimetypes",
        "multiprocessing", "netrc", "ntpath", "nturl2path", "numbers", "opcode", "operator",
        "os", "pathlib", "pdb", "pickle", "pkgutil", "platform", "posix", "posixpath", "pprint",
        "pwd", "py_compile", "pydoc", "pydoc_data", "queue", "quopri", "random", "re", "reprlib",
        "resource", "rlcompleter", "runpy", "secrets", "select", "selectors", "shlex", "shutil",
        "signal", "socket", "socketserver", "sqlite3", "sre_compile", "sre_constants",
        "sre_parse", "ssl", "stat", "statistics", "string", "stringprep", "struct", "subprocess",
        "sys", "sysconfig", "tarfile", "tempfile", "termios", "textwrap", "threading", "time",
        "token", "tokenize", "traceback", "tracemalloc", "tty", "types", "typing", "unicodedata",
        "unittest", "urllib", "warnings", "weakref", "webbrowser", "xml", "xmlrpc", "zipfile",
        "zipimport", "zlib",
    }
)
# وحدات يوفّرها التطبيق المجمّد نفسه أو تسافر داخل الترقيع.
BUNDLED_THIRD_PARTY = frozenset({"PySide6", "nacl", "packaging", "miniaudio", "_miniaudio", "_cffi_backend"})


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
        app_local = local_modules()
        allowed = FROZEN_BUNDLE_MODULES | BUNDLED_THIRD_PARTY | app_local
        offenders = {}
        for path in sorted(HERE.glob("*.py")):
            for module in sorted(required_imports(path.read_text(encoding="utf-8"))):
                if module not in allowed:
                    offenders.setdefault(path.name, []).append(module)
        self.assertEqual(
            offenders,
            {},
            "وحدات غير موجودة في الحزمة المجمّدة 4.1.1: اجعلها اختيارية أو وفّرها داخل الترقيع",
        )

    def test_zoneinfo_import_is_optional_in_main(self):
        source = (HERE / "main.py").read_text(encoding="utf-8")
        self.assertIn("except ImportError", source)
        self.assertIn("if zone_name and ZoneInfo is not None", source)

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
                    assert datetime(2026, 7, 1, 12, tzinfo=zoneinfo.ZoneInfo("Europe/London")).utcoffset().total_seconds() == 3600
                    assert datetime(2026, 1, 1, 12, tzinfo=zoneinfo.ZoneInfo("Europe/London")).utcoffset().total_seconds() == 0
                    assert datetime(2026, 7, 1, 12, tzinfo=zoneinfo.ZoneInfo("Africa/Cairo")).utcoffset().total_seconds() == 10800
                    """
                ).format(app=str(HERE)),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_signed_patch_payload_ships_vendored_zoneinfo(self):
        scripts = ROOT / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        spec = importlib.util.spec_from_file_location(
            "generate_signed_patch", scripts / "generate_signed_patch.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        files = module.default_patch_files(HERE)
        zoned = sorted(name for name in files if name.startswith("zoneinfo/"))
        self.assertEqual(zoned, ["zoneinfo/__init__.py", "zoneinfo/_common.py", "zoneinfo/_tzpath.py", "zoneinfo/_zoneinfo.py"])
        self.assertIn("main.py", files)


if __name__ == "__main__":
    unittest.main()
