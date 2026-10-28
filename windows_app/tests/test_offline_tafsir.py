import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "windows_app"
sys.path.insert(0, str(APP))

from offline_tafsir import OfflineTafsirStore  # noqa: E402


class OfflineTafsirTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = APP / "data/tafsir-offline.sqlite3"
        cls.lock = json.loads((ROOT / "audit/offline-tafsir-data.json").read_text(encoding="utf-8"))
        if not cls.database.is_file():
            raise unittest.SkipTest("locked offline tafsir asset has not been fetched")

    def test_asset_matches_immutable_lock_and_schema(self):
        digest = hashlib.sha256()
        with self.database.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        self.assertEqual(self.lock["asset"]["bytes"], self.database.stat().st_size)
        self.assertEqual(self.lock["asset"]["sha256"], digest.hexdigest())
        connection = sqlite3.connect(f"file:{self.database}?mode=ro&immutable=1", uri=True)
        try:
            self.assertEqual("ok", connection.execute("PRAGMA quick_check").fetchone()[0])
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            editions = dict(connection.execute("SELECT edition,source FROM editions"))
            self.assertEqual(78, len(editions))
            self.assertEqual(73, sum(source == "quranpedia" for source in editions.values()))
            self.assertEqual(5, sum(source == "alquran.cloud" for source in editions.values()))
            self.assertEqual("https://quranpedia.net", metadata["quranpedia_source"])
            self.assertEqual("2026-08-10", metadata["quranpedia_dump_version"])
            self.assertEqual("344605", str(int(metadata["quranpedia_source_ayahs"]) + int(metadata["alquran_source_ayahs"])))
        finally:
            connection.close()

    def test_representative_books_load_without_network(self):
        store = OfflineTafsirStore(self.database, cache_chunks=2)
        try:
            handled, short_text = store.lookup("ar.muyassar", 1, 1)
            self.assertTrue(handled)
            self.assertIn("الفاتحة", short_text)
            handled, large_text = store.lookup("qp:301", 2, 255)
            self.assertTrue(handled)
            self.assertGreater(len(large_text), 10_000)
            # Sparse works are represented locally too: missing coverage is a
            # valid source result, not a network/load failure.
            handled, absent = store.lookup("qp:27774", 1, 1)
            self.assertTrue(handled)
            self.assertIsNone(absent)
            handled, absent = store.lookup("unknown-edition", 1, 1)
            self.assertFalse(handled)
            self.assertIsNone(absent)
            self.assertLessEqual(len(store._cache), 2)
        finally:
            store.close()

    def test_catalog_and_database_contain_the_same_78_editions(self):
        catalog = json.loads((APP / "data/tafsir-catalog.json").read_text(encoding="utf-8"))
        expected = {item["edition"] for item in catalog["books"]} | {
            "ar.muyassar", "ar.jalalayn", "ar.baghawi", "ar.qurtubi", "ar.miqbas"
        }
        store = OfflineTafsirStore(self.database)
        try:
            self.assertTrue(store.available)
            self.assertEqual(expected, set(store.editions))
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
