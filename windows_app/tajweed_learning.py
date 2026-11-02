"""Local adaptive tajweed learning for Siraj desktop applications.

The module contains scheduling only. Rule text stays in the scoped curriculum
JSON so riwayah/tariq/wajh/edition data never falls back across scopes.
"""
from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import math
import re
import time
from typing import Any

DAY_MS = 86_400_000
TEN_MINUTES_MS = 600_000
MAX_INTERVAL_DAYS = 365
MAX_TIMESTAMP_MS = 4_102_444_800_000  # 2100-01-01; safely representable on supported desktops.
RATINGS = ("again", "hard", "good", "easy")
ACTIVITY_TYPES = ("learn", "recognize", "apply")
DEFAULT_CONFIG = {"newPerDay": 5, "reviewsPerDay": 20}
TAG_COLORS = {
    "h": "#8a8a8a", "s": "#8a8a8a", "l": "#8a8a8a",
    "n": "#537fff", "p": "#4050ff", "m": "#2536d6", "o": "#2144c1",
    "q": "#dd0008", "c": "#d500b7", "f": "#9400a8", "w": "#4d9f00",
    "i": "#168fbf", "a": "#169777", "u": "#147d00", "d": "#8a8a8a",
    "b": "#8a8a8a", "g": "#e26600",
}
WEAK_THRESHOLD = 0.45
MASTERY_THRESHOLD = 0.70
_TOKEN = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_TAGGED_TOKEN = re.compile(r"\[([a-z]+)(?::\d+)?\[([^\[\]]*)\]")
_SCOPE_FIELDS = ("riwayah", "tariq", "wajh", "edition")


def _clamp(value: Any, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    if not math.isfinite(number):
        return low
    return min(high, max(low, number))


def _token(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text if _TOKEN.fullmatch(text) else None


def normalize_scope(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    result = {field: _token(value.get(field)) for field in _SCOPE_FIELDS}
    return result if all(result.values()) else None


def scope_key(value: Any) -> str | None:
    scope = normalize_scope(value)
    return "/".join(scope[field] for field in _SCOPE_FIELDS) if scope else None


def normalize_config(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    return {
        "newPerDay": round(_clamp(source.get("newPerDay", 5), 1, 20)),
        "reviewsPerDay": round(_clamp(source.get("reviewsPerDay", 20), 5, 100)),
    }


def normalize_entry(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    rating = source.get("lastRating")
    return {
        "dueAt": max(0, round(_clamp(source.get("dueAt", 0), 0, MAX_TIMESTAMP_MS))),
        "intervalDays": _clamp(source.get("intervalDays", 0), 0, MAX_INTERVAL_DAYS),
        "ease": _clamp(source.get("ease", 2.5), 1.3, 3),
        "repetitions": round(_clamp(source.get("repetitions", 0), 0, 10_000)),
        "lapses": round(_clamp(source.get("lapses", 0), 0, 10_000)),
        "reviewCount": round(_clamp(source.get("reviewCount", 0), 0, 1_000_000)),
        "correctCount": round(_clamp(source.get("correctCount", 0), 0, 1_000_000)),
        "introducedAt": max(0, round(_clamp(source.get("introducedAt", 0), 0, MAX_TIMESTAMP_MS))),
        "lastReviewedAt": max(0, round(_clamp(source.get("lastReviewedAt", 0), 0, MAX_TIMESTAMP_MS))),
        "lastRating": rating if rating in RATINGS else None,
        "suspended": bool(source.get("suspended", False)),
        "leech": bool(source.get("leech", False)),
    }


def normalize_state(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    progress: dict[str, dict[str, Any]] = {}
    raw = source.get("progress") if isinstance(source.get("progress"), dict) else {}
    for key in list(raw)[:20_000]:
        if isinstance(key, str) and len(key) <= 320 and "::" in key:
            progress[key] = normalize_entry(raw[key])
    return {"schema": 1, "config": normalize_config(source.get("config")), "progress": progress}


def normalize_card(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    card_id = _token(value.get("id"))
    scope = normalize_scope(value.get("scope"))
    if not card_id or not scope:
        return None
    base_id = _token(value.get("baseId")) or card_id
    activity = value.get("activityType") if value.get("activityType") in ACTIVITY_TYPES else "learn"
    category = _token(value.get("category")) or "general"
    prerequisites = []
    for raw in (value.get("prerequisites") if isinstance(value.get("prerequisites"), list) else [])[:12]:
        item = _token(raw)
        if item and item != card_id and item not in prerequisites:
            prerequisites.append(item)
    result = dict(value)
    result.update({
        "id": card_id,
        "baseId": base_id,
        "scope": scope,
        "activityType": activity,
        "category": category,
        "level": round(_clamp(value.get("level", 1), 1, 10)),
        "stage": round(_clamp(value.get("stage", 1), 1, 10)),
        "prerequisites": prerequisites,
        "key": f"{scope_key(scope)}::{card_id}",
    })
    return result


def tagged_examples(rows: Any) -> dict[str, dict[str, Any]]:
    """Extract one locked local quran-tajweed example per source tag."""
    examples: dict[str, dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, list) or len(row) < 4:
            continue
        raw = str(row[3])
        for match in _TAGGED_TOKEN.finditer(raw):
            tag_code = _token(match.group(1))
            if not tag_code or tag_code in examples:
                continue
            try:
                surah, ayah = int(row[0]), int(row[1])
            except (TypeError, ValueError):
                continue
            examples[tag_code] = {
                "text": match.group(2).strip(),
                "ayahText": _TAGGED_TOKEN.sub(lambda item: item.group(2), raw).strip(),
                "surah": surah,
                "ayah": ayah,
            }
    return examples


def build_cards(curriculum: Any, tagged_rows: Any = None) -> list[dict[str, Any]]:
    if not isinstance(curriculum, dict) or not normalize_scope(curriculum.get("scope")):
        return []
    scope = normalize_scope(curriculum["scope"])
    source_examples = tagged_examples(tagged_rows)
    result: list[dict[str, Any]] = []
    for rule in curriculum.get("rules", []):
        if not isinstance(rule, dict) or not _token(rule.get("id")):
            continue
        learning = rule.get("learning") if isinstance(rule.get("learning"), dict) else {}
        category = _token(learning.get("categoryId")) or "general"
        category_name = str(learning.get("categoryNameAr") or "أساسيات التجويد").strip()
        level = round(_clamp(learning.get("level", 1), 1, 3))
        order = round(_clamp(rule.get("order", 0), 0, 100_000)) * 10
        tag_code = _token(rule.get("tagCode"))
        inline_example = rule.get("example") if isinstance(rule.get("example"), dict) else None
        example = inline_example or source_examples.get(tag_code or "")
        shared = {
            "baseId": rule["id"], "scope": scope, "ruleName": str(rule.get("name", "")),
            "tagCode": tag_code or "", "category": category,
            "categoryName": category_name, "level": level,
            "answer": str(rule.get("answer", "")), "example": example,
        }
        recognize_name = "تمييز الحكم من المثال" if example else "تمييز الحكم من الوصف"
        recognize_prompt = (
            "ما الحكم التجويدي الملوّن في هذا المثال؟ اختر الإجابة ثم راجع الشرح."
            if example else f"أي حكم يطابق هذا الوصف؟ {rule.get('answer', '')}"
        )
        apply_prompt = (
            f"اقرأ المثال وطبّق حكم «{rule.get('name', '')}»، ثم اشرح طريقة الأداء قبل كشف الجواب."
            if example else f"طبّق حكم «{rule.get('name', '')}» ثم اشرح طريقة الأداء قبل كشف الجواب."
        )
        activities = [
            {**shared, "id": rule["id"], "order": order + 1, "stage": 1,
             "activityType": "learn", "prerequisites": [], "name": str(rule.get("name", "")),
             "prompt": str(rule.get("prompt", ""))},
            {**shared, "id": f"{rule['id']}.recognize", "order": order + 2, "stage": 2,
             "activityType": "recognize", "prerequisites": [rule["id"]],
             "name": recognize_name, "prompt": recognize_prompt,
             "answer": f"الحكم هو «{rule.get('name', '')}». {rule.get('answer', '')}"},
            {**shared, "id": f"{rule['id']}.apply", "order": order + 3, "stage": 3,
             "activityType": "apply", "prerequisites": [f"{rule['id']}.recognize"],
             "name": f"تطبيق «{rule.get('name', '')}»", "prompt": apply_prompt},
        ]
        result.extend(card for item in activities if (card := normalize_card(item)))
    return result


def _local_day(timestamp_ms: int) -> str:
    return _dt.datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")


def _same_day(left: int, right: int) -> bool:
    return left > 0 and right > 0 and _local_day(left) == _local_day(right)


def entry_mastery(value: Any) -> float:
    entry = normalize_entry(value)
    if not entry["introducedAt"] and not entry["reviewCount"]:
        return 0.0
    accuracy = entry["correctCount"] / entry["reviewCount"] if entry["reviewCount"] else 0
    repetition = min(1, entry["repetitions"] / 3)
    stability = min(1, entry["intervalDays"] / 21)
    penalty = min(0.45, entry["lapses"] * 0.07 + (0.12 if entry["leech"] else 0))
    return _clamp(0.15 + repetition * 0.4 + accuracy * 0.3 + stability * 0.15 - penalty, 0, 1)


def entry_weakness(value: Any) -> float:
    entry = normalize_entry(value)
    if not entry["introducedAt"] and not entry["reviewCount"]:
        return 0.0
    accuracy = entry["correctCount"] / entry["reviewCount"] if entry["reviewCount"] else 0
    recent = 0.22 if entry["lastRating"] == "again" else (0.1 if entry["lastRating"] == "hard" else 0)
    return _clamp((1 - accuracy) * 0.45 + min(1, entry["lapses"] / 4) * 0.28
                  + recent + (0.2 if entry["leech"] else 0), 0, 1)


def reviewed_entry(previous: Any, rating: str, now_ms: int) -> dict[str, Any] | None:
    if rating not in RATINGS:
        return None
    entry = normalize_entry(previous)
    first = not entry["introducedAt"]
    result = dict(entry)
    result["introducedAt"] = entry["introducedAt"] or now_ms
    result["lastReviewedAt"] = now_ms
    result["lastRating"] = rating
    result["reviewCount"] += 1
    if rating != "again":
        result["correctCount"] += 1
    if rating == "again":
        result["repetitions"] = 0
        result["intervalDays"] = 0
        result["ease"] = _clamp(entry["ease"] - 0.2, 1.3, 3)
        result["lapses"] = entry["lapses"] + (0 if first else 1)
        result["dueAt"] = now_ms + TEN_MINUTES_MS
    elif rating == "hard":
        result["intervalDays"] = 1 if first else _clamp(max(1, entry["intervalDays"] * 1.2), 1, 365)
        result["ease"] = _clamp(entry["ease"] - 0.15, 1.3, 3)
        result["dueAt"] = now_ms + round(result["intervalDays"] * DAY_MS)
    elif rating == "good":
        result["repetitions"] = entry["repetitions"] + 1
        if entry["repetitions"] == 0:
            result["intervalDays"] = 1
        elif entry["repetitions"] == 1:
            result["intervalDays"] = 3
        else:
            result["intervalDays"] = _clamp(round(entry["intervalDays"] * entry["ease"]), 1, 365)
        result["dueAt"] = now_ms + round(result["intervalDays"] * DAY_MS)
    else:
        result["repetitions"] = entry["repetitions"] + 1
        result["ease"] = _clamp(entry["ease"] + 0.15, 1.3, 3)
        result["intervalDays"] = 4 if first else _clamp(
            max(4, round(max(1, entry["intervalDays"]) * result["ease"] * 1.3)), 1, 365)
        result["dueAt"] = now_ms + round(result["intervalDays"] * DAY_MS)
    result["leech"] = result["lapses"] >= 8
    return normalize_entry(result)


def _scoped_cards(cards: Any, scope: Any) -> list[dict[str, Any]]:
    wanted = scope_key(scope)
    seen = set()
    output = []
    for value in cards if isinstance(cards, list) else []:
        card = normalize_card(value)
        if card and scope_key(card["scope"]) == wanted and card["key"] not in seen:
            seen.add(card["key"])
            output.append(card)
    return output


def _prerequisites_met(card: dict[str, Any], progress: dict[str, Any], by_id: dict[str, Any]) -> bool:
    prefix = scope_key(card["scope"])
    for prerequisite in card["prerequisites"]:
        entry = progress.get(f"{prefix}::{prerequisite}")
        if prerequisite not in by_id or not entry or entry["suspended"] \
                or entry["correctCount"] < 1 or entry["lastRating"] == "again":
            return False
    return True


def adaptive_plan(cards: Any, state_value: Any, scope: Any, now_ms: int | None = None) -> list[dict[str, Any]]:
    now_ms = round(time.time() * 1000) if now_ms is None else int(now_ms)
    state = normalize_state(state_value)
    all_cards = _scoped_cards(cards, scope)
    wanted = scope_key(scope)
    if not wanted:
        return []
    prefix = f"{wanted}::"
    entries = [entry for key, entry in state["progress"].items() if key.startswith(prefix)]
    review_slots = max(0, state["config"]["reviewsPerDay"]
                       - sum(_same_day(entry["lastReviewedAt"], now_ms) for entry in entries))
    new_slots = max(0, state["config"]["newPerDay"]
                    - sum(_same_day(entry["introducedAt"], now_ms) for entry in entries))
    by_id = {card["id"]: card for card in all_cards}
    due = [card for card in all_cards if card["key"] in state["progress"]
           and not state["progress"][card["key"]]["suspended"]
           and state["progress"][card["key"]]["dueAt"] <= now_ms]
    due.sort(key=lambda card: (
        -int(state["progress"][card["key"]]["leech"]),
        -entry_weakness(state["progress"][card["key"]]),
        state["progress"][card["key"]]["dueAt"], card["stage"], card["id"],
    ))
    output = []
    for card in due[:review_slots]:
        entry = state["progress"][card["key"]]
        weakness = entry_weakness(entry)
        output.append({"card": card, "kind": "review", "progress": entry,
                       "reason": "weak-review" if entry["leech"] or weakness >= WEAK_THRESHOLD
                       else "due-review", "weakness": weakness})
    fresh = [card for card in all_cards if card["key"] not in state["progress"]
             and _prerequisites_met(card, state["progress"], by_id)]
    fresh.sort(key=lambda card: (card["level"], card["stage"], card.get("order", 0), card["id"]))
    interleaved = []
    previous = None
    while fresh:
        index = next((i for i, card in enumerate(fresh) if card["category"] != previous), 0)
        card = fresh.pop(index)
        interleaved.append(card)
        previous = card["category"]
    for card in interleaved[:new_slots]:
        output.append({"card": card, "kind": "new", "progress": None, "weakness": 0,
                       "reason": "new-unlocked" if card["prerequisites"] else "new-foundation"})
    return output


def path_stats(cards: Any, state_value: Any, scope: Any, now_ms: int | None = None) -> dict[str, Any]:
    now_ms = round(time.time() * 1000) if now_ms is None else int(now_ms)
    state = normalize_state(state_value)
    all_cards = _scoped_cards(cards, scope)
    by_id = {card["id"]: card for card in all_cards}
    result = {"total": len(all_cards), "introduced": 0, "mastered": 0, "weak": 0,
              "due": 0, "unlocked": 0, "locked": 0, "mastery": 0.0}
    mastery_sum = 0.0
    for card in all_cards:
        entry = state["progress"].get(card["key"])
        mastery = entry_mastery(entry) if entry else 0
        weakness = entry_weakness(entry) if entry else 0
        result["introduced"] += int(bool(entry))
        result["mastered"] += int(bool(entry) and mastery >= MASTERY_THRESHOLD)
        result["weak"] += int(bool(entry) and (entry["leech"] or weakness >= WEAK_THRESHOLD))
        result["due"] += int(bool(entry) and not entry["suspended"] and entry["dueAt"] <= now_ms)
        if not entry:
            if _prerequisites_met(card, state["progress"], by_id):
                result["unlocked"] += 1
            else:
                result["locked"] += 1
        mastery_sum += mastery
    result["mastery"] = mastery_sum / len(all_cards) if all_cards else 0
    result["learning"] = result["introduced"] - result["mastered"]
    return result


def recognition_options(card_value: Any, cards: Any, limit: int = 4) -> list[dict[str, Any]]:
    target = normalize_card(card_value)
    if not target or target["activityType"] != "recognize":
        return []
    roots = []
    seen = set()
    for card in _scoped_cards(cards, target["scope"]):
        if card["activityType"] == "learn" and card["baseId"] not in seen and card.get("ruleName"):
            seen.add(card["baseId"])
            roots.append(card)
    answer = next((card for card in roots if card["baseId"] == target["baseId"]), None)
    if not answer or len(roots) < 2:
        return []
    def digest(label: str) -> str:
        return hashlib.sha256(label.encode("utf-8")).hexdigest()
    distractors = sorted(
        (card for card in roots if card["baseId"] != target["baseId"]),
        key=lambda card: (-int(card["category"] == target["category"]),
                          digest(f"{target['key']}/{card['baseId']}"), card["baseId"]),
    )[:max(1, min(6, int(limit))) - 1]
    options = [{"id": card["baseId"], "label": card["ruleName"],
                "correct": card["baseId"] == target["baseId"]}
               for card in [answer, *distractors]]
    return sorted(options, key=lambda item: (digest(f"option/{target['key']}/{item['id']}"), item["id"]))


def apply_review(state_value: Any, card_value: Any, rating: str,
                 now_ms: int | None = None) -> dict[str, Any] | None:
    card = normalize_card(card_value)
    if not card or rating not in RATINGS:
        return None
    now_ms = round(time.time() * 1000) if now_ms is None else int(now_ms)
    state = normalize_state(copy.deepcopy(state_value))
    state["progress"][card["key"]] = reviewed_entry(state["progress"].get(card["key"]), rating, now_ms)
    return state
