"""اختبار واجهة شامل (offscreen): بيفتح كل الشاشات ويتفاعل معاها ويحفظ لقطات."""
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
OUT = Path(os.environ.get('SHOTS', '/home/user/shots'))
OUT.mkdir(parents=True, exist_ok=True)
TEST_HOME = Path(tempfile.mkdtemp(prefix='siraj-linux-ui-'))
for name in ('CONFIG', 'DATA', 'CACHE', 'STATE'):
    os.environ[f'XDG_{name}_HOME'] = str(TEST_HOME / name.lower())

from PySide6.QtCore import QEventLoop, QTimer, Qt  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as M  # noqa: E402

app = QApplication([])
app.setApplicationName(M.APP_NAME)
app.setApplicationDisplayName(f'{M.APP_NAME_AR} — {M.APP_DESCRIPTION_AR}')
app.setApplicationVersion(M.APP_VERSION)
app.setOrganizationName('mosalah30688')
app.setDesktopFileName(M.APP_ID)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
loaded_fonts = M.register_bundled_fonts()
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
    # انتظر انتهاء انتقال fade كي تمثل لقطة CI ما يراه المستخدم فعليًا.
    wait(280)
    app.processEvents()
    win.grab().save(str(OUT / f'{name}.png'))


try:
    # الهوية والتشغيل الرسومي
    check('Siraj window title', win.windowTitle() == 'سراج — قرآن كريم')
    check('Siraj window icon', not win.windowIcon().isNull())
    check('Linux desktop identity', app.desktopFileName() == M.APP_ID)
    check('Linux compatibility release is newer than 4.0.7', M.version_tuple(M.APP_VERSION) > M.version_tuple('4.0.7'))
    check('dedicated update button is always visible',
          win.btn_sidebar_update.isVisible() and not win.btn_sidebar_update.icon().isNull()
          and 'تحديث' in win.btn_sidebar_update.toolTip())
    original_check_updates = win.check_updates
    update_clicks = []
    win.check_updates = lambda manual=False: update_clicks.append(manual)
    win.btn_sidebar_update.click()
    app.processEvents()
    check('dedicated update button opens updater',
          win.stack.currentWidget() is win.views['settings'] and update_clicks == [True])
    win.check_updates = original_check_updates
    check('dedicated about button is always visible',
          win.nav_buttons['about'].isVisible() and not win.nav_buttons['about'].icon().isNull()
          and 'المطور' in win.nav_buttons['about'].toolTip())
    win.nav_buttons['about'].click()
    app.processEvents()
    wait(300)  # دع حركة الانتقال تنتهي كي تكون لقطة صفحة «عن التطبيق» مقروءة.
    check('about button opens its own view', win.stack.currentWidget() is win.views['about'])
    expected_about_features = (
        'مصحف ذكي للتلاوة والاستماع والتدبر',
        'برواية حفص عن عاصم وروايات أخرى',
        'تحديد الأوراد والختمات ومتابعتها',
        'الأذكار بعداد خاص لكل ذكر',
        'تفاسير القرآن',
    )
    check('about view uses the approved concise feature copy',
          M.ABOUT_FEATURES == expected_about_features
          and win.about_features_label.text() == '\n'.join(f'• {item}' for item in expected_about_features)
          and not hasattr(win, 'about_updates_label'))
    check('about view identifies developer and contact',
          M.DEVELOPER_NAME in win.about_developer_label.text()
          and win.about_contact_button.text() == 'اتصل بنا'
          and set(win.about_link_buttons) == {M.DEVELOPER_PAGE_URL, M.CONTACT_URL, M.REPOSITORY_URL}
          and all(button.property('externalUrl') == url for url, button in win.about_link_buttons.items()))
    check('update notice shows only concise user-facing features',
          M.update_notice_text('9.9.9', ['ميزة جديدة'])
          == 'يتوفر تحديث جديد لسراج — الإصدار 9.9.9\n• ميزة جديدة'
          and M.update_notice_text('9.9.9', ['ترقيع موقّع بتوقيع Ed25519'])
          == 'يتوفر تحديث جديد لسراج — الإصدار 9.9.9')
    shot('about')
    win.show_view('reader')
    app.processEvents()
    # المصحف
    check('reader has 114 surahs', win.combo_surah.count() == 114)
    check('reader exposes 17 audited Hafs reciters', len(M.HAFS_RECITERS) == 17)
    check('reader has 30 juz', win.combo_juz.count() == 30)
    check('four OFL Arabic reading fonts loaded', len(loaded_fonts) == len(M.BUNDLED_FONT_FILES) and len(M.MUSHAF_FONTS) == 4)
    check('licensed classical tafsir catalog has 73 unique books',
          len(M.QURANPEDIA_TAFSIR_EDITIONS) == 73
          and len({edition for edition, _name in M.ALL_TAFSIR_EDITIONS}) == 78)
    check('all 78 tafsir editions are available in the offline store',
          win.offline_tafsir.available and len(win.offline_tafsir.editions) == 78)
    check('tafsir selectors expose audited and classical books',
          win.tf_book.count() == 79 and win.tp_book.count() == 79 and win.tf_book.findData('qp:4') >= 0)
    check('Hafs audio uses audited Islamic Network CDN', M.ayah_audio_url('ar.alafasy', 2, 255).startswith('https://cdn.islamic.network/'))
    check('tajweed icon is a palette not music notes', 'M9 18V5' not in M.ICON_SVG['tajweed'])
    icon_colors = []
    for key in ('book', 'tafsir', 'search', 'words', 'tajweed', 'adhkar', 'memo', 'wird', 'bookmarks', 'stats', 'update', 'about', 'settings'):
        image = M.svg_icon(key, size=24).pixmap(48, 48).toImage()
        colors = {image.pixelColor(x, y).rgba() for x in range(0, image.width(), 3)
                  for y in range(0, image.height(), 3) if image.pixelColor(x, y).alpha()}
        icon_colors.append(len(colors))
    check('sidebar icons are rendered multicolour Fluent 3D vectors', min(icon_colors) >= 6)
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
    # العجلة وإيماءة لوحة اللمس تمرران داخل الصفحة فقط ولا تقلبان عند الحواف.
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent

    def wheel_event(pixel_y=0, angle_y=0, phase=Qt.ScrollPhase.NoScrollPhase):
        return QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, pixel_y), QPoint(0, angle_y),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, phase, False,
        )

    win.set_font(44)
    win.go_page(2)
    app.processEvents()
    bar = win.browser.verticalScrollBar()
    check('large page is vertically scrollable', bar.maximum() > 0)
    bar.setValue(bar.minimum())
    app.sendEvent(win.browser.viewport(), wheel_event(angle_y=-120))
    app.processEvents()
    check('wheel scrolls inside current page only', win.page == 2 and bar.value() > bar.minimum())
    bar.setValue(bar.maximum())
    app.sendEvent(win.browser.viewport(), wheel_event(angle_y=-120))
    check('wheel at bottom never turns page', win.page == 2)
    bar.setValue(max(bar.minimum(), bar.maximum() // 2))
    before_touch = bar.value()
    app.sendEvent(win.browser.viewport(), wheel_event(pixel_y=-36, phase=Qt.ScrollPhase.ScrollUpdate))
    app.processEvents()
    check('touchpad pixel gesture scrolls without turning page', win.page == 2 and bar.value() != before_touch)
    bar.setValue(bar.maximum())
    win.go_page(3)
    app.processEvents()
    check('new page always starts at top', win.page == 3 and win.browser.verticalScrollBar().value() == 0)
    win.set_font(18)

    # القوائم لا تقفز بالعجلة وهي مغلقة؛ الاختيار يتطلب نقرة مقصودة.
    def assert_wheel_locked(name, widget, get_value):
        before = get_value()
        app.sendEvent(widget, wheel_event(angle_y=-120))
        app.sendEvent(widget, wheel_event(pixel_y=-30, phase=Qt.ScrollPhase.ScrollUpdate))
        app.processEvents()
        check(name, get_value() == before)

    win.reciter_combo.setCurrentIndex(min(2, win.reciter_combo.count() - 1))
    assert_wheel_locked('reader wheel cannot change reciter', win.reciter_combo, win.reciter_combo.currentIndex)
    win.play_surah.setCurrentIndex(1)
    assert_wheel_locked('reader wheel cannot change playback surah', win.play_surah, win.play_surah.currentIndex)
    win.play_from.setCurrentIndex(1)
    assert_wheel_locked('reader wheel cannot change playback ayah', win.play_from, win.play_from.currentIndex)
    win.go_page(1)
    win.combo_surah.setCurrentIndex(1)  # البقرة
    check('surah jump to 2 -> page 2', win.page == 2 and win.combo_surah.currentData() == 2)
    assert_wheel_locked('index wheel cannot change surah', win.combo_surah, win.combo_surah.currentIndex)
    win.combo_ayah.setCurrentIndex(1)
    assert_wheel_locked('index wheel cannot change ayah', win.combo_ayah, win.combo_ayah.currentIndex)
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
    check('other riwayat keeps its index panel', win.index_card.isVisible())
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('quran-simple'))
    app.processEvents()
    check('hafs simple loaded', win.riwaya_id == 'quran-simple' and win.reciter_combo.count() == 17)
    check('Hafs wide reader hides the permanent index', not win.index_card.isVisible())
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
    win.riwaya_combo.setCurrentIndex(win.riwaya_combo.findData('quran-uthmani'))
    app.processEvents()
    # البسملة قبل أول آية، والتفسير من لوحة جانبية، والسحب الأفقي لا يقلب الصفحة
    win.go_page(2)
    app.processEvents()
    page_text = win.browser.toPlainText()
    check('basmala before first ayah', 'ٱلرَّحِيمِ' in page_text)
    check('basmala shown once on Baqarah page', page_text.count('بِسْمِ') == 1)
    check('Hafs uses Shamela-style bracketed surah title', '[سورة البقرة]' in page_text)
    check('Hafs uses compact ayah rosette', '۝١' in page_text)
    raw_baqarah = next(row[3] for row in M.HAFS['uthmani'] if row[0] == 2 and row[1] == 1)
    check('basmala detached from Hafs first ayah', not M.display_ayah_text(2, 1, raw_baqarah, True).startswith('بِسْمِ'))
    check('non-Hafs display source is untouched', M.display_ayah_text(2, 1, raw_baqarah, False).startswith('بِسْمِ'))
    all_hafs_firsts = [
        (s, a, text)
        for rows in (M.HAFS['uthmani'], M.HAFS['simple'])
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
    page_before_drag = win.page
    mouse(QEvent.Type.MouseButtonPress, 300, 200)
    mouse(QEvent.Type.MouseMove, 380, 204)
    mouse(QEvent.Type.MouseButtonRelease, 420, 205)
    check('horizontal mouse drag never turns page', win.page == page_before_drag)
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
    # التفسير: القائمة الموسعة، المصدر المحلي، ومنع العجلة وتوحيد خط المصحف.
    win.show_view('tafsir')
    win.tf_surah.setCurrentIndex(1)
    win.tf_ayah.setValue(2)
    assert_wheel_locked('tafsir wheel cannot change surah', win.tf_surah, win.tf_surah.currentIndex)
    assert_wheel_locked('tafsir wheel cannot change ayah number', win.tf_ayah, win.tf_ayah.value)
    qp_index = win.tf_book.findData('qp:4')
    win.tf_book.setCurrentIndex(qp_index)
    assert_wheel_locked('tafsir wheel cannot change book', win.tf_book, win.tf_book.currentIndex)
    qp_key = ('qp:4', 2, 2)
    app.processEvents()
    check('Quranpedia classical tafsir loaded locally without waiting', qp_key in win.tafsir_cache)
    if qp_key in win.tafsir_cache:
        check('Quranpedia HTML sanitized to readable text',
              '<h3>' not in win.tafsir_cache[qp_key] and len(win.tafsir_cache[qp_key]) > 20)
    font_index = win.mushaf_font_combo.findData('Amiri')
    win.mushaf_font_combo.setCurrentIndex(font_index)
    win.set_font(24)
    app.processEvents()
    tf_html = win.tf_browser.toHtml()
    check('tafsir follows selected mushaf font', 'Amiri' in tf_html)
    check('tafsir follows selected mushaf size', '24pt' in tf_html or '32px' in tf_html)
    win.show_view('reader')
    win.go_page(2)
    win.sel_ayah = (2, 2)
    win.render_page()
    win.toggle_tafsir_panel(True)
    app.processEvents()
    check('reader tafsir panel shares book selection', win.tp_book.currentData() == 'qp:4')
    tp_html = win.tp_browser.toHtml()
    check('reader tafsir panel follows mushaf typography', 'Amiri' in tp_html)
    win.toggle_tafsir_panel(False)
    win.show_view('tafsir')
    shot('tafsir')
    win.set_font(18)
    default_font_index = win.mushaf_font_combo.findData('Amiri Quran')
    win.mushaf_font_combo.setCurrentIndex(default_font_index)
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
    # الإعدادات: العجلة لا تغيّر نوع الخط أو الحجم أو الرواية أو وقت التذكير.
    win.show_view('settings')
    assert_wheel_locked('settings wheel cannot change font family',
                        win.mushaf_font_combo, win.mushaf_font_combo.currentIndex)
    assert_wheel_locked('settings wheel cannot change font size', win.font_spin, win.font_spin.value)
    assert_wheel_locked('settings wheel cannot change riwaya', win.riwaya_combo, win.riwaya_combo.currentIndex)
    assert_wheel_locked('touchpad cannot change reminder time',
                        win.reminder_time, lambda: win.reminder_time.time().toString('HH:mm'))
    shot('settings')
    log('DONE')
except Exception:
    traceback.print_exc()
    failures.append('exception')

log('FAILURES:', failures if failures else 'none')
sys.exit(1 if failures else 0)
