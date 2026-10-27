import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import main as app_main  # noqa: E402


class LinuxUpdateSecurityTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "schema": 1,
            "product": "siraj-quran-linux",
            "channel": "stable",
            "available": True,
            "version": "1.0.1",
            "assets": {
                "appimage": {
                    "url": (
                        "https://github.com/mosalah30688-gif/quran/releases/download/"
                        "siraj-linux-v1.0.1/Siraj-Quran-1.0.1-linux-x86_64.AppImage"
                    ),
                    "size": 65_000_000,
                    "sha256": "a" * 64,
                }
            },
        }

    def test_accepts_well_formed_repository_asset(self):
        info = app_main.validated_update_info(self.manifest)
        self.assertIsNotNone(info)
        self.assertEqual(info["sha256"], "a" * 64)

    def test_rejects_asset_outside_repository(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["assets"]["appimage"]["url"] = "https://example.com/Siraj.AppImage"
        self.assertIsNone(app_main.validated_update_info(tampered))

    def test_rejects_invalid_hash_or_size(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["assets"]["appimage"]["sha256"] = "not-a-sha256"
        self.assertIsNone(app_main.validated_update_info(tampered))
        tampered = copy.deepcopy(self.manifest)
        tampered["assets"]["appimage"]["size"] = 10
        self.assertIsNone(app_main.validated_update_info(tampered))


if __name__ == "__main__":
    unittest.main()
