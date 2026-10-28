#!/usr/bin/env python3
"""Verify a complete Siraj Draft Release before it may be promoted."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

from update_signing import verify_manifest

PLATFORMS = {
    "windows": {
        "product": "siraj-quran-windows",
        "payload_key": "portable",
        "payload": "Siraj-Quran-{version}-windows-portable-x64.zip",
        "source": "Siraj-Quran-{version}-windows-corresponding-source.zip",
    },
    "linux": {
        "product": "siraj-quran-linux",
        "payload_key": "appimage",
        "payload": "Siraj-Quran-{version}-linux-x86_64.AppImage",
        "source": "Siraj-Quran-{version}-linux-corresponding-source.zip",
    },
}
WINDOWS_SOURCE_MEMBERS = {
    "pyside-setup-everywhere-src-6.12.0.tar.xz",
    "qtbase-everywhere-src-6.12.0.tar.xz",
    "qtsvg-everywhere-src-6.12.0.tar.xz",
}
LINUX_SOURCE_MEMBERS = WINDOWS_SOURCE_MEMBERS | {
    "qtwayland-everywhere-src-6.12.0.tar.xz",
    "type2-runtime-dd6cebedcbddde9c82f89b011e8e1d40b6e43868.tar.gz",
    "fuse-3.15.0.tar.xz",
    "squashfuse-0.5.2.tar.gz",
    "zstd-1.5.6.tar.gz",
    "zlib-1.3.1.tar.gz",
    "mimalloc-2.1.7.tar.gz",
    "musl-1.2.5.tar.gz",
}
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[A-Za-z0-9.+-]*)?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def safe_patch_name(value: object) -> str | None:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} or not SAFE_NAME_RE.fullmatch(part) for part in path.parts):
        return None
    return path.as_posix()


def safe_archive_name(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(
        value
        and not value.startswith(("/", "\\"))
        and not path.is_absolute()
        and all(
            part not in {"", ".", ".."}
            and "\\" not in part
            and not any(ord(character) < 32 for character in part)
            for part in path.parts
        )
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_zip_member(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_sums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._+-]*)", raw)
        if not match:
            raise ValueError(f"invalid SHA256SUMS line {number}")
        digest, name = match.groups()
        if name in result:
            raise ValueError(f"duplicate SHA256SUMS entry: {name}")
        result[name] = digest
    return result


def checked_zip_infos(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    names = [item.filename for item in infos]
    if len(names) != len(set(names)):
        raise ValueError("ZIP archive contains duplicate members")
    result = {}
    logical_names = set()
    for item in infos:
        logical_name = item.filename.rstrip("/")
        if logical_name in logical_names:
            raise ValueError(f"ZIP file/directory name collision: {logical_name}")
        logical_names.add(logical_name)
        if not safe_archive_name(logical_name):
            raise ValueError(f"unsafe ZIP member: {item.filename!r}")
        mode = (item.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise ValueError(f"ZIP symlink is forbidden: {item.filename}")
        if item.is_dir():
            continue
        result[item.filename] = item
    return result


def verify_corresponding_source(path: Path, platform: str, version: str) -> None:
    with zipfile.ZipFile(path) as archive:
        infos = checked_zip_infos(archive)
        if "README.md" not in infos or "SHA256SUMS.txt" not in infos:
            raise ValueError("corresponding-source ZIP lacks README or SHA256SUMS")
        readme = archive.read("README.md").decode("utf-8")
        if version not in readme or "relink" not in readme.lower():
            raise ValueError("corresponding-source README lacks version/relinking instructions")
        sums: dict[str, str] = {}
        for number, raw in enumerate(archive.read("SHA256SUMS.txt").decode("utf-8").splitlines(), 1):
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
            if not match or not safe_archive_name(match.group(2)):
                raise ValueError(f"invalid corresponding-source checksum line {number}")
            digest, name = match.groups()
            if name in sums:
                raise ValueError(f"duplicate corresponding-source checksum: {name}")
            sums[name] = digest
        payload_names = set(infos) - {"README.md", "SHA256SUMS.txt"}
        if set(sums) != payload_names:
            raise ValueError("corresponding-source checksums do not cover the exact payload")
        for name, digest in sums.items():
            if sha256_zip_member(archive, name) != digest:
                raise ValueError(f"corresponding-source member hash mismatch: {name}")
        expected_upstream = LINUX_SOURCE_MEMBERS if platform == "linux" else WINDOWS_SOURCE_MEMBERS
        actual_upstream = {
            name.removeprefix("upstream/") for name in payload_names if name.startswith("upstream/")
        }
        if actual_upstream != expected_upstream:
            raise ValueError("corresponding-source upstream archive set is incomplete or unexpected")
        debian = [name for name in payload_names if name.startswith("debian-source/")]
        if platform == "linux":
            if not debian or not any(name.endswith(".dsc") for name in debian):
                raise ValueError("Linux corresponding source lacks exact distribution source packages")
        elif debian:
            raise ValueError("Windows corresponding source unexpectedly contains distribution sources")


def verify_windows_portable(path: Path, version: str) -> None:
    with zipfile.ZipFile(path) as archive:
        infos = checked_zip_infos(archive)
        prefix = f"Siraj-Quran-{version}-windows-portable-x64/"
        if not infos or any(not name.startswith(prefix) for name in infos):
            raise ValueError("Windows Portable ZIP has an unexpected root directory")
        relatives = {name.removeprefix(prefix) for name in infos}
        required = {
            "Siraj.exe",
            "SirajPortableUpdater.exe",
            "portable.flag",
            "LICENSE.txt",
            "THIRD_PARTY_NOTICES.md",
            "licenses/inventory.json",
        }
        if not required.issubset(relatives):
            raise ValueError("Windows Portable ZIP lacks executable, marker, notices, or licenses")
        if any(name == "UserData" or name.startswith("UserData/") for name in relatives):
            raise ValueError("Windows Portable ZIP contains test/user data")
        if infos[prefix + "Siraj.exe"].file_size < 1_000_000:
            raise ValueError("Windows executable is implausibly small")


def verify_linux_appimage(path: Path) -> None:
    with path.open("rb") as stream:
        magic = stream.read(4)
    if path.stat().st_size < 10_000_000 or magic != b"\x7fELF":
        raise ValueError("Linux AppImage is not a plausible ELF payload")


def verify_patch_archive(path: Path, outer: dict, public_key: str) -> None:
    """Mirror the immutable runtime's archive contract before publication."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "patch.json" not in names:
            raise ValueError("patch archive has duplicate entries or no patch.json")
        inner = json.loads(archive.read("patch.json"))
        if not verify_manifest(inner, public_key):
            raise ValueError("patch archive manifest signature is invalid")
        for key in ("product", "version", "runtime_api"):
            if inner.get(key) != outer.get(key):
                raise ValueError(f"patch inner/outer {key} mismatch")
        if inner.get("schema") != 1 or inner.get("kind") != "siraj-signed-patch":
            raise ValueError("invalid signed patch metadata")
        files = inner.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("patch contains no files")
        expected_names = {"patch.json"}
        for item in files:
            name = safe_patch_name(item.get("path") if isinstance(item, dict) else None)
            if name is None or name in expected_names:
                raise ValueError("unsafe or duplicate patch payload path")
            expected_names.add(name)
            try:
                data = archive.read(name)
            except KeyError as exc:
                raise ValueError(f"missing patch payload: {name}") from exc
            if len(data) != item.get("size") or hashlib.sha256(data).hexdigest() != item.get("sha256"):
                raise ValueError(f"invalid patch payload: {name}")
        if set(names) != expected_names:
            raise ValueError("patch archive contains unexpected members")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    parser.add_argument("--kind", choices=("full", "patch"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()

    if not VERSION_RE.fullmatch(args.version):
        parser.error("invalid release version")
    expected_tag = f"siraj-{args.platform}-{'patch-' if args.kind == 'patch' else ''}v{args.version}"
    if args.tag != expected_tag:
        parser.error(f"tag must be {expected_tag}")

    config = PLATFORMS[args.platform]
    manifest_name = "patch-stable.json" if args.kind == "patch" else "stable.json"
    manifest_path = args.release_dir / manifest_name
    public_key = args.public_key.read_text(encoding="ascii").strip()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not verify_manifest(manifest, public_key):
        raise ValueError("channel manifest signature is invalid")
    expected_top = {
        "schema": 1,
        "product": config["product"],
        "channel": "stable",
        "available": True,
        "version": args.version,
    }
    for key, expected in expected_top.items():
        if manifest.get(key) != expected:
            raise ValueError(f"unexpected manifest {key}: {manifest.get(key)!r}")

    if args.kind == "patch":
        if manifest.get("kind") != "siraj-patch-channel" or manifest.get("runtime_api") != 1:
            raise ValueError("invalid patch channel metadata")
        asset_key = "patch"
        payload_name = f"Siraj-Quran-{args.version}-{args.platform}.sirajpatch"
        expected_names = {payload_name, manifest_name, "SHA256SUMS.txt", "SBOM.cdx.json"}
    else:
        asset_key = config["payload_key"]
        payload_name = config["payload"].format(version=args.version)
        source_name = config["source"].format(version=args.version)
        expected_names = {payload_name, source_name, manifest_name, "SHA256SUMS.txt", "SBOM.cdx.json"}

    actual_names = {path.name for path in args.release_dir.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise ValueError(f"unexpected release assets: expected {sorted(expected_names)}, got {sorted(actual_names)}")

    asset = manifest.get("assets", {}).get(asset_key)
    if not isinstance(asset, dict) or asset.get("file_name") != payload_name:
        raise ValueError("manifest payload metadata is missing or names the wrong file")
    payload = args.release_dir / payload_name
    if asset.get("size") != payload.stat().st_size or asset.get("sha256") != sha256_file(payload):
        raise ValueError("manifest payload size or SHA-256 mismatch")
    expected_url = f"https://github.com/{args.repository}/releases/download/{args.tag}/{payload_name}"
    if asset.get("url") != expected_url:
        raise ValueError("manifest payload URL is not the exact release asset URL")

    sums = read_sums(args.release_dir / "SHA256SUMS.txt")
    required_sums = {payload_name}
    if args.kind == "full":
        required_sums.add(source_name)
    if not required_sums.issubset(sums):
        raise ValueError("SHA256SUMS is missing required assets")
    for name, digest in sums.items():
        file_path = args.release_dir / name
        if name not in expected_names or not file_path.is_file() or sha256_file(file_path) != digest:
            raise ValueError(f"SHA256SUMS mismatch or unknown asset: {name}")

    sbom = json.loads((args.release_dir / "SBOM.cdx.json").read_text(encoding="utf-8"))
    if (
        sbom.get("bomFormat") != "CycloneDX"
        or not re.fullmatch(r"1\.[4-9]", str(sbom.get("specVersion", "")))
        or not isinstance(sbom.get("version"), int)
        or sbom["version"] < 1
        or not isinstance(sbom.get("components"), list)
        or not sbom["components"]
    ):
        raise ValueError("invalid or empty CycloneDX SBOM")
    if args.kind == "patch":
        verify_patch_archive(payload, manifest, public_key)
    else:
        verify_corresponding_source(args.release_dir / source_name, args.platform, args.version)
        if args.platform == "windows":
            verify_windows_portable(payload, args.version)
        else:
            verify_linux_appimage(payload)

    print(f"Verified {args.platform} {args.kind} release {args.version}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"release verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
