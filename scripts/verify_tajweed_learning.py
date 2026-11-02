#!/usr/bin/env python3
"""Fail-closed checks for the scoped tajweed learning catalogue."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    catalog = load("tajweed-learning-catalog.json")
    authored = load("mushaf_app/data/tajweed.json")
    tagged = load("quran-tajweed.json")

    assert catalog["schema"] == 1
    curricula = catalog["curricula"]
    assert isinstance(curricula, list) and curricula
    scope_keys: set[tuple[str, str, str, str]] = set()
    for curriculum in curricula:
        scope = curriculum["scope"]
        scope_key = tuple(scope[key] for key in ("riwayah", "tariq", "wajh", "edition"))
        assert all(TOKEN.fullmatch(value) for value in scope_key), scope_key
        assert scope_key not in scope_keys, scope_key
        scope_keys.add(scope_key)
        assert curriculum["status"] in {"PENDING_SCHOLARLY_REVIEW", "APPROVED"}
        if curriculum["status"] != "APPROVED":
            assert curriculum["publishableAsApproved"] is False
            assert "لا يُعد اعتمادًا علميًا" in curriculum["scopeWarning"]
        rule_ids = [rule["id"] for rule in curriculum["rules"]]
        assert len(rule_ids) == len(set(rule_ids))
        assert all(TOKEN.fullmatch(rule_id) for rule_id in rule_ids)

    hafs = next(item for item in curricula if item["scope"]["riwayah"] == "hafs-an-asim")
    assert hafs["scope"]["tariq"] == "source-unspecified"
    assert hafs["status"] == "PENDING_SCHOLARLY_REVIEW"
    assert hafs["publishableAsApproved"] is False
    rules = hafs["rules"]
    assert [rule["id"] for rule in rules] == list(authored)
    for rule in rules:
        name, answer = authored[rule["id"]]
        assert rule["name"] == name
        assert rule["answer"] == answer
        tag = rule["tagCode"]
        pattern = re.compile(rf"\[{re.escape(tag)}(?::\d+)?\[")
        assert any(pattern.search(str(row[3])) for row in tagged), f"tag without example: {tag}"

    unavailable = {item["settingId"]: item for item in catalog["unavailable"]}
    assert set(unavailable) == {"warsh", "qalun", "duri"}
    assert all(item["reason"] == "NO_REVIEWED_RULE_CORPUS_OR_DOCUMENTED_TARIQ"
               for item in unavailable.values())
    assert not any(item["scope"]["riwayah"].startswith(("warsh", "qalun", "al-duri"))
                   for item in curricula)

    print(
        "Verified tajweed learning catalogue: "
        f"{len(rules)} scoped Hafs draft rules; Warsh/Qalun/Duri fail closed"
    )


if __name__ == "__main__":
    main()
