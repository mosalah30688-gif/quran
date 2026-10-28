#!/usr/bin/env python3
"""Build Siraj's licensed classical-tafsir catalog from a locked Quranpedia dump.

The catalog controls the visible rights-audited selection. Full text is built
separately by ``build_offline_tafsir.py`` from the official per-book dumps.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://quranpedia.net/dumps"
SOURCE_DIR = ROOT / "audit" / "sources" / "quranpedia-tafsir" / "2026-10-28"
OUTPUTS = (
    ROOT / "mushaf_app" / "data" / "tafsir-catalog.json",
    ROOT / "windows_app" / "data" / "tafsir-catalog.json",
)
SOURCE_NAME = "tafsir.json.gz"
MAX_CLASSICAL_DEATH_YEAR = 1350

# These four works are already exposed through the separately audited AlQuran
# Cloud catalog. Keeping one visible entry per work avoids a confusing duplicate.
ALQURAN_EQUIVALENT_IDS = {2, 261, 272, 363}

# Quranpedia contains multiple digitizations/editions for a few works. The
# preferred ID is retained and the alternate ID below is omitted from the UI.
DUPLICATE_EDITION_IDS = {
    351,     # معاني القرآن للفراء -> qp:27768 has broader ayah coverage
    27769,   # مجاز القرآن -> qp:348
    295,     # تفسير ابن المنذر -> qp:27772
    542,     # النكت والعيون -> qp:1470 has complete ayah coverage
    347,     # تفسير القشيري -> qp:27777 (لطائف الإشارات)
    27783,   # التفسير القيم -> qp:332; both are later compilations, both omitted below
    332,     # later compilation from Ibn al-Qayyim's words, not an authored classical edition
    331,     # تفسير ابن كثير -> qp:136, documented multi-part edition
    27756,   # كشف التنزيل -> qp:1239
    6,       # تفسير ابن عرفة -> qp:555
    273,     # الدر المنثور -> qp:1499 with complete ayah coverage
    206,     # البحر المديد -> qp:27789 with broader coverage
    284,     # التفسير المظهري -> qp:27788 with broader coverage
}
EXCLUDED_TITLE_PREFIXES = ("جهود ", "آراء ")
EXPECTED_AYAH_ROWS = 6236
EXPECTED_SOURCE_BOOKS = 149
EXPECTED_SELECTED_BOOKS = 73


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compact(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


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


def _envelope_prefix(stream) -> tuple[str, str]:
    """Read only through the opening of the top-level data array."""
    buffer = ""
    marker = '"data":['
    while marker not in buffer:
        chunk = stream.read(65_536)
        if not chunk:
            raise ValueError("Quranpedia tafsir dump has no data array")
        buffer += chunk
        if len(buffer) > 2_000_000:
            raise ValueError("Quranpedia tafsir envelope header is unexpectedly large")
    return buffer.split(marker, 1)


def _header_value(prefix: str, field: str):
    marker = f'"{field}":'
    start = prefix.find(marker)
    if start < 0:
        raise ValueError(f"Quranpedia tafsir envelope has no {field!r}")
    value, _end = json.JSONDecoder().raw_decode(prefix, start + len(marker))
    return value


def read_tafsir_header(path: Path) -> tuple[dict, str]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        prefix, _tail = _envelope_prefix(stream)
    return _header_value(prefix, "license"), _header_value(prefix, "schema")


def iter_tafsir_rows(path: Path):
    """Yield one ayah row at a time; the compact dump expands very heavily."""
    decoder = json.JSONDecoder()
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        _prefix, buffer = _envelope_prefix(stream)
        eof = False
        while True:
            buffer = buffer.lstrip()
            if buffer.startswith(","):
                buffer = buffer[1:].lstrip()
            if buffer.startswith("]"):
                return
            try:
                value, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                chunk = stream.read(65_536)
                if not chunk:
                    if eof:
                        raise ValueError("truncated Quranpedia tafsir data array")
                    eof = True
                else:
                    buffer += chunk
                continue
            if not isinstance(value, dict):
                raise ValueError("Quranpedia tafsir data row is not an object")
            yield value
            buffer = buffer[end:]


def build(source_dir: Path) -> tuple[bytes, dict]:
    manifest_raw = (source_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest.get("source") != "https://quranpedia.net" or manifest.get("version") != "2026-10-28":
        raise ValueError("unexpected Quranpedia tafsir manifest identity/version")
    listed = next(
        (item for item in manifest.get("files", []) if item.get("name") == SOURCE_NAME),
        None,
    )
    source_raw = (source_dir / SOURCE_NAME).read_bytes()
    if (
        not listed
        or listed.get("sha256") != sha256(source_raw)
        or listed.get("bytes") != len(source_raw)
    ):
        raise ValueError("official Quranpedia manifest hash/size mismatch for tafsir dump")

    license_data, service_schema = read_tafsir_header(source_dir / SOURCE_NAME)
    if service_schema != "/v1/ayah/{surah}/{ayah}/tafsir":
        raise ValueError("unexpected Quranpedia tafsir schema")
    if (
        not isinstance(license_data, dict)
        or license_data.get("source") != "https://quranpedia.net"
        or license_data.get("version") != "2026-10-24"
        or not license_data.get("ar")
        or not license_data.get("en")
    ):
        raise ValueError("Quranpedia tafsir license/version metadata is incomplete")

    field_values: dict[int, dict[str, collections.Counter]] = {}
    coverage: collections.Counter[int] = collections.Counter()
    seen_refs = set()
    row_count = 0
    for row in iter_tafsir_rows(source_dir / SOURCE_NAME):
        row_count += 1
        ref = (int(row["surah"]), int(row["ayah"]))
        if ref in seen_refs:
            raise ValueError(f"duplicate tafsir ayah reference: {ref}")
        seen_refs.add(ref)
        for item in row.get("tafsir", []):
            book_id = int(item["id"])
            values = field_values.setdefault(
                book_id,
                {field: collections.Counter() for field in ("name", "author", "year", "parts")},
            )
            for field in values:
                value = item.get(field)
                # Eight service rows omit some author names. The non-empty modal
                # value is the stable metadata used by the rest of the dump.
                if value is not None and value != "":
                    values[field][value] += 1
            coverage[book_id] += 1
    if row_count != EXPECTED_AYAH_ROWS:
        raise ValueError(f"expected {EXPECTED_AYAH_ROWS} tafsir ayah rows, got {row_count}")
    books = {
        book_id: {
            "id": book_id,
            **{
                field: counts.most_common(1)[0][0] if counts else None
                for field, counts in values.items()
            },
        }
        for book_id, values in field_values.items()
    }
    if len(books) != EXPECTED_SOURCE_BOOKS:
        raise ValueError(f"expected {EXPECTED_SOURCE_BOOKS} source tafsir books, got {len(books)}")

    excluded_ids = ALQURAN_EQUIVALENT_IDS | DUPLICATE_EDITION_IDS
    selected = []
    for item in books.values():
        death_year = item.get("year")
        title = str(item.get("name") or "").strip()
        author = str(item.get("author") or "").strip()
        book_id = int(item["id"])
        if not isinstance(death_year, int) or death_year > MAX_CLASSICAL_DEATH_YEAR:
            continue
        if title.startswith(EXCLUDED_TITLE_PREFIXES) or book_id in excluded_ids:
            continue
        selected.append(
            {
                "edition": f"qp:{book_id}",
                "book_id": book_id,
                "name": title,
                "author": author,
                "author_death_hijri": death_year,
                "parts": int(item.get("parts") or 1),
                "coverage_ayahs": coverage[book_id],
            }
        )
    selected.sort(key=lambda item: (item["author_death_hijri"], item["name"], item["book_id"]))
    if len(selected) != EXPECTED_SELECTED_BOOKS:
        raise ValueError(f"expected {EXPECTED_SELECTED_BOOKS} selected classical books, got {len(selected)}")
    if len({item["edition"] for item in selected}) != len(selected):
        raise ValueError("duplicate Quranpedia edition ID in generated catalog")

    output_value = {
        "schema": 1,
        "source": "الموسوعة القرآنية Quranpedia.net",
        "source_url": "https://quranpedia.net",
        "api_base": "https://api.quranpedia.net/v1",
        "dump_version": license_data["version"],
        "manifest_snapshot": manifest["version"],
        "license": {
            "url": f"{BASE_URL}/LICENSE.md",
            "policy": "https://quranpedia.net/api-docs#usage-policy",
            "notice_ar": (
                "يجوز استعمال البيانات داخل التطبيقات مجانًا؛ النصوص التراثية تراث مشترك، "
                "والرقمنة والهيكلة والتدقيق للموسوعة القرآنية. يدمج سراج النصوص محليًا للعمل دون إنترنت."
            ),
        },
        "selection": {
            "kind": "classical-primary-works",
            "maximum_author_death_hijri": MAX_CLASSICAL_DEATH_YEAR,
            "excludes_modern_compilations_by_title_prefix": list(EXCLUDED_TITLE_PREFIXES),
            "deduplicated": True,
            "offline_text_bundled": True,
            "book_dump_version": "2026-08-10",
        },
        "source_file": {"name": SOURCE_NAME, "sha256": sha256(source_raw)},
        "generated_by": "scripts/generate_quranpedia_tafsir_catalog.py",
        "books": selected,
    }
    output_raw = compact(output_value)
    source_record = {
        "schema": 1,
        "dump_version": license_data["version"],
        "manifest_snapshot": manifest["version"],
        "generated_at": manifest.get("generated_at"),
        "manifest_url": f"{BASE_URL}/manifest.json",
        "manifest_bytes": len(manifest_raw),
        "manifest_sha256": sha256(manifest_raw),
        "license_url": f"{BASE_URL}/LICENSE.md",
        "files": {
            SOURCE_NAME: {
                "url": f"{BASE_URL}/{SOURCE_NAME}",
                "bytes": len(source_raw),
                "sha256": sha256(source_raw),
                "built_at": listed.get("built_at"),
            }
        },
        "selection": {
            "source_book_count": len(books),
            "selected_book_count": len(selected),
            "maximum_author_death_hijri": MAX_CLASSICAL_DEATH_YEAR,
            "alquran_equivalent_ids": sorted(ALQURAN_EQUIVALENT_IDS),
            "duplicate_or_compilation_ids": sorted(DUPLICATE_EDITION_IDS),
            "excluded_title_prefixes": list(EXCLUDED_TITLE_PREFIXES),
        },
        "transformation": {
            "script": "scripts/generate_quranpedia_tafsir_catalog.py",
            "description": (
                "Union the official per-ayah tafsir metadata; retain licensed classical primary works "
                "whose recorded author death is no later than 1350 AH; remove modern compilations "
                "and duplicate editions. This metadata controls the full offline text store built "
                "from the matching official per-book dumps."
            ),
        },
        "outputs": {
            path.relative_to(ROOT).as_posix(): {"bytes": len(output_raw), "sha256": sha256(output_raw)}
            for path in OUTPUTS
        },
    }
    return output_raw, source_record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    source_dir.mkdir(parents=True, exist_ok=True)

    if args.refresh:
        manifest_raw = fetch("manifest.json", args.timeout)
        manifest = json.loads(manifest_raw)
        if manifest.get("version") != "2026-10-28":
            raise SystemExit(f"refusing to overwrite dated evidence with dump {manifest.get('version')!r}")
        listed = next(
            (item for item in manifest.get("files", []) if item.get("name") == SOURCE_NAME),
            None,
        )
        source_raw = fetch(SOURCE_NAME, args.timeout)
        if (
            not listed
            or listed.get("sha256") != sha256(source_raw)
            or listed.get("bytes") != len(source_raw)
        ):
            raise SystemExit("downloaded tafsir dump does not match official manifest")
        (source_dir / "manifest.json").write_bytes(manifest_raw)
        (source_dir / "LICENSE.md").write_bytes(fetch("LICENSE.md", args.timeout))
        (source_dir / SOURCE_NAME).write_bytes(source_raw)

    output_raw, source_record = build(source_dir)
    source_path = source_dir / "SOURCE.json"
    if args.verify:
        failures = []
        for output in OUTPUTS:
            if not output.is_file() or output.read_bytes() != output_raw:
                failures.append(output.relative_to(ROOT).as_posix())
        if not source_path.is_file():
            failures.append(source_path.relative_to(ROOT).as_posix())
        else:
            recorded = json.loads(source_path.read_text(encoding="utf-8"))
            if recorded != source_record:
                failures.append(source_path.relative_to(ROOT).as_posix())
        if failures:
            raise SystemExit("generated tafsir catalog/evidence mismatch: " + ", ".join(failures))
    else:
        for output in OUTPUTS:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(output_raw)
        source_path.write_text(
            json.dumps(source_record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Verified {len(json.loads(output_raw)['books'])} licensed classical Quranpedia tafsir books")
    print(source_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
