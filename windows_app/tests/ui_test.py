"""اختبار واجهة شامل (offscreen): بيفتح كل الشاشات ويتفاعل معاها ويحفظ لقطات."""
import os
import sys
import time
import traceback
from pathlib import Path

# Windows CI قد يختار cp1252 افتراضيًا، بينما سجل الاختبار يحتوي نصًا عربيًا.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='backslashreplace')

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
OUT = Path(os.environ.get('SHOTS', '/home/user/shots'))
OUT.mkdir(parents=True, exist_ok=True)

from PySide6.QtCore import QEventLoop, QTimer, Qt  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as M  # noqa: E402
from runtime import is_portable  # noqa: E402

app = QApplication([])
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
for name in (
    'AmiriQuran-Regular.ttf', 'Amiri-Regular.ttf', 'NotoNaskhArabic-Variable.ttf',
    'ScheherazadeNew-Regular.ttf', 'NotoSansArabic-Regular.ttf', 'NotoSansArabic-Bold.ttf',
):
    QFontDatabase.addApplicationFont(str(M.FONTS / name))
t0 = time.time()


def log(*a):
    print(f'{time.time() - t0:6.2f}', *a, flush=True)


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


win = M.Main()
win.engine.allow_null = True  # بيئة بدون كارت صوت
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
    check('reader exposes 17 audited Hafs reciters', len(M.HAFS_RECITERS) == 17)
    check('reader has 30 juz', win.combo_juz.count() == 30)
    check('Hafs audio uses audited Islamic Network CDN', M.ayah_audio_url('ar.alafasy', 2, 255).startswith('https://cdn.islamic.network/'))
    check('tajweed icon is a palette not music notes', 'M9 18V5' not in M.ICON_SVG['tajweed'])
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
    check('other riwayat keeps expanded navigation', win.sidebar.width() == 228)
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('quran-simple'))
    app.processEvents()
    check('hafs simple loaded', win.riwaya_id == 'quran-simple' and win.reciter_combo.count() == 17)
    check('Hafs uses wide compact navigation', win.sidebar.width() == 76)
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
    # ورش (ملف كامل لكل سورة من مصدر MP3Quran المدقق)
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('warsh'))
    win.reciter_combo.setCurrentIndex(0)
    queue = win.audio_queue_for_page()
    check(
        'warsh MP3Quran surah queue',
        len(queue) > 0
        and queue[0][1][1] is None
        and queue[0][0].startswith('https://cdn.mp3quran.net/audio/abdulbasit-abdulsamad/r2/')
        and queue[0][0].endswith('.mp3'),
    )
    # قالون (ملف لكل سورة)
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('qalun'))
    queue = win.audio_queue_for_page()
    check('qalun surah queue', len(queue) > 0 and queue[0][1][1] is None and queue[0][0].endswith('.mp3'))
    log('  qalun queue sample:', queue[:1])
    # التجويد الملوّن محلي بالكامل، مع نص نظيف عند النسخ.
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('quran-tajweed'))
    win.go_page(2)
    app.processEvents()
    check('local tajweed markup loaded', '[m[' in win.book.texts[(2, 1)])
    check('tajweed colors rendered', '#2536d6' in win.browser.toHtml().lower())
    check('tajweed markers hidden from reader', '[m[' not in win.browser.toPlainText())
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('quran-uthmani'))
    app.processEvents()
    # البسملة قبل أول آية، والتفسير من لوحة جانبية، والسحب بالفأرة يقلب الصفحة
    win.go_page(2)
    app.processEvents()
    page_text = win.browser.toPlainText()
    check('basmala before first ayah', 'ٱلرَّحِيمِ' in page_text)
    check('basmala shown once on Baqarah page', page_text.count('بِسْمِ') == 1)
    check('Hafs uses Shamela-style bracketed surah title', '[سورة البقرة]' in page_text)
    check('Hafs uses compact ayah rosette', '۝١' in page_text)
    raw_baqarah = win.book.texts[(2, 1)]
    check('basmala detached from first ayah text', not M.display_ayah_text(2, 1, raw_baqarah, True).startswith('بِسْمِ'))
    check('non-Hafs display source is untouched', M.display_ayah_text(2, 1, raw_baqarah, False).startswith('بِسْمِ'))
    simple_first = next(row[3] for row in M.HAFS['simple'] if row[0] == 2 and row[1] == 1)
    check('basmala detached in simple script too', not M.display_ayah_text(2, 1, simple_first, True).startswith('بِسْمِ'))
    all_hafs_firsts = [
        (s, a, text)
        for rows in (M.HAFS['uthmani'], M.HAFS['simple'], M.TAJWEED_QURAN)
        for s, a, _page, text in rows
        if a == 1 and s not in (1, 9)
    ]
    check('all Hafs surah starts deduplicate basmala', all(
        not M.display_ayah_text(s, a, text, True).startswith('بِسْمِ')
        for s, a, text in all_hafs_firsts
    ))
    check('compact line spacing', 'line-height:125%' in win.browser.toHtml().replace(' ', ''))
    saved_font = win.font_pt
    saved_size = win.size()
    win.resize(1920, 900)
    win.set_font(18)
    win.go_page(win.book.page_of(15, 1))
    app.processEvents()
    check('Hijr page has exactly one displayed basmala', win.browser.toPlainText().count('بِسْمِ') == 1)
    blocks = []
    block = win.browser.document().begin()
    while block.isValid():
        if block.text().strip():
            blocks.append(block)
        block = block.next()
    check('Hijr page is one continuous compact paragraph', len(blocks) == 3)
    flow_block = max(blocks, key=lambda item: len(item.text()))
    check('Hijr page matches three-line Shamela layout at 1920px', flow_block.layout().lineCount() == 3)
    win.resize(saved_size)
    win.set_font(saved_font)
    win.go_page(2)
    app.processEvents()
    # الترجمات الأربع ذات الإسناد المعتمد تظهر تحت الآية وتُزامن بين الإعدادات والتفسير.
    win.translation_cache[('en.sahih', 2, 1)] = 'Alif, Lam, Meem.'
    win.translation_attempted.add(('en.sahih', 2))
    win.translation_combo.setCurrentIndex(win.translation_combo.findData('en.sahih'))
    app.processEvents()
    check('four approved translation choices plus disabled option', len(M.TRANSLATION_EDITIONS) == 5)
    check('translation rendered under ayah', 'Alif, Lam, Meem.' in win.browser.toPlainText())
    check('translation selection synced', win.tf_translation.currentData() == 'en.sahih')
    win.translation_combo.setCurrentIndex(0)
    app.processEvents()
    # النسخ والتظليل الدائم
    win.sel_ayah = (2, 2)
    win.copy_current_ayah()
    check('copy ayah with reference', 'الآية ٢' in QApplication.clipboard().text())
    win.set_ayah_highlight('#f4df9b')
    check('persistent ayah highlight', win.user_highlights.get('2:2') == '#f4df9b')
    win.clear_ayah_highlight()
    check('remove ayah highlight', '2:2' not in win.user_highlights)
    # الفهرس منسدل ولا يحجز عموداً دائماً
    check('index popup exists and starts hidden', hasattr(win, 'index_popup') and not win.index_popup.isVisible())
    win.sel_ayah = (2, 3)
    win.render_page()
    win.toggle_tafsir_panel(True)
    check('tafsir panel shows selected ayah', win.tp_title.text().endswith('الآية ٣'))
    win.toggle_tafsir_panel(False)
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QEvent
    vp = win.browser.viewport()
    def mouse(kind, x, y):
        ev = QMouseEvent(kind, QPointF(x, y), QPointF(x, y), Qt.MouseButton.LeftButton,
                         Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        app.sendEvent(vp, ev)
    win.browser._last_turn = -1e9
    mouse(QEvent.Type.MouseButtonPress, 300, 200)
    mouse(QEvent.Type.MouseButtonRelease, 420, 205)
    check('mouse drag right -> next page', win.page == 3)
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
    win.memo_level.setCurrentIndex(4)
    app.processEvents()
    check('memo hidden words', 'background-color:#d9d2bd' in win.memo_browser.toHtml())
    win.on_memo_anchor('w:2:1:0')
    check('memo word reveal', (2, 1, 0) in win.memo_shown)
    win.memo_save_range()
    check('memo saved for review', any(k.startswith('2:') for k in win.memo_progress()))
    check('memo review rows', win.memo_review_list.count() >= 0)
    shot('memo')
    # مشاركة الآية كصورة، وتحديد نطاق التحميل
    img = M.share_card_image(M.AYAH_TEXT[(2, 255)], 'البقرة', 255)
    check('share image rendered', not img.isNull() and img.width() == 1080 and img.height() >= 900)
    check('download refs full mushaf', len(win.dl_refs()) == 6236)
    win.memo_surah.setCurrentIndex(0)
    win.memo_to.setCurrentIndex(2)
    win.memo_repeat.setCurrentIndex(0)
    win.memo_play()
    check('memo play queue', win.queue_list and len(win.queue) == 3 and win.playing)
    check('memo pause and stop controls enabled', win.btn_memo_pause.isEnabled() and win.btn_memo_stop.isEnabled())
    win.memo_pause_resume()
    check('memo pause works', win.engine.paused and 'استئناف' in win.btn_memo_pause.text())
    win.memo_pause_resume()
    check('memo resume works', not win.engine.paused)
    win.memo_stop()
    check('memo full stop works', not win.playing and not win.queue_list and not win.btn_memo_stop.isEnabled())
    import tempfile
    tmp_dir = tempfile.mkdtemp()
    win.settings.setValue('dl_folder', tmp_dir)
    win.dl_reciter.setCurrentIndex(max(win.dl_reciter.findData('ar.alafasy'), 0))
    win.dl_one.setChecked(True)
    win.dl_surah.setCurrentIndex(111)
    win.dl_target.setCurrentIndex(1)
    cache = win.audio_cache_dir()
    for a in range(1, 5):
        (cache / M.audio_file_name(M.ayah_audio_url('ar.alafasy', 112, a))).write_bytes(b'x' * 3000)
    win.start_dl()
    check('download skips cached', win.dl.get('skipped') == 4 and not win.dl.get('running'))
    check('download copies to folder', (Path(tmp_dir) / 'ar.alafasy' / '112' / '1.mp3').exists())
    win.delete_dl()
    check('download delete', not (cache / M.audio_file_name(M.ayah_audio_url('ar.alafasy', 112, 1))).exists())
    # تتبع الختمة تلقائياً بلا هدف صفحات
    M.set_khatma_pointer(win.settings, 40)
    win.go_page(40)
    win.show_view('reader')
    win.reading_pending_page = 40
    result = win.commit_reading_page()
    check('khatma records reading automatically', result and result['advanced'])
    win.show_view('wird')
    check('khatma pointer advanced', M.khatma_progress(win.settings, win.page)['pointer'] == 41)
    check('khatma has no daily target control', not hasattr(win, 'wird_target'))
    check('khatma reminder controls', win.reminder_enabled is not None and win.reminder_time is not None)
    shot('wird')
    # الإحصائيات
    win.show_view('stats')
    check('stats today', win.st_cards['today'].text() != '')
    shot('stats')
    # الإعدادات والخطوط والتجاوب
    win.show_view('settings')
    check('four bundled mushaf fonts', win.mushaf_font_combo.count() >= 4)
    noto = win.mushaf_font_combo.findData('Noto Naskh Arabic')
    win.mushaf_font_combo.setCurrentIndex(noto)
    check('mushaf font can change', win.mushaf_font == 'Noto Naskh Arabic')
    win.resize(800, 600)
    app.processEvents()
    check('compact sidebar on small window', win.sidebar.width() == 76)
    win.resize(1300, 820)
    app.processEvents()
    check('expanded sidebar on wide window', win.sidebar.width() == 228)
    check('portable test mode', is_portable())
    shot('settings')
    log('DONE')
except Exception:
    traceback.print_exc()
    failures.append('exception')

log('FAILURES:', failures if failures else 'none')
sys.exit(1 if failures else 0)
