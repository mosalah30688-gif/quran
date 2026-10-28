#!/usr/bin/env python3
"""يولّد قناة ترقيعات داخلية موقّعة لسراج."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from update_signing import sign_manifest


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", required=True, choices=("siraj-quran-windows", "siraj-quran-linux"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--runtime-api", type=int, default=1)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--notes", default="تحديث داخلي لسراج.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--signing-seed",
        default=os.environ.get("SIRAJ_UPDATE_SIGNING_SEED") or os.environ.get("WINDOWS_UPDATE_SIGNING_SEED", ""),
    )
    args = parser.parse_args()
    if not args.signing_seed:
        parser.error("update signing seed is required")
    if not args.patch.is_file():
        parser.error(f"missing patch: {args.patch}")
    manifest = sign_manifest({
        "schema": 1,
        "kind": "siraj-patch-channel",
        "product": args.product,
        "channel": "stable",
        "available": True,
        "version": args.version,
        "runtime_api": args.runtime_api,
        "published_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "release_notes": args.notes,
        "assets": {
            "patch": {
                "file_name": args.patch.name,
                "url": f"{args.base_url.rstrip('/')}/{args.patch.name}",
                "size": args.patch.stat().st_size,
                "sha256": sha256(args.patch),
            }
        },
    }, args.signing_seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
