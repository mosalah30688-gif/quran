"""تتبّع القراءة والختمة تلقائياً بلا أهداف يومية إلزامية.

الوحدة مستقلة عن الواجهة كي تُستخدم من التطبيق ومن مشغّل التذكير، وتحافظ على
بيانات الإصدارات السابقة من دون تفسير «الورد المكتمل» على أنه ختمة كاملة.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Any

TOTAL_PAGES = 604
READING_KEY = "reading_v2"
KHATMA_KEY = "khatma_v2"


def _today(value: dt.date | None = None) -> dt.date:
    return value or dt.date.today()


def _json_value(settings, key: str, default: Any) -> Any:
    raw = settings.value(key, "", type=str)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _save_json(settings, key: str, value: Any) -> None:
    settings.setValue(key, json.dumps(value, ensure_ascii=False, sort_keys=True))
    settings.sync()


def _valid_date_key(value: object) -> bool:
    try:
        dt.date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def reading_state(settings) -> dict:
    """يعيد سجل القراءة ويهاجر عدادات ``days`` القديمة مرة واحدة.

    العدادات القديمة لا تعرف أرقام الصفحات، لذلك تُحفظ كخط أساس تاريخي، بينما
    يسجل الإصدار الجديد أرقام الصفحات المختلفة لكل يوم لمنع العد المكرر.
    """
    value = _json_value(settings, READING_KEY, None)
    if isinstance(value, dict) and value.get("schema") == 2:
        legacy = value.get("legacy_counts")
        pages = value.get("pages")
        if isinstance(legacy, dict) and isinstance(pages, dict):
            return value

    old = _json_value(settings, "days", {})
    legacy_counts = {}
    if isinstance(old, dict):
        for key, count in old.items():
            try:
                number = max(0, int(count))
            except (TypeError, ValueError):
                continue
            if number and _valid_date_key(key):
                legacy_counts[str(key)] = number
    value = {"schema": 2, "legacy_counts": legacy_counts, "pages": {}}
    _save_json(settings, READING_KEY, value)
    return value


def reading_pages(settings, day: dt.date | None = None) -> list[int]:
    key = _today(day).isoformat()
    raw = reading_state(settings).get("pages", {}).get(key, [])
    if not isinstance(raw, list):
        return []
    return sorted({int(p) for p in raw if isinstance(p, int) and 1 <= p <= TOTAL_PAGES})


def reading_count(settings, day: dt.date | None = None) -> int:
    key = _today(day).isoformat()
    state = reading_state(settings)
    try:
        legacy = max(0, int(state.get("legacy_counts", {}).get(key, 0)))
    except (TypeError, ValueError):
        legacy = 0
    raw = state.get("pages", {}).get(key, [])
    current = len({int(p) for p in raw if isinstance(p, int) and 1 <= p <= TOTAL_PAGES}) if isinstance(raw, list) else 0
    return legacy + current


def reading_counts(settings) -> dict[str, int]:
    state = reading_state(settings)
    keys = set(state.get("legacy_counts", {})) | set(state.get("pages", {}))
    result = {}
    for key in keys:
        if not _valid_date_key(key):
            continue
        result[str(key)] = reading_count(settings, dt.date.fromisoformat(str(key)))
    return result


def reading_streak(settings, today: dt.date | None = None) -> int:
    day = _today(today)
    if reading_count(settings, day) == 0:
        day -= dt.timedelta(days=1)
    count = 0
    while reading_count(settings, day) > 0 and count < 36500:
        count += 1
        day -= dt.timedelta(days=1)
    return count


def habit_average(settings, today: dt.date | None = None, window: int = 14) -> float:
    """متوسط الصفحات في أيام القراءة الفعلية ضمن النافذة، وليس هدفاً."""
    day = _today(today)
    values = [reading_count(settings, day - dt.timedelta(days=i)) for i in range(max(1, window))]
    active = [value for value in values if value > 0]
    return (sum(active) / len(active)) if active else 0.0


def khatma_state(settings, current_page: int = 1, today: dt.date | None = None) -> dict:
    value = _json_value(settings, KHATMA_KEY, None)
    if isinstance(value, dict) and value.get("schema") == 2:
        try:
            pointer = int(value.get("pointer", 1))
        except (TypeError, ValueError):
            pointer = 1
        value["pointer"] = min(TOTAL_PAGES, max(1, pointer))
        if not isinstance(value.get("finished"), list):
            value["finished"] = []
        if not _valid_date_key(value.get("start_date")):
            value["start_date"] = _today(today).isoformat()
        return value

    # ترحيل موضع الورد السابق فقط؛ عدد الأوراد القديمة ليس عدد ختمات.
    try:
        old_pointer = int(settings.value("wird_next", 0, type=int) or 0)
    except (TypeError, ValueError):
        old_pointer = 0
    pointer = old_pointer if 1 <= old_pointer <= TOTAL_PAGES else int(current_page or 1)
    value = {
        "schema": 2,
        "pointer": min(TOTAL_PAGES, max(1, pointer)),
        "start_date": _today(today).isoformat(),
        "finished": [],
    }
    _save_json(settings, KHATMA_KEY, value)
    settings.setValue("migration/khatma-v2", True)
    settings.sync()
    return value


def save_khatma_state(settings, value: dict) -> None:
    clean = {
        "schema": 2,
        "pointer": min(TOTAL_PAGES, max(1, int(value.get("pointer", 1)))),
        "start_date": str(value.get("start_date") or dt.date.today().isoformat()),
        "finished": list(value.get("finished", []))[-500:],
    }
    _save_json(settings, KHATMA_KEY, clean)


def set_khatma_pointer(settings, page: int, today: dt.date | None = None) -> dict:
    page = min(TOTAL_PAGES, max(1, int(page)))
    value = khatma_state(settings, page, today)
    value["pointer"] = page
    save_khatma_state(settings, value)
    return value


def start_new_khatma(settings, today: dt.date | None = None) -> dict:
    value = khatma_state(settings, 1, today)
    value["pointer"] = 1
    value["start_date"] = _today(today).isoformat()
    save_khatma_state(settings, value)
    return value


def record_reading(settings, page: int, today: dt.date | None = None) -> dict:
    """يسجل صفحة بعد بقائها معروضة، ويقدّم الختمة فقط بالتتابع.

    فتح نتيجة بحث بعيدة لا يتخطى صفحات غير مقروءة: يتقدم المؤشر تلقائياً عندما
    تكون الصفحة المسجلة هي صفحة المتابعة نفسها. ويمكن تصحيح المؤشر من الواجهة.
    """
    page = min(TOTAL_PAGES, max(1, int(page)))
    day = _today(today)
    key = day.isoformat()
    state = reading_state(settings)
    pages = state.setdefault("pages", {})
    raw = pages.get(key, [])
    known = {int(p) for p in raw if isinstance(p, int) and 1 <= p <= TOTAL_PAGES} if isinstance(raw, list) else set()
    is_new_page = page not in known
    if is_new_page:
        known.add(page)
        pages[key] = sorted(known)
        _save_json(settings, READING_KEY, state)

    khatma = khatma_state(settings, page, day)
    advanced = page == int(khatma.get("pointer", 1))
    completed = False
    if advanced:
        if page == TOTAL_PAGES:
            khatma.setdefault("finished", []).append({
                "start": str(khatma.get("start_date") or key),
                "end": key,
            })
            khatma["pointer"] = 1
            khatma["start_date"] = key
            completed = True
        else:
            khatma["pointer"] = page + 1
        save_khatma_state(settings, khatma)

    return {
        "new_page": is_new_page,
        "advanced": advanced,
        "completed": completed,
        "pointer": int(khatma.get("pointer", 1)),
        "today_count": reading_count(settings, day),
    }


def khatma_progress(settings, current_page: int = 1, today: dt.date | None = None) -> dict:
    value = khatma_state(settings, current_page, today)
    pointer = int(value["pointer"])
    read = pointer - 1
    return {
        "pointer": pointer,
        "read": read,
        "left": TOTAL_PAGES - read,
        "percent": (read / TOTAL_PAGES) * 100.0,
        "finished": list(value.get("finished", [])),
        "start_date": value.get("start_date"),
    }


def estimated_finish(settings, current_page: int = 1, today: dt.date | None = None) -> dt.date | None:
    day = _today(today)
    average = habit_average(settings, day)
    if average <= 0:
        return None
    left = khatma_progress(settings, current_page, day)["left"]
    days = max(1, int((left + average - 1) // average))
    return day + dt.timedelta(days=days)


def clear_tracking(settings) -> None:
    for key in (READING_KEY, KHATMA_KEY, "days", "wird_count", "wird_next", "wird_day", "wird_target"):
        settings.remove(key)
    settings.sync()
