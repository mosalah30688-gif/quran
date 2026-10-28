#!/usr/bin/env python3
"""Fail closed unless downloaded Debian/Ubuntu source files match every exact lock."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_dsc(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw == "-----BEGIN PGP SIGNATURE-----":
            break
        if not raw or raw.startswith(("-----BEGIN PGP SIGNED MESSAGE-----", "Hash: ")):
            continue
        if raw[0].isspace():
            if current is not None:
                fields[current] += "\n" + raw.strip()
            continue
        if ":" not in raw:
            continue
        current, value = raw.split(":", 1)
        fields[current] = value.strip()
    return fields


def read_locks(path: Path) -> dict[str, str]:
    locks: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            raise ValueError(f"invalid lock line {number}")
        package, version = raw.split("=", 1)
        if not package or not version or package in locks or "/" in package or package in {".", ".."}:
            raise ValueError(f"invalid or duplicate lock line {number}")
        locks[package] = version
    if not locks:
        raise ValueError("source lock file is empty")
    return locks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--locks", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()

    locks = read_locks(args.locks)
    source_dir = args.source_dir.resolve(strict=True)
    actual_dirs = {path.name for path in source_dir.iterdir() if path.is_dir()}
    if actual_dirs != set(locks):
        missing = sorted(set(locks) - actual_dirs)
        extra = sorted(actual_dirs - set(locks))
        raise ValueError(f"source directory set mismatch; missing={missing}, extra={extra}")

    file_count = 0
    for package, wanted_version in sorted(locks.items()):
        directory = source_dir / package
        dsc_files = list(directory.glob("*.dsc"))
        if len(dsc_files) != 1:
            raise ValueError(f"{package}: expected exactly one .dsc, found {len(dsc_files)}")
        fields = parse_dsc(dsc_files[0])
        actual_package = fields.get("Source", "").split(" ", 1)[0]
        actual_version = fields.get("Version")
        if actual_package != package or actual_version != wanted_version:
            raise ValueError(
                f"{package}: requested {wanted_version}, downloaded {actual_package}={actual_version}"
            )
        checksums = fields.get("Checksums-Sha256", "")
        if not checksums:
            raise ValueError(f"{package}: .dsc has no Checksums-Sha256 field")
        expected_files = {dsc_files[0].name}
        for line in checksums.splitlines():
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 3:
                raise ValueError(f"{package}: malformed Checksums-Sha256 line")
            digest, size_text, name = parts
            if not SHA256_RE.fullmatch(digest) or not size_text.isdigit() or Path(name).name != name:
                raise ValueError(f"{package}: unsafe or invalid source member {name!r}")
            path = directory / name
            if not path.is_file() or path.stat().st_size != int(size_text) or sha256(path) != digest:
                raise ValueError(f"{package}: source member hash/size mismatch: {name}")
            expected_files.add(name)
        actual_files = {path.name for path in directory.iterdir() if path.is_file()}
        if actual_files != expected_files:
            raise ValueError(
                f"{package}: unexpected/missing downloaded files; expected={sorted(expected_files)}, "
                f"actual={sorted(actual_files)}"
            )
        file_count += len(actual_files)

    print(f"Verified {len(locks)} exact source locks and {file_count} source files")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"source lock verification failed: {exc}")
