#!/usr/bin/env python3
"""المصحف - تطبيق سطح المكتب (Qt أصلي) بنفس مميزات تطبيق الأندرويد 1.3.1.

الملفات كلها محلية، والتلاوة والتفسير من الإنترنت كما في الأندرويد.
تشغيل:   python3 main.py
اختبار:  python3 main.py --selftest
"""
import datetime
import array
import hashlib
from collections import deque
import html
import json
import os
import re
import sys
import time
from pathlib import Path

from PySide6.QtCore import QByteArray, QObject, QPropertyAnimation, QRect, QSettings, QSize, QStandardPaths, Qt, QTimer, QUrl, Signal
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QFontDatabase, QGuiApplication, QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut, QTextDocument
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame,
    QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QDialog, QMainWindow, QMessageBox, QProgressBar, QPushButton, QRadioButton, QScrollArea, QSpinBox,
    QStackedWidget, QTextBrowser,
    QVBoxLayout, QWidget,
)

APP_NAME = 'Mushaf'
APP_VERSION = '4.0.6'  # محتوى مطابق لتطبيق الأندرويد 1.3.1

if getattr(sys, 'frozen', False):
    BASE = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
else:
    BASE = Path(__file__).resolve().parent
DATA = BASE / 'data'
FONTS = BASE / 'fonts'
ICON = BASE / 'icon.png'

ARABIC_DIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def ar(n):
    return str(n).translate(ARABIC_DIGITS)


def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


SURAHS = load('surahs.json')
JUZ_START = [tuple(x) for x in load('juz.json')]
TAJWEED = load('tajweed.json')
MEANINGS = load('quran-meanings.json')['ayahs']
ADHKAR = load('adhkar.json')['categories']
SEARCH_AYAHS = load('quran-search.json')['ayahs']
RIW_DATA = load('quran-riwayat.json')['riwayat']
HAFS = load('hafs.json')
AYAH_TEXT = {(s, a): t for s, a, _p, t in HAFS['uthmani']}

TOTAL_PAGES = 604

HAFS_EDITIONS = [
    ('quran-uthmani', 'حفص عن عاصم - الرسم العثماني'),
    ('quran-simple', 'حفص - رسم إملائي مبسط'),
    ('quran-uthmani-min', 'حفص - عثماني مختصر'),
    ('quran-tajweed', 'حفص - بألوان أحكام التجويد'),
]
OTHER_RIWAYAT = [
    ('warsh', 'ورش عن نافع'),
    ('qalun', 'قالون عن نافع'),
    ('duri', 'الدوري عن أبي عمرو'),
]
RIWAYA_NAMES = dict(HAFS_EDITIONS + OTHER_RIWAYAT)

# قراء حفص (everyayah: ملف لكل آية) - نفس مصادر تطبيق الأندرويد
HAFS_RECITERS = [
    ('ar.alafasy', 'مشاري العفاسي', 'Alafasy_128kbps'),
    ('ar.abdurrahmaansudais', 'عبدالرحمن السديس', 'Abdurrahmaan_As-Sudais_192kbps'),
    ('ar.husary', 'محمود خليل الحصري', 'Husary_128kbps'),
    ('ar.husarymujawwad', 'الحصري (المجوّد)', 'Husary_128kbps_Mujawwad'),
    ('ar.hudhaify', 'علي الحذيفي', 'Hudhaify_128kbps'),
    ('ar.shaatree', 'أبو بكر الشاطري', 'Abu_Bakr_Ash-Shaatree_128kbps'),
    ('ar.hanirifai', 'هاني الرفاعي', 'Hani_Rifai_192kbps'),
    ('ar.ibrahimakhbar', 'إبراهيم الأخضر', 'Ibrahim_Akhdar_32kbps'),
    ('ar.aymanswoaid', 'أيمن سويد', 'Ayman_Sowaid_64kbps'),
    ('ar.abdullahbasfar', 'عبدالله بصفر', 'Abdullah_Basfar_192kbps'),
]
# قراء الروايات الثلاث: ayah = ملف لكل آية، surah = ملف لكل سورة (mp3quran)
RIW_RECITERS = {
    'warsh': [
        ('warsh_abdulbasit', 'عبدالباسط عبدالصمد', 'ayah', 'https://everyayah.com/data/warsh/warsh_Abdul_Basit_128kbps/'),
        ('warsh_husary', 'محمود خليل الحصري', 'surah', 'https://cdn.mp3quran.net/audio/mahmoud-husary/r3/'),
    ],
    'qalun': [
        ('qalun_husary', 'محمود خليل الحصري', 'surah', 'https://cdn.mp3quran.net/audio/mahmoud-husary/r5/'),
        ('qalun_hudhaify', 'علي الحذيفي', 'surah', 'https://cdn.mp3quran.net/audio/ali-hudhaifi/r2/'),
    ],
    'duri': [
        ('duri_husary', 'محمود خليل الحصري', 'surah', 'https://cdn.mp3quran.net/audio/mahmoud-husary/r4/'),
    ],
}
EVERY_FOLDER = {rid: folder for rid, _n, folder in HAFS_RECITERS}

TAFSIR_EDITIONS = [
    ('ar.muyassar', 'التفسير الميسر (مجمع الملك فهد)'),
    ('ar.jalalayn', 'تفسير الجلالين'),
    ('ar.waseet', 'التفسير الوسيط'),
    ('ar.baghawi', 'تفسير البغوي'),
    ('ar.qurtubi', 'تفسير القرطبي'),
    ('ar.miqbas', 'تنوير المقباس'),
]

_DIACRITICS = re.compile('[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]')


def norm(text):
    """تطبيع للبحث: بدون تشكيل ولا تطويل، والألفات والياء والتاء المربوطة موحّدة."""
    t = _DIACRITICS.sub('', text)
    return t.translate(str.maketrans('أإآٱىة', 'ااااية'))


SEARCH_INDEX = [(s, a, norm(t), t) for s, a, t in SEARCH_AYAHS]


def riwaya_rows(rid):
    if rid == 'quran-simple':
        return HAFS['simple']
    if rid in ('quran-uthmani', 'quran-uthmani-min', 'quran-tajweed'):
        return HAFS['uthmani']
    return RIW_DATA[rid]


class Book:
    """فهرس الرواية: من الصفحة إلى آياتها، ومن الآية إلى صفحتها."""

    def __init__(self, rid):
        self.rid = rid
        self.by_page = {}
        self.where = {}
        for row in riwaya_rows(rid):
            s, a, page, text = row
            self.by_page.setdefault(page, []).append((s, a, text))
            self.where[(s, a)] = page
        self.max_page = TOTAL_PAGES

    def page_of(self, s, a):
        while a >= 1:
            if (s, a) in self.where:
                return self.where[(s, a)]
            a -= 1
        return 1

    def ayahs_on_page(self, page):
        return self.by_page.get(page, [])


def juz_of(s, a):
    idx = 0
    for i, (js, ja) in enumerate(JUZ_START):
        if (js, ja) <= (s, a):
            idx = i
    return idx + 1


# ---------- الألوان والتصميم ----------
BASMALA = 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ'

THEMES = {
    'light': dict(bg='#eef3ef', side='#0f3d32', side_hi='#15614d', card='#ffffff', text='#1d2a26',
                  muted='#6b7b75', brand='#0f7a5c', brand_hi='#14996f', line='#d7e2dc',
                  paper='#fbf6e6', paper_line='#b8985a', hover='#e4ece8', danger='#b3261e'),
    'dark': dict(bg='#0c1210', side='#07110e', side_hi='#12332a', card='#16201d', text='#e6ede9',
                 muted='#8fa19a', brand='#22a77c', brand_hi='#2fc092', line='#26332f',
                 paper='#1d1c14', paper_line='#8c7440', hover='#1d2a26', danger='#ef6a60'),
}


def qss(t):
    return f"""
    QWidget {{ color: {t['text']}; font-family: 'Noto Sans Arabic'; font-size: 14px; }}
    QMainWindow, QWidget#root {{ background: {t['bg']}; }}
    QWidget#sidebar {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['side']}, stop:1 {t['side_hi']}); }}
    QLabel#brand {{ color: #ffffff; font-size: 22px; font-weight: 700; padding: 18px 16px 4px 16px; }}
    QLabel#brandSub {{ color: #bfe6d8; font-size: 12px; padding: 0 16px 14px 16px; }}
    QPushButton#nav {{ background: transparent; color: #cfe9df; border: none; border-radius: 12px;
                      padding: 11px 16px; text-align: right; font-size: 15px; margin: 2px 12px; }}
    QPushButton#nav:hover {{ background: rgba(255,255,255,0.08); }}
    QPushButton#nav:checked {{ background: {t['brand']}; color: #ffffff; font-weight: 700; }}
    QLabel#pageTitle {{ font-size: 24px; font-weight: 700; }}
    QLabel#pageSub {{ color: {t['muted']}; font-size: 13px; }}
    QFrame#card {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 16px; }}
    QLabel#muted {{ color: {t['muted']}; }}
    QLabel#stat {{ font-size: 34px; font-weight: 800; color: {t['brand']}; }}
    QTextBrowser#mushaf {{ background: {t['paper']}; border: 2px solid {t['paper_line']};
                          border-radius: 18px; padding: 26px 34px; }}
    QTextBrowser {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 16px; padding: 14px; }}
    QComboBox, QSpinBox, QLineEdit {{ background: {t['card']}; border: 1px solid {t['line']};
                                     border-radius: 10px; padding: 7px 12px; min-height: 26px; }}
    QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{ border: 1px solid {t['brand']}; }}
    QComboBox QAbstractItemView {{ background: {t['card']}; border: 1px solid {t['line']};
                                  selection-background-color: {t['brand']}; selection-color: #ffffff; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QPushButton {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 10px;
                  padding: 8px 16px; font-size: 14px; }}
    QPushButton:hover {{ background: {t['hover']}; }}
    QPushButton:disabled {{ color: {t['muted']}; }}
    QPushButton#primary {{ background: {t['brand']}; color: #ffffff; border: none; font-weight: 700; }}
    QPushButton#primary:hover {{ background: {t['brand_hi']}; }}
    QPushButton#danger {{ color: {t['danger']}; }}
    QListWidget {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 14px; padding: 6px; }}
    QListWidget::item {{ padding: 10px; border-radius: 8px; }}
    QListWidget::item:selected {{ background: {t['brand']}; color: #ffffff; }}
    QListWidget::item:hover {{ background: {t['hover']}; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {t['line']}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QGroupBox {{ font-weight: 700; }}
    QCheckBox {{ spacing: 8px; }}
    QMessageBox {{ background: {t['card']}; }}
    """


ICON_SVG = {
    'book': '<path d="M2 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H2z"/><path d="M22 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z"/>',
    'tafsir': '<path d="M4 4h12a2 2 0 0 1 2 2v14H6a2 2 0 0 1-2-2z"/><path d="M8 9h6M8 13h6"/>',
    'search': '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    'words': '<path d="M3 6h9M7.5 4v2M5 6c.8 3 2.5 5.5 5 7M10 6c-.8 3-2.5 5.5-5 7M13 20l4-10 4 10M14.5 16.5h5"/>',
    'tajweed': '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    'adhkar': '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="3.5" r="1.4"/><circle cx="12" cy="20.5" r="1.4"/><circle cx="3.5" cy="12" r="1.4"/><circle cx="20.5" cy="12" r="1.4"/>',
    'memo': '<path d="M4 20l4-1L19 8l-3-3L5 16z"/>',
    'wird': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    'bookmarks': '<path d="M6 3h12v18l-6-4-6 4z"/>',
    'stats': '<path d="M5 20V12M12 20V6M19 20V10"/>',
    'settings': '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8.5" stroke-dasharray="3 3"/>',
    'play': '<path d="M7 5l12 7-12 7z" fill="{c}"/>',
}


def svg_icon(name, color='#dff3ea', size=20):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size * 2}" height="{size * 2}" '
           f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           + ICON_SVG[name].replace('{c}', color) + '</svg>')
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    QSvgRenderer(QByteArray(svg.encode('utf-8'))).render(painter)
    painter.end()
    return QIcon(pm)


MEMO_GAPS = [1, 3, 7, 14, 30, 60]  # أيام بين المراجعات: تتباعد كلما أُتقن المقطع
MEMO_LEVELS = [0, 25, 50, 75, 100]  # نسبة الكلمات المخفية


def ayah_audio_url(rid, s, a):
    folder = EVERY_FOLDER.get(rid)
    return f'https://everyayah.com/data/{folder}/{s:03d}{a:03d}.mp3' if folder else None


def audio_file_name(url):
    return hashlib.sha1(url.encode('utf-8')).hexdigest()[:20] + '.mp3'


def full_refs():
    return [(s['number'], a) for s in SURAHS for a in range(1, s['numberOfAyahs'] + 1)]


def memo_word_hidden(s, a, i, pct):
    """إخفاء ثابت لكل كلمة: نفس الكلمة تختفي في كل مرة يُعرض فيها المقطع."""
    if pct >= 100:
        return True
    return ((i * 37 + a * 11 + s * 13) % 100) < pct


def share_card_image(text, surah_label, ayah_no):
    """صورة الآية للمشاركة: خط المصحف على خلفية ورقية وإطار ذهبي."""
    width, pad = 1080, 110
    doc = QTextDocument()
    doc.setHtml('<html><body dir="rtl"><div align="center" style="font-family:\'Amiri Quran\'; '
                'font-size:44pt; line-height:160%; color:#1d1d1b;">' + html.escape(text) + '</div></body></html>')
    doc.setTextWidth(width - 2 * pad)
    height = max(900, int(doc.size().height()) + 520)
    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(QColor('#fbf7ec'))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#b8924a'), 6))
    p.drawRect(36, 36, width - 72, height - 72)
    p.setPen(QPen(QColor('#b8924a'), 2))
    p.drawRect(56, 56, width - 112, height - 112)
    p.setPen(QColor('#8a6d2f'))
    p.setFont(QFont('Amiri Quran', 40))
    p.drawText(QRect(0, 110, width, 110), Qt.AlignmentFlag.AlignCenter, surah_label)
    p.translate(pad, 260)
    doc.drawContents(p)
    p.resetTransform()
    p.setFont(QFont('Amiri Quran', 34))
    p.drawText(QRect(0, height - 230, width, 80), Qt.AlignmentFlag.AlignCenter, '﴿ ' + ar(ayah_no) + ' ﴾')
    p.setFont(QFont('Amiri Quran', 28))
    p.drawText(QRect(0, height - 150, width, 60), Qt.AlignmentFlag.AlignCenter, 'القرآن الكريم')
    p.end()
    return img


def _miniaudio():
    """تحميل miniaudio عند أول تشغيل فقط: الإقلاع ما يعتمدش على الوحدة الأصلية."""
    import miniaudio
    return miniaudio


class AudioEngine(QObject):
    """يفك ملف MP3 ويشغّله على جهاز الصوت (miniaudio): مستقل عن Qt Multimedia وFFmpeg."""
    RATE = 44100
    CHUNK = 2048

    def __init__(self, parent=None):
        super().__init__(parent)
        self.src = None
        self.dev = None
        self.gen = None
        self.paused = False
        self.frames = 0
        self.ended = False
        self._done = False
        self.error = ''
        self.allow_null = False  # للاختبار فقط: بدون جهاز صوت يتقدم الوقت بالساعة
        self.null_mode = False
        self.pump = QTimer(self)
        self.pump.setInterval(40)
        self.pump.timeout.connect(self._pump_tick)

    def play(self, path):
        self.stop()
        self.error = ''
        ma = _miniaudio()
        self.src = ma.stream_file(str(path), output_format=ma.SampleFormat.SIGNED16,
                                  nchannels=2, sample_rate=self.RATE, frames_to_read=self.CHUNK)
        next(self.src)
        self.gen = self._callback()
        next(self.gen)
        self.frames = 0
        self.ended = False
        self._done = False
        self.paused = False
        try:
            self.dev = ma.PlaybackDevice(output_format=ma.SampleFormat.SIGNED16,
                                         nchannels=2, sample_rate=self.RATE)
            self.dev.start(self.gen)
            self.null_mode = False
        except Exception as exc:
            self.dev = None
            if not self.allow_null:
                self.stop()
                self.error = str(exc)
                raise
            self.null_mode = True
            self.pump.start()

    def _callback(self):
        silence = lambda n: bytes(n * 4)  # noqa: E731
        n = yield b''
        while True:
            n = n or self.CHUNK
            out = silence(n)
            if not (self.paused or self.src is None or self._done):
                try:
                    chunk = self.src.send(n)
                except StopIteration:
                    chunk = b''
                if isinstance(chunk, array.array):
                    chunk = chunk.tobytes()
                if chunk:
                    self.frames += len(chunk) // 4
                    out = chunk if len(chunk) == n * 4 else chunk + bytes(n * 4 - len(chunk))
                else:
                    self._done = True
                    self.ended = True
            n = yield out

    def _pump_tick(self):
        if self.gen is not None:
            try:
                self.gen.send(self.CHUNK)
            except StopIteration:
                pass

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def position_ms(self):
        return int(self.frames * 1000 / self.RATE)

    def take_ended(self):
        if self.ended:
            self.ended = False
            return True
        return False

    def stop(self):
        self.pump.stop()
        if self.dev is not None:
            try:
                self.dev.close()
            except Exception:
                pass
        self.dev = None
        self.gen = None
        self.src = None
        self.paused = False
        self.ended = False
        self._done = False
        self.null_mode = False
        self.frames = 0


class PageBrowser(QTextBrowser):
    """عرض الصفحة: عجلة الماوس عند الحافة تقلب الصفحة (مع فاصل زمني لمنع التقليب المتكرر)."""

    def __init__(self, on_turn):
        super().__init__()
        self._on_turn = on_turn
        self._last_turn = -1e9  # وقت آخر تقليب (ثوانٍ)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = (event.position().x(), event.position().y(), time.monotonic())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        super().mouseReleaseEvent(event)
        press = getattr(self, '_press', None)
        self._press = None
        if not press or event.button() != Qt.MouseButton.LeftButton:
            return
        dx = event.position().x() - press[0]
        dy = event.position().y() - press[1]
        held = time.monotonic() - press[2]
        if held < 0.35 and abs(dx) > 60 and abs(dx) > abs(dy) * 1.6:
            cur = self.textCursor()
            cur.clearSelection()
            self.setTextCursor(cur)
            self._on_turn(1 if dx > 0 else -1)

    def wheelEvent(self, event):  # noqa: N802
        bar = self.verticalScrollBar()
        dy = event.angleDelta().y()
        at_end = (dy < 0 and bar.value() >= bar.maximum()) or (dy > 0 and bar.value() <= bar.minimum())
        if dy and at_end:
            now = time.monotonic()
            if now - self._last_turn > 0.65:
                self._last_turn = now
                self._on_turn(1 if dy < 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


def card():
    f = QFrame()
    f.setObjectName('card')
    return f


def heading(title, sub=''):
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName('pageTitle')
    lay.addWidget(t)
    if False and sub:  # بدون جمل إرشادية في الواجهة
        s = QLabel(sub)
        s.setObjectName('pageSub')
        lay.addWidget(s)
    return box


def fade_in(widget):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b'opacity', widget)
    anim.setDuration(220)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start()
    widget._fade_anim = anim


UPDATE_MANIFEST = 'https://raw.githubusercontent.com/mosalah30688-gif/quran/main/update/manifest.json'


def version_tuple(v):
    nums = [int(x) for x in re.findall(r'\d+', str(v))][:4]
    return tuple(nums) or (0,)


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('المصحف')
        if ICON.exists():
            self.setWindowIcon(QIcon(str(ICON)))
        self.settings = QSettings('mosalah30688', APP_NAME)
        self.theme_name = self.settings.value('theme', 'light', type=str)
        if self.theme_name not in THEMES:
            self.theme_name = 'light'
        self.font_pt = self.settings.value('font_pt', 22, type=int)
        riwaya = self.settings.value('riwaya', 'quran-uthmani', type=str)
        if riwaya not in RIWAYA_NAMES:
            riwaya = 'quran-uthmani'
        self.riwaya_id = riwaya
        self.book = Book(riwaya)
        self.page = min(max(self.settings.value('page', 1, type=int), 1), TOTAL_PAGES)
        self.last_counted = None

        self.nam = QNetworkAccessManager(self)
        self.tafsir_cache = {}
        self.tafsir_key = None
        self.engine = AudioEngine(self)
        self.engine_timer = QTimer(self)
        self.engine_timer.setInterval(150)
        self.engine_timer.timeout.connect(self.on_audio_tick)
        self.engine_timer.start()
        self.play_token = 0
        self._auto_turn = False
        self.sel_ayah = None
        self.update_info = None
        self.update_busy = False
        self.upd_target = None
        self.queue_list = False
        self.dl = {'running': False}
        self.queue = []
        self.queue_index = -1
        self.playing = False
        self.highlight = None

        avail = QGuiApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(min(1000, avail.width() - 40), min(620, avail.height() - 80))
        self.resize(min(1440, int(avail.width() * 0.94)), min(900, int(avail.height() * 0.9)))
        self.move(avail.center() - self.rect().center())
        self.build_ui()
        self.apply_theme()
        self.show_view('reader')
        self.render_page()

        QShortcut(QKeySequence('PgDown'), self, activated=lambda: self.go_page(self.page + 1))
        QShortcut(QKeySequence('PgUp'), self, activated=lambda: self.go_page(self.page - 1))
        QShortcut(QKeySequence('Ctrl+P'), self, activated=self.toggle_play)
        QShortcut(QKeySequence('Ctrl+F'), self, activated=lambda: self.show_view('search'))
        QShortcut(QKeySequence('Ctrl+0'), self, activated=lambda: self.set_font(22))
        QShortcut(QKeySequence('Ctrl+='), self, activated=lambda: self.set_font(self.font_pt + 2))
        QShortcut(QKeySequence('Ctrl+-'), self, activated=lambda: self.set_font(self.font_pt - 2))
        QTimer.singleShot(4000, self.check_updates)  # فحص التحديث من المستودع عند البدء
        # الأسهم: يسار = الصفحة التالية، يمين = السابقة (اتجاه القراءة العربي وعكس أزرار الشاشة)
        for key, step in (('Left', 1), ('Right', -1)):
            sc = QShortcut(QKeySequence(key), self.views['reader'])
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(lambda d=step: self.go_page(self.page + d))

    # ---------- بناء الواجهة ----------
    def build_ui(self):
        root = QWidget()
        root.setObjectName('root')
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        side = QWidget()
        side.setObjectName('sidebar')
        side.setFixedWidth(248)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 12)
        brand = QLabel('المصحف')
        brand.setObjectName('brand')
        sub = QLabel(f'الإصدار {APP_VERSION}')
        sub.setObjectName('brandSub')
        sl.addWidget(brand)
        sl.addWidget(sub)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.views = {}
        self.nav_buttons = {}
        nav_items = [
            ('reader', 'book', 'المصحف'),
            ('tafsir', 'tafsir', 'التفسير'),
            ('search', 'search', 'البحث في القرآن'),
            ('meanings', 'words', 'معاني الكلمات'),
            ('tajweed', 'tajweed', 'أحكام التجويد'),
            ('adhkar', 'adhkar', 'الأذكار'),
            ('memo', 'memo', 'وضع الحفظ'),
            ('wird', 'wird', 'الورد اليومي'),
            ('bookmarks', 'bookmarks', 'المحفوظات'),
            ('stats', 'stats', 'الإحصائيات'),
        ]
        for key, icon, label in nav_items:
            b = QPushButton(label)
            b.setIcon(svg_icon(icon))
            b.setIconSize(QSize(20, 20))
            b.setObjectName('nav')
            b.setCheckable(True)
            b.clicked.connect(lambda _c=False, k=key: self.show_view(k))
            self.nav_group.addButton(b)
            self.nav_buttons[key] = b
            sl.addWidget(b)
        self.update_banner = QFrame()
        self.update_banner.setObjectName('card')
        ub = QVBoxLayout(self.update_banner)
        ub.setContentsMargins(12, 10, 12, 10)
        self.update_banner_label = QLabel()
        self.update_banner_label.setWordWrap(True)
        btn_update = QPushButton('تحميل التحديث')
        btn_update.setObjectName('primary')
        btn_update.clicked.connect(self.on_update_button)
        ub.addWidget(self.update_banner_label)
        ub.addWidget(btn_update)
        self.update_banner.hide()
        wrap_banner = QWidget()
        wl = QVBoxLayout(wrap_banner)
        wl.setContentsMargins(12, 0, 12, 0)
        wl.addWidget(self.update_banner)
        sl.addWidget(wrap_banner)
        sl.addStretch(1)
        b = QPushButton('الإعدادات')
        b.setIcon(svg_icon('settings'))
        b.setIconSize(QSize(20, 20))
        b.setObjectName('nav')
        b.setCheckable(True)
        b.clicked.connect(lambda: self.show_view('settings'))
        self.nav_group.addButton(b)
        self.nav_buttons['settings'] = b
        sl.addWidget(b)
        row.addWidget(side)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(26, 20, 26, 16)
        rl.setSpacing(14)
        self.stack = QStackedWidget()
        rl.addWidget(self.stack, 1)
        row.addWidget(right, 1)

        self.views['reader'] = self.build_reader()
        self.views['tafsir'] = self.build_tafsir()
        self.views['search'] = self.build_search()
        self.views['meanings'] = self.build_meanings()
        self.views['tajweed'] = self.build_tajweed()
        self.views['adhkar'] = self.build_adhkar()
        self.views['memo'] = self.build_memo()
        self.views['wird'] = self.build_wird()
        self.views['bookmarks'] = self.build_bookmarks()
        self.views['stats'] = self.build_stats()
        self.views['settings'] = self.build_settings()
        for w in self.views.values():
            self.stack.addWidget(w)
        self.statusBar().setSizeGripEnabled(False)

    def show_view(self, name):
        self.stack.setCurrentWidget(self.views[name])
        self.nav_buttons[name].setChecked(True)
        fade_in(self.views[name])
        if name == 'reader':
            self.sync_index()
        elif name == 'tafsir':
            self.load_tafsir()
        elif name == 'meanings':
            self.render_meanings()
        elif name == 'tajweed':
            self.render_tajweed()
        elif name == 'adhkar':
            self.show_adhkar(self.adh_cat)
        elif name == 'memo':
            self.render_memo()
        elif name == 'wird':
            self.render_wird()
        elif name == 'bookmarks':
            self.render_bookmarks()
        elif name == 'stats':
            self.render_stats()
        elif name == 'search':
            self.search_input.setFocus()

    # ---------- المصحف ----------
    def build_reader(self):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)

        # الفهرس على الجانب الأيمن: قوائم منسدلة للسورة والجزء والآية
        index_card = card()
        index_card.setFixedWidth(236)
        il = QVBoxLayout(index_card)
        il.setContentsMargins(14, 14, 14, 14)
        il.setSpacing(8)
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
        for title, combo in (('السورة', self.combo_surah), ('الجزء', self.combo_juz), ('الآية', self.combo_ayah)):
            lab = QLabel(title)
            lab.setObjectName('muted')
            il.addWidget(lab)
            il.addWidget(combo)
        il.addStretch(1)
        row.addWidget(index_card)

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(10)

        # شريط أعلى الصفحة: المشغل وزر العلامة وزر التفسير
        top = card()
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 8, 12, 8)
        tl.setSpacing(8)
        self.btn_play = QPushButton('▶  تشغيل')
        self.btn_play.setObjectName('primary')
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_stop = QPushButton('إيقاف')
        self.btn_stop.clicked.connect(lambda: self.stop_play(''))
        self.reciter_combo = QComboBox()
        self.reciter_combo.setMinimumWidth(190)
        self.reciter_combo.currentIndexChanged.connect(self.on_reciter_change)
        self.play_surah = QComboBox()
        for s in SURAHS:
            self.play_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.play_surah.currentIndexChanged.connect(self.on_play_surah)
        self.play_from = QComboBox()
        self.play_from.setMinimumWidth(80)
        self.btn_mark = QPushButton('علامة')
        self.btn_mark.clicked.connect(self.toggle_bookmark)
        self.btn_tafsir = QPushButton('التفسير')
        self.btn_tafsir.clicked.connect(lambda: self.toggle_tafsir_panel())
        for wdg in (self.btn_play, self.btn_stop, self.reciter_combo, self.play_surah, self.play_from):
            tl.addWidget(wdg)
        self.play_status = QLabel('')
        self.play_status.setObjectName('muted')
        tl.addWidget(self.play_status)
        tl.addStretch(1)
        tl.addWidget(self.btn_mark)
        tl.addWidget(self.btn_tafsir)
        cl.addWidget(top)

        self.page_info = QLabel()
        self.page_info.setObjectName('pageSub')
        self.page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.page_info)

        self.browser = PageBrowser(lambda d: self.go_page(self.page + d))
        self.browser.setObjectName('mushaf')
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        self.browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.browser.anchorClicked.connect(self.on_ayah_anchor)
        cl.addWidget(self.browser, 1)

        # التقليب أسفل الصفحة في المنتصف
        pager = QHBoxLayout()
        pager.setSpacing(12)
        self.btn_prev = QPushButton('‹ السابقة')
        self.btn_next = QPushButton('التالية ›')
        self.btn_next.clicked.connect(lambda: self.go_page(self.page + 1))
        self.btn_prev.clicked.connect(lambda: self.go_page(self.page - 1))
        self.page_label = QLabel()
        self.page_label.setObjectName('pageSub')
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumWidth(150)
        pager.addStretch(1)
        pager.addWidget(self.btn_prev)
        pager.addWidget(self.page_label)
        pager.addWidget(self.btn_next)
        pager.addStretch(1)
        cl.addLayout(pager)
        row.addWidget(center, 1)

        # لوحة التفسير (على اليسار، تظهر عند الضغط على زر التفسير)
        self.tp_frame = card()
        self.tp_frame.setFixedWidth(370)
        tpl = QVBoxLayout(self.tp_frame)
        tpl.setContentsMargins(14, 14, 14, 14)
        tpl.setSpacing(8)
        hdr = QHBoxLayout()
        self.tp_title = QLabel()
        self.tp_title.setStyleSheet('font-weight:700; font-size:16px;')
        btn_close = QPushButton('×')
        btn_close.setFixedWidth(36)
        btn_close.clicked.connect(lambda: self.toggle_tafsir_panel(False))
        hdr.addWidget(self.tp_title, 1)
        hdr.addWidget(btn_close)
        tpl.addLayout(hdr)
        self.tp_book = QComboBox()
        for eid, name in TAFSIR_EDITIONS:
            self.tp_book.addItem(name, eid)
        self.tp_book.setCurrentIndex(max(self.tp_book.findData(
            self.settings.value('tafsir', 'ar.muyassar', type=str)), 0))
        self.tp_book.currentIndexChanged.connect(self.on_tp_book)
        tpl.addWidget(self.tp_book)
        tools = QHBoxLayout()
        btn_mn = QPushButton('معاني الكلمات')
        btn_mn.clicked.connect(self.open_meanings_for_selected)
        btn_share_ayah = QPushButton('مشاركة الآية')
        btn_share_ayah.clicked.connect(self.share_selected_ayah)
        tools.addWidget(btn_mn)
        tools.addWidget(btn_share_ayah)
        tpl.addLayout(tools)
        self.tp_browser = QTextBrowser()
        self.tp_browser.setOpenExternalLinks(False)
        tpl.addWidget(self.tp_browser, 1)
        self.tp_frame.hide()
        row.addWidget(self.tp_frame)

        self.populate_reciters()
        self.populate_play_from()
        return w

    def populate_play_from(self):
        s = self.play_surah.currentData() or 1
        self.play_from.blockSignals(True)
        self.play_from.clear()
        for n in range(1, SURAHS[s - 1]['numberOfAyahs'] + 1):
            self.play_from.addItem(ar(n), n)
        self.play_from.blockSignals(False)

    def on_play_surah(self, _idx):
        self.populate_play_from()

    def toggle_tafsir_panel(self, show=None):
        if show is None:
            show = not self.tp_frame.isVisible()
        if show and self.sel_ayah is None:
            items = self.book.ayahs_on_page(self.page)
            if items:
                self.sel_ayah = (items[0][0], items[0][1])
                self.render_page()
        self.tp_frame.setVisible(show)
        if show:
            self.load_tp()

    def on_ayah_anchor(self, url):
        text = url.toString() if hasattr(url, 'toString') else str(url)
        m = re.match(r'ayah:(\d+):(\d+)$', text)
        if not m:
            return
        self.sel_ayah = (int(m.group(1)), int(m.group(2)))
        self.render_page()
        if self.tp_frame.isVisible():
            self.load_tp()

    def on_tp_book(self, _idx):
        self.settings.setValue('tafsir', self.tp_book.currentData())
        self.load_tp()

    def load_tp(self):
        if self.sel_ayah is None:
            return
        s, a = self.sel_ayah
        edition = self.tp_book.currentData()
        key = (edition, s, a)
        self.tp_key = key
        self.tp_title.setText(f'{SURAHS[s - 1]["name"]} · الآية {ar(a)}')
        if key in self.tafsir_cache:
            self.show_tp(self.tafsir_cache[key])
            return
        self.tp_browser.setHtml('<html><body dir="rtl"><p align="center">…</p></body></html>')
        req = QNetworkRequest(QUrl(f'https://api.alquran.cloud/v1/ayah/{s}:{a}/{edition}'))
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self.on_tp_reply(reply, key))

    def on_tp_reply(self, reply, key):
        text = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                text = json.loads(bytes(reply.readAll()).decode('utf-8'))['data']['text']
            except (ValueError, KeyError, TypeError):
                text = None
        reply.deleteLater()
        if text is None:
            if key == getattr(self, 'tp_key', None):
                self.tp_browser.setHtml('<html><body dir="rtl"><p align="center">تعذّر تحميل التفسير</p></body></html>')
            return
        self.tafsir_cache[key] = text
        if key == getattr(self, 'tp_key', None):
            self.show_tp(text)

    def show_tp(self, text):
        self.tp_browser.setHtml(
            f'<html><body dir="rtl"><p style="font-size:15pt; line-height:175%;">{html.escape(text)}</p></body></html>')

    def populate_reciters(self):
        self.reciter_combo.blockSignals(True)
        self.reciter_combo.clear()
        for rid, name in self.reciter_options():
            self.reciter_combo.addItem(name, rid)
        saved = self.settings.value(f'reciter:{self.riwaya_id}', '', type=str)
        idx = self.reciter_combo.findData(saved)
        self.reciter_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.reciter_combo.blockSignals(False)

    def reciter_options(self):
        if self.riwaya_id in RIW_RECITERS:
            return [(rid, name) for rid, name, _t, _b in RIW_RECITERS[self.riwaya_id]]
        return [(rid, name) for rid, name, _f in HAFS_RECITERS]

    def current_reciter(self):
        return self.reciter_combo.currentData()

    def on_reciter_change(self, _idx):
        rid = self.current_reciter()
        if rid:
            self.settings.setValue(f'reciter:{self.riwaya_id}', rid)

    def go_page(self, p):
        p = min(max(p, 1), TOTAL_PAGES)
        if p == self.page:
            return
        self.page = p
        self.settings.setValue('page', p)
        if self.playing and not self._auto_turn:
            self.stop_play()
        self.sel_ayah = None
        if self.last_counted != p:
            self.last_counted = p
            self.count_page_visit()
        self.render_page()
        self.sync_index()

    def render_page(self):
        page = self.page
        items = self.book.ayahs_on_page(page)
        t = THEMES[self.theme_name]
        fs = self.font_pt
        out = []
        flow = []

        def flush():
            if flow:
                out.append('<p align="center" dir="rtl" style="margin:0 0 4px 0;">' + ''.join(flow) + '</p>')
                flow.clear()

        last = None
        for s, a, text in items:
            if a == 1 and s != last:
                flush()
                out.append(f'<p align="center" style="margin:10px 0 0 0; font-size:{fs + 6}pt; font-weight:bold; '
                           f'color:{t["brand"]};">{html.escape(SURAHS[s - 1]["name"])}</p>')
                if s not in (1, 9):
                    out.append(f'<p align="center" style="margin:0 0 2px 0; font-size:{fs}pt;">{BASMALA}</p>')
                last = s
            if self.highlight == (s, a):
                style = f'background-color:{t["brand"]}; color:#ffffff;'
            elif self.sel_ayah == (s, a):
                style = f'background-color:{t["hover"]};'
            else:
                style = ''
            flow.append(f'<a href="ayah:{s}:{a}" style="text-decoration:none; color:{t["text"]};">'
                        f'<span style="{style}">{html.escape(text)}</span>'
                        f'<span style="font-size:{max(fs - 9, 10)}pt; color:{t["brand"]};"> ﴿{ar(a)}﴾</span></a> ')
        flush()
        body = ''.join(out) or '<p align="center">لا توجد آيات في هذه الصفحة</p>'
        bar = self.browser.verticalScrollBar()
        pos = bar.value()
        self.browser.setHtml(
            f'<html><body dir="rtl" style="font-family:\'Amiri Quran\'; font-size:{fs}pt; '
            f'line-height:150%; color:{t["text"]};">{body}</body></html>')
        bar.setValue(pos)
        first = items[0] if items else (1, 1, '')
        self.page_label.setText(f'صفحة {ar(page)} من {ar(TOTAL_PAGES)}')
        self.page_info.setText(f'الجزء {ar(juz_of(first[0], first[1]))}  ·  '
                               f'{SURAHS[first[0] - 1]["name"]}  ·  {RIWAYA_NAMES[self.riwaya_id]}')
        self.btn_prev.setEnabled(page > 1)
        self.btn_next.setEnabled(page < TOTAL_PAGES)
        self.update_mark_button()

    def set_font(self, value):
        self.font_pt = min(max(value, 14), 44)
        self.settings.setValue('font_pt', self.font_pt)
        if hasattr(self, 'font_spin'):
            self.font_spin.blockSignals(True)
            self.font_spin.setValue(self.font_pt)
            self.font_spin.blockSignals(False)
        self.render_page()

    def sync_index(self):
        items = self.book.ayahs_on_page(self.page)
        if not items:
            return
        s, a, _t = items[0]
        for combo, value in ((self.combo_surah, s), (self.combo_juz, juz_of(s, a) - 1)):
            combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(value) if combo is self.combo_surah else value)
            combo.blockSignals(False)
        self.fill_ayah_combo(s, a)

    def fill_ayah_combo(self, s, current):
        self.combo_ayah.blockSignals(True)
        self.combo_ayah.clear()
        for n in range(1, SURAHS[s - 1]['numberOfAyahs'] + 1):
            self.combo_ayah.addItem(ar(n), n)
        self.combo_ayah.setCurrentIndex(max(current - 1, 0))
        self.combo_ayah.blockSignals(False)

    def on_surah_index(self, idx):
        s = self.combo_surah.itemData(idx)
        if s is None:
            return
        self.fill_ayah_combo(s, 1)
        self.go_page(self.book.page_of(s, 1))

    def on_juz(self, idx):
        if idx < 0:
            return
        s, a = JUZ_START[idx]
        self.go_page(self.book.page_of(s, a))

    def on_ayah(self, idx):
        if idx < 0:
            return
        s = self.combo_surah.currentData()
        self.go_page(self.book.page_of(s, idx + 1))

    # ---------- التلاوة ----------
    def audio_queue_for_page(self, start=None):
        """قائمة ملفات الصفحة (من آية البداية إن وُجدت)."""
        items = self.book.ayahs_on_page(self.page)
        if start is not None:
            items = [it for it in items if (it[0], it[1]) >= start]
        return self.queue_for_items(items)

    def queue_for_items(self, items):
        """ملف لكل آية (حفص) أو لكل سورة (الروايات) للآيات المعطاة."""
        rid = self.current_reciter()
        if self.riwaya_id in RIW_RECITERS:
            entry = next((e for e in RIW_RECITERS[self.riwaya_id] if e[0] == rid), None)
            if entry is None:
                return []
            _id, _name, kind, base = entry
            if kind == 'ayah':
                return [(f'{base}{s:03d}{a:03d}.mp3', (s, a)) for s, a, _t in items]
            seen = []
            for s, _a, _t in items:
                if s not in seen:
                    seen.append(s)
            return [(f'{base}{s:03d}.mp3', (s, None)) for s in seen]
        out = []
        for s, a, _t in items:
            url = ayah_audio_url(rid, s, a)
            if url:
                out.append((url, (s, a)))
        return out

    def toggle_play(self):
        if self.playing:
            if self.engine.paused:
                self.engine.resume()
                self.btn_play.setText('⏸  إيقاف مؤقت')
            else:
                self.engine.pause()
                self.btn_play.setText('▶  متابعة')
                self.play_status.setText('متوقفة مؤقتاً')
            return
        s = self.play_surah.currentData()
        a = self.play_from.currentData()
        start = (s, a) if s and a else None
        if start is not None and self.book.page_of(s, a) != self.page:
            self.go_page(self.book.page_of(s, a))
        self.queue_list = False
        self.queue = self.audio_queue_for_page(start)
        if not self.queue:
            self.play_status.setText('لا توجد تلاوة لهذا القارئ')
            return
        self.playing = True
        self.btn_play.setText('⏸  إيقاف مؤقت')
        self.play_index(0)

    def audio_cache_dir(self):
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation) or str(BASE)
        path = Path(base) / 'audio'
        path.mkdir(parents=True, exist_ok=True)
        return path

    def local_audio(self, url, on_ready, on_fail):
        """ينزّل ملف التلاوة عبر شبكة Qt إلى الكاش (لو مش موجود) ويرجع مساره المحلي."""
        path = self.audio_cache_dir() / (hashlib.sha1(url.encode('utf-8')).hexdigest()[:20] + '.mp3')
        if path.exists() and path.stat().st_size > 2000:
            on_ready(path)
            return
        reply = self.nam.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(lambda: self._audio_downloaded(reply, path, on_ready, on_fail))

    def _audio_downloaded(self, reply, path, on_ready, on_fail):
        data = bytes(reply.readAll()) if reply.error() == QNetworkReply.NetworkError.NoError else b''
        err = reply.errorString()
        reply.deleteLater()
        if len(data) > 2000:
            tmp = path.with_suffix('.part')
            tmp.write_bytes(data)
            tmp.replace(path)
            on_ready(path)
        else:
            on_fail(err or 'ملف فارغ')

    def play_index(self, i):
        if i >= len(self.queue):
            # نهاية صفحة: ينتقل للصفحة التالية ويكمل التلاوة
            if self.playing and not self.queue_list and self.page < TOTAL_PAGES:
                self._auto_turn = True
                try:
                    self.go_page(self.page + 1)
                finally:
                    self._auto_turn = False
                self.queue = self.audio_queue_for_page()
                if self.queue:
                    return self.play_index(0)
            self.stop_play('')
            return
        self.queue_index = i
        url, label = self.queue[i]
        self.highlight = label if label and label[1] is not None else None
        if label[1] is None:
            title = f'تلاوة سورة {SURAHS[label[0] - 1]["name"]}'
        else:
            title = f'{SURAHS[label[0] - 1]["name"]} · الآية {ar(label[1])}'
        self.play_status.setText(title + ' · جارٍ التحميل…')
        self.render_page()
        self.play_token += 1
        token = self.play_token
        self.local_audio(url, lambda p: self._start_file(p, token, i, title),
                         lambda msg: self._audio_failed(token, msg))
        if i + 1 < len(self.queue):  # تحميل مسبق للتالي لتشغيل متصل
            self.local_audio(self.queue[i + 1][0], lambda _p: None, lambda _m: None)

    def _start_file(self, path, token, i, title):
        if token != self.play_token or not self.playing:
            return
        try:
            self.engine.play(path)
        except Exception:
            self.stop_play('تعذّر تشغيل الصوت على هذا الجهاز')
            return
        self.play_status.setText(title)

    def _audio_failed(self, token, msg):
        if token != self.play_token or not self.playing:
            return
        self.stop_play('تعذّر تحميل التلاوة، تحقّق من الاتصال')

    def stop_play(self, message=''):
        self.play_token += 1
        self.playing = False
        self.queue = []
        self.queue_list = False
        self.queue_index = -1
        self.highlight = None
        self.engine.stop()
        self.btn_play.setText('▶  تشغيل')
        self.play_status.setText(message)
        self.render_page()

    def on_audio_tick(self):
        if self.playing and self.engine.take_ended():
            self.play_index(self.queue_index + 1)

    # ---------- الرواية والإعدادات ----------
    def on_riwaya(self, idx):
        rid = self.riwaya_combo.itemData(idx)
        if not rid or rid == self.riwaya_id:
            return
        if self.playing:
            self.stop_play()
        self.riwaya_id = rid
        self.settings.setValue('riwaya', rid)
        self.book = Book(rid)
        self.page = min(self.page, TOTAL_PAGES)
        self.populate_reciters()
        self.render_page()
        self.sync_index()

    # ---------- التفسير ----------
    def build_tafsir(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(heading('التفسير', 'تفسير الآية من الإنترنت، ويُحفظ مؤقتاً أثناء التشغيل'))
        bar = card()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 10, 14, 10)
        self.tf_surah = QComboBox()
        for s in SURAHS:
            self.tf_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.tf_surah.currentIndexChanged.connect(self.on_tf_surah)
        self.tf_ayah = QSpinBox()
        self.tf_ayah.setRange(1, 286)
        self.tf_ayah.valueChanged.connect(lambda _v: self.load_tafsir())
        self.tf_book = QComboBox()
        for eid, name in TAFSIR_EDITIONS:
            self.tf_book.addItem(name, eid)
        self.tf_book.setCurrentIndex(max(self.tf_book.findData(
            self.settings.value('tafsir', 'ar.muyassar', type=str)), 0))
        self.tf_book.currentIndexChanged.connect(self.on_tf_book)
        btn_prev = QPushButton('‹ السابقة')
        btn_prev.clicked.connect(lambda: self.tf_ayah.setValue(self.tf_ayah.value() - 1))
        btn_next = QPushButton('التالية ›')
        btn_next.clicked.connect(lambda: self.tf_ayah.setValue(self.tf_ayah.value() + 1))
        bl.addWidget(QLabel('السورة'))
        bl.addWidget(self.tf_surah, 2)
        bl.addWidget(QLabel('الآية'))
        bl.addWidget(self.tf_ayah)
        bl.addWidget(self.tf_book, 2)
        bl.addWidget(btn_prev)
        bl.addWidget(btn_next)
        lay.addWidget(bar)
        self.tf_browser = QTextBrowser()
        self.tf_browser.setOpenExternalLinks(False)
        lay.addWidget(self.tf_browser, 1)
        return w

    def on_tf_surah(self, _idx):
        s = self.tf_surah.currentData() or 1
        self.tf_ayah.blockSignals(True)
        self.tf_ayah.setRange(1, SURAHS[s - 1]['numberOfAyahs'])
        self.tf_ayah.setValue(1)
        self.tf_ayah.blockSignals(False)
        self.load_tafsir()

    def on_tf_book(self, _idx):
        self.settings.setValue('tafsir', self.tf_book.currentData())
        self.load_tafsir()

    def load_tafsir(self):
        if not hasattr(self, 'tf_ayah'):
            return
        s = self.tf_surah.currentData() or 1
        a = self.tf_ayah.value()
        edition = self.tf_book.currentData()
        key = (edition, s, a)
        self.tf_key = key
        t = THEMES[self.theme_name]
        head = (f'<p align="center" style="font-family:\'Amiri Quran\'; font-size:26pt; line-height:200%;">'
                f'{html.escape(AYAH_TEXT.get((s, a), ""))} <span style="font-size:14pt; color:{t["brand"]}">'
                f'﴿{ar(a)}﴾</span></p><p align="center" style="color:{t["muted"]}">'
                f'{html.escape(SURAHS[s - 1]["name"])} · الآية {ar(a)}</p>')
        if key in self.tafsir_cache:
            self.show_tafsir(head, self.tafsir_cache[key])
            return
        self.tf_browser.setHtml(f'<html><body dir="rtl">{head}<p align="center">جارٍ تحميل التفسير…</p></body></html>')
        req = QNetworkRequest(QUrl(f'https://api.alquran.cloud/v1/ayah/{s}:{a}/{edition}'))
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self.on_tafsir_reply(reply, key, head))

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
                                        '</p></body></html>')
            return
        self.tafsir_cache[key] = text
        if key == self.tf_key:
            self.show_tafsir(head, text)

    def show_tafsir(self, head, text):
        self.tf_browser.setHtml(
            f'<html><body dir="rtl">{head}<h3>{html.escape(self.tf_book.currentText())}</h3>'
            f'<p style="font-size:16pt; line-height:190%;">{html.escape(text)}</p></body></html>')

    # ---------- البحث ----------
    def build_search(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(heading('البحث في القرآن', 'اكتب كلمة أو عبارة (بدون تشكيل)، وانقر النتيجة لتفتح صفحتها'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('ابحث…')
        self.search_input.returnPressed.connect(self.run_search)
        self.search_input.textChanged.connect(lambda _t: self.run_search())
        lay.addWidget(self.search_input)
        self.search_status = QLabel('')
        self.search_status.setObjectName('muted')
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
                item = QListWidgetItem(f'{SURAHS[s - 1]["name"]} · {ar(a)}    {text}')
                item.setData(Qt.ItemDataRole.UserRole, (s, a))
                self.search_results.addItem(item)
                if found >= 300:
                    break
        self.search_status.setText(f'{ar(found)} نتيجة' + (' (أول 300 فقط)' if found >= 300 else ''))

    def open_search_result(self, item):
        if item is None:
            return
        s, a = item.data(Qt.ItemDataRole.UserRole)
        self.go_page(self.book.page_of(s, a))
        self.show_view('reader')

    # ---------- المعاني ----------
    def build_meanings(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(heading('معاني الكلمات', 'من كتب غريب القرآن والمعاني المعتمدة في التطبيق'))
        self.mn_combo = QComboBox()
        for s in SURAHS:
            self.mn_combo.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.mn_combo.currentIndexChanged.connect(lambda _i: self.render_meanings())
        lay.addWidget(self.mn_combo)
        self.mn_browser = QTextBrowser()
        self.mn_browser.setOpenExternalLinks(False)
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
                for word, meaning in words:
                    parts.append(f'<p><b>{html.escape(word)}</b> {html.escape(meaning)}</p>')
        body = ''.join(parts) or '<p>لا توجد معانٍ مسجلة لهذه السورة.</p>'
        self.mn_browser.setHtml(f'<html><body dir="rtl">{body}</body></html>')

    # ---------- أحكام التجويد ----------
    def build_tajweed(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(heading('أحكام التجويد', 'القواعد السبعة عشر مع شرح مختصر لكل حكم'))
        self.tj_browser = QTextBrowser()
        lay.addWidget(self.tj_browser, 1)
        return w

    def render_tajweed(self):
        t = THEMES[self.theme_name]
        rows = ''.join(
            f'<p style="margin-bottom:14px"><b style="font-size:16pt; color:{t["brand"]}">{html.escape(name)}</b>'
            f'<br><span>{html.escape(desc)}</span></p>'
            for name, desc in TAJWEED.values())
        self.tj_browser.setHtml(f'<html><body dir="rtl">{rows}</body></html>')

    # ---------- الأذكار ----------
    def build_adhkar(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        self.adh_cat = 0
        self.adh_list = QListWidget()
        self.adh_list.setFixedWidth(260)
        for i, cat in enumerate(ADHKAR):
            self.adh_list.addItem(f'{cat["name"]}')
        self.adh_list.setCurrentRow(0)
        self.adh_list.currentRowChanged.connect(self.show_adhkar)
        lay.addWidget(self.adh_list)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.adh_title = QLabel()
        self.adh_title.setObjectName('pageTitle')
        rl.addWidget(self.adh_title)
        self.adh_scroll = QScrollArea()
        self.adh_scroll.setWidgetResizable(True)
        self.adh_inner = QWidget()
        self.adh_items = QVBoxLayout(self.adh_inner)
        self.adh_items.setSpacing(12)
        self.adh_scroll.setWidget(self.adh_inner)
        rl.addWidget(self.adh_scroll, 1)
        lay.addWidget(right, 1)
        return w

    def adhkar_state(self):
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
        if idx < 0:
            return
        self.adh_cat = idx
        cat = ADHKAR[idx]
        self.adh_title.setText(cat['name'])
        while self.adh_items.count():
            item = self.adh_items.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        state = self.adhkar_state()
        for i, it in enumerate(cat['items']):
            key = f'{idx}:{i}'
            n = min(it['count'], state['c'].get(key, 0))
            c = card()
            row = QHBoxLayout(c)
            row.setContentsMargins(18, 14, 18, 14)
            text = QLabel(it['text'])
            text.setWordWrap(True)
            text.setStyleSheet("font-family: 'Amiri Quran'; font-size: 19px; line-height: 170%;")
            btn = QPushButton(f'{ar(n)} / {ar(it["count"])}')
            btn.setMinimumWidth(110)
            btn.clicked.connect(lambda _c=False, k=key, mx=it['count'], b=btn: self.bump_adhkar(k, mx, b))
            row.addWidget(text, 1)
            row.addWidget(btn)
            self.adh_items.addWidget(c)
        self.adh_items.addStretch(1)

    def bump_adhkar(self, key, maximum, btn):
        data = self.adhkar_state()
        cur = data['c'].get(key, 0)
        data['c'][key] = 0 if cur >= maximum else cur + 1
        self.save_adhkar(data)
        btn.setText(f'{ar(data["c"][key])} / {ar(maximum)}')

    # ---------- وضع الحفظ ----------
    # ---------- وضع الحفظ ----------
    def build_memo(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(heading('وضع الحفظ'))
        self.memo_shown = set()
        self.memo_all_hidden = False
        bar = card()
        bl = QVBoxLayout(bar)
        bl.setContentsMargins(14, 12, 14, 12)
        bl.setSpacing(10)
        row = QHBoxLayout()
        self.memo_surah = QComboBox()
        for s in SURAHS:
            self.memo_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.memo_from = QComboBox()
        self.memo_to = QComboBox()
        self.memo_repeat = QComboBox()
        for n in (1, 3, 5, 10):
            self.memo_repeat.addItem(ar(n), n)
        self.memo_repeat.setCurrentIndex(1)
        self.memo_level = QComboBox()
        for lv, label in zip(MEMO_LEVELS, ('بدون إخفاء', 'ربع الكلمات', 'نصف الكلمات', 'ثلاثة أرباع', 'كل الكلمات')):
            self.memo_level.addItem(label, lv)
        self.memo_surah.currentIndexChanged.connect(self.on_memo_surah)
        for cb in (self.memo_from, self.memo_to, self.memo_level):
            cb.currentIndexChanged.connect(self.on_memo_change)
        for label, widget in (('السورة', self.memo_surah), ('من آية', self.memo_from), ('إلى آية', self.memo_to),
                              ('التكرار', self.memo_repeat), ('إخفاء الكلمات', self.memo_level)):
            row.addWidget(QLabel(label))
            row.addWidget(widget, 2 if widget is self.memo_surah else 1)
        bl.addLayout(row)
        acts = QHBoxLayout()
        btn_hide = QPushButton('إخفاء/إظهار النص')
        btn_hide.clicked.connect(self.on_memo_hide)
        btn_play = QPushButton('تشغيل مع التكرار')
        btn_play.clicked.connect(self.memo_play)
        btn_save = QPushButton('حفظت هذا المقطع')
        btn_save.clicked.connect(self.memo_save_range)
        for b in (btn_hide, btn_play, btn_save):
            acts.addWidget(b)
        acts.addStretch(1)
        bl.addLayout(acts)
        self.memo_status = QLabel()
        self.memo_status.setObjectName('muted')
        bl.addWidget(self.memo_status)
        lay.addWidget(bar)

        self.memo_review = card()
        rv = QVBoxLayout(self.memo_review)
        rv.setContentsMargins(14, 12, 14, 12)
        rv.setSpacing(8)
        title = QLabel('مراجعة اليوم')
        title.setStyleSheet('font-weight:700; font-size:15px;')
        rv.addWidget(title)
        self.memo_review_list = QVBoxLayout()
        rv.addLayout(self.memo_review_list)
        self.memo_review_note = QLabel()
        self.memo_review_note.setObjectName('muted')
        rv.addWidget(self.memo_review_note)
        lay.addWidget(self.memo_review)

        self.memo_browser = QTextBrowser()
        self.memo_browser.setOpenLinks(False)
        self.memo_browser.anchorClicked.connect(self.on_memo_anchor)
        lay.addWidget(self.memo_browser, 1)
        self.on_memo_surah(0)
        self.render_memo_review()
        return w

    def on_memo_surah(self, _idx):
        s = self.memo_surah.currentData() or 1
        count = SURAHS[s - 1]['numberOfAyahs']
        for cb, val in ((self.memo_from, 1), (self.memo_to, count)):
            cb.blockSignals(True)
            cb.clear()
            for n in range(1, count + 1):
                cb.addItem(ar(n), n)
            cb.setCurrentIndex(val - 1)
            cb.blockSignals(False)
        self.on_memo_change()

    def on_memo_change(self, _i=0):
        self.memo_shown.clear()
        self.render_memo()

    def on_memo_hide(self):
        self.memo_all_hidden = not self.memo_all_hidden
        self.on_memo_change()

    def memo_range(self):
        s = self.memo_surah.currentData() or 1
        lo, hi = sorted((self.memo_from.currentData() or 1, self.memo_to.currentData() or 1))
        return s, lo, hi

    def set_memo_range(self, s, lo, hi):
        idx = self.memo_surah.findData(s)
        self.memo_surah.setCurrentIndex(max(idx, 0))
        self.memo_from.setCurrentIndex(lo - 1)
        self.memo_to.setCurrentIndex(hi - 1)
        self.on_memo_change()

    def render_memo(self):
        if not hasattr(self, 'memo_browser'):
            return
        s, lo, hi = self.memo_range()
        pct = 100 if self.memo_all_hidden else (self.memo_level.currentData() or 0)
        parts = []
        for a in range(lo, hi + 1):
            words = AYAH_TEXT.get((s, a), '').split()
            ws = []
            for i, word in enumerate(words):
                revealed = (s, a, -1) in self.memo_shown or (s, a, i) in self.memo_shown
                esc = html.escape(word)
                if memo_word_hidden(s, a, i, pct) and not revealed:
                    ws.append(f'<a href="w:{s}:{a}:{i}" style="text-decoration:none;">'
                              f'<span style="background-color:#d9d2bd; color:#d9d2bd;">{esc}</span></a>')
                else:
                    ws.append(esc)
            parts.append(f'{" ".join(ws)} <a href="a:{s}:{a}" style="text-decoration:none; color:#8a6d2f;">'
                         f'﴿{ar(a)}﴾</a> ')
        body = ''.join(parts) or 'لا توجد آيات'
        self.memo_browser.setHtml(
            '<html><body dir="rtl" style="font-family:\'Amiri Quran\'; font-size:24pt; line-height:200%;">'
            f'<p align="center"><b>{html.escape(SURAHS[s - 1]["name"])}</b></p>'
            f'<p align="center" dir="rtl">{body}</p></body></html>')

    def on_memo_anchor(self, url):
        text = url.toString() if hasattr(url, 'toString') else str(url)
        parts = text.split(':')
        try:
            if parts[0] == 'w':
                self.memo_shown.add((int(parts[1]), int(parts[2]), int(parts[3])))
            elif parts[0] == 'a':
                self.memo_shown.add((int(parts[1]), int(parts[2]), -1))
            else:
                return
        except (ValueError, IndexError):
            return
        self.render_memo()

    def memo_progress(self):
        try:
            data = json.loads(self.settings.value('memo_progress', '{}', type=str))
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def save_memo_progress(self, prog):
        self.settings.setValue('memo_progress', json.dumps(prog, ensure_ascii=False))

    def memo_save_range(self):
        s, lo, hi = self.memo_range()
        prog = self.memo_progress()
        key = f'{s}:{lo}-{hi}'
        if key in prog:
            self.memo_status.setText('المقطع موجود في المراجعة')
        else:
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            prog[key] = {'s': s, 'from': lo, 'to': hi, 'step': 0, 'due': tomorrow.isoformat()}
            self.save_memo_progress(prog)
            self.memo_status.setText('أُضيف المقطع إلى المراجعة')
        self.render_memo_review()

    def render_memo_review(self):
        if not hasattr(self, 'memo_review_list'):
            return
        while self.memo_review_list.count():
            item = self.memo_review_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        prog = self.memo_progress()
        today = datetime.date.today().isoformat()
        items = sorted(prog.items(), key=lambda kv: str(kv[1].get('due', '')))
        due = [(k, v) for k, v in items if str(v.get('due', '')) <= today]
        later = len(items) - len(due)
        for k, v in due:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            name = SURAHS[int(v['s']) - 1]['name']
            rl.addWidget(QLabel(f'{name} · {ar(v["from"])} - {ar(v["to"])}'), 1)
            for label, act in (('أتقنتها', 'ok'), ('أعيدها', 'again'), ('فتح', 'open')):
                b = QPushButton(label)
                b.clicked.connect(lambda _c=False, key=k, a=act: self.memo_review_action(key, a))
                rl.addWidget(b)
            self.memo_review_list.addWidget(row)
        if not items:
            note = 'لا توجد مقاطع محفوظة'
        elif not due:
            note = 'لا توجد مراجعة اليوم'
        else:
            note = ''
        if later:
            note = (note + ' · ' if note else '') + f'مراجعات قادمة: {ar(later)}'
        self.memo_review_note.setText(note)

    def memo_review_action(self, key, act):
        prog = self.memo_progress()
        item = prog.get(key)
        if not item:
            return
        if act == 'open':
            self.set_memo_range(int(item['s']), int(item['from']), int(item['to']))
            return
        today = datetime.date.today()
        if act == 'ok':
            item['step'] = min(len(MEMO_GAPS) - 1, int(item.get('step', 0)) + 1)
            item['due'] = (today + datetime.timedelta(days=MEMO_GAPS[item['step']])).isoformat()
        else:
            item['step'] = 0
            item['due'] = (today + datetime.timedelta(days=1)).isoformat()
        self.save_memo_progress(prog)
        self.render_memo_review()

    def memo_play(self):
        s, lo, hi = self.memo_range()
        base = self.queue_for_items([(s, a, None) for a in range(lo, hi + 1)])
        if not base:
            self.memo_status.setText('لا توجد تلاوة لهذا القارئ')
            return
        if any(label[1] is None for _url, label in base):
            self.memo_status.setText('لا تتوفر تلاوة مقطعية لهذا القارئ')
            return
        repeat = self.memo_repeat.currentData() or 1
        self.stop_play()
        self.queue = base * repeat
        self.queue_list = True
        self.playing = True
        self.btn_play.setText('⏸  إيقاف مؤقت')
        self.memo_status.setText('')
        self.play_index(0)

    # ---------- مشاركة الآية كصورة ----------
    def share_selected_ayah(self):
        if self.sel_ayah is None:
            return
        s, a = self.sel_ayah
        text = AYAH_TEXT.get((s, a), '')
        if not text:
            return
        img = share_card_image(text, SURAHS[s - 1]['name'], a)
        dlg = QDialog(self)
        dlg.setWindowTitle('مشاركة الآية')
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        lay = QVBoxLayout(dlg)
        preview = QLabel()
        preview.setPixmap(QPixmap.fromImage(img).scaledToWidth(560, Qt.TransformationMode.SmoothTransformation))
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(preview)
        status = QLabel()
        status.setObjectName('muted')
        lay.addWidget(status)
        row = QHBoxLayout()
        b_share = QPushButton('مشاركة')
        b_save = QPushButton('تنزيل')
        b_close = QPushButton('إغلاق')
        row.addStretch(1)
        for b in (b_share, b_save, b_close):
            row.addWidget(b)
        lay.addLayout(row)

        def share():
            QGuiApplication.clipboard().setImage(img)
            status.setText('نُسخت الصورة إلى الحافظة')

        def save():
            downloads = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation) or str(Path.home())
            default = str(Path(downloads) / f'ayah-{s}-{a}.png')
            path, _f = QFileDialog.getSaveFileName(dlg, 'تنزيل الصورة', default, 'PNG (*.png)')
            if not path:
                return
            if not path.lower().endswith('.png'):
                path += '.png'
            status.setText(f'تم الحفظ: {path}' if img.save(path, 'PNG') else 'تعذّر الحفظ')

        b_share.clicked.connect(share)
        b_save.clicked.connect(save)
        b_close.clicked.connect(dlg.accept)
        dlg.exec()

    def open_meanings_for_selected(self):
        if self.sel_ayah is None:
            return
        idx = self.mn_combo.findData(self.sel_ayah[0])
        if idx >= 0:
            self.mn_combo.setCurrentIndex(idx)
        self.show_view('meanings')

    # ---------- تحميل التلاوات للاستماع بدون إنترنت ----------
    def build_dl_card(self):
        c = card()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)
        title = QLabel('تحميل التلاوات للاستماع بدون إنترنت')
        title.setStyleSheet('font-weight:700; font-size:15px;')
        lay.addWidget(title)
        self.dl_reciter = QComboBox()
        for rid, name, _folder in HAFS_RECITERS:
            self.dl_reciter.addItem(name, rid)
        saved = self.settings.value('dl_reciter', 'ar.alafasy', type=str)
        self.dl_reciter.setCurrentIndex(max(self.dl_reciter.findData(saved), 0))
        self.dl_reciter.currentIndexChanged.connect(self.on_dl_reciter)
        self.dl_full = QRadioButton('المصحف كاملاً')
        self.dl_one = QRadioButton('سورة محددة')
        self.dl_full.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.dl_full)
        group.addButton(self.dl_one)
        self.dl_surah = QComboBox()
        for s in SURAHS:
            self.dl_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        scope = QHBoxLayout()
        for widget in (self.dl_full, self.dl_one, self.dl_surah):
            scope.addWidget(widget)
        scope_w = QWidget()
        scope_w.setLayout(scope)
        self.dl_target = QComboBox()
        self.dl_target.addItem('داخل التطبيق', 'app')
        self.dl_target.addItem('مجلد على الجهاز', 'folder')
        form = QFormLayout()
        form.addRow('القارئ', self.dl_reciter)
        form.addRow('المدى', scope_w)
        form.addRow('التخزين', self.dl_target)
        lay.addLayout(form)
        self.dl_estimate = QLabel()
        self.dl_estimate.setObjectName('muted')
        lay.addWidget(self.dl_estimate)
        self.dl_full.toggled.connect(self.update_dl_estimate)
        self.dl_surah.currentIndexChanged.connect(self.update_dl_estimate)
        btns = QHBoxLayout()
        self.dl_start = QPushButton('بدء التحميل')
        self.dl_start.clicked.connect(self.start_dl)
        self.dl_cancel = QPushButton('إيقاف')
        self.dl_cancel.setEnabled(False)
        self.dl_cancel.clicked.connect(self.cancel_dl)
        self.dl_delete = QPushButton('حذف تحميلات هذا القارئ')
        self.dl_delete.clicked.connect(self.delete_dl)
        for b in (self.dl_start, self.dl_cancel, self.dl_delete):
            btns.addWidget(b)
        btns.addStretch(1)
        lay.addLayout(btns)
        self.dl_bar = QProgressBar()
        self.dl_bar.setVisible(False)
        lay.addWidget(self.dl_bar)
        self.dl_status = QLabel()
        self.dl_status.setObjectName('muted')
        lay.addWidget(self.dl_status)
        self.dl_stored = QLabel()
        self.dl_stored.setObjectName('muted')
        lay.addWidget(self.dl_stored)
        self.update_dl_estimate()
        self.refresh_dl_stored()
        return c

    def on_dl_reciter(self, _i=0):
        if self.dl_reciter.currentData():
            self.settings.setValue('dl_reciter', self.dl_reciter.currentData())
        self.refresh_dl_stored()

    def dl_refs(self):
        if self.dl_full.isChecked():
            return full_refs()
        s = self.dl_surah.currentData() or 1
        return [(s, a) for a in range(1, SURAHS[s - 1]['numberOfAyahs'] + 1)]

    def update_dl_estimate(self, *_args):
        if not hasattr(self, 'dl_estimate'):
            return
        self.dl_surah.setEnabled(self.dl_one.isChecked())
        refs = self.dl_refs()
        mb = len(refs) * 0.1
        size = 'أقل من ميجابايت' if mb < 1 else f'نحو {ar(round(mb))} ميجابايت'
        scope = 'المصحف كاملاً' if self.dl_full.isChecked() else f'سورة {SURAHS[(self.dl_surah.currentData() or 1) - 1]["name"]}'
        self.dl_estimate.setText(f'{scope}: {ar(len(refs))} آية، حجم تقريبي {size}')

    def start_dl(self):
        if self.dl.get('running'):
            return
        rid = self.dl_reciter.currentData()
        root = None
        if self.dl_target.currentData() == 'folder':
            root = self.settings.value('dl_folder', '', type=str)
            if not root or not Path(root).is_dir():
                root = QFileDialog.getExistingDirectory(self, 'اختر المجلد', str(Path.home()))
                if not root:
                    return
                self.settings.setValue('dl_folder', root)
        queue = deque()
        for s, a in self.dl_refs():
            url = ayah_audio_url(rid, s, a)
            if url:
                queue.append((url, rid, s, a))
        self.dl = {'running': True, 'cancel': False, 'queue': queue, 'active': 0, 'total': len(queue),
                   'done': 0, 'saved': 0, 'skipped': 0, 'failed': 0, 'root': root, 'final': ''}
        self.dl_bar.setRange(0, max(1, len(queue)))
        self.dl_bar.setValue(0)
        self.dl_bar.setVisible(True)
        self.dl_start.setEnabled(False)
        self.dl_cancel.setEnabled(True)
        self.dl_next()

    def dl_next(self):
        d = self.dl
        while d.get('running') and not d['cancel'] and d['queue'] and d['active'] < 6:
            url, rid, s, a = d['queue'].popleft()
            path = self.audio_cache_dir() / audio_file_name(url)
            if path.exists() and path.stat().st_size > 2000:
                d['skipped'] += 1
                d['done'] += 1
                self.dl_copy_to_folder(path, rid, s, a)
                continue
            d['active'] += 1
            reply = self.nam.get(QNetworkRequest(QUrl(url)))
            reply.finished.connect(lambda r=reply, p=path, i=rid, x=s, y=a: self.dl_done(r, p, i, x, y))
        self.update_dl_status()
        if d.get('running') and d['active'] == 0 and (not d['queue'] or d['cancel']):
            self.dl_finish()

    def dl_done(self, reply, path, rid, s, a):
        d = self.dl
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        data = bytes(reply.readAll()) if ok else b''
        reply.deleteLater()
        d['active'] -= 1
        d['done'] += 1
        if len(data) > 2000:
            tmp = path.with_suffix('.part')
            tmp.write_bytes(data)
            tmp.replace(path)
            d['saved'] += 1
            self.dl_copy_to_folder(path, rid, s, a)
        else:
            d['failed'] += 1
        self.dl_next()

    def dl_copy_to_folder(self, path, rid, s, a):
        root = self.dl.get('root')
        if not root:
            return
        try:
            dest = Path(root) / rid / str(s)
            dest.mkdir(parents=True, exist_ok=True)
            target = dest / f'{a}.mp3'
            if not target.exists():
                target.write_bytes(path.read_bytes())
        except OSError:
            self.dl['failed'] += 1

    def cancel_dl(self):
        if self.dl.get('running'):
            self.dl['cancel'] = True
            self.dl['queue'].clear()
            self.dl_cancel.setEnabled(False)
            self.dl_next()

    def dl_finish(self):
        d = self.dl
        d['running'] = False
        d['final'] = 'تم إيقاف التحميل' if d['cancel'] else 'انتهى التحميل'
        self.dl_start.setEnabled(True)
        self.dl_cancel.setEnabled(False)
        self.update_dl_status()
        self.refresh_dl_stored()

    def update_dl_status(self):
        d = self.dl
        if not d.get('total'):
            return
        self.dl_bar.setValue(d['done'])
        prefix = d.get('final') and d['final'] + ' · '
        self.dl_status.setText(f'{prefix or ""}{ar(d["done"])} من {ar(d["total"])} · محفوظ {ar(d["saved"])} · '
                               f'موجود {ar(d["skipped"])} · فشل {ar(d["failed"])}')

    def delete_dl(self):
        if self.dl.get('running'):
            return
        rid = self.dl_reciter.currentData()
        cache = self.audio_cache_dir()
        n = 0
        for s, a in full_refs():
            url = ayah_audio_url(rid, s, a)
            p = cache / audio_file_name(url)
            if url and p.exists():
                p.unlink()
                n += 1
        self.dl_status.setText(f'حُذف {ar(n)} ملف من التطبيق')
        self.refresh_dl_stored()

    def refresh_dl_stored(self):
        if not hasattr(self, 'dl_stored'):
            return
        rid = self.dl_reciter.currentData()
        cache = self.audio_cache_dir()
        per = {}
        total = 0
        for s, a in full_refs():
            url = ayah_audio_url(rid, s, a)
            if url and (cache / audio_file_name(url)).exists():
                total += 1
                per[s] = per.get(s, 0) + 1
        complete = sum(1 for s, n in per.items() if n >= SURAHS[s - 1]['numberOfAyahs'])
        self.dl_stored.setText(f'داخل التطبيق: {ar(total)} آية، {ar(complete)} سورة مكتملة لهذا القارئ')

    # ---------- الورد اليومي ----------
    def build_wird(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(heading('الورد اليومي', 'حدد عدد الصفحات كل يوم، والورد بيكمل من حيث وقفت'))
        c = card()
        cl = QFormLayout(c)
        cl.setContentsMargins(20, 18, 20, 18)
        self.wird_target = QSpinBox()
        self.wird_target.setRange(1, 60)
        self.wird_target.setValue(self.settings.value('wird_target', 5, type=int))
        self.wird_target.valueChanged.connect(self.on_wird_target)
        cl.addRow('عدد الصفحات في اليوم', self.wird_target)
        lay.addWidget(c)
        ci = card()
        il = QVBoxLayout(ci)
        il.setContentsMargins(20, 18, 20, 18)
        self.wird_text = QLabel()
        self.wird_text.setWordWrap(True)
        self.wird_text.setStyleSheet('font-size: 18px; font-weight: 600;')
        il.addWidget(self.wird_text)
        lay.addWidget(ci)
        row = QHBoxLayout()
        self.btn_wird_read = QPushButton('📖 ابدأ ورد اليوم')
        self.btn_wird_read.setObjectName('primary')
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
        start = min(max(start, 1), TOTAL_PAGES)
        end = min(start + self.wird_target.value() - 1, TOTAL_PAGES)
        return start, end

    def render_wird(self):
        self.wird_target.blockSignals(True)
        self.wird_target.setValue(self.settings.value('wird_target', 5, type=int))
        self.wird_target.blockSignals(False)
        start, end = self.wird_range()
        done_today = self.settings.value('wird_day', '', type=str) == datetime.date.today().isoformat()
        self.btn_wird_done.setEnabled(not done_today)
        head = 'أنجزت ورد اليوم ✔' if done_today else 'ورد اليوم'
        self.wird_text.setText(f'{head}: من صفحة {ar(start)} إلى صفحة {ar(end)} ({ar(end - start + 1)} صفحات)')

    def on_wird_target(self, value):
        self.settings.setValue('wird_target', value)
        self.render_wird()

    def start_wird(self):
        start, _end = self.wird_range()
        self.go_page(start)
        self.show_view('reader')

    def finish_wird(self):
        _start, end = self.wird_range()
        nxt = end + 1 if end < TOTAL_PAGES else 1
        self.settings.setValue('wird_next', nxt)
        self.settings.setValue('wird_day', datetime.date.today().isoformat())
        self.settings.setValue('wird_count', self.settings.value('wird_count', 0, type=int) + 1)
        self.render_wird()

    def reset_wird(self):
        self.settings.setValue('wird_next', 1)
        self.settings.setValue('wird_day', '')
        self.render_wird()

    # ---------- المحفوظات ----------
    def bookmarks(self):
        raw = self.settings.value('bookmarks', '[]', type=str)
        try:
            return sorted(set(int(p) for p in json.loads(raw)))
        except ValueError:
            return []

    def save_bookmarks(self, marks):
        self.settings.setValue('bookmarks', json.dumps(sorted(set(marks))))

    def toggle_bookmark(self):
        marks = self.bookmarks()
        if self.page in marks:
            marks.remove(self.page)
        else:
            marks.append(self.page)
        self.save_bookmarks(marks)
        self.update_mark_button()

    def update_mark_button(self):
        if hasattr(self, 'btn_mark'):
            self.btn_mark.setText('★ محفوظة' if self.page in self.bookmarks() else 'علامة')

    def page_title(self, page):
        items = self.book.ayahs_on_page(page)
        if not items:
            return f'صفحة {ar(page)}'
        s, a, _t = items[0]
        return f'صفحة {ar(page)} · الجزء {ar(juz_of(s, a))} · {SURAHS[s - 1]["name"]}'

    def build_bookmarks(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(heading('المحفوظات', 'الصفحات التي حفظتها من المصحف'))
        self.bm_list = QListWidget()
        self.bm_list.itemActivated.connect(self.open_bookmark)
        self.bm_list.itemDoubleClicked.connect(self.open_bookmark)
        lay.addWidget(self.bm_list, 1)
        row = QHBoxLayout()
        btn_open = QPushButton('فتح الصفحة')
        btn_open.setObjectName('primary')
        btn_open.clicked.connect(lambda: self.open_bookmark(self.bm_list.currentItem()))
        btn_del = QPushButton('حذف المحدد')
        btn_del.setObjectName('danger')
        btn_del.clicked.connect(self.delete_bookmark)
        row.addWidget(btn_open)
        row.addWidget(btn_del)
        row.addStretch(1)
        lay.addLayout(row)
        self.bm_empty = QLabel('لا توجد صفحات محفوظة')
        self.bm_empty.setObjectName('muted')
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
        self.save_bookmarks([p for p in self.bookmarks() if p != page])
        self.render_bookmarks()
        self.update_mark_button()

    # ---------- الإحصائيات ----------
    def days(self):
        raw = self.settings.value('days', '{}', type=str)
        try:
            return json.loads(raw)
        except ValueError:
            return {}

    def count_page_visit(self):
        days = self.days()
        key = datetime.date.today().isoformat()
        days[key] = days.get(key, 0) + 1
        self.settings.setValue('days', json.dumps(days))

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
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(heading('الإحصائيات', 'تُحسب صفحات القراءة عند التنقل بين صفحات المصحف'))
        grid = QHBoxLayout()
        grid.setSpacing(14)
        self.st_cards = {}
        for key, caption in (('today', 'صفحات اليوم'), ('total', 'إجمالي الصفحات'),
                             ('streak', 'أيام متتالية'), ('adhkar', 'أذكار مكتملة اليوم'),
                             ('bookmarks', 'صفحات محفوظة'), ('wird', 'أوراد مكتملة')):
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 18, 18, 18)
            value = QLabel('٠')
            value.setObjectName('stat')
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cap = QLabel(caption)
            cap.setObjectName('muted')
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(value)
            cl.addWidget(cap)
            self.st_cards[key] = value
            grid.addWidget(c, 1)
        lay.addLayout(grid)
        lay.addStretch(1)
        return w

    def render_stats(self):
        days = self.days()
        counts = self.adhkar_state()
        done = 0
        for idx, cat in enumerate(ADHKAR):
            for i, it in enumerate(cat['items']):
                if counts['c'].get(f'{idx}:{i}', 0) >= it['count']:
                    done += 1
        self.st_cards['today'].setText(ar(days.get(datetime.date.today().isoformat(), 0)))
        self.st_cards['total'].setText(ar(sum(days.values())))
        self.st_cards['streak'].setText(ar(self.streak(days)))
        self.st_cards['adhkar'].setText(ar(done))
        self.st_cards['bookmarks'].setText(ar(len(self.bookmarks())))
        self.st_cards['wird'].setText(ar(self.settings.value('wird_count', 0, type=int)))

    # ---------- الإعدادات ----------
    def build_settings(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(heading('الإعدادات', 'المظهر، والرواية والقارئ، والتفسير'))

        c1 = card()
        f1 = QFormLayout(c1)
        f1.setContentsMargins(20, 18, 20, 18)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem('فاتح', 'light')
        self.theme_combo.addItem('داكن', 'dark')
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(self.theme_name))
        self.theme_combo.currentIndexChanged.connect(self.on_theme_change)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(14, 44)
        self.font_spin.setValue(self.font_pt)
        self.font_spin.valueChanged.connect(self.set_font)
        f1.addRow('الوضع', self.theme_combo)
        f1.addRow('حجم خط المصحف', self.font_spin)
        lay.addWidget(c1)

        c2 = card()
        f2 = QFormLayout(c2)
        f2.setContentsMargins(20, 18, 20, 18)
        self.riwaya_combo = QComboBox()
        for rid, name in HAFS_EDITIONS + OTHER_RIWAYAT:
            self.riwaya_combo.addItem(name, rid)
        self.riwaya_combo.setCurrentIndex(self.riwaya_combo.findData(self.riwaya_id))
        self.riwaya_combo.currentIndexChanged.connect(self.on_riwaya)
        f2.addRow('الرواية والرسم', self.riwaya_combo)
        lay.addWidget(c2)

        c3 = card()
        cl3 = QVBoxLayout(c3)
        cl3.setContentsMargins(20, 18, 20, 18)
        about = QLabel(f'المصحف {APP_VERSION}')
        about.setStyleSheet('font-weight:700; font-size:16px;')
        cl3.addWidget(about)
        self.upd_status = QLabel('')
        self.upd_status.setObjectName('muted')
        cl3.addWidget(self.upd_status)
        self.btn_check_update = QPushButton('تحقق من التحديث')
        self.btn_check_update.clicked.connect(self.on_update_button)
        cl3.addWidget(self.btn_check_update)
        btn_reset = QPushButton('مسح بيانات الإحصائيات والمحفوظات')
        btn_reset.setObjectName('danger')
        btn_reset.clicked.connect(self.clear_user_data)
        cl3.addWidget(btn_reset)
        lay.addWidget(c3)
        lay.addStretch(1)
        lay.addWidget(self.build_dl_card())
        scroll.setWidget(inner)
        return scroll

    def on_theme_change(self, _idx):
        self.theme_name = self.theme_combo.currentData()
        self.settings.setValue('theme', self.theme_name)
        self.apply_theme()
        self.render_page()

    def clear_user_data(self):
        answer = QMessageBox.question(self, 'تأكيد', 'مسح الإحصائيات والمحفوظات والورد والأذكار؟')
        if answer != QMessageBox.StandardButton.Yes:
            return
        for key in ('days', 'bookmarks', 'adhkar', 'wird_count', 'wird_next', 'wird_day'):
            self.settings.remove(key)
        self.render_page()

    def apply_theme(self):
        self.setStyleSheet(qss(THEMES[self.theme_name]))
        self.render_page()

    def on_update_button(self):
        if self.update_info:
            self.download_update()
        else:
            self.check_updates(manual=True)

    def check_updates(self, manual=False):
        if self.update_busy:
            return
        self.update_busy = True
        if manual:
            self.upd_status.setText('جارٍ التحقق…')
        req = QNetworkRequest(QUrl(f'{UPDATE_MANIFEST}?t={int(time.time())}'))
        req.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                         QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self._update_checked(reply, manual))

    def _update_checked(self, reply, manual):
        self.update_busy = False
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        data = bytes(reply.readAll()) if ok else b''
        reply.deleteLater()
        try:
            info = json.loads(data.decode('utf-8')).get('desktop') if data else None
        except (ValueError, AttributeError):
            info = None
        platform_key = 'windows' if sys.platform.startswith('win') else 'linux'
        url = (info or {}).get(platform_key)
        newer = bool(info and url and version_tuple(info.get('version')) > version_tuple(APP_VERSION))
        if newer:
            self.update_info = (info['version'], url)
            self.update_banner_label.setText(f'يتوفر تحديث {info["version"]}')
            self.update_banner.show()
            self.upd_status.setText(f'الإصدار {info["version"]} متاح')
            self.btn_check_update.setText('تحميل التحديث')
            return
        self.update_info = None
        self.update_banner.hide()
        self.btn_check_update.setText('تحقق من التحديث')
        if manual:
            self.upd_status.setText('أنت على أحدث نسخة' if ok else 'تعذّر الاتصال بالمستودع')

    def download_update(self):
        version, url = self.update_info
        target_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
                          or Path.home() / 'Downloads')
        target_dir.mkdir(parents=True, exist_ok=True)
        self.upd_target = target_dir / url.rsplit('/', 1)[-1]
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        reply = self.nam.get(req)
        reply.downloadProgress.connect(self._update_progress)
        reply.finished.connect(lambda: self._update_downloaded(reply))
        self.upd_status.setText('جارٍ التنزيل…')
        self.btn_check_update.setEnabled(False)

    def _update_progress(self, got, total):
        if total > 0:
            self.upd_status.setText(f'جارٍ التنزيل… {got * 100 // total}%')

    def _update_downloaded(self, reply):
        self.btn_check_update.setEnabled(True)
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        data = bytes(reply.readAll()) if ok else b''
        reply.deleteLater()
        if len(data) < 1_000_000:
            self.upd_status.setText('تعذّر التنزيل')
            return
        self.upd_target.write_bytes(data)
        if not sys.platform.startswith('win'):
            self.upd_target.chmod(0o755)
        self.upd_status.setText(f'تم التنزيل: {self.upd_target}')
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.upd_target.parent)))

    def closeEvent(self, event):  # noqa: N802
        self.settings.setValue('geometry', self.saveGeometry())
        super().closeEvent(event)


def _hard_exit(code):
    """إنهاء وضع الاختبار بعد طباعة النتيجة. على ويندوز TerminateProcess يتجاوز انهيار تحرير المكتبات وقت الإغلاق."""
    sys.stdout.flush()
    sys.stderr.flush()
    if sys.platform.startswith('win'):
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.TerminateProcess(k32.GetCurrentProcess(), code)
    os._exit(code)


def run_selftest(app, win):
    """وضع الاختبار: يتأكد إن الصفحة اتعرضت والقوائم اتملت، ويطبع النتيجة ويقفل فوراً."""
    def finish(ok, info):
        import json as _json
        try:
            print(_json.dumps({'ok': ok, **info}), flush=True)
        finally:
            _hard_exit(0 if ok else 1)

    def check():
        text = win.browser.toPlainText()
        info = {
            'page': win.page,
            'textLength': len(text),
            'surahs': win.combo_surah.count(),
            'reciters': win.reciter_combo.count(),
            'riwaya': win.riwaya_id,
            'hasMushaf': 'الفاتح' in text or '﴿' in text or 'ال' in text,
        }
        ok = info['textLength'] > 200 and info['surahs'] == 114 and info['reciters'] >= 1
        finish(ok, info)

    QTimer.singleShot(600, check)
    QTimer.singleShot(60000, lambda: finish(False, {'error': 'timeout'}))


def run_audiotest(app, win):
    """يشغّل التلاوة من الواجهة نفسها (حفص: ملف لكل آية، ورش الحصري: ملف لكل سورة) ويتأكد إن الوقت بيتقدم."""
    import json as _json
    results = {}
    cases = [('hafs', 'quran-simple', 0), ('warsh', 'warsh', 1)]
    win.engine.allow_null = True  # بيئات بدون كارت صوت (CI): يتقدم الوقت بالساعة ويتحقق من فك الملف
    state = {'i': 0, 'started': 0.0}

    def finish(ok):
        try:
            print(_json.dumps({'ok': ok, **results}), flush=True)
        finally:
            _hard_exit(0 if ok else 1)

    def next_case():
        if state['i'] >= len(cases):
            finish(all(v.get('ok') for v in results.values()))
            return
        name, riwaya, reciter = cases[state['i']]
        win.stop_play()
        idx = win.riwaya_combo.findData(riwaya)
        win.riwaya_combo.setCurrentIndex(idx)
        win.reciter_combo.setCurrentIndex(reciter)
        win.go_page(2)
        win.toggle_play()
        state['started'] = time.monotonic()
        poll(name)

    def poll(name):
        pos = win.engine.position_ms()
        err = win.play_status.text()
        if pos > 1500:
            results[name] = {'ok': True, 'position_ms': pos, 'status': win.play_status.text(),
                             'device': 'null' if win.engine.null_mode else 'system'}
            state['i'] += 1
            QTimer.singleShot(300, next_case)
        elif time.monotonic() - state['started'] > 25:
            results[name] = {'ok': False, 'position_ms': pos, 'status': err, 'error': win.engine.error}
            state['i'] += 1
            QTimer.singleShot(300, next_case)
        else:
            QTimer.singleShot(250, lambda: poll(name))

    QTimer.singleShot(500, next_case)
    QTimer.singleShot(120000, lambda: finish(False))


def main():
    import faulthandler
    faulthandler.enable()  # يطبع مكان الانهيار لو حصل انهيار أصلي (لتشخيص ويندوز)
    if '--selftest' in sys.argv:
        print('stage: start', file=sys.stderr, flush=True)
    for stream in (sys.stdout, sys.stderr):  # الكونسول على ويندوز cp1252: ما نطبعش عربي بدون تحويل
        if stream is not None and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName('mosalah30688')
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    QFontDatabase.addApplicationFont(str(FONTS / 'AmiriQuran-arabic.woff2'))
    for name in ('NotoSansArabic-Regular.ttf', 'NotoSansArabic-Bold.ttf'):
        QFontDatabase.addApplicationFont(str(FONTS / name))
    app.setFont(QFont('Noto Sans Arabic', 11))
    win = Main()
    win.show()
    if '--selftest' in sys.argv or os.environ.get('MUSHAF_SELFTEST') == '1':
        run_selftest(app, win)
    if '--audiotest' in sys.argv:
        run_audiotest(app, win)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
