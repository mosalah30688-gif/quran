import base64
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path

from nacl.signing import SigningKey

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import patch_runtime as patches  # noqa: E402


class PatchRuntimeTests(unittest.TestCase):
    PRODUCT = "siraj-quran-windows"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.signing = SigningKey.generate()
        self.public = self.root / "public.txt"
        self.public.write_text(self.signing.verify_key.encode().hex(), encoding="ascii")

    def tearDown(self):
        self.tmp.cleanup()

    def sign(self, value):
        unsigned = deepcopy(value)
        unsigned.pop("signature", None)
        canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        result = deepcopy(unsigned)
        result["signature"] = {
            "algorithm": "ed25519",
            "key_id": patches.PATCH_KEY_ID,
            "value": base64.b64encode(self.signing.sign(canonical).signature).decode(),
        }
        return result

    def make_patch(self, folder, version="1.1.1", product=None):
        folder.mkdir(parents=True)
        content = {"main.py": b"print('patched')\n", "version.py": f'APP_VERSION = "{version}"\n'.encode()}
        files = []
        for name, data in content.items():
            (folder / name).write_bytes(data)
            files.append({"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        manifest = self.sign({
            "schema": 1,
            "kind": "siraj-signed-patch",
            "product": product or self.PRODUCT,
            "version": version,
            "runtime_api": 1,
            "published_at": "2026-10-28T00:00:00Z",
            "release_notes": "test",
            "files": files,
        })
        (folder / "patch.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def validate(self, folder):
        return patches.validate_patch_dir(
            folder, product=self.PRODUCT, runtime_api=1,
            bundled_version="1.1.0", public_key_path=self.public,
        )

    def test_valid_patch_and_tamper_rejection(self):
        folder = self.root / "valid"
        self.make_patch(folder)
        self.assertIsNotNone(self.validate(folder))
        (folder / "main.py").write_text("tampered", encoding="utf-8")
        self.assertIsNone(self.validate(folder))

    def test_wrong_product_and_old_version_are_rejected(self):
        wrong = self.root / "wrong"
        self.make_patch(wrong, product="siraj-quran-linux")
        self.assertIsNone(self.validate(wrong))
        old = self.root / "old"
        self.make_patch(old, version="1.0.9")
        self.assertIsNone(self.validate(old))

    def test_finds_highest_valid_patch(self):
        root = self.root / "patches"
        self.make_patch(root / "1.1.1", "1.1.1")
        self.make_patch(root / "1.2.0", "1.2.0")
        active = patches.find_active_patch(
            product=self.PRODUCT, runtime_api=1, bundled_version="1.1.0",
            public_key_path=self.public, patch_root=root,
        )
        self.assertIsNotNone(active)
        self.assertEqual(active[1]["version"], "1.2.0")

    def test_install_archive_and_reject_zip_slip(self):
        source = self.root / "source"
        self.make_patch(source)
        archive = self.root / "ok.sirajpatch"
        with zipfile.ZipFile(archive, "w") as zf:
            for path in source.iterdir():
                zf.write(path, path.name)
        installed = patches.install_patch_archive(
            archive, product=self.PRODUCT, runtime_api=1, bundled_version="1.1.0",
            public_key_path=self.public, patch_root=self.root / "installed",
        )
        self.assertEqual(installed["version"], "1.1.1")

        bad = self.root / "bad.sirajpatch"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("../escape.py", "bad")
        with self.assertRaises(ValueError):
            patches.install_patch_archive(
                bad, product=self.PRODUCT, runtime_api=1, bundled_version="1.1.0",
                public_key_path=self.public, patch_root=self.root / "bad-install",
            )
        self.assertFalse((self.root / "escape.py").exists())


if __name__ == "__main__":
    unittest.main()
