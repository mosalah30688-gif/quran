#!/usr/bin/env python3
"""يبني نص مصحف حفص المعروض (hafs.json) من مصحف Quranpedia الرسمي (mushafs-1).

النص المصدر هو «مصحف حفص» بضبط مصحف المدينة مع علامات الوقف الست (U+06D6–U+06DC)،
وهو نفس مصدر روايات ورش وقالون والدوري في التطبيق، فيتوحّد رسم المصحف كله.

ثوابت لا تتغيّر في الناتج:
  * ترقيم الصفحات (604 صفحة) يبقى كما هو مقفول في hafs.json السابق، لأن تقسيم
    الأسطر في quran-madani-lines.json مبني عليه.
  * علامة الحزب ۞ تظهر قبل أول كلمة في الآية التي يبدأ عندها ربع الحزب، كما في
    مصحف المدينة، وتُلصق بأول كلمة حتى لا يتغيّر عدد كلمات الآية.
  * علامة السجدة ۩ تظهر في نهاية الآية في المواضع الخمسة عشر فقط.
  * عدد كلمات كل آية يبقى مطابقًا للنص المقفول السابق، حتى يظل تقسيم الأسطر صحيحًا.

الاستخدام:
  python3 scripts/build_hafs_text.py            # بناء والتحقق
  python3 scripts/build_hafs_text.py --check    # تحقق فقط (يفشل إن اختلف الناتج)
  python3 scripts/build_hafs_text.py --update-lock
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://quranpedia.net/dumps/mushafs-1.json.gz"
LOCK = ROOT / "audit" / "sources" / "quranpedia-hafs" / "2026-11-06" / "SOURCE.json"
CACHE = ROOT / ".cache" / "mushafs-1.json.gz"
TARGETS = (
    ROOT / "quran-hafs.json",
    ROOT / "mushaf_app" / "data" / "hafs.json",
    ROOT / "windows_app" / "data" / "hafs.json",
)

WAQF = "\u06d6\u06d7\u06d8\u06d9\u06da\u06db\u06dc"  # علامات الوقف الست + ۜ
RUB = "\u06de"  # ۞ علامة الحزب — تُلصق بأول كلمة في الآية
SAJDA = "\u06e9"  # ۩ علامة السجدة
MARK_ONLY = set(WAQF + RUB + SAJDA)
BASMALA = ["بِسْمِ", "اللَّهِ", "الرَّحْمَٰنِ", "الرَّحِيمِ"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Siraj-Quran/1.4 hafs text build (https://github.com/mosalah30688-gif/quran)"
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status} for {url}")
        return response.read()


def load_source(update_lock: bool) -> tuple[dict[int, dict], dict]:
    lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    raw = CACHE.read_bytes() if CACHE.exists() else fetch(SOURCE_URL)
    digest = sha256(raw)
    expected = lock.get("source", {}).get("sha256")
    if expected and digest != expected and not update_lock:
        CACHE.unlink(missing_ok=True)
        raise SystemExit(
            f"بصمة مصدر المصحف تغيّرت: {digest} بدل {expected}. راجع المصدر ثم استخدم --update-lock."
        )
    envelope = json.loads(gzip.decompress(raw))
    data = envelope["data"]
    if data.get("name") != "مصحف حفص":
        raise SystemExit(f"مصدر غير متوقع: {data.get('name')!r}")
    verses: dict[tuple[int, int], dict] = {}
    for surah in data["surahs"]:
        for ayah in surah["ayahs"]:
            verses[(int(ayah["surah"]), int(ayah["number"]))] = ayah
    if len(verses) != 6236:
        raise SystemExit(f"عدد الآيات غير متوقع: {len(verses)}")
    record = {
        "url": SOURCE_URL,
        "bytes": len(raw),
        "sha256": digest,
        "provider_version": envelope.get("license", {}).get("version"),
        "schema": envelope.get("schema"),
    }
    return verses, record


def split_mark_only(text: str) -> tuple[list[str], bool, bool]:
    """يرجع كلمات الآية بعد فصل العلامات المستقلة، وهل فيها سجدة، وهل تبدأ بربع حزب."""
    words = [word for word in text.split() if not (word and all(ch in MARK_ONLY for ch in word))]
    sajda = SAJDA in text
    rub = RUB in text
    return [word.replace(SAJDA, "").replace(RUB, "") for word in words], sajda, rub


def build(verses: dict[tuple[int, int], dict], pages: dict[tuple[int, int], int], simple: list) -> dict:
    rows = []
    for (surah, ayah), page in sorted(pages.items()):
        words, sajda, rub = split_mark_only(verses[(surah, ayah)]["text"])
        if rub and words:
            words[0] = RUB + words[0]
        if (surah, ayah) == (15, 7):
            # المصدر يكتب «لَّوۡمَا» كلمة واحدة، والمصحف المقفول يفصلها؛ نحفظ حدود الكلمات.
            merged = [word for word in words if word.startswith("\u0644\u0651\u064e\u0648\u06e1\u0645")]
            if merged:
                word = merged[0]
                cut = word.index("\u0645\u064e\u0627") if "\u0645\u064e\u0627" in word else None
                if cut:
                    index = words.index(word)
                    words[index : index + 1] = [word[:cut], word[cut:]]
        text = re.sub(r"\s+", " ", " ".join(words)).strip()
        if sajda:
            text = f"{text} {SAJDA}"
        rows.append([surah, ayah, page, text])
    payload = {
        "uthmani": rows,
        "simple": simple,
        "source": (
            "Quranpedia.net — مصحف حفص (mushafs-1): رسم مصحف المدينة بعلامات الوقف؛ "
            "أرقام الصفحات من مصحف المدينة (604 صفحة)"
        ),
    }
    return payload


def verify(payload: dict, previous: dict, verses: dict[tuple[int, int], dict]) -> Counter:
    rows = payload["uthmani"]
    if len(rows) != 6236:
        raise SystemExit(f"عدد الآيات في الناتج غير صحيح: {len(rows)}")
    marks = Counter(ch for row in rows for ch in row[3] if ch in MARK_ONLY)
    if marks.get(RUB, 0) < 190:
        raise SystemExit(f"علامات الحزب ۞ ناقصة: {marks.get(RUB)}")
    if marks.get(SAJDA) != 15:
        raise SystemExit(f"عدد علامات السجدة غير صحيح: {marks.get(SAJDA)}")
    if sum(count for mark, count in marks.items() if mark in WAQF) < 4000:
        raise SystemExit(f"علامات الوقف ناقصة: {dict(marks)}")
    previous_rows = {(row[0], row[1]): row for row in previous["uthmani"]}
    for row in rows:
        key = (row[0], row[1])
        before = previous_rows[key]
        if row[2] != before[2]:
            raise SystemExit(f"تغيّر ترقيم الصفحة في {key[0]}:{key[1]}")
        if len(row[3].split()) != len(before[3].split()):
            # عدد الكلمات محفوظ لأن ۞ تُلصق بأول كلمة
            raise SystemExit(f"تغيّر عدد كلمات الآية {key[0]}:{key[1]}")
        if not row[3].strip():
            raise SystemExit(f"آية فارغة: {key}")
    for row in payload["simple"]:
        if "\ufeff" in row[3] or "  " in row[3]:
            raise SystemExit(f"نص إملائي غير منظّف: {row[0]}:{row[1]}")
    # سلامة المصدر نفسه: كل آية موجودة
    missing = set(verses) - {(row[0], row[1]) for row in rows}
    if missing:
        raise SystemExit(f"آيات مفقودة: {sorted(missing)[:5]}")
    return marks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="تحقق من الناتج دون كتابة")
    parser.add_argument("--update-lock", action="store_true", help="تحديث بصمة المصدر والناتج")
    args = parser.parse_args()

    verses, source_record = load_source(args.update_lock)
    current = json.loads((ROOT / "quran-hafs.json").read_text(encoding="utf-8"))
    pages = {(row[0], row[1]): row[2] for row in current["uthmani"]}
    payload = build(verses, pages, current["simple"])
    marks = verify(payload, current, verses)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    if args.check:
        for path in TARGETS:
            if path.read_bytes() != encoded:
                raise SystemExit(f"الناتج لا يطابق المقفول: {path.relative_to(ROOT)}")
        print(f"hafs text verified: {len(encoded)} bytes, sha256 {sha256(encoded)}")
        return 0

    for path in TARGETS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)

    if args.update_lock:
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
        lock.update(
            {
                "schema": "siraj-hafs-text/1",
                "retrieved_at": "2026-11-06",
                "provider": "Quranpedia.net",
                "terms": "https://quranpedia.net/api-docs#usage-policy",
                "source": source_record,
                "transformation": {
                    "desc": (
                        "إبقاء علامات الوقف الست، وإلصاق علامة الحزب ۞ بأول كلمة في الآية التي "
                        "يبدأ عندها ربع الحزب، ونقل علامة السجدة ۩ إلى نهاية الآية في مواضعها "
                        "الخمسة عشر، وتوحيد المسافات."
                    ),
                    "pagination": "منقولة كما هي من hafs.json المقفول سابقًا (604 صفحة)",
                    "word_boundaries": "مطابقة للنص السابق؛ 15:7 تُفصل «لَّوۡمَا» إلى كلمتين",
                    "sajda_ayahs": [
                        "7:206", "13:15", "16:50", "17:109", "19:58", "22:18", "22:77",
                        "25:60", "27:26", "32:15", "38:24", "41:38", "53:62", "84:21", "96:19",
                    ],
                },
                "marks": {mark: count for mark, count in sorted(marks.items())},
                "outputs": {"hafs.json": {"bytes": len(encoded), "sha256": sha256(encoded)}},
                "builder": "scripts/build_hafs_text.py",
            }
        )
        LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"hafs text built: {len(encoded)} bytes, sha256 {sha256(encoded)}, marks {dict(marks)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
