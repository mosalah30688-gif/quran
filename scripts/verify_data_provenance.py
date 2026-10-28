#!/usr/bin/env python3
"""Verify every bundled JSON data file has matching locked provenance evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ("windows_app", "mushaf_app")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    expected: dict[str, str] = {}

    alquran = json.loads(
        (ROOT / "audit/sources/alquran-cloud/2026-10-28/SOURCE.json").read_text(encoding="utf-8")
    )
    for name, metadata in alquran["outputs"].items():
        expected[name] = metadata["sha256"]

    quranpedia = json.loads(
        (ROOT / "audit/sources/quranpedia/2026-10-27/SOURCE.json").read_text(encoding="utf-8")
    )
    for name, metadata in quranpedia["outputs"].items():
        expected[name] = metadata["sha256"]

    quranpedia_tafsir = json.loads(
        (ROOT / "audit/sources/quranpedia-tafsir/2026-10-28/SOURCE.json").read_text(encoding="utf-8")
    )
    for name, metadata in quranpedia_tafsir["outputs"].items():
        # New generators lock each cross-platform output by repository path;
        # older source records use only the common basename.
        expected[name] = metadata["sha256"]

    adhkar = json.loads(
        (
            ROOT
            / "audit/sources/hisn-el-muslim/872764ca013116c905f7fc9c3dc972c27cd37d4a/SOURCE.json"
        ).read_text(encoding="utf-8")
    )
    expected["adhkar.json"] = adhkar["output"]["sha256"]

    authored = json.loads(
        (ROOT / "audit/sources/project-authored-data.json").read_text(encoding="utf-8")
    )
    authored_paths = {}
    for item in authored["items"]:
        for path in item["paths"]:
            authored_paths[path] = item["sha256"]

    failures = []
    seen_paths = set()
    for app in APPS:
        for path in sorted((ROOT / app / "data").glob("*.json")):
            relative = path.relative_to(ROOT).as_posix()
            seen_paths.add(relative)
            wanted = authored_paths.get(relative) or expected.get(relative) or expected.get(path.name)
            if wanted is None:
                failures.append(f"no provenance record: {relative}")
            elif sha256(path) != wanted:
                failures.append(f"provenance hash mismatch: {relative}")
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                failures.append(f"invalid JSON {relative}: {exc}")

    stale_authored = set(authored_paths) - seen_paths
    if stale_authored:
        failures.append("stale project-authored paths: " + ", ".join(sorted(stale_authored)))

    # All shared files must be byte-for-byte identical across Windows and Linux.
    left = {path.name: path for path in (ROOT / APPS[0] / "data").glob("*.json")}
    right = {path.name: path for path in (ROOT / APPS[1] / "data").glob("*.json")}
    for name in sorted(set(left) & set(right)):
        if left[name].read_bytes() != right[name].read_bytes():
            failures.append(f"cross-platform data mismatch: {name}")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Verified provenance for {len(seen_paths)} bundled JSON files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
