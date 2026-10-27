import json
import re
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


class QuranDataIntegrityTests(unittest.TestCase):
    def test_hafs_sets_match_canonical_counts(self):
        hafs = load("hafs.json")
        surahs = load("surahs.json")
        expected = sum(int(s["numberOfAyahs"]) for s in surahs)
        self.assertEqual(expected, 6236)
        for name in ("uthmani", "simple"):
            rows = hafs[name]
            self.assertEqual(len(rows), expected)
            self.assertEqual(len({(r[0], r[1]) for r in rows}), expected)
            self.assertEqual(rows[0][:3], [1, 1, 1])
            self.assertEqual(rows[-1][:3], [114, 6, 604])

    def test_local_tajweed_covers_all_hafs_ayahs(self):
        rows = load("quran-tajweed.json")
        self.assertEqual(len(rows), 6236)
        self.assertEqual(len({(r[0], r[1]) for r in rows}), 6236)
        self.assertEqual(rows[0][:3], [1, 1, 1])
        self.assertEqual(rows[-1][:3], [114, 6, 604])
        self.assertTrue(any(re.search(r"\[[a-z]+(?::\d+)?\[", r[3]) for r in rows))
        self.assertTrue(all(1 <= int(r[2]) <= 604 and str(r[3]).strip() for r in rows))

    def test_riwaya_numbering_is_unique_within_each_source(self):
        sources = load("quran-riwayat.json")["riwayat"]
        self.assertEqual(set(sources), {"warsh", "qalun", "duri"})
        for name, rows in sources.items():
            with self.subTest(name=name):
                self.assertEqual(len(rows), len({(r[0], r[1]) for r in rows}))
                self.assertEqual(rows[0][0], 1)
                self.assertEqual(rows[-1][0], 114)
                self.assertTrue(all(1 <= int(r[2]) <= 604 and str(r[3]).strip() for r in rows))


if __name__ == "__main__":
    unittest.main()
