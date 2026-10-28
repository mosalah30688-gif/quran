#!/usr/bin/env python3
"""Fetch or verify the immutable offline tafsir asset pinned by size and SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "audit" / "offline-tafsir-data.json"
USER_AGENT = "Siraj-Quran offline-tafsir-fetcher (https://github.com/mosalah30688-gif/quran)"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def matches(path: Path, asset: dict) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == int(asset["bytes"])
        and sha256_file(path) == asset["sha256"]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    lock_path = args.lock.expanduser().resolve()
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema") != 1:
        raise SystemExit("unsupported offline tafsir lock schema")
    asset = lock["asset"]
    output = args.output.expanduser().resolve() if args.output else ROOT / lock["output"]
    if matches(output, asset):
        print(f"Verified offline tafsir data: {output} ({asset['bytes']} bytes, {asset['sha256']})")
        return 0
    if args.verify:
        raise SystemExit(f"offline tafsir data is missing or does not match its lock: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)
    request = urllib.request.Request(asset["url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response, temporary.open("wb") as target:
            if response.status != 200:
                raise RuntimeError(f"unexpected HTTP {response.status}: {asset['url']}")
            while block := response.read(1024 * 1024):
                target.write(block)
        if not matches(temporary, asset):
            raise ValueError("downloaded offline tafsir asset failed size/SHA-256 verification")
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Downloaded and verified offline tafsir data: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
