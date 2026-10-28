import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import main as app  # noqa: E402


class ReciterCatalogTests(unittest.TestCase):
    def test_catalog_has_17_distinct_hafs_voices(self):
        identifiers = [row[0] for row in app.HAFS_RECITERS]
        names = [row[1] for row in app.HAFS_RECITERS]
        self.assertEqual(len(identifiers), 17)
        self.assertEqual(len(set(identifiers)), 17)
        self.assertEqual(len(set(names)), 17)
        self.assertIn("ar.parhizgar", identifiers)

    def test_cdn_urls_use_canonical_global_ayah_numbers(self):
        cases = [
            ((1, 1), 1),
            ((2, 1), 8),
            ((2, 255), 262),
            ((114, 6), 6236),
        ]
        for (surah, ayah), number in cases:
            url = app.ayah_audio_url("ar.alafasy", surah, ayah)
            self.assertEqual(urlparse(url).hostname, "cdn.islamic.network")
            self.assertTrue(url.endswith(f"/{number}.mp3"), url)

    def test_every_catalog_entry_has_a_published_bitrate(self):
        self.assertTrue(all(row[2] in {32, 48, 64, 128, 192} for row in app.HAFS_RECITERS))
        self.assertTrue(all(app.ayah_audio_url(row[0], 1, 1) for row in app.HAFS_RECITERS))

    def test_tajweed_icon_contains_no_music_note_path(self):
        icon = app.ICON_SVG["tajweed"]
        self.assertNotIn("M9 18V5", icon)
        self.assertIn("circle", icon)


if __name__ == "__main__":
    unittest.main()
