import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from nacl.signing import SigningKey

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(SCRIPTS))

import patch_runtime  # noqa: E402
import update_security  # noqa: E402
from product_copy import validate_update_features  # noqa: E402


class ReleaseToolTests(unittest.TestCase):
    PRODUCT = "siraj-quran-linux" if APP.name == "mushaf_app" else "siraj-quran-windows"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.signing = SigningKey.generate()
        self.seed = base64.b64encode(self.signing.encode()).decode("ascii")
        self.public = self.root / "public.txt"
        self.public.write_text(self.signing.verify_key.encode().hex(), encoding="ascii")
        self.env = dict(os.environ, SIRAJ_UPDATE_SIGNING_SEED=self.seed, WINDOWS_UPDATE_SIGNING_SEED=self.seed)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, name, *arguments):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / name), *map(str, arguments)],
            cwd=ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_signed_patch_and_channel_are_accepted_by_runtime(self):
        source = self.root / "source"
        source.mkdir()
        for name in ("main.py", "version.py", "reading_tracker.py", "reminder_scheduler.py"):
            (source / name).write_text(f"# {name}\n", encoding="utf-8")
        (source / "data").mkdir()
        (source / "data" / "content.json").write_text('{"ok": true}\n', encoding="utf-8")
        patch = self.root / "Siraj-1.1.1.sirajpatch"
        self.run_tool(
            "generate_signed_patch.py",
            "--product",
            self.PRODUCT,
            "--version",
            "1.1.1",
            "--app-dir",
            source,
            "--feature",
            "صفحة «عن التطبيق» بصياغة موجزة وموحدة.",
            "--output",
            patch,
        )
        self.assertTrue(zipfile.is_zipfile(patch))
        patch_root = self.root / "installed" / "patches"
        installed = patch_runtime.install_patch_archive(
            patch,
            product=self.PRODUCT,
            runtime_api=1,
            bundled_version="1.1.0",
            public_key_path=self.public,
            patch_root=patch_root,
        )
        self.assertEqual(installed["version"], "1.1.1")
        self.assertEqual(installed["product"], self.PRODUCT)
        self.assertEqual(installed["features"], ["صفحة «عن التطبيق» بصياغة موجزة وموحدة."])
        self.assertNotIn("release_notes", installed)
        self.assertTrue((patch_root / "1.1.1" / "data" / "content.json").is_file())

        channel = self.root / "patch-stable.json"
        self.run_tool(
            "generate_patch_channel.py",
            "--product",
            self.PRODUCT,
            "--version",
            "1.1.1",
            "--patch",
            patch,
            "--base-url",
            "https://github.com/mosalah30688-gif/quran/releases/download/test",
            "--feature",
            "صفحة «عن التطبيق» بصياغة موجزة وموحدة.",
            "--output",
            channel,
        )
        manifest = json.loads(channel.read_text(encoding="utf-8"))
        self.assertTrue(update_security.verify_update_manifest(manifest, self.public))
        self.assertEqual(manifest["features"], ["صفحة «عن التطبيق» بصياغة موجزة وموحدة."])
        self.assertNotIn("release_notes", manifest)
        asset = manifest["assets"]["patch"]
        self.assertEqual(asset["size"], patch.stat().st_size)
        self.assertEqual(asset["sha256"], hashlib.sha256(patch.read_bytes()).hexdigest())

    def test_update_feature_copy_rejects_technical_or_verbose_notes(self):
        self.assertEqual(
            validate_update_features(["صفحة «عن التطبيق» بصياغة موجزة وموحدة."]),
            ["صفحة «عن التطبيق» بصياغة موجزة وموحدة."],
        )
        for value in (
            ["ترقيع صغير موقّع بتوقيع Ed25519."],
            ["ميزة " + ("طويلة " * 30)],
            ["ميزة واحدة"] * 2,
        ):
            with self.assertRaises(ValueError):
                validate_update_features(value)

    def test_full_manifest_signature_covers_complete_asset_metadata(self):
        output = self.root / "stable.json"
        base_url = "https://github.com/mosalah30688-gif/quran/releases/download/test"
        if self.PRODUCT.endswith("linux"):
            artifact = self.root / "Siraj-Quran-1.1.0-linux-x86_64.AppImage"
            artifact.write_bytes(b"A" * 1_100_000)
            self.run_tool(
                "generate_linux_update_manifest.py",
                "--version",
                "1.1.0",
                "--appimage",
                artifact,
                "--base-url",
                base_url,
                "--output",
                output,
            )
            asset_key = "appimage"
        else:
            artifact = self.root / "Siraj-Quran-1.1.0-windows-portable-x64.zip"
            artifact.write_bytes(b"Z" * 1_100_000)
            self.run_tool(
                "generate_windows_update_manifest.py",
                "--version",
                "1.1.0",
                "--portable",
                artifact,
                "--base-url",
                base_url,
                "--output",
                output,
            )
            asset_key = "portable"
        manifest = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(update_security.verify_update_manifest(manifest, self.public))
        asset = manifest["assets"][asset_key]
        self.assertEqual(asset["file_name"], artifact.name)
        self.assertEqual(asset["size"], artifact.stat().st_size)
        self.assertEqual(asset["sha256"], hashlib.sha256(artifact.read_bytes()).hexdigest())

        # Any post-signing metadata change must invalidate the whole manifest.
        asset["size"] += 1
        self.assertFalse(update_security.verify_update_manifest(manifest, self.public))

    def test_distribution_source_lock_verifier_rejects_version_drift(self):
        source_root = self.root / "distribution-source"
        package_root = source_root / "demo"
        package_root.mkdir(parents=True)
        payload = package_root / "demo_1.0.orig.tar.gz"
        payload.write_bytes(b"source")
        digest = hashlib.sha256(payload.read_bytes()).hexdigest()
        dsc = package_root / "demo_1.0-1.dsc"
        dsc.write_text(
            "Format: 3.0 (quilt)\nSource: demo\nVersion: 1.0-1\n"
            f"Checksums-Sha256:\n {digest} {payload.stat().st_size} {payload.name}\n",
            encoding="utf-8",
        )
        locks = self.root / "source-locks.txt"
        locks.write_text("demo=1.0-1\n", encoding="utf-8")
        command = [
            sys.executable, str(SCRIPTS / "verify_debian_source_locks.py"),
            "--locks", str(locks), "--source-dir", str(source_root),
        ]
        accepted = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        dsc.write_text(dsc.read_text(encoding="utf-8").replace("Version: 1.0-1", "Version: 1.0-2"), encoding="utf-8")
        rejected = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertNotEqual(rejected.returncode, 0)

    def test_patch_promotion_requires_the_published_patch_capable_baseline(self):
        promote = (ROOT / ".github" / "workflows" / "promote-release.yml").read_text(encoding="utf-8")
        self.assertIn('BASE_TAG="siraj-windows-v4.1.1"', promote)
        self.assertIn('BASE_TAG="siraj-linux-test-v4.1.1"', promote)
        self.assertNotIn('BASE_TAG="siraj-${PLATFORM}-v1.1.0"', promote)
        workflow_name = "linux-appimage.yml" if self.PRODUCT.endswith("linux") else "windows-v1.yml"
        workflow = (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
        self.assertIn("bundled_version='4.1.1'", workflow)

    def test_release_gate_requires_exact_tag_commit_and_empty_blockers(self):
        platform = "linux" if self.PRODUCT.endswith("linux") else "windows"
        tag = f"siraj-{platform}-v1.1.0"
        commit = "0123456789abcdef0123456789abcdef01234567"
        gate = self.root / "RELEASE_GATE.json"
        gate.write_text(
            json.dumps({
                "schema": 1,
                "ready": True,
                "approved_commit": commit,
                "approved_tags": [tag],
                "approved_at": "2026-10-28T00:00:00Z",
                "approved_by": "project-owner",
                "blockers": [],
            }),
            encoding="utf-8",
        )
        command = [
            sys.executable, str(SCRIPTS / "check_release_gate.py"),
            "--gate", str(gate), "--tag", tag, "--commit", commit,
        ]
        accepted = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        value = json.loads(gate.read_text(encoding="utf-8"))
        value["blockers"] = ["still blocked"]
        gate.write_text(json.dumps(value), encoding="utf-8")
        rejected = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertNotEqual(rejected.returncode, 0)
        current_closed = command.copy()
        current_closed[current_closed.index(str(gate))] = str(ROOT / "audit/RELEASE_GATE.json")
        rejected = subprocess.run(current_closed, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertNotEqual(rejected.returncode, 0)

    def test_full_candidate_verifier_checks_payload_and_corresponding_source(self):
        platform = "linux" if self.PRODUCT.endswith("linux") else "windows"
        tag = f"siraj-{platform}-v1.1.0"
        candidate = self.root / "full-candidate"
        candidate.mkdir()
        common_sources = {
            "pyside-setup-everywhere-src-6.12.0.tar.xz",
            "qtbase-everywhere-src-6.12.0.tar.xz",
            "qtsvg-everywhere-src-6.12.0.tar.xz",
        }
        linux_sources = common_sources | {
            "qtwayland-everywhere-src-6.12.0.tar.xz",
            "type2-runtime-dd6cebedcbddde9c82f89b011e8e1d40b6e43868.tar.gz",
            "fuse-3.15.0.tar.xz",
            "squashfuse-0.5.2.tar.gz",
            "zstd-1.5.6.tar.gz",
            "zlib-1.3.1.tar.gz",
            "mimalloc-2.1.7.tar.gz",
            "musl-1.2.5.tar.gz",
        }
        source = candidate / f"Siraj-Quran-1.1.0-{platform}-corresponding-source.zip"

        def write_source(tampered=False):
            members = {f"upstream/{name}": name.encode() for name in (linux_sources if platform == "linux" else common_sources)}
            if platform == "linux":
                members["debian-source/demo/demo_1.0.dsc"] = b"Source: demo\nVersion: 1.0\n"
            if tampered:
                first = sorted(members)[0]
                members[first] += b"changed"
            sums = "".join(
                f"{hashlib.sha256(data).hexdigest()}  {name}\n"
                for name, data in sorted(members.items())
            )
            if tampered:
                # Preserve the old digest for one changed member to test the inner checksum.
                changed = sorted(members)[0]
                original = changed.removeprefix("upstream/").encode()
                sums = sums.replace(hashlib.sha256(members[changed]).hexdigest(), hashlib.sha256(original).hexdigest(), 1)
            with zipfile.ZipFile(source, "w") as archive:
                for name, data in members.items():
                    archive.writestr(name, data)
                archive.writestr("SHA256SUMS.txt", sums)
                archive.writestr("README.md", "Siraj 1.1.0 corresponding source and relinking instructions\n")

        write_source()
        if platform == "windows":
            payload = candidate / "Siraj-Quran-1.1.0-windows-portable-x64.zip"
            prefix = "Siraj-Quran-1.1.0-windows-portable-x64/"
            with zipfile.ZipFile(payload, "w") as archive:
                archive.writestr(prefix + "Siraj.exe", b"MZ" + b"0" * 1_000_000)
                archive.writestr(prefix + "SirajPortableUpdater.exe", b"MZ")
                archive.writestr(prefix + "portable.flag", b"")
                archive.writestr(prefix + "LICENSE.txt", b"MIT")
                archive.writestr(prefix + "THIRD_PARTY_NOTICES.md", b"notices")
                archive.writestr(prefix + "licenses/inventory.json", b"{}")
            self.run_tool(
                "generate_windows_update_manifest.py", "--version", "1.1.0",
                "--portable", payload,
                "--base-url", f"https://github.com/mosalah30688-gif/quran/releases/download/{tag}",
                "--output", candidate / "stable.json",
            )
        else:
            payload = candidate / "Siraj-Quran-1.1.0-linux-x86_64.AppImage"
            payload.write_bytes(b"\x7fELF" + b"0" * 10_000_000)
            self.run_tool(
                "generate_linux_update_manifest.py", "--version", "1.1.0",
                "--appimage", payload,
                "--base-url", f"https://github.com/mosalah30688-gif/quran/releases/download/{tag}",
                "--output", candidate / "stable.json",
            )
        (candidate / "SBOM.cdx.json").write_text(
            '{"bomFormat":"CycloneDX","specVersion":"1.6","version":1,'
            '"components":[{"type":"library","name":"PySide6-Essentials","version":"6.12.0"}]}\n',
            encoding="utf-8",
        )

        def write_sums():
            (candidate / "SHA256SUMS.txt").write_text(
                "".join(
                    f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {item.name}\n"
                    for item in (payload, source)
                ),
                encoding="ascii",
            )

        write_sums()
        command = [
            sys.executable, str(SCRIPTS / "verify_release_candidate.py"),
            "--platform", platform, "--kind", "full", "--version", "1.1.0",
            "--tag", tag, "--repository", "mosalah30688-gif/quran",
            "--release-dir", str(candidate), "--public-key", str(self.public),
        ]
        accepted = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        write_source(tampered=True)
        write_sums()
        rejected = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertNotEqual(rejected.returncode, 0, "invalid corresponding-source inner hash was accepted")

    def test_release_candidate_verifier_checks_inner_patch_payload(self):
        platform = "linux" if self.PRODUCT.endswith("linux") else "windows"
        tag = f"siraj-{platform}-patch-v1.1.1"
        candidate = self.root / "candidate"
        source = self.root / "source"
        candidate.mkdir()
        source.mkdir()
        for name in ("main.py", "version.py", "helper.py"):
            (source / name).write_text(f"# {name}\n", encoding="utf-8")
        patch = candidate / f"Siraj-Quran-1.1.1-{platform}.sirajpatch"
        self.run_tool(
            "generate_signed_patch.py",
            "--product", self.PRODUCT,
            "--version", "1.1.1",
            "--app-dir", source,
            "--output", patch,
        )
        channel = candidate / "patch-stable.json"
        base_url = f"https://github.com/mosalah30688-gif/quran/releases/download/{tag}"

        def write_outer_files():
            self.run_tool(
                "generate_patch_channel.py",
                "--product", self.PRODUCT,
                "--version", "1.1.1",
                "--patch", patch,
                "--base-url", base_url,
                "--output", channel,
            )
            (candidate / "SBOM.cdx.json").write_text(
                '{"bomFormat":"CycloneDX","specVersion":"1.6","version":1,'
                '"components":[{"type":"library","name":"PySide6-Essentials","version":"6.12.0"}]}\n',
                encoding="utf-8",
            )
            lines = []
            for item in (patch, channel):
                lines.append(f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {item.name}\n")
            (candidate / "SHA256SUMS.txt").write_text("".join(lines), encoding="ascii")

        write_outer_files()
        command = [
            sys.executable, str(SCRIPTS / "verify_release_candidate.py"),
            "--platform", platform,
            "--kind", "patch",
            "--version", "1.1.1",
            "--tag", tag,
            "--repository", "mosalah30688-gif/quran",
            "--release-dir", str(candidate),
            "--public-key", str(self.public),
        ]
        accepted = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)

        # Re-signing only the outer channel cannot legitimize a changed inner payload.
        with zipfile.ZipFile(patch) as archive:
            members = {name: archive.read(name) for name in archive.namelist()}
        changed = next(name for name in members if name != "patch.json")
        members[changed] += b"tampered"
        with zipfile.ZipFile(patch, "w") as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        write_outer_files()
        rejected = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertNotEqual(rejected.returncode, 0, "tampered inner payload was accepted")


if __name__ == "__main__":
    unittest.main()
