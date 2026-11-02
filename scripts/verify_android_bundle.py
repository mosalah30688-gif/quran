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

    project_license = (ROOT / "LICENSE").read_text(encoding="utf-8")
    historical_license = (ROOT / "LICENSES/MIT-HISTORICAL.txt").read_text(encoding="utf-8")
    build_script = (ROOT / "scripts/build-www.sh").read_text(encoding="utf-8")
    assert "SIRAJ PROPRIETARY SOURCE AND END-USER LICENSE" in project_license
    assert "4fda3631611b2eef8a630621719f9c9beef7390f" in project_license
    assert historical_license.startswith("MIT License\n")
    assert "cp LICENSE LICENSE.ar.md NOTICE.md www/legal/" in build_script
    assert "cp LICENSES/MIT-HISTORICAL.txt www/legal/" in build_script
    assert "index.html smart-context.js smart-services.js tajweed-learning.js app.js" in build_script

    app = (ROOT / "app.js").read_text(encoding="utf-8")
    smart_context = (ROOT / "smart-context.js").read_text(encoding="utf-8")
    smart_services = (ROOT / "smart-services.js").read_text(encoding="utf-8")
    tajweed_learning = (ROOT / "tajweed-learning.js").read_text(encoding="utf-8")
    tajweed_catalog = (ROOT / "tajweed-learning-catalog.json").read_text(encoding="utf-8")
    tajweed_registry = load("tajweed-scope-registry.json")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    service_worker = (ROOT / "sw.js").read_text(encoding="utf-8")
    capacitor = load("capacitor.config.json")
    android_strings = (ROOT / "android/app/src/main/res/values/strings.xml").read_text(encoding="utf-8")
    android_manifest = (ROOT / "android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    smart_plugin = (ROOT / "android/app/src/main/java/com/quran/mushaf/SmartDevicePlugin.java").read_text(encoding="utf-8")
    smart_receiver = (ROOT / "android/app/src/main/java/com/quran/mushaf/SmartNotificationReceiver.java").read_text(encoding="utf-8")
    reminder_receiver = (ROOT / "android/app/src/main/java/com/quran/mushaf/ReminderReceiver.java").read_text(encoding="utf-8")
    assert capacitor["appName"] == "سراج — قرآن كريم"
    assert load("manifest.json")["description"] == "مصحف قرآن كريم"
    assert '<string name="app_name">سراج — قرآن كريم</string>' in android_strings
    assert '<string name="title_activity_main">سراج — قرآن كريم</string>' in android_strings
    assert '.SmartNotificationReceiver' in android_manifest and '.SmartNotificationActionReceiver' in android_manifest
    assert 'name = "SmartDevice"' in smart_plugin and 'consumeFeedback' in smart_plugin
    assert 'SmartTimeWindow.nextAllowedAt' in smart_receiver
    assert 'SmartTimeWindow.nextAllowedAt' in reminder_receiver
    assert "ACCESS_FINE_LOCATION" not in android_manifest and "READ_CONTACTS" not in android_manifest
    assert "loadBundledData()" in app
    assert "SmartContextEngine" in smart_context and "LIKELY_SLEEPING" in smart_context
    assert "buildCandidates" in smart_services and "open_adhkar:morning" in smart_services
    assert "TajweedLearningEngine" in tajweed_learning and "reviewedEntry" in tajweed_learning
    assert "PENDING_SCHOLARLY_REVIEW" in tajweed_catalog and "source-unspecified" in tajweed_catalog
    assert tajweed_registry["scopeKey"] == "riwayah/tariq/wajh/edition"
    assert tajweed_registry["fallbackPolicy"] == "FORBIDDEN_BETWEEN_SCOPES"
    assert "tajweed-scope-registry.json" in build_script
    assert "run(null, 'smart-context.js')" in html
    assert "run(null, 'smart-services.js')" in html
    assert "run(null, 'tajweed-learning.js')" in html
    assert 'id="setSmartEnabled"' in html and 'id="smartSuggestion"' in html
    assert 'id="tjStartLearning"' in html and 'id="tjLearningCard"' in html
    assert "لا يرسل ملف عادات إلى خادم" in html
    assert "new SmartContextAPI.SmartContextEngine" in app
    assert "new TajweedLearningAPI.TajweedLearningEngine" in app
    assert "FORBIDDEN_BETWEEN_SCOPES" in app
    assert "لا تُعرض أحكام حفص أو أي طبقة عامة" in app
    assert "markShown(candidate, suggestionId, 'suggestion')" in app
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
    assert "siraj-shell-v14" in service_worker
    assert "'./smart-context.js'" in service_worker and "'./smart-services.js'" in service_worker
    assert "'./tajweed-learning.js'" in service_worker
    assert "'./tajweed-learning-catalog.json'" in service_worker
    assert "'./tajweed-scope-registry.json'" in service_worker
    assert "--quran-font" in html and "setFont" in html
    assert "data-icon=\"tajweed\"" in html and "🎵" not in html

    print("Verified Android local bundle: 6,236 Hafs/tajweed rows, 604 pages, 78 licensed tafsirs, four fonts")


if __name__ == "__main__":
    main()
