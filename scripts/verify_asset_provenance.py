#!/usr/bin/env python3
"""Verify the owner's icon declaration covers every shipped icon derivative."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "audit/icon-provenance.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discovered_paths() -> set[str]:
    paths = {
        "icon.png",
        "icon-192.png",
        "icon.svg",
        "www/icon.png",
        "www/icon-192.png",
        "mushaf_app/icon.png",
        "windows_app/assets/siraj.png",
        "windows_app/assets/siraj.ico",
    }
    paths.update(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "android/app/src/main/res").rglob("*.png")
        if path.is_file()
    )
    return paths


def main() -> int:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if value.get("schema") != 1 or not value.get("declaration") or not value.get("license_scope"):
        raise SystemExit("icon provenance declaration is incomplete")
    records = value.get("items")
    if not isinstance(records, list):
        raise SystemExit("icon provenance items must be a list")
    by_path = {}
    for item in records:
        path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(path, str) or path in by_path:
            raise SystemExit("invalid or duplicate icon provenance path")
        by_path[path] = item
    discovered = discovered_paths()
    if set(by_path) != discovered:
        raise SystemExit(
            f"icon provenance path mismatch; missing={sorted(discovered - set(by_path))}, "
            f"stale={sorted(set(by_path) - discovered)}"
        )
    for relative, item in by_path.items():
        path = ROOT / relative
        if (
            not path.is_file()
            or path.stat().st_size != item.get("bytes")
            or sha256(path) != item.get("sha256")
        ):
            raise SystemExit(f"icon provenance hash/size mismatch: {relative}")
    print(f"Verified owner provenance and hashes for {len(by_path)} icon assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
