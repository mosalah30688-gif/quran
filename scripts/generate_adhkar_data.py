#!/usr/bin/env python3
"""Generate referenced adhkar data from a pinned MIT dataset plus locked Quran text."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "872764ca013116c905f7fc9c3dc972c27cd37d4a"
SOURCE_DIR = ROOT / "audit" / "sources" / "hisn-el-muslim" / COMMIT
CURATION = ROOT / "audit" / "sources" / "adhkar-curation-1.1.0.json"
HISN_SHA256 = "b30a448ef40184b0422c40bd3c372bf2b25bfb5b0539fd3699e6b4fba9459d80"
LICENSE_SHA256 = "65b11add3112689b4a61aa53fb127705522c19eb1a809556a67410e2a335ef00"
RAW_ROOT = f"https://raw.githubusercontent.com/asellam/HisnElMuslim/{COMMIT}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub("[إأآٱ]", "ا", value)
    value = value.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return re.sub(r"[^ء-ي0-9]+", "", value)


def related_text(curated: str, source: str) -> bool:
    left, right = normalize(curated), normalize(source)
    return bool(left and right and (left in right or right in left))


def fetch(name: str, timeout: int) -> bytes:
    request = urllib.request.Request(
        f"{RAW_ROOT}/{name}",
        headers={"User-Agent": "Siraj-Quran-source-audit/1.1"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status}: {request.full_url}")
        return response.read()


def quran_lookup() -> dict[tuple[int, int], str]:
    import gzip

    path = ROOT / "audit" / "sources" / "alquran-cloud" / "2026-10-28" / "quran-simple.json.gz"
    envelope = json.loads(gzip.decompress(path.read_bytes()))
    result = {}
    for surah in envelope["data"]["surahs"]:
        for ayah in surah["ayahs"]:
            result[(surah["number"], ayah["numberInSurah"])] = ayah["text"].lstrip("\ufeff")
    if len(result) != 6236:
        raise ValueError("locked Quran source does not contain 6236 ayahs")
    return result


def build() -> tuple[bytes, dict]:
    hisn_raw = (SOURCE_DIR / "hisn.json").read_bytes()
    license_raw = (SOURCE_DIR / "LICENSE.md").read_bytes()
    if sha256(hisn_raw) != HISN_SHA256 or sha256(license_raw) != LICENSE_SHA256:
        raise ValueError("pinned HisnElMuslim source or MIT license hash mismatch")
    hisn = json.loads(hisn_raw)
    hisn_categories = list(hisn)
    curation_raw = CURATION.read_bytes()
    curation = json.loads(curation_raw)
    if curation.get("schema") != 1 or curation.get("hisn_commit") != COMMIT:
        raise ValueError("adhkar curation does not name the pinned source commit")
    quran = quran_lookup()

    categories = []
    ids = set()
    for category in curation.get("categories", []):
        output_items = []
        for item in category.get("items", []):
            item_id = item.get("id")
            if not isinstance(item_id, str) or item_id in ids:
                raise ValueError(f"invalid or duplicate adhkar id: {item_id!r}")
            ids.add(item_id)
            text = item.get("text")
            count = item.get("count")
            if not isinstance(text, str) or not text.strip() or not isinstance(count, int) or count < 1:
                raise ValueError(f"invalid adhkar text/count: {item_id}")
            resolved = []
            for evidence in item.get("evidence", []):
                kind = evidence.get("kind")
                if kind == "hisn":
                    category_index = evidence.get("category_index")
                    item_index = evidence.get("item_index")
                    try:
                        source_category = hisn_categories[category_index]
                        source_item = hisn[source_category]["Adhkar"][item_index]
                    except (IndexError, KeyError, TypeError) as exc:
                        raise ValueError(f"bad Hisn evidence pointer for {item_id}") from exc
                    quote = evidence.get("quote", text)
                    if not related_text(quote, source_item["Text"]):
                        raise ValueError(f"curated text is not traceable to Hisn source: {item_id}")
                    resolved.append(
                        {
                            "source": "حصن المسلم من أذكار الكتاب والسنة",
                            "dataset": "asellam/HisnElMuslim",
                            "commit": COMMIT,
                            "category": source_category,
                            "reference": source_item["Reference"],
                            "license": "MIT",
                            "source_item": f"{category_index}:{item_index}",
                        }
                    )
                elif kind == "quran":
                    ref = (int(evidence["surah"]), int(evidence["ayah"]))
                    source_text = quran.get(ref)
                    quote = evidence.get("quote", text)
                    if source_text is None or not related_text(quote, source_text):
                        raise ValueError(f"curated text is not traceable to Quran source: {item_id}")
                    resolved.append(
                        {
                            "source": "القرآن الكريم — AlQuran Cloud quran-simple",
                            "reference": f"سورة {ref[0]}، آية {ref[1]}",
                            "edition": "quran-simple",
                            "source_manifest": "audit/sources/alquran-cloud/2026-10-28/SOURCE.json",
                        }
                    )
                else:
                    raise ValueError(f"unknown evidence kind for {item_id}: {kind!r}")
            if not resolved:
                raise ValueError(f"adhkar item has no evidence: {item_id}")
            output_items.append(
                {
                    "id": item_id,
                    "text": text,
                    "count": count,
                    "evidence": resolved,
                }
            )
        categories.append({"id": category["id"], "name": category["name"], "items": output_items})

    if len(categories) != 14 or len(ids) != 50:
        raise ValueError(f"expected 14 categories and 50 curated items; got {len(categories)} and {len(ids)}")
    output = {
        "v": 2,
        "source": "Curated from the pinned MIT-licensed asellam/HisnElMuslim dataset and locked Quran text",
        "source_url": f"https://github.com/asellam/HisnElMuslim/tree/{COMMIT}",
        "license": {
            "dataset": "MIT — copyright 2021 Abdellah SELLAM",
            "license_file": f"audit/sources/hisn-el-muslim/{COMMIT}/LICENSE.md",
            "note": "نصوص القرآن والحديث الأصلية تراثية؛ ترخيص MIT يغطي رقمنة مجموعة البيانات وبنيتها. المراجع مثبتة لكل عنصر.",
        },
        "generated_by": "scripts/generate_adhkar_data.py",
        "scholarly_review": "pending",
        "categories": categories,
    }
    encoded = (json.dumps(output, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    source_record = {
        "schema": 1,
        "repository": "https://github.com/asellam/HisnElMuslim",
        "commit": COMMIT,
        "files": {
            "hisn.json": {"bytes": len(hisn_raw), "sha256": sha256(hisn_raw)},
            "LICENSE.md": {"bytes": len(license_raw), "sha256": sha256(license_raw), "license": "MIT"},
            CURATION.relative_to(ROOT).as_posix(): {
                "bytes": len(curation_raw),
                "sha256": sha256(curation_raw),
            },
        },
        "output": {"bytes": len(encoded), "sha256": sha256(encoded), "items": len(ids)},
        "note": "Automated traceability is complete; scholarly approval remains a separate human gate.",
    }
    return encoded, source_record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    if args.refresh:
        files = {"hisn.json": fetch("hisn.json", args.timeout), "LICENSE.md": fetch("LICENSE.md", args.timeout)}
        if sha256(files["hisn.json"]) != HISN_SHA256 or sha256(files["LICENSE.md"]) != LICENSE_SHA256:
            raise SystemExit("pinned upstream content no longer matches its recorded hash")
        for name, content in files.items():
            (SOURCE_DIR / name).write_bytes(content)

    encoded, source_record = build()
    mismatches = []
    for app in ("windows_app", "mushaf_app"):
        path = ROOT / app / "data" / "adhkar.json"
        if args.verify:
            if not path.is_file() or path.read_bytes() != encoded:
                mismatches.append(path.relative_to(ROOT).as_posix())
        else:
            path.write_bytes(encoded)
    record_path = SOURCE_DIR / "SOURCE.json"
    if args.verify and mismatches:
        raise SystemExit("generated data mismatch: " + ", ".join(mismatches))
    if not args.verify:
        record_path.write_text(json.dumps(source_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified 50 referenced adhkar items in 14 categories")
    print(record_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
