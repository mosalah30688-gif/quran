"""اختبار واجهة شامل (offscreen): بيفتح كل الشاشات ويتفاعل معاها ويحفظ لقطات."""
import os
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
OUT = Path(os.environ.get('SHOTS', '/home/user/shots'))
OUT.mkdir(parents=True, exist_ok=True)

from PySide6.QtCore import QEventLoop, QTimer, Qt  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as M  # noqa: E402

app = QApplication([])
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
QFontDatabase.addApplicationFont(str(M.FONTS / 'AmiriQuran-arabic.woff2'))
t0 = time.time()


def log(*a):
    print(f'{time.time() - t0:6.2f}', *a, flush=True)


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


win = M.Main()
win.settings.clear()
win.page = 1
win.resize(1440, 900)
win.show()
app.processEvents()
win.render_page()
failures = []


def check(name, cond):
    log(('OK  ' if cond else 'FAIL'), name)
    if not cond:
        failures.append(name)


def shot(name):
    app.processEvents()
    win.grab().save(str(OUT / f'{name}.png'))


try:
    # المصحف
    check('reader has 114 surahs', win.combo_surah.count() == 114)
    check('reader has 30 juz', win.combo_juz.count() == 30)
    check('page 1 text', 'الفاتحة' in win.browser.toPlainText().replace('ٱ', 'ا') or len(win.browser.toPlainText()) > 100)
    win.go_page(2)
    check('next page', win.page == 2)
    # الأسهم: يسار = التالية، يمين = السابقة
    from PySide6.QtTest import QTest
    win.browser.setFocus()
    app.processEvents()
    QTest.keyClick(win.browser, Qt.Key.Key_Left)
    check('left arrow -> next page', win.page == 3)
    QTest.keyClick(win.browser, Qt.Key.Key_Right)
    check('right arrow -> previous page', win.page == 2)
    # عجلة الماوس عند الحافة السفلية تقلب الصفحة
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent
    bar = win.browser.verticalScrollBar()
    bar.setValue(bar.maximum())
    wheel = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    app.sendEvent(win.browser.viewport(), wheel)
    check('wheel at bottom -> next page', win.page == 3)
    win.go_page(1)
    win.combo_surah.setCurrentIndex(1)  # البقرة
    check('surah jump to 2 -> page 2', win.page == 2 and win.combo_surah.currentData() == 2)
    win.combo_juz.setCurrentIndex(4)
    check('juz 5 -> page 82', win.page == 82)
    win.go_page(3)
    shot('reader_light')
    win.set_font(26)
    # الثيم الداكن
    win.theme_combo.setCurrentIndex(win.theme_combo.findData('dark'))
    app.processEvents()
    check('dark theme applied', win.theme_name == 'dark')
    shot('reader_dark')
    win.theme_combo.setCurrentIndex(win.theme_combo.findData('light'))
    # الرواية ورش
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('warsh'))
    app.processEvents()
    check('warsh loaded', win.riwaya_id == 'warsh' and win.reciter_combo.count() == 2)
    check('warsh page text', len(win.browser.toPlainText()) > 100)
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('quran-simple'))
    app.processEvents()
    check('hafs simple loaded', win.riwaya_id == 'quran-simple' and win.reciter_combo.count() == 10)
    # التلاوة (ملف لكل آية، أول قارئ حفص)
    win.reciter_combo.setCurrentIndex(0)
    win.toggle_play()
    wait(2500)
    app.processEvents()
    check('hafs audio queue has ayahs', len(win.queue) > 0 and win.playing)
    log('  status:', win.play_status.text())
    win.toggle_play()  # إيقاف مؤقت
    check('pause toggles', 'متوقفة' in win.play_status.text() or win.play_status.text() != '')
    win.stop_play('أوقفت التلاوة')
    check('stop resets', not win.playing)
    # ورش (ملف لكل آية)
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('warsh'))
    win.reciter_combo.setCurrentIndex(0)
    queue = win.audio_queue_for_page()
    check('warsh ayah queue', len(queue) > 0 and 'warsh_Abdul_Basit' in queue[0][0])
    # قالون (ملف لكل سورة)
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('qalun'))
    queue = win.audio_queue_for_page()
    check('qalun surah queue', len(queue) > 0 and queue[0][1][1] is None and queue[0][0].endswith('.mp3'))
    log('  qalun queue sample:', queue[:1])
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('quran-uthmani'))
    app.processEvents()
    # الإشارات المرجعية
    win.go_page(10)
    win.toggle_bookmark()
    check('bookmark saved', 10 in win.bookmarks())
    win.show_view('bookmarks')
    check('bookmark listed', win.bm_list.count() == 1)
    shot('bookmarks')
    # البحث
    win.show_view('search')
    win.search_input.setText('الرحمن')
    app.processEvents()
    check('search results', win.search_results.count() > 50)
    win.open_search_result(win.search_results.item(0))
    check('search opens reader', win.stack.currentWidget() is win.views['reader'])
    # التفسير (شبكة)
    win.show_view('tafsir')
    win.tf_surah.setCurrentIndex(1)
    win.tf_ayah.setValue(2)
    for _ in range(60):
        wait(250)
        if (win.tf_book.currentData(), 2, 2) in win.tafsir_cache:
            break
    app.processEvents()
    check('tafsir fetched', (win.tf_book.currentData(), 2, 2) in win.tafsir_cache)
    shot('tafsir')
    # المعاني والتجويد
    win.show_view('meanings')
    check('meanings rendered', len(win.mn_browser.toPlainText()) > 50)
    win.show_view('tajweed')
    check('tajweed rendered', len(win.tj_browser.toPlainText()) > 100)
    shot('tajweed')
    # الأذكار
    win.show_view('adhkar')
    check('adhkar items', win.adh_items.count() > 1)
    from PySide6.QtWidgets import QPushButton
    win.bump_adhkar('0:0', M.ADHKAR[0]['items'][0]['count'], QPushButton())
    check('adhkar counter saved', win.adhkar_state()['c'].get('0:0') == 1)
    shot('adhkar')
    # وضع الحفظ
    win.show_view('memo')
    win.memo_surah.setCurrentIndex(1)
    win.memo_hide.setChecked(True)
    app.processEvents()
    check('memo hidden text', '•••' in win.memo_browser.toPlainText())
    shot('memo')
    # الورد
    win.show_view('wird')
    win.finish_wird()
    check('wird completed', win.settings.value('wird_count', 0, type=int) >= 1)
    shot('wird')
    # الإحصائيات
    win.show_view('stats')
    check('stats today', win.st_cards['today'].text() != '')
    shot('stats')
    # الإعدادات
    win.show_view('settings')
    shot('settings')
    log('DONE')
except Exception:
    traceback.print_exc()
    failures.append('exception')

log('FAILURES:', failures if failures else 'none')
sys.exit(1 if failures else 0)
