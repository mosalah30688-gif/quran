import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from nacl.signing import SigningKey

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from update_signing import verify_manifest  # noqa: E402


class PortableManifestTests(unittest.TestCase):
    def test_generator_emits_portable_asset_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "Siraj-Quran-1.0.1-windows-portable-x64.zip"
            archive.write_bytes(b"portable-test" * 100_000)
            output = root / "stable.json"
            key = SigningKey.generate()
            env = os.environ.copy()
            env["WINDOWS_UPDATE_SIGNING_SEED"] = base64.b64encode(bytes(key)).decode("ascii")
            subprocess.run(
                [
                    sys.executable,
                    str(REPO / "scripts" / "generate_windows_update_manifest.py"),
                    "--version", "1.0.1",
                    "--portable", str(archive),
                    "--base-url", "https://github.com/mosalah30688-gif/quran/releases/download/test",
                    "--output", str(output),
                ],
                check=True,
                env=env,
                capture_output=True,
                text=True,
            )
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(set(manifest["assets"]), {"portable"})
            self.assertTrue(verify_manifest(manifest, key.verify_key.encode().hex()))


if __name__ == "__main__":
    unittest.main()
