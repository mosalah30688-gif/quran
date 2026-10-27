import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock
import sys

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import portable_updater as updater  # noqa: E402


class PortableUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = self.root / "Siraj"
        self.target.mkdir()
        (self.target / "portable.flag").write_text("")
        (self.target / "Siraj.exe").write_bytes(b"old")
        (self.target / "old.dll").write_bytes(b"old-dll")
        (self.target / "UserData").mkdir()
        (self.target / "UserData" / "settings.ini").write_text("saved=true")

    def tearDown(self):
        self.tmp.cleanup()

    def make_archive(self):
        archive = self.root / "update.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("Siraj-1.0.1/Siraj.exe", b"new")
            zf.writestr("Siraj-1.0.1/new.dll", b"new-dll")
            zf.writestr("Siraj-1.0.1/portable.flag", b"")
        return archive

    @mock.patch.object(updater, "wait_for_process")
    @mock.patch.object(updater.subprocess, "Popen")
    def test_update_preserves_user_data(self, popen, wait):
        archive = self.make_archive()
        updater.install(archive, self.target, 123, "Siraj.exe")
        self.assertEqual((self.target / "Siraj.exe").read_bytes(), b"new")
        self.assertTrue((self.target / "new.dll").exists())
        self.assertFalse((self.target / "old.dll").exists())
        self.assertEqual((self.target / "UserData" / "settings.ini").read_text(), "saved=true")
        self.assertTrue((self.target / "portable.flag").exists())
        self.assertFalse(archive.exists())
        popen.assert_called_once()
        wait.assert_called_once_with(123)

    def test_rejects_zip_slip(self):
        archive = self.root / "unsafe.zip"
        destination = self.root / "extract"
        destination.mkdir()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../outside.txt", b"bad")
        with self.assertRaises(RuntimeError):
            updater.safe_extract(archive, destination)
        self.assertFalse((self.root / "outside.txt").exists())

    @mock.patch.object(updater, "wait_for_process")
    def test_invalid_archive_keeps_current_version(self, _wait):
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("readme.txt", "missing exe")
        with self.assertRaises(RuntimeError):
            updater.install(archive, self.target, 123, "Siraj.exe")
        self.assertEqual((self.target / "Siraj.exe").read_bytes(), b"old")
        self.assertTrue((self.target / "old.dll").exists())
        self.assertEqual((self.target / "UserData" / "settings.ini").read_text(), "saved=true")


if __name__ == "__main__":
    unittest.main()
