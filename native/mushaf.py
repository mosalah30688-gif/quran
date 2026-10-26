#!/usr/bin/env python3
"""المصحف - واجهة سطح مكتب أصلية (Qt)، بدون متصفح.

تشغيل: python3 mushaf.py
"""
import datetime
import html
import json
import re
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QFontDatabase
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QPushButton, QScrollArea,
    QSpinBox, QStackedWidget, QTextBrowser, QToolButton, QVBoxLayout, QWidget,
)

APP_VERSION = '2.0.0'

if getattr(sys, 'frozen', False):
    HERE = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
else:
    HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
FONTS = HERE / 'fonts'

ARABIC_DIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def ar(n):
    return str(n).translate(ARABIC_DIGITS)


def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


SURAHS = load('surahs.json')
RIWAYAT = load('quran-riwayat.json')['riwayat']
MEANINGS = load('quran-meanings.json')['ayahs']
ADHKAR = load('adhkar.json')['categories']
JUZ_START = load('juz.json')
TAJWEED = load('tajweed.json')
SEARCH_AYAHS = load('quran-search.json')['ayahs']          # [surah, ayah, text] (حفص)
AYAH_TEXT = {(s, a): t for s, a, t in SEARCH_AYAHS}

# القراء للتلاوة: مجلد everyayah (آية بآية). التلاوة هنا بالرواية الحفصية.
RECITERS = {
    'alafasy': ('مشاري العفاسي', 'Alafasy_128kbps'),
    'husary': ('محمود خليل الحصري', 'Husary_128kbps'),
    'husary_m': ('الحصري (مجوّد)', 'Husary_128kbps_Mujawwad'),
    'sudais': ('عبدالرحمن السديس', 'Abdurrahmaan_As-Sudais_192kbps'),
}

_DIACRITICS = re.compile('[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]')


def norm(text):
    """تطبيع للبحث: بدون تشكيل ولا تطويل، والألفات والياء موحدة."""
    t = _DIACRITICS.sub('', text)
    return t.translate(str.maketrans('أإآٱىة', 'ااااية'))


SEARCH_INDEX = [(s, a, norm(t), t) for s, a, t in SEARCH_AYAHS]

RIWAYA_NAMES = {'warsh': 'ورش عن نافع', 'qalun': 'قالون عن نافع', 'duri': 'الدوري عن أبي عمرو'}

THEMES = {
    False: dict(bg='#f6f1e4', card='#ffffff', text='#222222', muted='#7a7468', brand='#0f5a46',
                line='#e2dccb', page='#f3e9cf', hover='#ece6d6'),
    True: dict(bg='#15191a', card='#1f2526', text='#e8e6df', muted='#9aa39f', brand='#2f8f6f',
               line='#33393a', page='#2a2820', hover='#2a3132'),
}


class Riwaya:
    """فهرس صفحات الرواية: من الصفحة إلى الآيات، ومن الآية إلى الصفحة."""

    def __init__(self, rid):
        self.rid = rid
        self.by_page = {}
        self.where = {}
        for s, a, page, text in RIWAYAT[rid]:
            self.by_page.setdefault(page, []).append((s, a, text))
            self.where[(s, a)] = page
        self.max_page = max(self.by_page)

    def page_of(self, s, a):
        """صفحة الآية، ولو مش موجودة في الرواية بنرجع لأقرب آية قبلها في نفس السورة."""
        while a >= 1:
            if (s, a) in self.where:
                return self.where[(s, a)]
            a -= 1
        return 1


def juz_of(s, a):
    idx = 0
    for i, (js, ja) in enumerate(JUZ_START):
        if (js, ja) <= (s, a):
            idx = i
    return idx + 1


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('المصحف')
        self.settings = QSettings('mosalah30688', 'Mushaf')
        self.dark = self.settings.value('dark', False, type=bool)
        self.riwaya_id = self.settings.value('riwaya', 'warsh', type=str)
        if self.riwaya_id not in RIWAYAT:
            self.riwaya_id = 'warsh'
        self.font_pt = self.settings.value('font_pt', 20, type=int)
        self.riw = Riwaya(self.riwaya_id)
        self.page = min(max(self.settings.value('page', 1, type=int), 1), self.riw.max_page)

        self.root = QWidget()
        self.root.setObjectName('root')
        self.setCentralWidget(self.root)
        outer = QVBoxLayout(self.root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self.build_topbar())
        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        # الشبكة (للتفسير) والصوت (للتلاوة)
        self.nam = QNetworkAccessManager(self)
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.audio_out.setVolume(1.0)
        self.player.setAudioOutput(self.audio_out)
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.errorOccurred.connect(self.on_media_error)
        self.play_queue = []
        self.playing = False

        self.views = {}
        self.views['reader'] = self.build_reader()
        self.views['settings'] = self.build_settings()
        self.views['adhkar'] = self.build_adhkar()
        self.views['tajweed'] = self.build_tajweed()
        self.views['meanings'] = self.build_meanings()
        self.views['stats'] = self.build_stats()
        self.views['memo'] = self.build_memo()
        self.views['wird'] = self.build_wird()
        self.views['bookmarks'] = self.build_bookmarks()
        self.views['tafsir'] = self.build_tafsir()
        self.views['search'] = self.build_search()
        for w in self.views.values():
            self.stack.addWidget(w)

        self.apply_theme()
        self.show_view('reader')
        self.render_page()
        self.resize(1280, 860)
        self.showMaximized()

    # ---------- الشريط العلوي ----------
    def build_topbar(self):
        bar = QWidget()
        bar.setObjectName('topbar')
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(8)

        self.btn_reader = self.tool_button('📖 المصحف', lambda: self.show_view('reader'))
        row.addWidget(self.btn_reader)

        self.menu_wealth = self.menu_button('🏅 رصيدك ▾', [
            ('📊 الإحصائيات', 'stats'), ('🧠 الحفظ', 'memo'),
            ('🌿 الورد', 'wird'), ('⭐ المحفوظات', 'bookmarks'),
        ])
        row.addWidget(self.menu_wealth)

        self.menu_tadabbur = self.menu_button('💡 تدبر ▾', [
            ('📚 التفسير', 'tafsir'), ('🎨 أحكام التجويد', 'tajweed'), ('🔤 المعاني', 'meanings'),
        ])
        row.addWidget(self.menu_tadabbur)

        self.menu_adhkar = QMenu(self)
        for i, cat in enumerate(ADHKAR):
            act = self.menu_adhkar.addAction(f'📿 {cat["name"]}')
            act.triggered.connect(lambda checked=False, idx=i: self.show_adhkar(idx))
        btn_adhkar = QToolButton()
        btn_adhkar.setText('📿 أذكارك ▾')
        btn_adhkar.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn_adhkar.setMenu(self.menu_adhkar)
        row.addWidget(btn_adhkar)

        row.addStretch(1)
        row.addWidget(self.tool_button('⚙️ الإعدادات', lambda: self.show_view('settings')))
        return bar

    def tool_button(self, text, slot):
        b = QToolButton()
        b.setText(text)
        b.clicked.connect(slot)
        return b

    def menu_button(self, text, items):
        menu = QMenu(self)
        for label, view in items:
            act = menu.addAction(label)
            act.triggered.connect(lambda checked=False, v=view: self.show_view(v))
        b = QToolButton()
        b.setText(text)
        b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        b.setMenu(menu)
        return b

    def show_view(self, name):
        self.stack.setCurrentWidget(self.views[name])
        self.btn_reader.setProperty('active', name == 'reader')
        self.refresh_styles()
        if name == 'settings':
            self.sync_index()
        if name == 'tajweed':
            self.fill_tajweed()
        if name == 'meanings':
            self.render_meanings()
        if name == 'stats':
            self.render_stats()
        if name == 'memo':
            self.render_memo()
        if name == 'wird':
            self.render_wird()
        if name == 'bookmarks':
            self.render_bookmarks()
        if name == 'tafsir':
            self.load_tafsir()
        if name == 'search':
            self.search_input.setFocus()

    def refresh_styles(self):
        for w in (self.btn_reader,):
            w.style().unpolish(w)
            w.style().polish(w)

    # ---------- المصحف ----------
    def build_reader(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        nav = QHBoxLayout()
        self.btn_next = QPushButton('التالية ›')
        self.btn_prev = QPushButton('‹ السابقة')
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_prev.clicked.connect(lambda: self.go_page(self.page - 1))
        self.btn_next.clicked.connect(lambda: self.go_page(self.page + 1))
        nav.addWidget(self.btn_next)
        nav.addStretch(1)
        nav.addWidget(self.page_label)
        nav.addStretch(1)
        nav.addWidget(self.btn_prev)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        tools = QHBoxLayout()
        self.btn_play = QPushButton('▶ تلاوة الصفحة')
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_mark = QPushButton('⭐ حفظ الصفحة')
        self.btn_mark.clicked.connect(self.toggle_bookmark)
        self.reciter_combo = QComboBox()
        for rid, (name, _folder) in RECITERS.items():
            self.reciter_combo.addItem(name, rid)
        self.reciter_combo.setCurrentIndex(
            max(self.reciter_combo.findData(self.settings.value('reciter', 'alafasy', type=str)), 0))
        self.reciter_combo.currentIndexChanged.connect(
            lambda i: self.settings.setValue('reciter', self.reciter_combo.itemData(i)))
        self.play_status = QLabel()
        tools.addWidget(self.btn_play)
        tools.addWidget(self.reciter_combo)
        tools.addWidget(self.btn_mark)
        tools.addStretch(1)
        tools.addWidget(self.play_status)
        lay.addLayout(nav)
        lay.addWidget(self.browser, 1)
        lay.addLayout(tools)
        return w

    def go_page(self, p):
        p = min(max(p, 1), self.riw.max_page)
        if p != self.page:
            self.page = p
            self.settings.setValue('page', p)
            if self.playing:
                self.stop_play()
            self.count_page_visit()
            self.render_page()
            self.update_mark_button()

    def render_page(self):
        page = self.page
        items = self.riw.by_page.get(page, [])
        parts = []
        last = None
        for s, a, text in items:
            if a == 1 and s != last:
                parts.append(f'<p align="center" style="font-size:{self.font_pt + 4}pt; font-weight:bold">'
                             f'{html.escape(SURAHS[s - 1]["name"])}</p>')
                last = s
            parts.append(f'{html.escape(text)} <span style="font-size:{max(self.font_pt - 10, 10)}pt">'
                         f'﴿{ar(a)}﴾</span> ')
        body = ''.join(parts) or '<p align="center">لا توجد آيات في هذه الصفحة</p>'
        first = items[0] if items else (1, 1, '')
        self.browser.setHtml(
            f'<html><body dir="rtl" style="font-family:\'Amiri Quran\'; font-size:{self.font_pt}pt; '
            f'line-height:180%;"><p align="center" dir="rtl">{body}</p></body></html>')
        self.page_label.setText(f'الجزء {ar(juz_of(first[0], first[1]))}  ·  صفحة {ar(page)} من {ar(self.riw.max_page)}')
        self.btn_prev.setEnabled(page > 1)
        self.btn_next.setEnabled(page < self.riw.max_page)
        if hasattr(self, 'btn_mark'):
            self.update_mark_button()

    # ---------- الإعدادات (فيها الفهرس) ----------
    def build_settings(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(14)

        # المظهر
        g_look = QGroupBox('المظهر')
        f = QFormLayout(g_look)
        self.chk_dark = QCheckBox('الوضع الليلي')
        self.chk_dark.setChecked(self.dark)
        self.chk_dark.toggled.connect(self.on_dark)
        self.spin_font = QSpinBox()
        self.spin_font.setRange(16, 48)
        self.spin_font.setValue(self.font_pt)
        self.spin_font.valueChanged.connect(self.on_font)
        f.addRow(self.chk_dark)
        f.addRow('حجم خط المصحف', self.spin_font)
        lay.addWidget(g_look)

        # اختيار المصحف
        g_mushaf = QGroupBox('اختيار المصحف')
        f2 = QFormLayout(g_mushaf)
        self.combo_riwaya = QComboBox()
        for rid in ('warsh', 'qalun', 'duri'):
            self.combo_riwaya.addItem(RIWAYA_NAMES[rid], rid)
        self.combo_riwaya.setCurrentIndex(self.combo_riwaya.findData(self.riwaya_id))
        self.combo_riwaya.currentIndexChanged.connect(self.on_riwaya)
        f2.addRow('الرواية والرسم', self.combo_riwaya)
        lay.addWidget(g_mushaf)

        # الفهرس: السورة، الجزء، الآية
        g_idx = QGroupBox('الفهرس')
        f3 = QFormLayout(g_idx)
        self.combo_surah = QComboBox()
        for s in SURAHS:
            self.combo_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.combo_surah.currentIndexChanged.connect(self.on_surah_index)
        self.combo_juz = QComboBox()
        for i in range(len(JUZ_START)):
            self.combo_juz.addItem(f'الجزء {ar(i + 1)}', i)
        self.combo_juz.currentIndexChanged.connect(self.on_juz)
        self.combo_ayah = QComboBox()
        self.combo_ayah.currentIndexChanged.connect(self.on_ayah)
        f3.addRow('السورة', self.combo_surah)
        f3.addRow('الجزء', self.combo_juz)
        f3.addRow('الآية', self.combo_ayah)
        lay.addWidget(g_idx)

        # عن التطبيق
        g_about = QGroupBox('عن التطبيق')
        a = QVBoxLayout(g_about)
        about = QLabel(f'المصحف - نسخة سطح المكتب الأصلية، الإصدار {APP_VERSION}.\n'
                       'مصحف بالرواية المختارة، صفحة بصفحة، مع التلاوة والتفسير والحفظ والورد.')
        about.setWordWrap(True)
        a.addWidget(about)
        btn_search = QPushButton('🔍 البحث في القرآن')
        btn_search.clicked.connect(lambda: self.show_view('search'))
        a.addWidget(btn_search)
        lay.addWidget(g_about)

        lay.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    def sync_index(self):
        """يخلي الفهرس يعرض مكان القراءة الحالي."""
        s, a = self.current_ayah()
        self.combo_surah.blockSignals(True)
        self.combo_surah.setCurrentIndex(self.combo_surah.findData(s))
        self.combo_surah.blockSignals(False)
        self.combo_juz.blockSignals(True)
        self.combo_juz.setCurrentIndex(juz_of(s, a) - 1)
        self.combo_juz.blockSignals(False)
        self.fill_ayah_combo(s, a)

    def current_ayah(self):
        for (s, a), page in sorted(self.riw.where.items(), key=lambda kv: kv[1]):
            if page == self.page:
                return s, a
            if page > self.page:
                break
        return 1, 1

    def fill_ayah_combo(self, s, current=1):
        self.combo_ayah.blockSignals(True)
        self.combo_ayah.clear()
        count = SURAHS[s - 1]['numberOfAyahs']
        for n in range(1, count + 1):
            self.combo_ayah.addItem(ar(n), n)
        self.combo_ayah.setCurrentIndex(max(current - 1, 0))
        self.combo_ayah.blockSignals(False)

    def on_surah_index(self, idx):
        s = self.combo_surah.itemData(idx)
        if s is None:
            return
        self.fill_ayah_combo(s, 1)
        self.go_page(self.riw.page_of(s, 1))
        self.show_view('reader')

    def on_juz(self, idx):
        if idx < 0:
            return
        s, a = JUZ_START[idx]
        self.go_page(self.riw.page_of(s, a))
        self.show_view('reader')

    def on_ayah(self, idx):
        if idx < 0:
            return
        s = self.combo_surah.currentData()
        self.go_page(self.riw.page_of(s, idx + 1))
        self.show_view('reader')

    def on_dark(self, checked):
        self.dark = checked
        self.settings.setValue('dark', checked)
        self.apply_theme()

    def on_font(self, value):
        self.font_pt = value
        self.settings.setValue('font_pt', value)
        self.render_page()

    def on_riwaya(self, idx):
        rid = self.combo_riwaya.itemData(idx)
        if rid == self.riwaya_id:
            return
        self.riwaya_id = rid
        self.settings.setValue('riwaya', rid)
        self.riw = Riwaya(rid)
        self.page = min(self.page, self.riw.max_page)
        self.render_page()

    # ---------- الأذكار ----------
    def build_adhkar(self):
        w = QWidget()
        self.adh_lay = QVBoxLayout(w)
        self.adh_lay.setContentsMargins(24, 16, 24, 16)
        self.adh_title = QLabel()
        self.adh_title.setStyleSheet('font-size: 20px; font-weight: bold;')
        self.adh_lay.addWidget(self.adh_title)
        self.adh_browser = QScrollArea()
        self.adh_browser.setWidgetResizable(True)
        self.adh_browser.setFrameShape(QScrollArea.Shape.NoFrame)
        self.adh_list = QWidget()
        self.adh_items = QVBoxLayout(self.adh_list)
        self.adh_items.setSpacing(10)
        self.adh_browser.setWidget(self.adh_list)
        self.adh_lay.addWidget(self.adh_browser, 1)
        self.adh_cat = 0
        return w

    def adhkar_counts(self):
        raw = self.settings.value('adhkar', '{}', type=str)
        try:
            data = json.loads(raw)
        except ValueError:
            data = {}
        today = datetime.date.today().isoformat()
        if data.get('day') != today:
            data = {'day': today, 'c': {}}
        return data

    def save_adhkar(self, data):
        self.settings.setValue('adhkar', json.dumps(data, ensure_ascii=False))

    def show_adhkar(self, idx):
        self.adh_cat = idx
        cat = ADHKAR[idx]
        self.adh_title.setText(cat['name'])
        while self.adh_items.count():
            item = self.adh_items.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        counts = self.adhkar_counts()
        for i, it in enumerate(cat['items']):
            key = f'{idx}:{i}'
            n = min(it['count'], counts['c'].get(key, 0))
            card = QWidget()
            card.setObjectName('card')
            row = QHBoxLayout(card)
            text = QLabel(it['text'])
            text.setWordWrap(True)
            text.setStyleSheet('font-family: "Amiri Quran"; font-size: 18px; line-height: 170%;')
            btn = QPushButton(f'{ar(n)} / {ar(it["count"])}')
            btn.setMinimumWidth(96)
            btn.clicked.connect(lambda checked=False, k=key, mx=it['count'], b=btn: self.bump_adhkar(k, mx, b))
            row.addWidget(text, 1)
            row.addWidget(btn)
            self.adh_items.addWidget(card)
        self.adh_items.addStretch(1)
        self.show_view('adhkar')

    def bump_adhkar(self, key, maximum, btn):
        data = self.adhkar_counts()
        cur = data['c'].get(key, 0)
        data['c'][key] = 0 if cur >= maximum else cur + 1
        self.save_adhkar(data)
        btn.setText(f'{ar(data["c"][key])} / {ar(maximum)}')

    # ---------- أحكام التجويد ----------
    def build_tajweed(self):
        self.tj_browser = QTextBrowser()
        self.tj_browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        return self.tj_browser

    def fill_tajweed(self):
        rows = ''.join(
            f'<p><b style="font-size:16pt">{html.escape(name)}</b><br>'
            f'<span>{html.escape(desc)}</span></p>'
            for name, desc in TAJWEED.values())
        self.tj_browser.setHtml(f'<html><body dir="rtl"><h2 align="center">أحكام التجويد</h2>{rows}</body></html>')

    # ---------- المعاني ----------
    def build_meanings(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        self.mn_combo = QComboBox()
        for s in SURAHS:
            self.mn_combo.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.mn_combo.currentIndexChanged.connect(lambda _i: self.render_meanings())
        lay.addWidget(self.mn_combo)
        self.mn_browser = QTextBrowser()
        self.mn_browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        lay.addWidget(self.mn_browser, 1)
        return w

    def render_meanings(self):
        s = self.mn_combo.currentData() or 1
        info = SURAHS[s - 1]
        parts = []
        for n in range(1, info['numberOfAyahs'] + 1):
            books = MEANINGS.get(f'{s}:{n}')
            if not books:
                continue
            parts.append(f'<h3>{html.escape(info["name"])} - الآية {ar(n)}</h3>')
            for book, words in books:
                parts.append(f'<p style="color:#888">{html.escape(book)}</p>')
                for t, m in words:
                    parts.append(f'<p><b>{html.escape(t)}</b> {html.escape(m)}</p>')
        body = ''.join(parts) or '<p>لا توجد معانٍ مسجلة لهذه السورة.</p>'
        self.mn_browser.setHtml(f'<html><body dir="rtl">{body}</body></html>')

    # ---------- مساعدات التخزين ----------
    def get_json_setting(self, key, default):
        try:
            return json.loads(self.settings.value(key, '', type=str) or 'null') or default
        except ValueError:
            return default

    def set_json_setting(self, key, value):
        self.settings.setValue(key, json.dumps(value, ensure_ascii=False))

    @staticmethod
    def today():
        return datetime.date.today().isoformat()

    def make_card(self, title):
        card = QWidget()
        card.setObjectName('card')
        lay = QVBoxLayout(card)
        value = QLabel('٠')
        value.setStyleSheet('font-size: 30px; font-weight: bold;')
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption = QLabel(title)
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(value)
        lay.addWidget(caption)
        return card, value

    # ---------- الصوت (التلاوة) ----------
    def toggle_play(self):
        if self.playing:
            self.stop_play('أوقفت التلاوة')
            return
        self.play_queue = [(s, a) for s, a, _t in self.riw.by_page.get(self.page, [])]
        if not self.play_queue:
            return
        self.playing = True
        self.btn_play.setText('⏹ إيقاف التلاوة')
        self.play_next()

    def play_next(self):
        if not self.play_queue:
            self.stop_play('انتهت تلاوة الصفحة')
            return
        s, a = self.play_queue.pop(0)
        rid = self.reciter_combo.currentData()
        folder = RECITERS[rid][1]
        self.player.setSource(QUrl(f'https://everyayah.com/data/{folder}/{s:03d}{a:03d}.mp3'))
        self.player.play()
        self.play_status.setText(f'{SURAHS[s - 1]["name"]} · الآية {ar(a)}')

    def stop_play(self, message=''):
        self.playing = False
        self.play_queue = []
        self.player.stop()
        self.btn_play.setText('▶ تلاوة الصفحة')
        self.play_status.setText(message)

    def on_media_status(self, status):
        if self.playing and status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next()

    def on_media_error(self, *_args):
        if self.playing:
            self.stop_play('تعذّر تشغيل الصوت، تأكد من الاتصال بالإنترنت')

    # ---------- المحفوظات (الصفحات المحفوظة) ----------
    def bookmarks(self):
        return sorted(set(int(p) for p in self.get_json_setting('bookmarks', [])))

    def toggle_bookmark(self):
        marks = self.bookmarks()
        if self.page in marks:
            marks.remove(self.page)
        else:
            marks.append(self.page)
        self.set_json_setting('bookmarks', sorted(marks))
        self.update_mark_button()

    def update_mark_button(self):
        saved = self.page in self.bookmarks()
        self.btn_mark.setText('★ الصفحة محفوظة' if saved else '☆ حفظ الصفحة')

    def page_title(self, page):
        items = self.riw.by_page.get(page, [])
        if not items:
            return f'صفحة {ar(page)}'
        s, a, _t = items[0]
        return f'صفحة {ar(page)} · الجزء {ar(juz_of(s, a))} · {SURAHS[s - 1]["name"]}'

    def build_bookmarks(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        title = QLabel('المحفوظات')
        title.setStyleSheet('font-size: 20px; font-weight: bold;')
        lay.addWidget(title)
        self.bm_list = QListWidget()
        self.bm_list.itemActivated.connect(self.open_bookmark)
        lay.addWidget(self.bm_list, 1)
        row = QHBoxLayout()
        btn_open = QPushButton('فتح الصفحة')
        btn_open.clicked.connect(lambda: self.open_bookmark(self.bm_list.currentItem()))
        btn_del = QPushButton('حذف المحدد')
        btn_del.clicked.connect(self.delete_bookmark)
        row.addWidget(btn_open)
        row.addWidget(btn_del)
        row.addStretch(1)
        lay.addLayout(row)
        self.bm_empty = QLabel('لا توجد صفحات محفوظة بعد. اضغط "☆ حفظ الصفحة" من المصحف.')
        self.bm_empty.setStyleSheet('color: #888;')
        lay.addWidget(self.bm_empty)
        return w

    def render_bookmarks(self):
        self.bm_list.clear()
        for page in self.bookmarks():
            item = QListWidgetItem(self.page_title(page))
            item.setData(Qt.ItemDataRole.UserRole, page)
            self.bm_list.addItem(item)
        self.bm_empty.setVisible(self.bm_list.count() == 0)

    def open_bookmark(self, item):
        if item is None:
            return
        self.go_page(item.data(Qt.ItemDataRole.UserRole))
        self.show_view('reader')

    def delete_bookmark(self):
        item = self.bm_list.currentItem()
        if item is None:
            return
        page = item.data(Qt.ItemDataRole.UserRole)
        self.set_json_setting('bookmarks', [p for p in self.bookmarks() if p != page])
        self.render_bookmarks()
        self.update_mark_button()

    # ---------- الإحصائيات ----------
    def count_page_visit(self):
        days = self.get_json_setting('days', {})
        key = self.today()
        days[key] = days.get(key, 0) + 1
        self.set_json_setting('days', days)

    def streak(self, days):
        day = datetime.date.today()
        if days.get(day.isoformat(), 0) == 0:
            day -= datetime.timedelta(days=1)
        count = 0
        while days.get(day.isoformat(), 0) > 0:
            count += 1
            day -= datetime.timedelta(days=1)
        return count

    def build_stats(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        title = QLabel('الإحصائيات')
        title.setStyleSheet('font-size: 20px; font-weight: bold;')
        lay.addWidget(title)
        grid = QHBoxLayout()
        self.st_cards = {}
        for key, caption in (('today', 'صفحات اليوم'), ('total', 'إجمالي الصفحات المقروءة'),
                             ('streak', 'أيام متتالية'), ('adhkar', 'أذكار مكتملة اليوم'),
                             ('bookmarks', 'صفحات محفوظة'), ('wird', 'أوراد مكتملة')):
            card, value = self.make_card(caption)
            self.st_cards[key] = value
            grid.addWidget(card, 1)
        lay.addLayout(grid)
        note = QLabel('تُحسب صفحات القراءة عند التنقل بين صفحات المصحف.')
        note.setStyleSheet('color: #888;')
        lay.addWidget(note)
        lay.addStretch(1)
        return w

    def render_stats(self):
        days = self.get_json_setting('days', {})
        total = sum(days.values())
        counts = self.adhkar_counts()
        done = 0
        for idx, cat in enumerate(ADHKAR):
            for i, it in enumerate(cat['items']):
                if counts['c'].get(f'{idx}:{i}', 0) >= it['count']:
                    done += 1
        self.st_cards['today'].setText(ar(days.get(self.today(), 0)))
        self.st_cards['total'].setText(ar(total))
        self.st_cards['streak'].setText(ar(self.streak(days)))
        self.st_cards['adhkar'].setText(ar(done))
        self.st_cards['bookmarks'].setText(ar(len(self.bookmarks())))
        self.st_cards['wird'].setText(ar(self.settings.value('wird_count', 0, type=int)))

    # ---------- الورد ----------
    def build_wird(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        title = QLabel('الورد اليومي')
        title.setStyleSheet('font-size: 20px; font-weight: bold;')
        lay.addWidget(title)
        form = QFormLayout()
        self.wird_target = QSpinBox()
        self.wird_target.setRange(1, 60)
        self.wird_target.setValue(self.settings.value('wird_target', 5, type=int))
        self.wird_target.valueChanged.connect(self.on_wird_target)
        form.addRow('عدد الصفحات في اليوم', self.wird_target)
        lay.addLayout(form)
        card = QWidget()
        card.setObjectName('card')
        cl = QVBoxLayout(card)
        self.wird_text = QLabel()
        self.wird_text.setWordWrap(True)
        self.wird_text.setStyleSheet('font-size: 18px;')
        cl.addWidget(self.wird_text)
        lay.addWidget(card)
        row = QHBoxLayout()
        self.btn_wird_read = QPushButton('📖 ابدأ ورد اليوم')
        self.btn_wird_read.clicked.connect(self.start_wird)
        self.btn_wird_done = QPushButton('✔ تم الورد')
        self.btn_wird_done.clicked.connect(self.finish_wird)
        self.btn_wird_reset = QPushButton('↺ ابدأ من أول القرآن')
        self.btn_wird_reset.clicked.connect(self.reset_wird)
        row.addWidget(self.btn_wird_read)
        row.addWidget(self.btn_wird_done)
        row.addWidget(self.btn_wird_reset)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
        return w

    def wird_range(self):
        start = self.settings.value('wird_next', 0, type=int) or self.page
        start = min(max(start, 1), self.riw.max_page)
        end = min(start + self.wird_target.value() - 1, self.riw.max_page)
        return start, end

    def render_wird(self):
        self.wird_target.blockSignals(True)
        self.wird_target.setValue(self.settings.value('wird_target', 5, type=int))
        self.wird_target.blockSignals(False)
        start, end = self.wird_range()
        done_today = self.settings.value('wird_day', '', type=str) == self.today()
        self.btn_wird_done.setEnabled(not done_today)
        head = 'أنجزت ورد اليوم ✔' if done_today else 'ورد اليوم'
        self.wird_text.setText(f'{head}: من صفحة {ar(start)} إلى صفحة {ar(end)} '
                               f'({ar(end - start + 1)} صفحات)')

    def on_wird_target(self, value):
        self.settings.setValue('wird_target', value)
        self.render_wird()

    def start_wird(self):
        start, _end = self.wird_range()
        self.go_page(start)
        self.show_view('reader')

    def finish_wird(self):
        _start, end = self.wird_range()
        nxt = end + 1
        if nxt > self.riw.max_page:
            nxt = 1
        self.settings.setValue('wird_next', nxt)
        self.settings.setValue('wird_day', self.today())
        self.settings.setValue('wird_count', self.settings.value('wird_count', 0, type=int) + 1)
        self.render_wird()

    def reset_wird(self):
        self.settings.setValue('wird_next', 1)
        self.settings.setValue('wird_day', '')
        self.render_wird()

    # ---------- وضع الحفظ ----------
    def build_memo(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        title = QLabel('وضع الحفظ')
        title.setStyleSheet('font-size: 20px; font-weight: bold;')
        lay.addWidget(title)
        row = QHBoxLayout()
        self.memo_surah = QComboBox()
        for s in SURAHS:
            self.memo_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.memo_surah.currentIndexChanged.connect(self.on_memo_surah)
        self.memo_from = QSpinBox()
        self.memo_to = QSpinBox()
        for sp in (self.memo_from, self.memo_to):
            sp.valueChanged.connect(lambda _v: self.render_memo())
        self.memo_hide = QCheckBox('إخفاء النص للاختبار')
        self.memo_hide.toggled.connect(lambda _c: self.render_memo())
        row.addWidget(QLabel('السورة'))
        row.addWidget(self.memo_surah, 1)
        row.addWidget(QLabel('من آية'))
        row.addWidget(self.memo_from)
        row.addWidget(QLabel('إلى آية'))
        row.addWidget(self.memo_to)
        lay.addLayout(row)
        lay.addWidget(self.memo_hide)
        self.memo_browser = QTextBrowser()
        self.memo_browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        lay.addWidget(self.memo_browser, 1)
        self.on_memo_surah(0)
        return w

    def on_memo_surah(self, _idx):
        s = self.memo_surah.currentData()
        count = SURAHS[s - 1]['numberOfAyahs']
        for sp, val in ((self.memo_from, 1), (self.memo_to, count)):
            sp.blockSignals(True)
            sp.setRange(1, count)
            sp.setValue(val)
            sp.blockSignals(False)
        self.render_memo()

    def render_memo(self):
        if not hasattr(self, 'memo_from'):
            return
        s = self.memo_surah.currentData() or 1
        lo, hi = sorted((self.memo_from.value(), self.memo_to.value()))
        hide = self.memo_hide.isChecked()
        parts = []
        for a in range(lo, hi + 1):
            text = AYAH_TEXT.get((s, a), '')
            if hide:
                text = ' '.join('•••' for _ in text.split())
            parts.append(f'{html.escape(text)} <span style="font-size:14pt">﴿{ar(a)}﴾</span> ')
        head = html.escape(SURAHS[s - 1]['name'])
        body = ''.join(parts) or 'لا توجد آيات'
        self.memo_browser.setHtml(
            f'<html><body dir="rtl" style="font-family:\'Amiri Quran\'; font-size:24pt; line-height:180%;">'
            f'<p align="center"><b>{head}</b></p><p align="center" dir="rtl">{body}</p></body></html>')

    # ---------- التفسير ----------
    def build_tafsir(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        row = QHBoxLayout()
        self.tf_surah = QComboBox()
        for s in SURAHS:
            self.tf_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.tf_surah.currentIndexChanged.connect(self.on_tf_surah)
        self.tf_ayah = QSpinBox()
        self.tf_ayah.valueChanged.connect(lambda _v: self.load_tafsir())
        btn_prev = QPushButton('‹ السابقة')
        btn_prev.clicked.connect(lambda: self.tf_ayah.setValue(self.tf_ayah.value() - 1))
        btn_next = QPushButton('التالية ›')
        btn_next.clicked.connect(lambda: self.tf_ayah.setValue(self.tf_ayah.value() + 1))
        row.addWidget(QLabel('السورة'))
        row.addWidget(self.tf_surah, 1)
        row.addWidget(QLabel('الآية'))
        row.addWidget(self.tf_ayah)
        row.addWidget(btn_prev)
        row.addWidget(btn_next)
        lay.addLayout(row)
        self.tf_browser = QTextBrowser()
        self.tf_browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        lay.addWidget(self.tf_browser, 1)
        self.tf_cache = {}
        self.tf_key = None
        self.on_tf_surah(0)
        return w

    def on_tf_surah(self, _idx):
        s = self.tf_surah.currentData() or 1
        self.tf_ayah.blockSignals(True)
        self.tf_ayah.setRange(1, SURAHS[s - 1]['numberOfAyahs'])
        self.tf_ayah.setValue(1)
        self.tf_ayah.blockSignals(False)
        self.load_tafsir()

    def load_tafsir(self):
        if not hasattr(self, 'tf_ayah'):
            return
        s = self.tf_surah.currentData() or 1
        a = self.tf_ayah.value()
        self.tf_key = (s, a)
        arabic = html.escape(AYAH_TEXT.get((s, a), ''))
        head = (f'<p align="center" style="font-family:\'Amiri Quran\'; font-size:24pt;">{arabic} '
                f'<span style="font-size:14pt">﴿{ar(a)}﴾</span></p>'
                f'<p align="center"><b>{html.escape(SURAHS[s - 1]["name"])} · الآية {ar(a)}</b></p>')
        if (s, a) in self.tf_cache:
            self.show_tafsir(head, self.tf_cache[(s, a)])
            return
        self.tf_browser.setHtml(f'<html><body dir="rtl">{head}<p align="center">جارٍ تحميل التفسير…</p></body></html>')
        req = QNetworkRequest(QUrl(f'https://api.alquran.cloud/v1/ayah/{s}:{a}/ar.muyassar'))
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self.on_tafsir_reply(reply, (s, a), head))

    def on_tafsir_reply(self, reply, key, head):
        text = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                text = json.loads(bytes(reply.readAll()).decode('utf-8'))['data']['text']
            except (ValueError, KeyError, TypeError):
                text = None
        reply.deleteLater()
        if text is None:
            if key == self.tf_key:
                self.tf_browser.setHtml(f'<html><body dir="rtl">{head}<p align="center">تعذّر تحميل التفسير، '
                                        'تأكد من الاتصال بالإنترنت.</p></body></html>')
            return
        self.tf_cache[key] = text
        if key == self.tf_key:
            self.show_tafsir(head, text)

    def show_tafsir(self, head, text):
        self.tf_browser.setHtml(
            f'<html><body dir="rtl">{head}<h3>التفسير الميسر</h3>'
            f'<p style="font-size:16pt; line-height:170%;">{html.escape(text)}</p></body></html>')

    # ---------- البحث ----------
    def build_search(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        title = QLabel('البحث في القرآن')
        title.setStyleSheet('font-size: 20px; font-weight: bold;')
        lay.addWidget(title)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('اكتب كلمة أو عبارة، ثم اضغط Enter')
        self.search_input.returnPressed.connect(self.run_search)
        self.search_input.textChanged.connect(lambda _t: self.run_search())
        lay.addWidget(self.search_input)
        self.search_status = QLabel()
        self.search_status.setStyleSheet('color: #888;')
        lay.addWidget(self.search_status)
        self.search_results = QListWidget()
        self.search_results.itemActivated.connect(self.open_search_result)
        self.search_results.itemDoubleClicked.connect(self.open_search_result)
        lay.addWidget(self.search_results, 1)
        return w

    def run_search(self):
        q = norm(self.search_input.text().strip())
        self.search_results.clear()
        if not q:
            self.search_status.setText('')
            return
        found = 0
        for s, a, n, text in SEARCH_INDEX:
            if q in n:
                found += 1
                item = QListWidgetItem(f'{SURAHS[s - 1]["name"]} {ar(a)}  ·  {text}')
                item.setData(Qt.ItemDataRole.UserRole, (s, a))
                self.search_results.addItem(item)
                if found >= 300:
                    break
        self.search_status.setText(f'{ar(found)} نتيجة' + (' (أول 300 فقط)' if found >= 300 else ''))

    def open_search_result(self, item):
        if item is None:
            return
        s, a = item.data(Qt.ItemDataRole.UserRole)
        self.go_page(self.riw.page_of(s, a))
        self.show_view('reader')

    # ---------- الثيم ----------
    def apply_theme(self):
        t = THEMES[self.dark]
        self.setStyleSheet(f"""
            QWidget#root {{ background: {t['bg']}; color: {t['text']}; }}
            QWidget#topbar {{ background: {t['card']}; border-bottom: 1px solid {t['line']}; }}
            QWidget#card {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 12px; }}
            QLabel#placeholder {{ color: {t['muted']}; font-size: 18px; }}
            QToolButton {{ background: transparent; color: {t['text']}; border: 1px solid transparent;
                          border-radius: 10px; padding: 8px 14px; font-size: 15px; }}
            QToolButton:hover {{ background: {t['hover']}; }}
            QToolButton::menu-indicator {{ image: none; width: 0px; }}
            QToolButton[active="true"] {{ background: {t['brand']}; color: #ffffff; }}
            QToolButton:pressed {{ background: {t['brand']}; color: #ffffff; }}
            QTextBrowser {{ background: {t['page']}; color: {t['text']}; border: 1px solid {t['line']};
                           border-radius: 14px; padding: 18px; }}
            QScrollArea {{ background: {t['bg']}; }}
            QWidget {{ color: {t['text']}; }}
            QComboBox, QSpinBox {{ background: {t['card']}; color: {t['text']}; border: 1px solid {t['line']};
                                   border-radius: 8px; padding: 6px 10px; min-height: 28px; }}
            QComboBox QAbstractItemView {{ background: {t['card']}; color: {t['text']};
                                           selection-background-color: {t['brand']}; }}
            QPushButton {{ background: {t['brand']}; color: #ffffff; border: none; border-radius: 10px;
                          padding: 8px 14px; font-size: 14px; }}
            QPushButton:disabled {{ background: {t['line']}; color: {t['muted']}; }}
            QGroupBox {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 14px;
                        margin-top: 22px; padding: 14px; font-weight: bold; }}
            QGroupBox::title {{ subcontrol-origin: margin; right: 14px; padding: 0 6px; }}
            QMenu {{ background: {t['card']}; color: {t['text']}; border: 1px solid {t['line']}; padding: 6px; }}
            QMenu::item {{ padding: 9px 26px; font-size: 14px; }}
            QMenu::item:selected {{ background: {t['brand']}; color: #ffffff; }}
            QCheckBox {{ color: {t['text']}; }}
            QLineEdit {{ background: {t['card']}; color: {t['text']}; border: 1px solid {t['line']};
                        border-radius: 10px; padding: 8px 12px; font-size: 16px; }}
            QListWidget {{ background: {t['card']}; color: {t['text']}; border: 1px solid {t['line']};
                          border-radius: 12px; padding: 6px; font-size: 15px; }}
            QListWidget::item {{ padding: 8px; }}
            QListWidget::item:selected {{ background: {t['brand']}; color: #ffffff; }}
        """)
        # خط القرآن للمحتوى، والخط العادي للواجهة
        self.refresh_styles()


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    QFontDatabase.addApplicationFont(str(FONTS / 'AmiriQuran-arabic.woff2'))
    win = Main()
    win.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
