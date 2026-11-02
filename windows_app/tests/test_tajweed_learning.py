import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import tajweed_learning as learning  # noqa: E402

NOW = 1_800_000_000_000
SCOPE = {
    "riwayah": "hafs-an-asim",
    "tariq": "source-unspecified",
    "wajh": "source-default",
    "edition": "alquran-cloud-tajweed-v1",
}


def curriculum():
    return {
        "scope": SCOPE,
        "rules": [
            {"id": "a", "order": 1, "name": "الأول", "prompt": "اشرح الأول",
             "answer": "جواب الأول", "learning": {"categoryId": "one",
             "categoryNameAr": "المجموعة الأولى", "level": 1}},
            {"id": "b", "order": 2, "name": "الثاني", "prompt": "اشرح الثاني",
             "answer": "جواب الثاني", "learning": {"categoryId": "two",
             "categoryNameAr": "المجموعة الثانية", "level": 1}},
            {"id": "c", "order": 3, "name": "الثالث", "prompt": "اشرح الثالث",
             "answer": "جواب الثالث", "learning": {"categoryId": "one",
             "categoryNameAr": "المجموعة الأولى", "level": 2}},
            {"id": "d", "order": 4, "name": "الرابع", "prompt": "اشرح الرابع",
             "answer": "جواب الرابع", "learning": {"categoryId": "two",
             "categoryNameAr": "المجموعة الثانية", "level": 2}},
        ],
    }


class TajweedLearningTests(unittest.TestCase):
    def test_locked_catalog_uses_local_tagged_examples_for_all_activities(self):
        catalog = json.loads((HERE / "data" / "tajweed-learning-catalog.json").read_text(encoding="utf-8"))
        rows = json.loads((HERE / "data" / "quran-tajweed.json").read_text(encoding="utf-8"))
        locked = next(item for item in catalog["curricula"]
                      if item["scope"]["riwayah"] == "hafs-an-asim")
        cards = learning.build_cards(locked, rows)
        self.assertEqual(len(cards), 51)
        self.assertTrue(all(card["example"] and card["example"]["text"] for card in cards))
        self.assertTrue(all(card["tagCode"] in learning.TAG_COLORS for card in cards))
        self.assertTrue(all(1 <= card["example"]["surah"] <= 114 and card["example"]["ayah"] > 0
                            for card in cards))

    def test_builds_three_scoped_stages_per_rule(self):
        cards = learning.build_cards(curriculum())
        self.assertEqual(len(cards), 12)
        self.assertEqual([card["activityType"] for card in cards[:3]],
                         ["learn", "recognize", "apply"])
        self.assertEqual(cards[1]["prerequisites"], ["a"])
        self.assertEqual(cards[2]["prerequisites"], ["a.recognize"])
        self.assertTrue(all(learning.scope_key(card["scope"]) == learning.scope_key(SCOPE)
                            for card in cards))

    def test_plan_unlocks_recognition_after_success(self):
        cards = learning.build_cards(curriculum())
        initial = learning.adaptive_plan(cards, {"config": {"newPerDay": 20}}, SCOPE, NOW)
        self.assertTrue(initial)
        self.assertTrue(all(item["card"]["activityType"] == "learn" for item in initial))
        first = next(card for card in cards if card["id"] == "a")
        state = learning.apply_review({}, first, "good", NOW - learning.DAY_MS)
        plan = learning.adaptive_plan(cards, state, SCOPE, NOW)
        self.assertIn("a.recognize", [item["card"]["id"] for item in plan])
        self.assertNotIn("a.apply", [item["card"]["id"] for item in plan])

    def test_weak_due_card_is_first(self):
        cards = learning.build_cards(curriculum())
        a = next(card for card in cards if card["id"] == "a")
        b = next(card for card in cards if card["id"] == "b")
        state = {"progress": {
            a["key"]: {"introducedAt": NOW - 10 * learning.DAY_MS,
                       "dueAt": NOW - learning.DAY_MS, "reviewCount": 6,
                       "correctCount": 2, "lapses": 3, "lastRating": "again"},
            b["key"]: {"introducedAt": NOW - 10 * learning.DAY_MS,
                       "dueAt": NOW - 2 * learning.DAY_MS, "reviewCount": 6,
                       "correctCount": 6, "repetitions": 4, "lastRating": "good"},
        }}
        plan = learning.adaptive_plan(cards, state, SCOPE, NOW)
        self.assertEqual(plan[0]["card"]["id"], "a")
        self.assertEqual(plan[0]["reason"], "weak-review")

    def test_recognition_options_are_deterministic_and_have_one_answer(self):
        cards = learning.build_cards(curriculum())
        target = next(card for card in cards if card["id"] == "a.recognize")
        first = learning.recognition_options(target, cards)
        self.assertEqual(first, learning.recognition_options(target, cards))
        self.assertEqual(len(first), 4)
        self.assertEqual(sum(item["correct"] for item in first), 1)

    def test_state_is_local_bounded_and_mastery_is_reported(self):
        cards = learning.build_cards(curriculum())
        first = cards[0]
        state = learning.apply_review({}, first, "easy", NOW)
        stats = learning.path_stats(cards, state, SCOPE, NOW)
        self.assertEqual(stats["total"], 12)
        self.assertEqual(stats["introduced"], 1)
        self.assertGreater(stats["mastery"], 0)
        self.assertLessEqual(stats["mastery"], 1)
        self.assertIsNone(learning.apply_review(state, first, "perfect", NOW))

        corrupt = {"progress": {first["key"]: {
            "introducedAt": 10**40, "lastReviewedAt": 10**40, "dueAt": 10**40,
        }}}
        normalized = learning.normalize_state(corrupt)["progress"][first["key"]]
        self.assertTrue(all(normalized[field] <= learning.MAX_TIMESTAMP_MS
                            for field in ("introducedAt", "lastReviewedAt", "dueAt")))
        self.assertIsInstance(learning.adaptive_plan(cards, corrupt, SCOPE, NOW), list)


if __name__ == "__main__":
    unittest.main()
