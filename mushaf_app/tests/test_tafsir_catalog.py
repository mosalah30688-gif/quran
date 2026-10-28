import gzip
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "mushaf_app/data/tafsir-catalog.json"
SOURCE_DIR = ROOT / "audit/sources/quranpedia-tafsir/2026-10-28"


class TafsirCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.source_record = json.loads((SOURCE_DIR / "SOURCE.json").read_text(encoding="utf-8"))

    def test_catalog_is_offline_licensed_classical_metadata(self):
        books = self.catalog["books"]
        self.assertEqual(73, len(books))
        self.assertEqual(73, len({book["edition"] for book in books}))
        self.assertTrue(self.catalog["selection"]["offline_text_bundled"])
        self.assertEqual("2026-08-10", self.catalog["selection"]["book_dump_version"])
        self.assertEqual("2026-10-24", self.catalog["dump_version"])
        self.assertTrue(all(book["edition"] == f"qp:{book['book_id']}" for book in books))
        self.assertTrue(all(book["author_death_hijri"] <= 1350 for book in books))
        self.assertTrue(all(not book["name"].startswith(("جهود ", "آراء ")) for book in books))

    def test_source_dump_and_output_match_locked_hashes(self):
        source = SOURCE_DIR / "tafsir.json.gz"
        raw = source.read_bytes()
        source_meta = self.source_record["files"]["tafsir.json.gz"]
        self.assertEqual(source_meta["bytes"], len(raw))
        self.assertEqual(source_meta["sha256"], hashlib.sha256(raw).hexdigest())
        # The highly repetitive 6236-row service dump expands to hundreds of
        # megabytes. Inspect its signed envelope prefix without materializing
        # the whole JSON in the unit-test process (the generator validates all rows).
        with gzip.open(source, "rt", encoding="utf-8") as stream:
            prefix = stream.read(32_768)
        self.assertIn('"schema":"/v1/ayah/{surah}/{ayah}/tafsir"', prefix)
        self.assertIn('"source":"https://quranpedia.net"', prefix)
        output_meta = self.source_record["outputs"]["mushaf_app/data/tafsir-catalog.json"]
        output_raw = CATALOG_PATH.read_bytes()
        self.assertEqual(output_meta["bytes"], len(output_raw))
        self.assertEqual(output_meta["sha256"], hashlib.sha256(output_raw).hexdigest())

    def test_core_reference_works_are_present_without_alquran_duplicates(self):
        editions = {book["edition"] for book in self.catalog["books"]}
        self.assertTrue({"qp:4", "qp:136", "qp:1499", "qp:350", "qp:352"} <= editions)
        # Baghawi, Jalalayn and Tanwir al-Miqbas already exist in the separately
        # audited AlQuran Cloud list and are intentionally not duplicated here.
        self.assertTrue({"qp:2", "qp:261", "qp:272", "qp:363"}.isdisjoint(editions))


if __name__ == "__main__":
    unittest.main()
