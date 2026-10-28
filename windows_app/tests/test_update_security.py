import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

from update_security import verify_update_manifest  # noqa: E402


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

    def test_modified_version_is_rejected(self):
        self.manifest["version"] = "99.0.0"
        self.assertFalse(verify_update_manifest(self.manifest, self.key))

    def test_modified_asset_is_rejected(self):
        self.manifest["assets"] = {"portable": {"url": "https://example.invalid/bad.zip"}}
        self.assertFalse(verify_update_manifest(self.manifest, self.key))


if __name__ == "__main__":
    unittest.main()
