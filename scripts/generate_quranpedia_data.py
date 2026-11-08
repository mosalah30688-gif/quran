#!/usr/bin/env python3
"""Rebuild local Quranpedia subsets from official, versioned dump files."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://quranpedia.net/dumps"
SOURCE_DIR = ROOT / "audit" / "sources" / "quranpedia" / "2026-10-27"
FILES = ("meanings.json.gz", "mushafs-4.json.gz", "mushafs-7.json.gz", "mushafs-6.json.gz")
MUSHAFS = {"warsh": 4, "qalun": 7, "duri": 6}
# لقطة لاحقة للروايات الأربع المضافة (البزي، قنبل، شعبة، السوسي): النسخة الأصلية
# لا تحتوي عليها، ونصوص الروايات الثلاث المعتمدة تبقى كما هي بلا أي تغيير.
EXTRA_SOURCE_DIR = ROOT / "audit" / "sources" / "quranpedia" / "2026-11-08"
EXTRA_FILES = ("mushafs-5.json.gz", "mushafs-8.json.gz", "mushafs-9.json.gz", "mushafs-10.json.gz")
EXTRA_MUSHAFS = {"bazzi": 5, "qunbul": 8, "shubah": 9, "susi": 10}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(name: str, timeout: int) -> bytes:
    request = urllib.request.Request(
        f"{BASE_URL}/{name}",
        headers={
            "User-Agent": "Siraj-Quran/1.1 source audit (https://github.com/mosalah30688-gif/quran)"
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status} for {request.full_url}")
        return response.read()


def read_gzip_json(path: Path) -> dict:
    import gzip

    return json.loads(gzip.decompress(path.read_bytes()))


def compact(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def validate_license(envelope: dict, expected_schema: str) -> dict:
    if envelope.get("schema") != expected_schema:
        raise ValueError(f"unexpected Quranpedia schema: {envelope.get('schema')!r}")
    license_data = envelope.get("license")
    if not isinstance(license_data, dict) or license_data.get("source") != "https://quranpedia.net":
        raise ValueError("Quranpedia source/license metadata is absent")
    if not license_data.get("version") or not license_data.get("ar") or not license_data.get("en"):
        raise ValueError("Quranpedia license metadata is incomplete")
    return license_data


def build(source_dir: Path) -> tuple[dict[str, bytes], dict]:
    manifest_raw = (source_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest.get("source") != "https://quranpedia.net" or not manifest.get("version"):
        raise ValueError("invalid Quranpedia dump manifest")
    index = {item["name"]: item for item in manifest.get("files", [])}
    evidence = {}
    envelopes = {}
    for name in FILES:
        raw = (source_dir / name).read_bytes()
        listed = index.get(name)
        if not listed or listed.get("sha256") != sha256(raw) or listed.get("bytes") != len(raw):
            raise ValueError(f"official manifest hash/size mismatch: {name}")
        envelopes[name] = read_gzip_json(source_dir / name)
        evidence[name] = {
            "url": f"{BASE_URL}/{name}",
            "bytes": len(raw),
            "sha256": sha256(raw),
            "built_at": listed.get("built_at"),
        }

    meanings_envelope = envelopes["meanings.json.gz"]
    meanings_license = validate_license(meanings_envelope, "/v1/ayah/{surah}/{ayah}/meanings")
    ayahs = {}
    for row in meanings_envelope.get("data", []):
        key = f"{int(row['surah'])}:{int(row['ayah'])}"
        if key in ayahs:
            raise ValueError(f"duplicate meanings reference: {key}")
        ayahs[key] = [
            [
                item["book_info"]["name"],
                [[word["text"], word["meaning"]] for word in item.get("words", [])],
            ]
            for item in row.get("meanings", [])
        ]
    if len(ayahs) != 4799:
        raise ValueError(f"expected 4799 ayahs with word meanings, got {len(ayahs)}")

    riwayat = {}
    riwayat_licenses = []
    for key, mushaf_id in MUSHAFS.items():
        name = f"mushafs-{mushaf_id}.json.gz"
        envelope = envelopes[name]
        license_data = validate_license(envelope, f"/v1/mushafs/{mushaf_id}")
        riwayat_licenses.append(license_data)
        data = envelope.get("data", {})
        if data.get("id") != mushaf_id or len(data.get("surahs", [])) != 114:
            raise ValueError(f"incomplete or wrong Quranpedia mushaf: {name}")
        rows = []
        seen = set()
        for surah in data["surahs"]:
            surah_number = int(surah["id"])
            for ayah in surah.get("ayahs", []):
                ref = (surah_number, int(ayah["number"]))
                if ref in seen:
                    raise ValueError(f"duplicate {key} ayah reference: {ref}")
                seen.add(ref)
                rows.append([ref[0], ref[1], int(ayah["page_number"]), ayah["text"]])
        if not rows or any(page < 1 or page > 604 for _s, _a, page, _text in rows):
            raise ValueError(f"invalid pages or no ayahs in {name}")
        riwayat[key] = rows

    extra_evidence = {}
    extra_riwayat = {}
    extra_versions = set()
    extra_manifest_raw = (EXTRA_SOURCE_DIR / "manifest.json").read_bytes()
    extra_manifest = json.loads(extra_manifest_raw)
    if extra_manifest.get("source") != "https://quranpedia.net" or not extra_manifest.get("version"):
        raise ValueError("invalid Quranpedia extra dump manifest")
    extra_index = {item["name"]: item for item in extra_manifest.get("files", [])}
    for key, mushaf_id in EXTRA_MUSHAFS.items():
        name = f"mushafs-{mushaf_id}.json.gz"
        raw = (EXTRA_SOURCE_DIR / name).read_bytes()
        listed = extra_index.get(name)
        if not listed or listed.get("sha256") != sha256(raw) or listed.get("bytes") != len(raw):
            raise ValueError(f"official extra manifest hash/size mismatch: {name}")
        envelope = read_gzip_json(EXTRA_SOURCE_DIR / name)
        license_data = validate_license(envelope, f"/v1/mushafs/{mushaf_id}")
        extra_versions.add(license_data["version"])
        data = envelope.get("data", {})
        if data.get("id") != mushaf_id or len(data.get("surahs", [])) != 114:
            raise ValueError(f"incomplete or wrong Quranpedia extra mushaf: {name}")
        rows = []
        seen = set()
        for surah in data["surahs"]:
            surah_number = int(surah["id"])
            for ayah in surah.get("ayahs", []):
                ref = (surah_number, int(ayah["number"]))
                if ref in seen:
                    raise ValueError(f"duplicate {key} ayah reference: {ref}")
                seen.add(ref)
                rows.append([ref[0], ref[1], int(ayah["page_number"]), ayah["text"]])
        if not rows or any(page < 1 or page > 604 for _s, _a, page, _text in rows):
            raise ValueError(f"invalid pages or no ayahs in {name}")
        extra_riwayat[key] = rows
        extra_evidence[name] = {
            "url": f"{BASE_URL}/{name}",
            "bytes": len(raw),
            "sha256": sha256(raw),
            "built_at": listed.get("built_at"),
            "manifest_version": extra_manifest["version"],
        }
    if len(extra_versions) != 1:
        raise ValueError("Quranpedia extra mushaf dump versions are inconsistent")
    extra_version = extra_versions.pop()
    riwayat.update(extra_riwayat)

    expected_counts = {"warsh": 6214, "qalun": 6214, "duri": 6218,
                       "bazzi": 6220, "qunbul": 6221, "shubah": 6236, "susi": 6218}
    if {key: len(value) for key, value in riwayat.items()} != expected_counts:
        raise ValueError("Quranpedia riwayat ayah counts changed unexpectedly")
    versions = {item["version"] for item in riwayat_licenses}
    if len(versions) != 1:
        raise ValueError("Quranpedia mushaf dump versions are inconsistent")
    riwayat_version = versions.pop()

    license_notice = {
        "source": "https://quranpedia.net",
        "policy": "https://quranpedia.net/api-docs#usage-policy",
        "license_file": f"{BASE_URL}/LICENSE.md",
        "notice": "يجوز الاستعمال داخل التطبيقات؛ وعند نشر ملف البيانات يلزم ذكر الموسوعة القرآنية quranpedia.net ورقم النسخة.",
    }
    outputs = {
        "quran-meanings.json": compact(
            {
                "v": 1,
                "source": "الموسوعة القرآنية quranpedia.net",
                "source_url": "https://quranpedia.net",
                "version": meanings_license["version"],
                "license": license_notice,
                "source_files": {"meanings.json.gz": evidence["meanings.json.gz"]["sha256"]},
                "generated_by": "scripts/generate_quranpedia_data.py",
                "ayahs": ayahs,
            }
        ),
        "quran-riwayat.json": compact(
            {
                "v": 1,
                "source": "الموسوعة القرآنية quranpedia.net",
                "source_url": "https://quranpedia.net",
                "version": riwayat_version,
                "additional_source_version": extra_version,
                "license": license_notice,
                "source_files": {
                    name: evidence[name]["sha256"] for name in FILES if name.startswith("mushafs-")
                },
                "additional_source_files": {
                    name: item["sha256"] for name, item in extra_evidence.items()
                },
                "generated_by": "scripts/generate_quranpedia_data.py",
                "riwayat": riwayat,
            }
        ),
    }
    source_record = {
        "schema": 1,
        "dump_version": manifest["version"],
        "generated_at": manifest.get("generated_at"),
        "manifest_url": f"{BASE_URL}/manifest.json",
        "manifest_bytes": len(manifest_raw),
        "manifest_sha256": sha256(manifest_raw),
        "license_url": f"{BASE_URL}/LICENSE.md",
        "files": evidence,
        "additional_files": extra_evidence,
        "additional_manifest": {
            "url": f"{BASE_URL}/manifest.json",
            "version": extra_manifest["version"],
            "bytes": len(extra_manifest_raw),
            "sha256": sha256(extra_manifest_raw),
        },
        "transformation": {
            "script": "scripts/generate_quranpedia_data.py",
            "description": "Select word/book pairs from the official meanings service dump and flatten official mushafs 4 (Warsh), 7 (Qalun), and 6 (Duri) while preserving their numbering, page, and text; the added riwayat (5 Bazzi, 8 Qunbul, 9 Shubah, 10 Susi) come from the later 2026-11-08 dump without altering the three pinned riwayat.",
        },
        "outputs": {
            name: {"bytes": len(content), "sha256": sha256(content)}
            for name, content in outputs.items()
        },
    }
    return outputs, source_record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    source_dir.mkdir(parents=True, exist_ok=True)

    if args.refresh:
        manifest_raw = fetch("manifest.json", args.timeout)
        manifest = json.loads(manifest_raw)
        if manifest.get("version") != "2026-10-27":
            raise SystemExit(f"refusing to overwrite dated evidence with dump {manifest.get('version')!r}")
        index = {item["name"]: item for item in manifest.get("files", [])}
        downloaded = {"manifest.json": manifest_raw, "LICENSE.md": fetch("LICENSE.md", args.timeout)}
        for name in FILES:
            raw = fetch(name, args.timeout)
            expected = index.get(name, {})
            if expected.get("sha256") != sha256(raw) or expected.get("bytes") != len(raw):
                raise SystemExit(f"downloaded file does not match official manifest: {name}")
            downloaded[name] = raw
        for name, raw in downloaded.items():
            (source_dir / name).write_bytes(raw)

    outputs, source_record = build(source_dir)
    mismatches = []
    for name, content in outputs.items():
        for app in ("windows_app", "mushaf_app"):
            path = ROOT / app / "data" / name
            if args.verify:
                if not path.is_file() or path.read_bytes() != content:
                    mismatches.append(path.relative_to(ROOT).as_posix())
            else:
                path.write_bytes(content)
    source_path = source_dir / "SOURCE.json"
    if args.verify and mismatches:
        raise SystemExit("generated data mismatch: " + ", ".join(mismatches))
    if not args.verify:
        source_path.write_text(json.dumps(source_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified official Quranpedia meanings and seven riwayat dumps")
    print(source_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
