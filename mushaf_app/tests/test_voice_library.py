"""اختبارات قائمة القرّاء الموحّدة في نسخة لينكس.

قائمة واحدة لكل رواية: قرّاء التلاوة المتزامنة أولًا ثم مصاحف المكتبة (mp3quran)
التابعة لنفس الرواية، بلا تقسيم «آية بآية / سورة كاملة» وبلا خلط روايات.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import main as M  # noqa: E402


class _Scope:
    """كائن خفيف يجرّب reciter_options() دون بناء نافذة Qt."""

    reciter_options = M.Main.reciter_options

    def __init__(self, riwaya_id):
        self.riwaya_id = riwaya_id


class CatalogTest(unittest.TestCase):
    def test_catalog_is_complete(self):
        self.assertGreaterEqual(len(M.RECITER_LIBRARY), 174)
        for item in M.RECITER_LIBRARY:
            self.assertEqual(item['surahs'], 114)
            self.assertTrue(item['server'].startswith('https://'))
            self.assertTrue(item['name'].strip())
            self.assertIn('family', item)

    def test_catalog_covers_four_riwayat(self):
        families = {item['family'] for item in M.RECITER_LIBRARY}
        for family in ('حفص', 'ورش', 'قالون', 'الدوري'):
            self.assertIn(family, families)

    def test_ids_are_unique_and_indexed(self):
        ids = [str(item['id']) for item in M.RECITER_LIBRARY]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(M.LIBRARY_BY_ID), len(ids))

    def test_qualifier_drops_riwaya_name(self):
        self.assertEqual(M.library_qualifier('حفص عن عاصم - مرتل'), 'مرتل')
        self.assertEqual(M.library_qualifier('حفص عن عاصم - المصحف المجود'), 'المصحف المجود')
        self.assertEqual(M.library_qualifier('ورش عن نافع من طريق الأزرق مرتل', 'ورش'), 'مرتل')
        self.assertEqual(M.library_qualifier('حفص عن عاصم - مرتل', 'حفص'), 'مرتل')


class UnifiedListTest(unittest.TestCase):
    def test_hafs_list_starts_with_audited_sync_voices(self):
        options = _Scope('quran-uthmani').reciter_options()
        self.assertEqual([rid for rid, _n in options[:17]], [row[0] for row in M.HAFS_RECITERS])
        self.assertEqual(len(options), len({rid for rid, _n in options}))

    def test_each_riwaya_only_shows_its_own_mushafs(self):
        for riwaya, family in M.RIW_FAMILY.items():
            options = _Scope(riwaya).reciter_options()
            for rid, _name in options:
                if str(rid).startswith('lib:'):
                    item = M.LIBRARY_BY_ID[str(rid)[4:]]
                    self.assertEqual((item.get('family') or 'حفص'), family, riwaya)

    def test_hafs_list_never_mixes_other_riwayat(self):
        for rid, _name in _Scope('quran-simple').reciter_options():
            if str(rid).startswith('lib:'):
                item = M.LIBRARY_BY_ID[str(rid)[4:]]
                self.assertEqual((item.get('family') or 'حفص'), 'حفص')

    def test_library_mushafs_are_present_for_every_riwaya(self):
        for riwaya in ('quran-uthmani', 'warsh', 'qalun', 'duri'):
            options = _Scope(riwaya).reciter_options()
            self.assertTrue(
                any(str(rid).startswith('lib:') for rid, _n in options),
                f'لا مصاحف مكتبة في {riwaya}',
            )

    def test_no_duplicate_voice_with_default_murattal(self):
        names = [n for _rid, n in _Scope('quran-uthmani').reciter_options()]
        self.assertEqual(len(names), len(set(names)))

    def test_minshawi_variants_are_available(self):
        labels = ' | '.join(n for _rid, n in _Scope('quran-uthmani').reciter_options())
        self.assertIn('المنشاوي', labels)
        self.assertIn('1387', labels)


if __name__ == '__main__':
    unittest.main()
