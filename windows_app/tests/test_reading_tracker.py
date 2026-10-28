import datetime as dt
import json
import sys
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import reading_tracker as tracker  # noqa: E402


class Settings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        if type is None:
            return value
        try:
            if type is bool and isinstance(value, str):
                return value.lower() in {"1", "true", "yes"}
            return type(value)
        except (TypeError, ValueError):
            return default

    def setValue(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)

    def sync(self):
        pass


class ReadingTrackerTests(unittest.TestCase):
    DAY = dt.date(2026, 10, 28)

    def test_migrates_old_counts_and_counts_each_new_page_once(self):
        settings = Settings({"days": json.dumps({self.DAY.isoformat(): 3}), "wird_next": 10})
        first = tracker.record_reading(settings, 10, self.DAY)
        again = tracker.record_reading(settings, 10, self.DAY)
        self.assertTrue(first["new_page"])
        self.assertFalse(again["new_page"])
        self.assertEqual(tracker.reading_count(settings, self.DAY), 4)
        self.assertEqual(tracker.khatma_progress(settings, today=self.DAY)["pointer"], 11)

    def test_khatma_advances_only_from_the_expected_page(self):
        settings = Settings({"wird_next": 20})
        jumped = tracker.record_reading(settings, 100, self.DAY)
        self.assertFalse(jumped["advanced"])
        self.assertEqual(tracker.khatma_progress(settings, today=self.DAY)["pointer"], 20)
        expected = tracker.record_reading(settings, 20, self.DAY)
        self.assertTrue(expected["advanced"])
        self.assertEqual(expected["pointer"], 21)

    def test_finishing_page_604_records_a_khatma_and_wraps(self):
        settings = Settings({"wird_next": 604})
        result = tracker.record_reading(settings, 604, self.DAY)
        info = tracker.khatma_progress(settings, today=self.DAY)
        self.assertTrue(result["completed"])
        self.assertEqual(info["pointer"], 1)
        self.assertEqual(len(info["finished"]), 1)
        self.assertEqual(info["finished"][0]["end"], self.DAY.isoformat())

    def test_habit_average_is_observed_not_a_target(self):
        settings = Settings({"wird_next": 1})
        tracker.record_reading(settings, 1, self.DAY - dt.timedelta(days=2))
        tracker.record_reading(settings, 2, self.DAY - dt.timedelta(days=2))
        tracker.record_reading(settings, 3, self.DAY - dt.timedelta(days=1))
        self.assertEqual(tracker.habit_average(settings, self.DAY), 1.5)
        self.assertNotIn("target", tracker.khatma_state(settings, today=self.DAY))

    def test_manual_pointer_and_new_khatma_preserve_reading_history(self):
        settings = Settings()
        tracker.record_reading(settings, 1, self.DAY)
        tracker.set_khatma_pointer(settings, 300, self.DAY)
        self.assertEqual(tracker.khatma_progress(settings, today=self.DAY)["pointer"], 300)
        tracker.start_new_khatma(settings, self.DAY)
        self.assertEqual(tracker.khatma_progress(settings, today=self.DAY)["pointer"], 1)
        self.assertEqual(tracker.reading_count(settings, self.DAY), 1)

    def test_clear_tracking_removes_old_and_new_keys(self):
        settings = Settings({
            "days": "{}", "wird_target": 5, "wird_next": 4,
            tracker.READING_KEY: "{}", tracker.KHATMA_KEY: "{}",
        })
        tracker.clear_tracking(settings)
        for key in ("days", "wird_target", "wird_next", tracker.READING_KEY, tracker.KHATMA_KEY):
            self.assertNotIn(key, settings.values)


if __name__ == "__main__":
    unittest.main()
