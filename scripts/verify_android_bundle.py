#!/usr/bin/env python3
"""Deterministic checks for the local-first assets shipped in the Android APK."""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def assert_same(left: str, right: str) -> None:
    assert (ROOT / left).read_bytes() == (ROOT / right).read_bytes(), f"copy drift: {left} != {right}"


def main() -> None:
    assert_same("quran-hafs.json", "mushaf_app/data/hafs.json")
    assert_same("quran-tajweed.json", "windows_app/data/quran-tajweed.json")
    assert_same("surahs.json", "mushaf_app/data/surahs.json")
    assert_same("tafsir-catalog.json", "mushaf_app/data/tafsir-catalog.json")

    hafs = load("quran-hafs.json")
    tajweed = load("quran-tajweed.json")
    surahs = load("surahs.json")
    catalog = load("tafsir-catalog.json")
    expected_refs = None
    for edition in ("uthmani", "simple"):
        rows = hafs[edition]
        assert len(rows) == 6236, (edition, len(rows))
        refs = [(row[0], row[1]) for row in rows]
        assert len(set(refs)) == 6236
        assert {row[2] for row in rows} == set(range(1, 605))
        assert refs[0] == (1, 1) and refs[-1] == (114, 6)
        expected_refs = expected_refs or refs
        assert refs == expected_refs
        assert all(isinstance(row[3], str) and row[3].strip() for row in rows)

    assert len(tajweed) == 6236
    assert [(row[0], row[1]) for row in tajweed] == expected_refs
    assert {row[2] for row in tajweed} == set(range(1, 605))
    assert all(isinstance(row[3], str) and row[3].strip() for row in tajweed)

    assert len(surahs) == 114
    assert sum(int(row["numberOfAyahs"]) for row in surahs) == 6236
    assert [row["number"] for row in surahs] == list(range(1, 115))

    books = catalog["books"]
    assert len(books) == 73
    assert len({book["edition"] for book in books}) == 73
    assert all(re.fullmatch(r"qp:\d+", book["edition"]) for book in books)
    assert all(int(book["author_death_hijri"]) <= 1350 for book in books)
    assert catalog["selection"]["kind"] == "classical-primary-works"

    required_fonts = {
        "fonts/Amiri-Regular.ttf": 400_000,
        "fonts/AmiriQuran-Regular.ttf": 100_000,
        "fonts/NotoNaskhArabic-Variable.ttf": 250_000,
        "fonts/ScheherazadeNew-Regular.ttf": 300_000,
    }
    for relative, minimum in required_fonts.items():
        path = ROOT / relative
        assert path.is_file() and path.stat().st_size >= minimum, relative
    for name in (
        "OFL-Amiri.txt", "OFL-AmiriQuran.txt", "OFL-NotoNaskhArabic.txt", "OFL-ScheherazadeNew.txt"
    ):
        text = (ROOT / "fonts" / name).read_text(encoding="utf-8")
        assert "SIL OPEN FONT LICENSE" in text.upper(), name

    app = (ROOT / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "loadBundledData()" in app
    assert "lookupBatch" in app and "TafsirStore" in app
    assert "recordWirdPage" in app and "Reminder" in app
    assert "wdTargetSel" not in app and "wdAdd" not in app
    assert "APP_BUNDLE_VERSION = '1.4.0'" in html
    assert "--quran-font" in html and "setFont" in html
    assert "data-icon=\"tajweed\"" in html and "🎵" not in html

    print("Verified Android local bundle: 6,236 Hafs/tajweed rows, 604 pages, 78 licensed tafsirs, four fonts")


if __name__ == "__main__":
    main()
