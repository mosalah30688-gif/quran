#!/usr/bin/env python3
"""Generate a fully signed Linux AppImage update manifest."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path

from product_copy import validate_update_features
from update_signing import sign_manifest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--appimage", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--feature",
        action="append",
        default=[],
        help="ميزة جديدة موجزة موجهة للمستخدم؛ يمكن تكرارها حتى خمس مرات",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--signing-seed",
        default=os.environ.get("SIRAJ_UPDATE_SIGNING_SEED")
        or os.environ.get("WINDOWS_UPDATE_SIGNING_SEED", ""),
        help="Base64 Ed25519 seed supplied by GitHub Actions",
    )
    args = parser.parse_args()
    if not args.signing_seed:
        parser.error("SIRAJ_UPDATE_SIGNING_SEED or WINDOWS_UPDATE_SIGNING_SEED is required")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[.-][0-9A-Za-z.-]+)?", args.version):
        parser.error("invalid version")
    if not args.appimage.is_file() or not args.appimage.name.endswith(".AppImage"):
        parser.error(f"missing AppImage: {args.appimage}")
    manifest = sign_manifest(
        {
            "schema": 1,
            "product": "siraj-quran-linux",
            "channel": "stable",
            "available": True,
            "version": args.version,
            "published_at": dt.datetime.now(dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "minimum_linux": "Ubuntu 22.04 or equivalent x86_64",
            "features": validate_update_features(args.feature),
            "assets": {
                "appimage": {
                    "file_name": args.appimage.name,
                    "url": f"{args.base_url.rstrip('/')}/{args.appimage.name}",
                    "size": args.appimage.stat().st_size,
                    "sha256": sha256(args.appimage),
                }
            },
        },
        args.signing_seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
