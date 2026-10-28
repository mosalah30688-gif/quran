#!/usr/bin/env python3
"""Rebuild and verify bundled Hafs/metadata files from locked AlQuran Cloud responses."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = "https://api.alquran.cloud/v1/quran"
EDITIONS = ("quran-uthmani", "quran-simple", "quran-simple-clean", "quran-tajweed")
DEFAULT_SOURCE_DIR = ROOT / "audit" / "sources" / "alquran-cloud" / "2026-10-28"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: object, *, compact: bool) -> bytes:
    options = {"ensure_ascii": False}
    if compact:
        options["separators"] = (",", ":")
    return json.dumps(value, **options).encode("utf-8")


def fetch(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Siraj-Quran-source-audit/1.1 (+https://github.com/mosalah30688-gif/quran)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200 or response.headers.get_content_type() != "application/json":
            raise RuntimeError(f"unexpected response for {url}: {response.status} {response.headers.get_content_type()}")
        return response.read()


def load_editions(source_dir: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    editions: dict[str, dict] = {}
    evidence: dict[str, dict] = {}
    for edition in EDITIONS:
        path = source_dir / f"{edition}.json.gz"
        compressed = path.read_bytes()
        raw = gzip.decompress(compressed)
        envelope = json.loads(raw)
        if envelope.get("code") != 200 or envelope.get("status") != "OK":
            raise ValueError(f"invalid locked API envelope: {path}")
        data = envelope.get("data")
        metadata = data.get("edition", {}) if isinstance(data, dict) else {}
        if metadata.get("identifier") != edition or metadata.get("language") != "ar":
            raise ValueError(f"locked edition identity mismatch: {path}")
        editions[edition] = data
        evidence[edition] = {
            "url": f"{API_ROOT}/{edition}",
            "snapshot": path.relative_to(ROOT).as_posix(),
            "response_bytes": len(raw),
            "response_sha256": sha256(raw),
            "snapshot_bytes": len(compressed),
            "snapshot_sha256": sha256(compressed),
            "compression": "gzip (mtime=0)",
            "edition": metadata,
        }
    return editions, evidence


def flattened(data: dict, *, strip_bom: bool = False) -> list[list]:
    rows = []
    for surah in data["surahs"]:
        for ayah in surah["ayahs"]:
            text = ayah["text"]
            if strip_bom:
                text = text.lstrip("\ufeff")
            rows.append([surah["number"], ayah["numberInSurah"], ayah["page"], text])
    return rows


def build_outputs(editions: dict[str, dict]) -> dict[str, bytes]:
    uthmani = flattened(editions["quran-uthmani"])
    simple = flattened(editions["quran-simple"])
    clean = flattened(editions["quran-simple-clean"], strip_bom=True)
    tajweed = flattened(editions["quran-tajweed"])
    if not all(len(rows) == 6236 for rows in (uthmani, simple, clean, tajweed)):
        raise ValueError("an edition does not contain exactly 6236 ayahs")
    refs = [[row[0], row[1]] for row in uthmani]
    if refs != [[row[0], row[1]] for row in simple] or refs != [[row[0], row[1]] for row in clean]:
        raise ValueError("edition ayah references are not identical")

    source_surahs = editions["quran-uthmani"]["surahs"]
    if len(source_surahs) != 114 or [item["number"] for item in source_surahs] != list(range(1, 115)):
        raise ValueError("source does not contain the ordered 114 surahs")
    surahs = [
        {
            "number": item["number"],
            "name": item["name"],
            "englishName": item["englishName"],
            "numberOfAyahs": len(item["ayahs"]),
            "revelationType": item["revelationType"],
        }
        for item in source_surahs
    ]
    juz = []
    seen_juz: set[int] = set()
    for item in source_surahs:
        for ayah in item["ayahs"]:
            number = int(ayah["juz"])
            if number not in seen_juz:
                seen_juz.add(number)
                juz.append([item["number"], ayah["numberInSurah"]])
    if len(juz) != 30 or seen_juz != set(range(1, 31)):
        raise ValueError("source does not contain all 30 ordered juz boundaries")

    return {
        "hafs.json": encode({"uthmani": uthmani, "simple": simple}, compact=False),
        "quran-search.json": encode(
            {
                "v": 1,
                "source": "alquran.cloud quran-simple-clean",
                "ayahs": [[row[0], row[1], row[3]] for row in clean],
            },
            compact=True,
        ),
        "quran-tajweed.json": encode(tajweed, compact=True),
        "surahs.json": encode(surahs, compact=False),
        "juz.json": encode(juz, compact=False),
    }


def targets(name: str) -> list[Path]:
    if name == "quran-tajweed.json":
        return [ROOT / "windows_app" / "data" / name]
    return [ROOT / app / "data" / name for app in ("windows_app", "mushaf_app")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--refresh", action="store_true", help="Download and replace locked upstream responses")
    parser.add_argument("--verify", action="store_true", help="Compare generated bytes without changing app data")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    source_dir.mkdir(parents=True, exist_ok=True)

    if args.refresh:
        for edition in EDITIONS:
            raw = fetch(f"{API_ROOT}/{edition}", args.timeout)
            # Parse before replacing evidence with a malformed response.
            json.loads(raw)
            (source_dir / f"{edition}.json.gz").write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))

    editions, evidence = load_editions(source_dir)
    outputs = build_outputs(editions)
    mismatches = []
    for name, content in outputs.items():
        for path in targets(name):
            if args.verify:
                if not path.is_file() or path.read_bytes() != content:
                    mismatches.append(path.relative_to(ROOT).as_posix())
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

    manifest_path = source_dir / "SOURCE.json"
    retrieved_at = None
    if manifest_path.is_file() and not args.refresh:
        try:
            retrieved_at = json.loads(manifest_path.read_text(encoding="utf-8")).get("retrieved_at")
        except (OSError, json.JSONDecodeError):
            retrieved_at = None
    if not retrieved_at:
        retrieved_at = (
            dt.datetime.now(dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    manifest = {
        "schema": 1,
        "retrieved_at": retrieved_at,
        "provider": "AlQuran Cloud / Islamic Network",
        "terms": "https://alquran.cloud/terms-and-conditions",
        "cdn_documentation": "https://alquran.cloud/cdn",
        "sources": evidence,
        "transformation": {
            "script": "scripts/generate_alquran_data.py",
            "description": "Flatten ordered surah/ayah API data, retain page metadata, strip only the leading BOM in quran-simple-clean search text, and derive surah and juz indexes.",
        },
        "outputs": {
            name: {"bytes": len(content), "sha256": sha256(content)}
            for name, content in outputs.items()
        },
    }
    if not args.verify:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif mismatches:
        raise SystemExit("generated data mismatch: " + ", ".join(mismatches))

    print(f"Verified {len(outputs)} generated files from {len(editions)} locked editions")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
