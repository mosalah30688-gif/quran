#!/usr/bin/env python3
"""يولّد Manifest قناة تحديث Windows من الأصول النهائية بعد بنائها."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from update_signing import sign_manifest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def asset(path: Path, base_url: str) -> dict:
    return {
        "file_name": path.name,
        "url": f"{base_url.rstrip('/')}/{path.name}",
        "size": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument("--portable", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--notes", default="تحديث جديد لسراج على Windows.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--signing-seed",
        default=os.environ.get("WINDOWS_UPDATE_SIGNING_SEED", ""),
        help="Base64 Ed25519 seed; normally supplied through a GitHub Actions secret",
    )
    args = parser.parse_args()
    if not args.signing_seed:
        parser.error("WINDOWS_UPDATE_SIGNING_SEED is required")
    for path in (args.installer, args.portable):
        if not path.is_file():
            parser.error(f"missing artifact: {path}")
    manifest = {
        "schema": 1,
        "product": "siraj-quran-windows",
        "channel": "stable",
        "available": True,
        "version": args.version,
        "published_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "minimum_windows": "10.0.17763",
        "release_notes": args.notes,
        "assets": {
            "installer": asset(args.installer, args.base_url),
            "portable": asset(args.portable, args.base_url),
        },
    }
    manifest = sign_manifest(manifest, args.signing_seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
