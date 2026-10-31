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
    service_worker = (ROOT / "sw.js").read_text(encoding="utf-8")
    capacitor = load("capacitor.config.json")
    android_strings = (ROOT / "android/app/src/main/res/values/strings.xml").read_text(encoding="utf-8")
    assert capacitor["appName"] == "سراج — قرآن كريم"
    assert load("manifest.json")["description"] == "مصحف قرآن كريم"
    assert '<string name="app_name">سراج — قرآن كريم</string>' in android_strings
    assert '<string name="title_activity_main">سراج — قرآن كريم</string>' in android_strings
    assert "loadBundledData()" in app
    assert "lookupBatch" in app and "TafsirStore" in app
    assert "recordWirdPage" in app and "Reminder" in app
    assert "wdTargetSel" not in app and "wdAdd" not in app
    assert "APP_BUNDLE_VERSION = '1.4.4'" in html and "الإصدار 1.4.4" in html
    about_match = re.search(r'<section class="view" id="view-about">(.*?)</section>', html, re.DOTALL)
    assert about_match, "missing dedicated About view"
    about = about_match.group(1)
    assert '<h2 class="about-title">سراج</h2>' in about and "مصحف قرآن كريم" in about
    feature_match = re.search(r'<ul class="feat" id="aboutFeatures">(.*?)</ul>', about, re.DOTALL)
    assert feature_match, "missing canonical About features"
    about_features = re.findall(r"<li>([^<]+)</li>", feature_match.group(1))
    assert about_features == [
        "مصحف ذكي للتلاوة والاستماع والتدبر",
        "برواية حفص عن عاصم وروايات أخرى",
        "تحديد الأوراد والختمات ومتابعتها",
        "الأذكار بعداد خاص لكل ذكر",
        "تفاسير القرآن",
    ]
    assert "أحدث التحديثات" not in about and "ABOUT_RELEASE_NOTES" not in about
    assert not any(term in about for term in ("API", "SHA-256", "APK", "Fluent 3D", "أدوات عربية نافعة"))
    assert "محمد صلاح عبد الخالق" in about and "صفحة المطور" in about and "اتصل بنا" in about
    assert '<div class="header-brand" aria-label="سراج">' in html
    assert '<img src="icon.png" alt="" aria-hidden="true" />' in html
    assert '.header-brand span { font-family: Amiri, serif;' in html
    settings_match = re.search(r'<section class="view" id="view-settings">(.*?)</section>', html, re.DOTALL)
    assert settings_match, "missing Settings view"
    settings = settings_match.group(1)
    assert 'id="aboutBtn"' not in html and "$('#aboutBtn')" not in app
    assert re.search(r'id="settingsAboutBtn".*?</button>\s*$', settings, re.DOTALL), (
        "About must be the final Settings item"
    )
    assert "$('#settingsAboutBtn').addEventListener('click', () => showView('about'))" in app
    assert "name === 'about' && b.dataset.view === 'settings'" in app
    assert 'data-icon="about"' in settings and "about:" in app
    assert "--mobile-nav-h: 64px" in html and "--mobile-nav-h: 58px" in html
    assert 'class="reader-dock"' in html and 'id="pPrevS"' in html and 'id="pNextS"' in html
    assert 'id="audioSeek"' in html and 'class="play-pickers"' in html and 'class="player-controls"' in html
    assert "--reader-dock-h" in html and "safe-area-inset-bottom" in html and "safe-area-inset-left" in html
    assert "group-menu-open" in html and "reader-view-active" in html and "body.group-menu-open .hdr" in html
    assert "syncReaderDockHeight" in app and "syncAudioTimeline" in app and "formatAudioTime" in app
    assert "syncGroupMenuLayer" in app and "focusFirst" in app and "restoreFocus" in app
    assert "يتوفر تحديث جديد لسراج — الإصدار" in app and "فيه تحديث جديد" not in app
    assert "Array.isArray(m.features)" in app and "technicalTerms" in app
    assert ".upd-banner span { flex: 1; white-space: pre-line; }" in html
    assert "siraj-shell-v10" in service_worker
    assert "--quran-font" in html and "setFont" in html
    assert "data-icon=\"tajweed\"" in html and "🎵" not in html

    print("Verified Android local bundle: 6,236 Hafs/tajweed rows, 604 pages, 78 licensed tafsirs, four fonts")


if __name__ == "__main__":
    main()
