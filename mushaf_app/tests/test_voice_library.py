"""اختبارات مكتبة القرّاء في نسخة لينكس (بحث، مفضلة، اختيار، بناء قائمة السورة)."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from PySide6.QtWidgets import QApplication  # noqa: E402

import main as M  # noqa: E402

app = QApplication.instance() or QApplication([])


class VoiceLibraryDataTest(unittest.TestCase):
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


class VoiceLibraryDialogTest(unittest.TestCase):
    def make(self, mode='sync', current_id='', favorites=None):
        return M.VoiceLibraryDialog(
            None, M.RECITER_LIBRARY, favorites or [], mode, current_id, 'مشاري العفاسي',
        )

    def test_sync_row_is_first(self):
        dialog = self.make()
        first = dialog.listw.item(0).data(M.Qt.ItemDataRole.UserRole)
        self.assertEqual(first, ('sync', ''))

    def test_search_filters_by_rewaya(self):
        dialog = self.make()
        everything = dialog.listw.count()
        dialog.search.setText('ورش')
        self.assertLess(dialog.listw.count(), everything)
        self.assertGreaterEqual(dialog.listw.count(), 2)

    def test_favorite_pins_reciter_to_top(self):
        target = M.RECITER_LIBRARY[-1]
        dialog = self.make()
        for row in range(dialog.listw.count()):
            item = dialog.listw.item(row)
            data = item.data(M.Qt.ItemDataRole.UserRole)
            if data and data[0] == 'library' and str(data[1]) == str(target['id']):
                dialog.listw.setCurrentRow(row)
                break
        dialog.toggle_favorite()
        self.assertIn(str(target['id']), dialog.favorites())
        top = dialog.listw.item(1).data(M.Qt.ItemDataRole.UserRole)
        self.assertEqual(top, ('library', str(target['id'])))

    def test_selection_returns_library_mode(self):
        target = M.RECITER_LIBRARY[3]
        dialog = self.make()
        for row in range(dialog.listw.count()):
            data = dialog.listw.item(row).data(M.Qt.ItemDataRole.UserRole)
            if data and data[0] == 'library' and str(data[1]) == str(target['id']):
                dialog.listw.setCurrentRow(row)
                break
        dialog.accept()
        self.assertEqual(dialog.selection(), ('library', str(target['id'])))

    def test_accepting_sync_row_restores_sync(self):
        dialog = self.make(mode='library', current_id=str(M.RECITER_LIBRARY[0]['id']))
        dialog.listw.setCurrentRow(0)
        dialog.accept()
        self.assertEqual(dialog.selection(), ('sync', ''))


if __name__ == '__main__':
    unittest.main()
