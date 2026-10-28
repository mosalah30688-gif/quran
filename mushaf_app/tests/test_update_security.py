import base64
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from nacl.signing import SigningKey

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import main as app_main  # noqa: E402
from update_security import canonical_manifest_bytes  # noqa: E402


class LinuxUpdateSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.signing = SigningKey.generate()
        self.public = Path(self.temp.name) / "public.txt"
        self.public.write_text(self.signing.verify_key.encode().hex(), encoding="ascii")
        self.old_public = app_main.UPDATE_PUBLIC_KEY
        app_main.UPDATE_PUBLIC_KEY = self.public
        self.manifest = {
            "schema": 1,
            "product": "siraj-quran-linux",
            "channel": "stable",
            "available": True,
            "version": "1.1.1",
            "assets": {
                "appimage": {
                    "url": (
                        "https://github.com/mosalah30688-gif/quran/releases/download/"
                        "siraj-linux-v1.1.1/Siraj-Quran-1.1.1-linux-x86_64.AppImage"
                    ),
                    "size": 65_000_000,
                    "sha256": "a" * 64,
                }
            },
        }
        raw = self.signing.sign(canonical_manifest_bytes(self.manifest)).signature
        self.manifest["signature"] = {
            "algorithm": "ed25519",
            "key_id": "siraj-update-2026-01",
            "value": base64.b64encode(raw).decode("ascii"),
        }

    def tearDown(self):
        app_main.UPDATE_PUBLIC_KEY = self.old_public
        self.temp.cleanup()

    def test_accepts_signed_repository_asset(self):
        info = app_main.validated_update_info(self.manifest)
        self.assertIsNotNone(info)
        self.assertEqual(info["sha256"], "a" * 64)

    def test_rejects_asset_outside_repository(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["assets"]["appimage"]["url"] = "https://example.com/Siraj.AppImage"
        self.assertIsNone(app_main.validated_update_info(tampered))

    def test_rejects_invalid_hash_size_or_signature(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["assets"]["appimage"]["sha256"] = "not-a-sha256"
        self.assertIsNone(app_main.validated_update_info(tampered))
        tampered = copy.deepcopy(self.manifest)
        tampered["assets"]["appimage"]["size"] = 10
        self.assertIsNone(app_main.validated_update_info(tampered))
        tampered = copy.deepcopy(self.manifest)
        tampered["signature"]["value"] = base64.b64encode(b"x" * 64).decode("ascii")
        self.assertIsNone(app_main.validated_update_info(tampered))


if __name__ == "__main__":
    unittest.main()
