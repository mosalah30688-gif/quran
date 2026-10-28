import configparser
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent


def load_version(path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LinuxPackagingTests(unittest.TestCase):
    def test_linux_identity_matches_siraj_product(self):
        linux = load_version(HERE / "version.py", "linux_version")
        windows = load_version(ROOT / "windows_app" / "version.py", "windows_version")
        # Windows is still not built or published, but shared source metadata stays aligned.
        self.assertEqual(linux.APP_VERSION, windows.APP_VERSION)
        self.assertGreater(tuple(map(int, linux.APP_VERSION.split("."))), (4, 0, 7))
        self.assertEqual(linux.APP_NAME_AR, "سراج")
        self.assertEqual(linux.APP_DESCRIPTION_AR, "قرآن كريم")

    def test_desktop_entry_is_graphical_siraj_launcher(self):
        desktop = HERE / "packaging" / "com.mosalah30688.siraj.quran.desktop"
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        parser.optionxform = str
        parser.read(desktop, encoding="utf-8")
        entry = parser["Desktop Entry"]
        self.assertEqual(entry["Name"], "سراج")
        self.assertEqual(entry["Exec"], "siraj")
        self.assertEqual(entry["Terminal"], "false")
        self.assertEqual(entry["Icon"], "com.mosalah30688.siraj.quran")

    def test_stable_channel_is_not_publicly_available(self):
        manifest = json.loads((ROOT / "update" / "linux" / "stable.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["product"], "siraj-quran-linux")
        self.assertFalse(manifest["available"])
        self.assertEqual(manifest["assets"], {})


if __name__ == "__main__":
    unittest.main()
