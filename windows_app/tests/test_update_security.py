import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

from update_security import verify_update_manifest  # noqa: E402
from version import APP_VERSION  # noqa: E402


class UpdateSecurityTests(unittest.TestCase):
    def setUp(self):
        self.key = HERE / "assets" / "update_public_key.txt"
        self.manifest = json.loads((REPO / "update" / "windows" / "stable.json").read_text(encoding="utf-8"))

    def test_committed_channel_is_signed_or_explicitly_fail_closed(self):
        if self.manifest.get("available") is True:
            self.assertTrue(verify_update_manifest(self.manifest, self.key))
        else:
            self.assertIs(self.manifest.get("available"), False)
            self.assertEqual(self.manifest.get("assets"), {})
            self.assertFalse(verify_update_manifest(self.manifest, self.key))

    def test_stable_channel_publishes_the_latest_approved_portable_package(self):
        asset = self.manifest["assets"]["portable"]
        self.assertIs(self.manifest["available"], True)
        self.assertEqual(self.manifest["product"], "siraj-quran-windows")
        self.assertEqual(self.manifest["channel"], "stable")
        stable_version = self.manifest["version"]
        self.assertLessEqual(
            tuple(map(int, stable_version.split("."))),
            tuple(map(int, APP_VERSION.split("."))),
        )
        self.assertEqual(asset["file_name"], f"Siraj-Quran-{stable_version}-windows-portable-x64.zip")
        self.assertEqual(
            asset["url"],
            f"https://github.com/mosalah30688-gif/quran/releases/download/"
            f"siraj-windows-v{stable_version}/{asset['file_name']}",
        )
        self.assertGreater(asset["size"], 100 * 1024 * 1024)
        self.assertEqual(len(asset["sha256"]), 64)
        self.assertTrue(verify_update_manifest(self.manifest, self.key))

    def test_modified_version_is_rejected(self):
        self.manifest["version"] = "99.0.0"
        self.assertFalse(verify_update_manifest(self.manifest, self.key))

    def test_modified_asset_is_rejected(self):
        self.manifest["assets"] = {"portable": {"url": "https://example.invalid/bad.zip"}}
        self.assertFalse(verify_update_manifest(self.manifest, self.key))


if __name__ == "__main__":
    unittest.main()
