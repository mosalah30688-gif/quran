#!/usr/bin/env python3
"""سراج — تطبيق قرآن كريم أصلي بواجهة Qt لنظام Linux.

البيانات الأساسية والتفاسير محلية؛ الاتصال مطلوب للتلاوة والتحديثات فقط.
تشغيل:   python3 main.py
اختبار:  python3 main.py --selftest
"""
import datetime
import array
import hashlib
from collections import deque
import html
from html.parser import HTMLParser
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import QByteArray, QObject, QPropertyAnimation, QRect, QSettings, QSize, QStandardPaths, Qt, QTime, QTimer, QUrl
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QGuiApplication, QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut, QTextDocument
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame,
    QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QDialog, QMainWindow, QMessageBox, QProgressBar, QPushButton, QRadioButton, QScrollArea, QSpinBox,
    QStackedWidget, QSystemTrayIcon, QTextBrowser, QTimeEdit,
    QVBoxLayout, QWidget,
)

from offline_tafsir import OfflineTafsirStore
from patch_runtime import install_patch_archive
from reading_tracker import (
    TOTAL_PAGES, clear_tracking, estimated_finish, habit_average, khatma_progress,
    khatma_state, reading_count, reading_counts, reading_streak, record_reading,
    set_khatma_pointer, start_new_khatma,
)
from reminder_scheduler import (
    configure_system_reminder, reminder_config, save_reminder_config, valid_time,
)
from runtime import configure_runtime_streams
from update_security import verify_update_manifest
from version import APP_DESCRIPTION_AR, APP_ID, APP_NAME, APP_NAME_AR, APP_VERSION

if getattr(sys, 'frozen', False):
    BASE = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
else:
    BASE = Path(__file__).resolve().parent
_PATCH_BASE = Path(os.environ['SIRAJ_PATCH_ROOT']).resolve() if os.environ.get('SIRAJ_PATCH_ROOT') else None


def resource_file(relative):
    relative = Path(relative)
    if _PATCH_BASE is not None:
        candidate = _PATCH_BASE / relative
        if candidate.is_file():
            return candidate
    return BASE / relative


FONTS = (_PATCH_BASE / 'fonts') if _PATCH_BASE is not None and (_PATCH_BASE / 'fonts').is_dir() else BASE / 'fonts'
ICON = resource_file('icon.png')
UPDATE_PUBLIC_KEY = BASE / 'assets' / 'update_public_key.txt'

ARABIC_DIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def ar(n):
    return str(n).translate(ARABIC_DIGITS)


def load(name):
    return json.loads(resource_file(Path('data') / name).read_text(encoding='utf-8'))


SURAHS = load('surahs.json')
JUZ_START = [tuple(x) for x in load('juz.json')]
TAJWEED = load('tajweed.json')
MEANINGS = load('quran-meanings.json')['ayahs']
ADHKAR = load('adhkar.json')['categories']
SEARCH_AYAHS = load('quran-search.json')['ayahs']
RIW_DATA = load('quran-riwayat.json')['riwayat']
HAFS = load('hafs.json')
TAFSIR_CATALOG = load('tafsir-catalog.json')
AYAH_TEXT = {(s, a): t for s, a, _p, t in HAFS['uthmani']}

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

# 17 صوتاً مختلفاً لحفص من CDN شبكة Islamic Network/AlQuran Cloud.
# الحقل الثالث معدل البت المنشور؛ لا نعرض نسخ -2 المكررة كأنها قراء جدد.
HAFS_RECITERS = [
    ('ar.alafasy', 'مشاري العفاسي', 128),
    ('ar.abdurrahmaansudais', 'عبدالرحمن السديس', 192),
    ('ar.mahermuaiqly', 'ماهر المعيقلي', 128),
    ('ar.husary', 'محمود خليل الحصري', 128),
    ('ar.husarymujawwad', 'الحصري (المجوّد)', 128),
    ('ar.hudhaify', 'علي الحذيفي', 128),
    ('ar.shaatree', 'أبو بكر الشاطري', 128),
    ('ar.abdulsamad', 'عبدالباسط عبدالصمد', 64),
    ('ar.saoodshuraym', 'سعود الشريم', 64),
    ('ar.muhammadayyoub', 'محمد أيوب', 128),
    ('ar.muhammadjibreel', 'محمد جبريل', 128),
    ('ar.abdullahbasfar', 'عبدالله بصفر', 64),
    ('ar.ahmedajamy', 'أحمد العجمي', 128),
    ('ar.hanirifai', 'هاني الرفاعي', 192),
    ('ar.ibrahimakhbar', 'إبراهيم الأخضر', 32),
    ('ar.aymanswoaid', 'أيمن سويد', 64),
    ('ar.parhizgar', 'شهريار پرهيزكار', 48),
]
# قراء الروايات الثلاث: ayah = ملف لكل آية، surah = ملف لكل سورة (mp3quran)
RIW_RECITERS = {
    'warsh': [
        ('warsh_abdulbasit', 'عبدالباسط عبدالصمد', 'surah', 'https://cdn.mp3quran.net/audio/abdulbasit-abdulsamad/r2/'),
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
AUDIO_BITRATE = {rid: bitrate for rid, _name, bitrate in HAFS_RECITERS}
AYAH_OFFSETS = {}
_offset = 0
for _surah in SURAHS:
    AYAH_OFFSETS[int(_surah['number'])] = _offset
    _offset += int(_surah['numberOfAyahs'])

# طبعات AlQuran Cloud الخمس تبقى قائمة حرفية كي يدققها سجل الحقوق الآلي.
TAFSIR_EDITIONS = [
    ('ar.muyassar', 'التفسير الميسر (مجمع الملك فهد)'),
    ('ar.jalalayn', 'تفسير الجلالين'),
    ('ar.baghawi', 'تفسير البغوي'),
    ('ar.qurtubi', 'تفسير القرطبي'),
    ('ar.miqbas', 'تنوير المقباس'),
]
# الكتب التراثية الإضافية: فهرس مقفول مولد من dump Quranpedia الرسمي؛
# النصوص الكاملة تُقرأ من قاعدة محلية مضغوطة ولا تحتاج إلى اتصال.
QURANPEDIA_TAFSIR_EDITIONS = [
    (
        book['edition'],
        f"{book['name']} — {book['author']} (ت {ar(book['author_death_hijri'])}هـ)",
    )
    for book in TAFSIR_CATALOG['books']
]
ALL_TAFSIR_EDITIONS = TAFSIR_EDITIONS + QURANPEDIA_TAFSIR_EDITIONS
TAFSIR_METADATA = {book['edition']: book for book in TAFSIR_CATALOG['books']}

_DIACRITICS = re.compile('[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]')


class _TafsirTextExtractor(HTMLParser):
    """يحّول HTML المصدر إلى نص آمن مع إبقاء حدود الفقرات والقوائم."""

    BLOCKS = {'address', 'blockquote', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'p', 'tr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in self.BLOCKS:
            self.parts.append('\n')
        if not self.ignored_depth and tag == 'li':
            self.parts.append('• ')

    def handle_endtag(self, tag):
        if tag in {'script', 'style'} and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in self.BLOCKS:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.ignored_depth:
            self.parts.append(data)

    def text(self):
        value = ''.join(self.parts).replace('\r', '\n').replace('\xa0', ' ')
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in value.split('\n')]
        out = []
        for line in lines:
            if line:
                out.append(line)
            elif out and out[-1] != '':
                out.append('')
        return '\n'.join(out).strip()


def tafsir_fragment_text(value):
    parser = _TafsirTextExtractor()
    try:
        parser.feed(str(value or ''))
        parser.close()
    except (ValueError, AssertionError):
        return re.sub(r'<[^>]+>', ' ', str(value or '')).strip()
    return parser.text()


def parse_tafsir_payload(edition, payload):
    """يفك استجابة المصدر المختار إلى نص موحّد بلا HTML غير موثوق."""
    if str(edition).startswith('qp:'):
        content = payload.get('content') if isinstance(payload, dict) else None
        if not isinstance(content, list):
            return None
        segments = []
        seen = set()
        for item in content:
            text = tafsir_fragment_text(item.get('text') if isinstance(item, dict) else '')
            if text and text not in seen:
                seen.add(text)
                segments.append(text)
        return '\n\n'.join(segments) if segments else 'لا يوجد نص خاص بهذه الآية في هذا الكتاب.'
    try:
        return str(payload['data']['text']).strip() or None
    except (KeyError, TypeError):
        return None


def tafsir_request(edition, surah, ayah):
    if str(edition).startswith('qp:'):
        book_id = int(str(edition).split(':', 1)[1])
        url = f"{TAFSIR_CATALOG['api_base']}/ayah/{surah}/{ayah}/book/{book_id}"
    else:
        url = f'https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/{edition}'
    request = QNetworkRequest(QUrl(url))
    request.setRawHeader(
        QByteArray(b'User-Agent'),
        QByteArray(f'Siraj-Quran/{APP_VERSION} live-tafsir'.encode('ascii')),
    )
    return request


def populate_tafsir_books(combo):
    """يعرض الطبعات المدققة أولًا ثم المكتبة التراثية المرخصة بلا تكرار."""
    for edition, name in TAFSIR_EDITIONS:
        combo.addItem(name, edition)
    combo.insertSeparator(combo.count())
    for edition, name in QURANPEDIA_TAFSIR_EDITIONS:
        combo.addItem(name, edition)
    combo.setMaxVisibleItems(22)
    combo.setMinimumContentsLength(28)
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setToolTip('اختر تفسيرًا؛ جميع النصوص الموثقة مدمجة محليًا وتعمل دون إنترنت')


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
BASMALA_HAFS = 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ'
BASMALA_SIMPLE = 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ'

# خطوط عربية حرة مضمّنة تحت SIL OFL 1.1 وتُطبق على المصحف والتفسير معًا.
MUSHAF_FONTS = [
    ('Amiri Quran', 'أميري قرآن — الافتراضي'),
    ('Amiri', 'أميري'),
    ('Noto Naskh Arabic', 'نوتو نسخ عربي'),
    ('Scheherazade New', 'شهرزاد الجديد'),
]
BUNDLED_FONT_FILES = (
    'AmiriQuran-Regular.ttf',
    'Amiri-Regular.ttf',
    'NotoNaskhArabic-Variable.ttf',
    'ScheherazadeNew-Regular.ttf',
    'NotoSansArabic-Regular.ttf',
    'NotoSansArabic-Bold.ttf',
)


def register_bundled_fonts():
    """يسجّل الخطوط المضمّنة ويعيد أسماء الملفات التي حمّلها Qt بنجاح."""
    loaded = []
    for name in BUNDLED_FONT_FILES:
        path = FONTS / name
        if path.is_file() and QFontDatabase.addApplicationFont(str(path)) >= 0:
            loaded.append(name)
    return loaded


def display_ayah_source(surah, ayah, text, is_hafs):
    """يفصل بسملة حفص المدمجة للعرض فقط، مع إبقاء ملف المصدر والترقيم كما هما."""
    source = str(text).lstrip('\ufeff').strip()
    if not is_hafs or ayah != 1 or surah in (1, 9):
        return source
    for prefix in (BASMALA_HAFS, BASMALA_SIMPLE):
        if source.startswith(prefix):
            words = source.split(maxsplit=4)
            return words[4].strip() if len(words) == 5 else ''
    return source


def display_ayah_text(surah, ayah, text, is_hafs):
    """النص المرئي؛ يجب تحديد حفص صراحةً حتى لا تتأثر الروايات الأخرى."""
    return display_ayah_source(surah, ayah, text, is_hafs)


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
    QTextBrowser#mushaf {{ background: {t['paper']}; border: 1px solid {t['paper_line']};
                          border-radius: 12px; padding: 18px 22px; }}
    QTextBrowser {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 16px; padding: 14px; }}
    QComboBox, QSpinBox, QTimeEdit, QLineEdit {{ background: {t['card']}; border: 1px solid {t['line']};
                                                border-radius: 10px; padding: 7px 12px; min-height: 26px; }}
    QComboBox:focus, QSpinBox:focus, QTimeEdit:focus, QLineEdit:focus {{ border: 1px solid {t['brand']}; }}
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


# Fluent-inspired 3D vectors authored for Siraj. They remain crisp at 20 px,
# use layered highlights/shadows instead of external image assets, and keep the
# original application icon completely unchanged.
ICON_SVG = {
    'book': '''
        <path d="M3.1 5.2h7.1c1.15 0 1.8.55 1.8 1.55V21c-.55-1.05-1.35-1.5-2.55-1.5H3.1z" fill="#063f36" opacity=".38" transform="translate(.45 .7)"/>
        <path d="M2.5 3.5h7.1c1.2 0 2.05.58 2.4 1.5v14.4c-.72-.82-1.5-1.2-2.65-1.2H2.5z" fill="url(#gEmerald)" stroke="#063e36" stroke-width=".75"/>
        <path d="M21.5 3.5h-7.1c-1.2 0-2.05.58-2.4 1.5v14.4c.72-.82 1.5-1.2 2.65-1.2h6.85z" fill="url(#gBlue)" stroke="#164675" stroke-width=".75"/>
        <path d="M4 5h5.3c.8 0 1.45.34 1.7.82v10.7c-.5-.3-1.05-.45-1.75-.45H4z" fill="url(#gPaper)"/>
        <path d="M20 5h-5.3c-.8 0-1.45.34-1.7.82v10.7c.5-.3 1.05-.45 1.75-.45H20z" fill="url(#gPaper)"/>
        <path d="M6 7.1h3.6M6 9.3h3.9M14.4 7.1H18M14.1 9.3H18" stroke="#b59a66" stroke-width=".7" stroke-linecap="round" opacity=".8"/>
        <path d="M12 5v14.35" stroke="#d3b059" stroke-width="1.05"/><path d="M3.2 4.1h6" stroke="#fff" stroke-width=".7" opacity=".48"/>
    ''',
    'tafsir': '''
        <path d="M2.7 6.5c3.1-1.3 6.4-1 9.3 1.1 2.9-2.1 6.2-2.4 9.3-1.1v12.8c-3.2-1.1-6.3-.65-9.3 1.35-3-2-6.1-2.45-9.3-1.35z" fill="#102d4a" opacity=".34" transform="translate(.35 .65)"/>
        <path d="M2.2 4.8c3.25-1.35 6.7-.95 9.8 1.2v12.8c-3.1-2.05-6.35-2.45-9.8-1.15z" fill="url(#gPaper)" stroke="#7e6945" stroke-width=".7"/>
        <path d="M21.8 4.8c-3.25-1.35-6.7-.95-9.8 1.2v12.8c3.1-2.05 6.35-2.45 9.8-1.15z" fill="url(#gPaper)" stroke="#7e6945" stroke-width=".7"/>
        <path d="M12 6v12.8" stroke="#ad8c45" stroke-width="1"/>
        <path d="M4.4 7.3c2-.55 3.7-.35 5.45.55M4.4 9.7c1.85-.48 3.55-.3 5.25.5M14.15 7.85c1.75-.9 3.45-1.1 5.45-.55M14.35 10.2c1.7-.8 3.4-.98 5.25-.5" fill="none" stroke="#5d7793" stroke-width=".75" stroke-linecap="round"/>
        <path d="M17.7 12.15l1.1 1.45 1.85-.25-.95 1.6.8 1.68-1.82-.4-1.2 1.4-.18-1.85-1.73-.72 1.7-.75z" fill="url(#gGold)" stroke="#9b6716" stroke-width=".45"/>
        <path d="M3.5 5.2c2.5-.85 4.8-.55 7 .85" stroke="#fff" stroke-width=".65" opacity=".55"/>
    ''',
    'search': '''
        <ellipse cx="10.1" cy="10.1" rx="7.2" ry="7.2" fill="#071d30" opacity=".35" transform="translate(.6 .85)"/>
        <circle cx="9.7" cy="9.6" r="6.65" fill="url(#gGlass)" stroke="url(#gMetal)" stroke-width="2"/>
        <path d="M14.6 14.5l2.05 2.05" stroke="#39556d" stroke-width="2.25" stroke-linecap="round"/>
        <path d="M16.2 16.05l4.4 4.4c.55.55.55 1.45 0 2s-1.45.55-2 0l-4.4-4.4z" fill="url(#gGold)" stroke="#7d531a" stroke-width=".7"/>
        <path d="M5.8 6.2c1.65-1.65 4.15-2.15 6.25-1.1" fill="none" stroke="#fff" stroke-width="1.2" stroke-linecap="round" opacity=".82"/>
        <circle cx="7.1" cy="6.3" r=".75" fill="#fff" opacity=".65"/>
    ''',
    'words': '''
        <path d="M3.1 4h10.7a2.2 2.2 0 0 1 2.2 2.2v5.3a2.2 2.2 0 0 1-2.2 2.2H8l-3.45 2.55.75-2.55H3.1A2.2 2.2 0 0 1 .9 11.5V6.2A2.2 2.2 0 0 1 3.1 4z" fill="#10253c" opacity=".3" transform="translate(.5 .65)"/>
        <path d="M2.6 2.8h10.7A2.2 2.2 0 0 1 15.5 5v5.3a2.2 2.2 0 0 1-2.2 2.2H7.5l-3.45 2.55.75-2.55H2.6a2.2 2.2 0 0 1-2.2-2.2V5a2.2 2.2 0 0 1 2.2-2.2z" fill="url(#gBlue)" stroke="#164675" stroke-width=".7"/>
        <path d="M10.4 12.2h9a2.2 2.2 0 0 1 2.2 2.2v3.35a2.2 2.2 0 0 1-2.2 2.2h-1.8l.55 2.1-3-2.1h-4.75a2.2 2.2 0 0 1-2.2-2.2V14.4a2.2 2.2 0 0 1 2.2-2.2z" fill="url(#gEmerald)" stroke="#075044" stroke-width=".7"/>
        <path d="M3.6 5.7h8.7M3.6 8.4h6.2M11.2 15.3h7.4M11.2 17.4h5.2" stroke="#fff" stroke-width="1" stroke-linecap="round" opacity=".9"/>
        <path d="M2.2 3.6h9" stroke="#fff" stroke-width=".65" opacity=".42"/>
    ''',
    'tajweed': '''
        <path d="M12.1 2.2c-5.65 0-10.2 4.1-10.2 9.25 0 5.75 5.2 10.1 11.05 10.1h1.35c1.7 0 2.95-1.1 2.95-2.55 0-1.65-1.2-2.55-2.75-2.55h-1.2c-1.15 0-1.9-.8-1.9-1.75 0-1.05.85-1.85 2.05-1.85h2.8c3.35 0 5.85-2.15 5.85-5.05 0-3.25-4.05-5.6-10-5.6z" fill="#40276b" opacity=".35" transform="translate(.35 .65)"/>
        <path d="M11.8 1.3c-5.65 0-10.2 4.1-10.2 9.25 0 5.75 5.2 10.1 11.05 10.1H14c1.7 0 2.95-1.1 2.95-2.55 0-1.65-1.2-2.55-2.75-2.55H13c-1.15 0-1.9-.8-1.9-1.75 0-1.05.85-1.85 2.05-1.85h2.8c3.35 0 5.85-2.15 5.85-5.05 0-3.25-4.05-5.6-10-5.6z" fill="url(#gViolet)" stroke="#48236c" stroke-width=".7"/>
        <circle cx="6.1" cy="7.1" r="1.65" fill="#ff515b" stroke="#9d1720" stroke-width=".45"/><circle cx="10.2" cy="4.9" r="1.65" fill="#ffba36" stroke="#a56400" stroke-width=".45"/><circle cx="14.5" cy="5" r="1.65" fill="#48d17d" stroke="#16733e" stroke-width=".45"/><circle cx="18" cy="8" r="1.65" fill="#50bfff" stroke="#176a9d" stroke-width=".45"/>
        <circle cx="5.6" cy="6.55" r=".52" fill="#fff" opacity=".75"/><circle cx="9.7" cy="4.35" r=".52" fill="#fff" opacity=".75"/><circle cx="14" cy="4.45" r=".52" fill="#fff" opacity=".75"/>
        <path d="M17.6 14.2l4.55 6.15" stroke="#6b4219" stroke-width="1.8" stroke-linecap="round"/><path d="M16.2 12.55l2.65 2.3-1.8 1.5-2.35-2.65z" fill="url(#gGold)" stroke="#7f5315" stroke-width=".5"/>
    ''',
    'adhkar': '''
        <path d="M12 2.15c-5.4 0-9.45 4.25-9.45 9.5 0 4.55 3.25 8.3 7.55 9.2" fill="none" stroke="#173d34" stroke-width="2.15" opacity=".42" transform="translate(.45 .55)"/>
        <path d="M12 1.45c-5.4 0-9.45 4.25-9.45 9.5 0 4.55 3.25 8.3 7.55 9.2" fill="none" stroke="#d1aa52" stroke-width="1.15"/>
        <g fill="url(#gBead)" stroke="#075044" stroke-width=".5"><circle cx="12" cy="2" r="1.75"/><circle cx="6.8" cy="3.5" r="1.75"/><circle cx="3.35" cy="7.55" r="1.75"/><circle cx="3.15" cy="12.9" r="1.75"/><circle cx="6.2" cy="17.3" r="1.75"/><circle cx="10.85" cy="19.75" r="1.75"/></g>
        <g fill="#fff" opacity=".62"><circle cx="11.45" cy="1.45" r=".45"/><circle cx="6.25" cy="2.95" r=".45"/><circle cx="2.8" cy="7" r=".45"/><circle cx="2.6" cy="12.35" r=".45"/></g>
        <path d="M12.2 19.8c2.8-.45 5.35-2.15 6.7-4.45" stroke="#d1aa52" stroke-width="1.15" fill="none"/>
        <path d="M18.9 14.5l1.2 2.45-1.05 1.15 1.55 3.75-2.2.8-1.5-3.75-1.5-.15.35-2.7z" fill="url(#gGold)" stroke="#7e5215" stroke-width=".55"/>
    ''',
    'memo': '''
        <path d="M4.2 2.4h11.9l4 4v14.8H4.2z" fill="#193247" opacity=".32" transform="translate(.55 .7)"/>
        <path d="M3.5 1.5h11.9l4 4v14.8H3.5z" fill="url(#gPaper)" stroke="#806b47" stroke-width=".7"/>
        <path d="M15.4 1.5v4h4" fill="#e5ce9e" stroke="#806b47" stroke-width=".55"/>
        <path d="M6 7.1h9.8M6 10h8.2M6 12.9h6.2" stroke="#7d91a2" stroke-width=".85" stroke-linecap="round"/>
        <path d="M7.25 18.6l1-3.1 8.55-8.55 2.35 2.35-8.55 8.55z" fill="url(#gEmerald)" stroke="#075044" stroke-width=".65"/>
        <path d="M16.8 6.95l1.2-1.2c.5-.5 1.25-.5 1.75 0l.6.6c.5.5.5 1.25 0 1.75l-1.2 1.2z" fill="url(#gGold)" stroke="#805317" stroke-width=".55"/>
        <path d="M7.25 18.6l3.35-.75-2.35-2.35z" fill="#f1c79b" stroke="#805317" stroke-width=".45"/><path d="M18.2 6.15l1.75 1.75" stroke="#fff" stroke-width=".55" opacity=".72"/>
    ''',
    'wird': '''
        <path d="M3.1 4.8h17.8v17H3.1z" rx="2" fill="#102d3f" opacity=".32" transform="translate(.45 .65)"/>
        <rect x="2.4" y="3.7" width="19.2" height="17.1" rx="2.2" fill="url(#gPaper)" stroke="#745e3d" stroke-width=".7"/>
        <path d="M2.4 5.9c0-1.2 1-2.2 2.2-2.2h14.8c1.2 0 2.2 1 2.2 2.2v3H2.4z" fill="url(#gBlue)"/>
        <path d="M7 1.8v4.1M17 1.8v4.1" stroke="#d8b45f" stroke-width="2.1" stroke-linecap="round"/><path d="M7 1.8v2" stroke="#fff" stroke-width=".65" opacity=".62"/>
        <path d="M6.5 14.3l3.2 3.15 7.8-7.3" fill="none" stroke="url(#gEmerald)" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M3.2 4.6h16" stroke="#fff" stroke-width=".65" opacity=".4"/>
    ''',
    'bookmarks': '''
        <path d="M3.3 5.2h15.4c1.3 0 2.35 1.05 2.35 2.35v12.1H5.65A2.35 2.35 0 0 1 3.3 17.3z" fill="#142e43" opacity=".34" transform="translate(.5 .65)"/>
        <path d="M2.6 3.9H18c1.3 0 2.35 1.05 2.35 2.35v12.1H4.95A2.35 2.35 0 0 1 2.6 16z" fill="url(#gBlue)" stroke="#164675" stroke-width=".7"/>
        <path d="M4.5 5.7h12.1c.9 0 1.65.75 1.65 1.65V16H5.8c-.5 0-.95.12-1.3.35z" fill="url(#gPaper)"/>
        <path d="M7.1 7.5h7.6M7.1 9.7h6.1" stroke="#8c9eab" stroke-width=".75" stroke-linecap="round"/>
        <path d="M12.5 3.1h4.45v10.1l-2.22-1.55-2.23 1.55z" fill="url(#gRed)" stroke="#8f1e2f" stroke-width=".65"/><path d="M13.2 3.75h2.75" stroke="#fff" stroke-width=".55" opacity=".55"/>
        <path d="M3.2 4.5h8" stroke="#fff" stroke-width=".65" opacity=".35"/>
    ''',
    'stats': '''
        <path d="M2.3 20.7h19.5" stroke="#152c3d" stroke-width="1.7" stroke-linecap="round" opacity=".45" transform="translate(.25 .5)"/>
        <rect x="3.1" y="12" width="4.8" height="8.1" rx="1.25" fill="url(#gBlue)" stroke="#164675" stroke-width=".6"/>
        <rect x="9.6" y="5.3" width="4.8" height="14.8" rx="1.25" fill="url(#gEmerald)" stroke="#075044" stroke-width=".6"/>
        <rect x="16.1" y="8.7" width="4.8" height="11.4" rx="1.25" fill="url(#gGold)" stroke="#815417" stroke-width=".6"/>
        <path d="M4.1 13h2.7M10.6 6.4h2.7M17.1 9.8h2.7" stroke="#fff" stroke-width=".85" stroke-linecap="round" opacity=".64"/>
        <path d="M2.3 20.1h19.5" stroke="#d8b45f" stroke-width="1" stroke-linecap="round"/>
        <path d="M4 9.2l4-3.15 3.7 1.2 5.2-4" fill="none" stroke="#ef5b6c" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/><path d="M16.3 2.9l1.85-.7-.2 1.95" fill="none" stroke="#ef5b6c" stroke-width="1.2"/>
    ''',
    'update': '''
        <path d="M3.2 13.1a8.9 8.9 0 0 0 15.25 5.45l1.75 1.65.7-6.25-6.25.7 1.72 1.62A6.05 6.05 0 0 1 6.1 12.75z" fill="#102d3f" opacity=".34" transform="translate(.45 .65)"/>
        <path d="M20.8 10.9A8.9 8.9 0 0 0 5.55 5.45L3.8 3.8l-.7 6.25 6.25-.7-1.72-1.62A6.05 6.05 0 0 1 17.9 11.25z" fill="url(#gBlue)" stroke="#164675" stroke-width=".65"/>
        <path d="M3.2 12.75a8.9 8.9 0 0 0 15.25 5.8l1.75 1.65.7-6.25-6.25.7 1.72 1.62A6.05 6.05 0 0 1 6.1 12.75z" fill="url(#gEmerald)" stroke="#075044" stroke-width=".65"/>
        <path d="M12 5.9v8.25M8.85 11.05 12 14.25l3.15-3.2" fill="none" stroke="#fff" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M17.1 5.15c1.25 1.05 2.1 2.4 2.45 3.85" fill="none" stroke="#fff" stroke-width=".7" stroke-linecap="round" opacity=".65"/>
    ''',
    'settings': '''
        <path d="M9.6 2.2h4.8l.65 2.35c.62.2 1.2.45 1.75.78l2.15-1.2 3.4 3.4-1.2 2.15c.33.55.58 1.13.78 1.75l2.35.65v4.8l-2.35.65c-.2.62-.45 1.2-.78 1.75l1.2 2.15-3.4 3.4-2.15-1.2c-.55.33-1.13.58-1.75.78l-.65 2.35H9.6l-.65-2.35a9.2 9.2 0 0 1-1.75-.78l-2.15 1.2-3.4-3.4 1.2-2.15a9.2 9.2 0 0 1-.78-1.75l-2.35-.65v-4.8l2.35-.65c.2-.62.45-1.2.78-1.75l-1.2-2.15 3.4-3.4 2.15 1.2c.55-.33 1.13-.58 1.75-.78z" fill="#1a2d3d" opacity=".35" transform="scale(.82) translate(3.4 2.8)"/>
        <path d="M9.6 1.1h4.8l.65 2.35c.62.2 1.2.45 1.75.78l2.15-1.2 3.4 3.4-1.2 2.15c.33.55.58 1.13.78 1.75l2.35.65v4.8l-2.35.65c-.2.62-.45 1.2-.78 1.75l1.2 2.15-3.4 3.4-2.15-1.2c-.55.33-1.13.58-1.75.78l-.65 2.35H9.6l-.65-2.35a9.2 9.2 0 0 1-1.75-.78l-2.15 1.2-3.4-3.4 1.2-2.15a9.2 9.2 0 0 1-.78-1.75l-2.35-.65v-4.8l2.35-.65c.2-.62.45-1.2.78-1.75l-1.2-2.15 3.4-3.4 2.15 1.2c.55-.33 1.13-.58 1.75-.78z" fill="url(#gMetal)" stroke="#304b61" stroke-width=".65" transform="scale(.82) translate(3.4 2.8)"/>
        <circle cx="12" cy="12" r="5.25" fill="url(#gBlue)" stroke="#164675" stroke-width=".7"/><circle cx="12" cy="12" r="2.3" fill="url(#gGold)" stroke="#7c5016" stroke-width=".65"/>
        <path d="M8.3 7.4a6.2 6.2 0 0 1 5.9-1.25" fill="none" stroke="#fff" stroke-width=".85" stroke-linecap="round" opacity=".68"/><circle cx="11.35" cy="11.35" r=".65" fill="#fff" opacity=".64"/>
    ''',
    'play': '''<path d="M6 3.7v16.6c0 1.1 1.2 1.75 2.15 1.18l12.1-8.3c.85-.58.85-1.78 0-2.36L8.15 2.52C7.2 1.95 6 2.6 6 3.7z" fill="url(#gEmerald)" stroke="#075044" stroke-width=".8"/><path d="M7.3 4.5l8.5 5.8" stroke="#fff" stroke-width=".8" opacity=".5"/>''',
}


def svg_icon(name, color='#dff3ea', size=20):
    defs = f'''
      <defs>
        <linearGradient id="gEmerald" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#62e2b1"/><stop offset=".48" stop-color="#18a87c"/><stop offset="1" stop-color="#08624f"/></linearGradient>
        <linearGradient id="gBlue" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#86d8ff"/><stop offset=".5" stop-color="#378fd6"/><stop offset="1" stop-color="#23518d"/></linearGradient>
        <linearGradient id="gGold" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff0a6"/><stop offset=".48" stop-color="#e5ad3c"/><stop offset="1" stop-color="#a66516"/></linearGradient>
        <linearGradient id="gRed" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ff9a9d"/><stop offset=".48" stop-color="#e64f61"/><stop offset="1" stop-color="#9e263b"/></linearGradient>
        <linearGradient id="gPaper" x1="0" y1="0" x2=".8" y2="1"><stop stop-color="#fffdf3"/><stop offset=".6" stop-color="#f4e8ca"/><stop offset="1" stop-color="#d7bd82"/></linearGradient>
        <linearGradient id="gMetal" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#eff8ff"/><stop offset=".35" stop-color="#9bb5c7"/><stop offset=".68" stop-color="#4d6e85"/><stop offset="1" stop-color="#c6d8e3"/></linearGradient>
        <linearGradient id="gViolet" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#d4a1ff"/><stop offset=".48" stop-color="#8f59cf"/><stop offset="1" stop-color="#54307e"/></linearGradient>
        <linearGradient id="gTint" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff"/><stop offset=".35" stop-color="{color}"/><stop offset="1" stop-color="#316352"/></linearGradient>
        <radialGradient id="gGlass" cx=".32" cy=".25" r=".85"><stop stop-color="#effcff" stop-opacity=".92"/><stop offset=".45" stop-color="#8ee3ff" stop-opacity=".55"/><stop offset="1" stop-color="#2784c5" stop-opacity=".42"/></radialGradient>
        <radialGradient id="gBead" cx=".3" cy=".25" r=".8"><stop stop-color="#a8ffe1"/><stop offset=".38" stop-color="#20b785"/><stop offset="1" stop-color="#08604d"/></radialGradient>
      </defs>'''
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size * 2}" height="{size * 2}">'
        + defs + ICON_SVG[name].replace('{c}', color) + '</svg>'
    )
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    renderer.render(painter)
    painter.end()
    return QIcon(pm)


MEMO_GAPS = [1, 3, 7, 14, 30, 60]  # أيام بين المراجعات: تتباعد كلما أُتقن المقطع
MEMO_LEVELS = [0, 25, 50, 75, 100]  # نسبة الكلمات المخفية


def ayah_audio_url(rid, s, a):
    bitrate = AUDIO_BITRATE.get(rid)
    offset = AYAH_OFFSETS.get(int(s))
    if bitrate is None or offset is None:
        return None
    number = offset + int(a)
    return f'https://cdn.islamic.network/quran/audio/{bitrate}/{rid}/{number}.mp3'


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


class NoWheelComboBox(QComboBox):
    """قائمة لا تغيّر الاختيار بعجلة الماوس/لوحة اللمس وهي مغلقة."""

    def wheelEvent(self, event):  # noqa: N802
        event.accept()


class NoWheelSpinBox(QSpinBox):
    """حقل رقمي لا يقفز بين القيم لمجرد مرور المؤشر فوقه."""

    def wheelEvent(self, event):  # noqa: N802
        event.accept()


class NoWheelTimeEdit(QTimeEdit):
    """حقل وقت يتطلب اختيارًا مقصودًا بدل تغيير اللمس العرضي."""

    def wheelEvent(self, event):  # noqa: N802
        event.accept()


class PageBrowser(QTextBrowser):
    """العجلة/لوحة اللمس تمرران الصفحة الحالية فقط؛ التقليب بالأسهم وحدها."""

    def __init__(self, _on_turn=None):
        super().__init__()

    def wheelEvent(self, event):  # noqa: N802
        # بعض منصات Qt لا تحرّك QTextBrowser عند وصول pixelDelta فقط من لوحة
        # اللمس؛ نعالجه رأسيًا صراحةً. الإيماءة الأفقية تُمتص ولا تقلب صفحة.
        pixel = event.pixelDelta()
        if not pixel.isNull():
            if pixel.y():
                bar = self.verticalScrollBar()
                bar.setValue(bar.value() - pixel.y())
            event.accept()
            return
        # عجلة الماوس التقليدية تبقى معالجة Qt الطبيعية داخل المستند، حتى عند
        # الحافة؛ لا توجد أي دعوة لتغيير الصفحة.
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


UPDATE_MANIFEST = 'https://raw.githubusercontent.com/mosalah30688-gif/quran/main/update/linux/stable.json'
PATCH_MANIFEST = 'https://raw.githubusercontent.com/mosalah30688-gif/quran/main/update/linux/patch-stable.json'
RUNTIME_API = 1


def version_tuple(v):
    nums = [int(x) for x in re.findall(r'\d+', str(v))][:4]
    return tuple(nums) or (0,)


def validated_update_info(manifest):
    """يرفض أي أصل تحديث لا يحمل هوية سراج أو حجمًا وSHA-256 صالحين."""
    try:
        asset = (manifest.get('assets') or {}).get('appimage') or {}
        info = {
            'version': str(manifest.get('version', '')),
            'url': str(asset.get('url', '')),
            'sha256': str(asset.get('sha256', '')).lower(),
            'size': int(asset.get('size', 0)),
        }
    except (ValueError, TypeError, AttributeError):
        return None
    expected_prefix = 'https://github.com/mosalah30688-gif/quran/releases/download/'
    valid = (
        verify_update_manifest(manifest, UPDATE_PUBLIC_KEY)
        and manifest.get('schema') == 1
        and manifest.get('product') == 'siraj-quran-linux'
        and manifest.get('channel') == 'stable'
        and manifest.get('available') is True
        and info['url'].startswith(expected_prefix)
        and re.fullmatch(r'[0-9a-f]{64}', info['sha256']) is not None
        and info['size'] > 1_000_000
    )
    return info if valid else None


def app_settings():
    """إعدادات سراج مع ترحيل صامت لإعدادات AppImage القديمة مرة واحدة."""
    current = QSettings('mosalah30688', APP_NAME)
    marker = 'migration/mushaf-settings-v1'
    if not current.value(marker, False, type=bool):
        legacy = QSettings('mosalah30688', 'Mushaf')
        if not current.allKeys():
            for key in legacy.allKeys():
                current.setValue(key, legacy.value(key))
        current.setValue(marker, True)
        current.sync()
    return current


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'{APP_NAME_AR} — {APP_DESCRIPTION_AR}')
        if ICON.exists():
            self.setWindowIcon(QIcon(str(ICON)))
        self.settings = app_settings()
        self.theme_name = self.settings.value('theme', 'light', type=str)
        if self.theme_name not in THEMES:
            self.theme_name = 'light'
        shamela_marker = 'migration/hafs-shamela-layout-v1'
        if not self.settings.value(shamela_marker, False, type=bool):
            if self.settings.value('font_pt', 22, type=int) == 22:
                self.settings.setValue('font_pt', 18)
            self.settings.setValue(shamela_marker, True)
        self.font_pt = self.settings.value('font_pt', 18, type=int)
        self.mushaf_font = self.settings.value('mushaf_font', 'Amiri Quran', type=str)
        if self.mushaf_font not in {family for family, _label in MUSHAF_FONTS}:
            self.mushaf_font = 'Amiri Quran'
        riwaya = self.settings.value('riwaya', 'quran-uthmani', type=str)
        if riwaya not in RIWAYA_NAMES:
            riwaya = 'quran-uthmani'
        self.riwaya_id = riwaya
        self.book = Book(riwaya)
        self.page = min(max(self.settings.value('page', 1, type=int), 1), TOTAL_PAGES)
        self._rendered_page = None
        khatma_state(self.settings, self.page)
        self.reading_pending_page = self.page
        self.reading_timer = QTimer(self)
        self.reading_timer.setSingleShot(True)
        self.reading_timer.setInterval(10_000)
        self.reading_timer.timeout.connect(self.commit_reading_page)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(60_000)
        self.reminder_timer.timeout.connect(self.update_khatma_reminder)

        self.nam = QNetworkAccessManager(self)
        self.offline_tafsir = OfflineTafsirStore(resource_file('data/tafsir-offline.sqlite3'))
        self.tafsir_cache = {}
        self.tafsir_key = None
        valid_tafsirs = {edition for edition, _name in ALL_TAFSIR_EDITIONS}
        if self.settings.value('tafsir', 'ar.muyassar', type=str) not in valid_tafsirs:
            self.settings.setValue('tafsir', 'ar.muyassar')
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
        self.upd_stream = None
        self.queue_list = False
        self.dl = {'running': False}
        self.queue = []
        self.queue_index = -1
        self.playing = False
        self.highlight = None

        avail = QGuiApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(min(1000, avail.width() - 40), min(620, avail.height() - 80))
        self.resize(min(1880, int(avail.width() * 0.96)), min(920, int(avail.height() * 0.92)))
        self.move(avail.center() - self.rect().center())
        self.build_ui()
        self.apply_theme()
        self.show_view('reader')
        self.render_page()
        self.schedule_reading_record()
        self.reminder_timer.start()
        QTimer.singleShot(1200, self.initialize_reminders)

        QShortcut(QKeySequence('PgDown'), self, activated=lambda: self.go_page(self.page + 1))
        QShortcut(QKeySequence('PgUp'), self, activated=lambda: self.go_page(self.page - 1))
        QShortcut(QKeySequence('Ctrl+P'), self, activated=self.toggle_play)
        QShortcut(QKeySequence('Ctrl+F'), self, activated=lambda: self.show_view('search'))
        QShortcut(QKeySequence('Ctrl+0'), self, activated=lambda: self.set_font(18))
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

        self.sidebar = QWidget()
        side = self.sidebar
        side.setObjectName('sidebar')
        side.setFixedWidth(248)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 12)
        self.brand_label = QLabel(APP_NAME_AR)
        self.brand_label.setObjectName('brand')
        self.brand_sub = QLabel(f'{APP_DESCRIPTION_AR} · الإصدار {APP_VERSION}')
        self.brand_sub.setObjectName('brandSub')
        sl.addWidget(self.brand_label)
        sl.addWidget(self.brand_sub)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.views = {}
        self.nav_buttons = {}
        self.nav_labels = {}
        nav_items = [
            ('reader', 'book', 'المصحف'),
            ('tafsir', 'tafsir', 'التفسير'),
            ('search', 'search', 'البحث في القرآن'),
            ('meanings', 'words', 'معاني الكلمات'),
            ('tajweed', 'tajweed', 'أحكام التجويد'),
            ('adhkar', 'adhkar', 'الأذكار'),
            ('memo', 'memo', 'وضع الحفظ'),
            ('wird', 'wird', 'متابعة الختمة'),
            ('bookmarks', 'bookmarks', 'المحفوظات'),
            ('stats', 'stats', 'الإحصائيات'),
        ]
        for key, icon, label in nav_items:
            b = QPushButton(label)
            b.setIcon(svg_icon(icon))
            b.setIconSize(QSize(22, 22))
            b.setObjectName('nav')
            b.setCheckable(True)
            b.clicked.connect(lambda _c=False, k=key: self.show_view(k))
            self.nav_group.addButton(b)
            self.nav_buttons[key] = b
            self.nav_labels[key] = label
            b.setToolTip(label)
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
        self.khatma_banner = QFrame()
        self.khatma_banner.setObjectName('card')
        kb = QVBoxLayout(self.khatma_banner)
        kb.setContentsMargins(12, 10, 12, 10)
        self.khatma_banner_label = QLabel()
        self.khatma_banner_label.setWordWrap(True)
        btn_continue = QPushButton('متابعة الختمة')
        btn_continue.setObjectName('primary')
        btn_continue.clicked.connect(self.start_wird)
        kb.addWidget(self.khatma_banner_label)
        kb.addWidget(btn_continue)
        self.khatma_banner.hide()
        wrap_banner = QWidget()
        wl = QVBoxLayout(wrap_banner)
        wl.setContentsMargins(12, 0, 12, 0)
        wl.setSpacing(8)
        wl.addWidget(self.khatma_banner)
        wl.addWidget(self.update_banner)
        sl.addWidget(wrap_banner)
        sl.addStretch(1)
        self.btn_sidebar_update = QPushButton('التحديثات')
        self.btn_sidebar_update.setIcon(svg_icon('update'))
        self.btn_sidebar_update.setIconSize(QSize(22, 22))
        self.btn_sidebar_update.setObjectName('nav')
        self.btn_sidebar_update.setToolTip('فحص وتنزيل تحديثات سراج')
        self.btn_sidebar_update.clicked.connect(self.open_updates)
        sl.addWidget(self.btn_sidebar_update)
        b = QPushButton('الإعدادات')
        b.setIcon(svg_icon('settings'))
        b.setIconSize(QSize(22, 22))
        b.setObjectName('nav')
        b.setCheckable(True)
        b.clicked.connect(lambda: self.show_view('settings'))
        self.nav_group.addButton(b)
        self.nav_buttons['settings'] = b
        self.nav_labels['settings'] = 'الإعدادات'
        b.setToolTip('الإعدادات')
        sl.addWidget(b)
        row.addWidget(side)

        right = QWidget()
        self.content_layout = QVBoxLayout(right)
        rl = self.content_layout
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
        self._apply_responsive_layout()

    def _apply_responsive_layout(self):
        """يوسّع قارئ حفص مع إبقاء كل أقسام سراج متاحة من أيقوناتها."""
        if not hasattr(self, 'sidebar'):
            return
        reader_wide = (
            hasattr(self, 'stack')
            and self.stack.currentWidget() is self.views.get('reader')
            and self.riwaya_id.startswith('quran-')
        )
        compact = self.width() < 1120 or reader_wide
        self.sidebar.setFixedWidth(76 if compact else 248)
        self.brand_label.setText('سراج' if compact else APP_NAME_AR)
        self.brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter if compact else Qt.AlignmentFlag.AlignRight)
        self.brand_sub.setVisible(not compact)
        for key, button in self.nav_buttons.items():
            button.setText('' if compact else self.nav_labels[key])
            button.setMinimumHeight(44 if compact else 40)
        self.btn_sidebar_update.setText('' if compact else 'التحديثات')
        self.btn_sidebar_update.setMinimumHeight(44 if compact else 40)
        margin = 12 if self.width() < 920 or reader_wide else 26
        self.content_layout.setContentsMargins(margin, 14, margin, 12)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def show_view(self, name):
        self.stack.setCurrentWidget(self.views[name])
        self.nav_buttons[name].setChecked(True)
        fade_in(self.views[name])
        if name == 'reader':
            self.sync_index()
            self.schedule_reading_record()
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
        self._apply_responsive_layout()

    # ---------- المصحف ----------
    def build_reader(self):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)

        # الفهرس قابل للفتح عند الحاجة حتى تبقى صفحة حفص بعرض واسع مثل الشاملة.
        self.index_card = card()
        self.index_card.setFixedWidth(236)
        il = QVBoxLayout(self.index_card)
        il.setContentsMargins(14, 14, 14, 14)
        il.setSpacing(8)
        self.combo_surah = NoWheelComboBox()
        for s in SURAHS:
            self.combo_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.combo_surah.currentIndexChanged.connect(self.on_surah_index)
        self.combo_juz = NoWheelComboBox()
        for i in range(len(JUZ_START)):
            self.combo_juz.addItem(f'الجزء {ar(i + 1)}', i)
        self.combo_juz.currentIndexChanged.connect(self.on_juz)
        self.combo_ayah = NoWheelComboBox()
        self.combo_ayah.currentIndexChanged.connect(self.on_ayah)
        for title, combo in (('السورة', self.combo_surah), ('الجزء', self.combo_juz), ('الآية', self.combo_ayah)):
            lab = QLabel(title)
            lab.setObjectName('muted')
            il.addWidget(lab)
            il.addWidget(combo)
        il.addStretch(1)
        # يبقى فهرس الروايات الأخرى كما كان؛ الإخفاء الافتراضي خاص بعرض حفص الواسع.
        self.index_card.setVisible(not self.riwaya_id.startswith('quran-'))
        row.addWidget(self.index_card)

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(10)

        # شريط أعلى الصفحة: المشغل وزر العلامة وزر التفسير
        top = card()
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 8, 12, 8)
        tl.setSpacing(8)
        self.btn_index = QPushButton('☰  الفهرس')
        self.btn_index.clicked.connect(self.toggle_index_panel)
        self.btn_play = QPushButton('▶  تشغيل')
        self.btn_play.setObjectName('primary')
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_stop = QPushButton('إيقاف')
        self.btn_stop.clicked.connect(lambda: self.stop_play(''))
        self.reciter_combo = NoWheelComboBox()
        self.reciter_combo.setMinimumWidth(190)
        self.reciter_combo.currentIndexChanged.connect(self.on_reciter_change)
        self.play_surah = NoWheelComboBox()
        for s in SURAHS:
            self.play_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.play_surah.currentIndexChanged.connect(self.on_play_surah)
        self.play_from = NoWheelComboBox()
        self.play_from.setMinimumWidth(80)
        self.btn_mark = QPushButton('علامة')
        self.btn_mark.clicked.connect(self.toggle_bookmark)
        self.btn_tafsir = QPushButton('التفسير')
        self.btn_tafsir.clicked.connect(lambda: self.toggle_tafsir_panel())
        for wdg in (self.btn_index, self.btn_play, self.btn_stop, self.reciter_combo, self.play_surah, self.play_from):
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
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        self.tp_book = NoWheelComboBox()
        populate_tafsir_books(self.tp_book)
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
        self.tp_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tpl.addWidget(self.tp_browser, 1)
        self.tp_frame.hide()
        row.addWidget(self.tp_frame)

        self.populate_reciters()
        self.populate_play_from()
        return w

    def toggle_index_panel(self):
        """يفتح فهرس السورة/الجزء/الآية دون حجز عرض دائم من صفحة المصحف."""
        visible = not self.index_card.isVisible()
        self.index_card.setVisible(visible)
        self.btn_index.setText('إغلاق الفهرس' if visible else '☰  الفهرس')

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

    def _sync_tafsir_book(self, edition, source_name):
        if not edition:
            return
        self.settings.setValue('tafsir', edition)
        for name in ('tp_book', 'tf_book'):
            combo = getattr(self, name, None)
            if combo is None or name == source_name or combo.currentData() == edition:
                continue
            index = combo.findData(edition)
            if index >= 0:
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)

    def _offline_tafsir_text(self, key):
        handled, text = self.offline_tafsir.lookup(key[0], key[1], key[2])
        if not handled:
            return False, None
        if not text:
            text = 'لا يوجد نص خاص بهذه الآية في هذا الكتاب؛ فالمصدر لا يغطي جميع الآيات.'
        self.tafsir_cache[key] = text
        return True, text

    def _tafsir_source_footer(self, edition):
        t = THEMES[self.theme_name]
        if str(edition).startswith('qp:'):
            meta = TAFSIR_METADATA.get(edition, {})
            detail = (
                'الموسوعة القرآنية Quranpedia.net · '
                f"نسخة بيانات الكتب {TAFSIR_CATALOG['selection']['book_dump_version']} · "
                f"{html.escape(str(meta.get('author', '')))}"
            )
        else:
            detail = 'AlQuran Cloud · لقطة محلية موثقة ٢٠٢٦-١٠-٢٨'
        return (
            f'<hr><p style="font-family:\'Noto Sans Arabic\'; font-size:10pt; '
            f'line-height:150%; color:{t["muted"]};">المصدر الرقمي: {detail}. '
            'النص مدمج محليًا للعمل دون إنترنت ويُعرض دون تغيير في المحتوى.</p>'
        )

    def _tafsir_document(self, inner):
        family = html.escape(self.mushaf_font, quote=True)
        return (
            f"<html><body dir=\"rtl\" style=\"font-family:'{family}'; "
            f'font-size:{self.font_pt}pt; line-height:185%; margin:10px;\">{inner}</body></html>'
        )

    def _tafsir_text_html(self, text):
        return html.escape(str(text)).replace('\n', '<br>')

    def on_tp_book(self, _idx):
        edition = self.tp_book.currentData()
        self._sync_tafsir_book(edition, 'tp_book')
        self.load_tp()

    def load_tp(self):
        if self.sel_ayah is None:
            return
        s, a = self.sel_ayah
        edition = self.tp_book.currentData()
        if not edition:
            return
        key = (edition, s, a)
        self.tp_key = key
        self.tp_title.setText(f'{SURAHS[s - 1]["name"]} · الآية {ar(a)}')
        if key in self.tafsir_cache:
            self.show_tp(self.tafsir_cache[key], key)
            return
        handled, text = self._offline_tafsir_text(key)
        if handled:
            self.show_tp(text, key)
            return
        self.tp_browser.setHtml(self._tafsir_document('<p align="center">جارٍ تحميل التفسير…</p>'))
        reply = self.nam.get(tafsir_request(edition, s, a))
        reply.finished.connect(lambda: self.on_tp_reply(reply, key))

    def on_tp_reply(self, reply, key):
        text = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                payload = json.loads(bytes(reply.readAll()).decode('utf-8'))
                text = parse_tafsir_payload(key[0], payload)
            except (ValueError, TypeError, UnicodeDecodeError):
                text = None
        reply.deleteLater()
        if text is None:
            if key == getattr(self, 'tp_key', None):
                self.tp_browser.setHtml(
                    self._tafsir_document('<p align="center">تعذّر تحميل التفسير؛ تحقّق من الاتصال.</p>')
                )
            return
        self.tafsir_cache[key] = text
        if key == getattr(self, 'tp_key', None):
            self.show_tp(text, key)

    def show_tp(self, text, key=None):
        key = key or getattr(self, 'tp_key', None)
        edition = key[0] if key else self.tp_book.currentData()
        body = f'<p style="margin:0;">{self._tafsir_text_html(text)}</p>'
        self.tp_browser.setHtml(self._tafsir_document(body + self._tafsir_source_footer(edition)))

    def populate_reciters(self):
        self.reciter_combo.blockSignals(True)
        self.reciter_combo.clear()
        for rid, name in self.reciter_options():
            self.reciter_combo.addItem(name, rid)
        saved = self.settings.value(f'reciter:{self.riwaya_id}', '', type=str)
        idx = self.reciter_combo.findData(saved)
        self.reciter_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.reciter_combo.setToolTip(f'{ar(self.reciter_combo.count())} قارئاً متاحاً للرواية المختارة')
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
        self.render_page()
        self.sync_index()
        self.schedule_reading_record()

    def render_page(self):
        page = self.page
        items = self.book.ayahs_on_page(page)
        t = THEMES[self.theme_name]
        fs = self.font_pt
        is_hafs = self.riwaya_id.startswith('quran-')
        shamela_color = '#8b3028' if self.theme_name == 'light' else '#e2aaa1'
        flow_line_height = 125 if is_hafs else 150
        reader_text = t['text']
        if is_hafs:
            paper = '#f5f0dc' if self.theme_name == 'light' else '#211f17'
            reader_text = '#19140e' if self.theme_name == 'light' else '#f2ecdd'
            self.browser.setStyleSheet(
                f'background:{paper}; color:{reader_text}; border:none; border-radius:0; padding:0; '
                f'selection-background-color:{t["brand"]}; selection-color:#ffffff;'
            )
        else:
            self.browser.setStyleSheet('')
        out = []
        flow = []

        def flush():
            if flow:
                out.append(
                    f'<p align="center" dir="rtl" style="margin:0; padding:0; '
                    f'line-height:{flow_line_height}%;">' + ''.join(flow) + '</p>'
                )
                flow.clear()

        last = None
        for s, a, raw_text in items:
            if a == 1 and s != last:
                flush()
                if is_hafs:
                    title = f'[{norm(SURAHS[s - 1]["name"])}]'
                    out.append(
                        f'<p align="center" style="margin:5px 0 1px 0; padding:0; '
                        f'font-size:{max(fs - 3, 14)}pt; line-height:115%; font-weight:bold; '
                        f'color:{shamela_color};">{html.escape(title)}</p>'
                    )
                else:
                    out.append(
                        f'<p align="center" style="margin:10px 0 0 0; font-size:{fs + 6}pt; '
                        f'font-weight:bold; color:{t["brand"]};">'
                        f'{html.escape(SURAHS[s - 1]["name"])}</p>'
                    )
                hafs_fatiha = s == 1 and is_hafs
                if s != 9 and not hafs_fatiha:
                    bism_color = shamela_color if is_hafs else t['text']
                    out.append(
                        f'<p align="center" dir="rtl" style="margin:0 0 2px 0; padding:0; '
                        f'line-height:115%; font-size:{fs}pt; color:{bism_color};">{BASMALA}</p>'
                    )
                last = s

            text = display_ayah_text(s, a, raw_text, is_hafs)
            if not text:
                continue
            if self.highlight == (s, a):
                style = f'background-color:{t["brand"]}; color:#ffffff;'
            elif self.sel_ayah == (s, a):
                style = f'background-color:{t["hover"]};'
            else:
                style = ''
            marker = f'۝{ar(a)}' if is_hafs else f'﴿{ar(a)}﴾'
            marker_color = shamela_color if is_hafs else t['brand']
            marker_size = max(fs - 6, 11) if is_hafs else max(fs - 9, 10)
            flow.append(
                f'<a href="ayah:{s}:{a}" style="text-decoration:none; color:{reader_text};">'
                f'<span style="{style}">{html.escape(text)}</span>'
                f"<span style=\"font-family:'Amiri Quran','Amiri'; font-size:{marker_size}pt; "
                f'color:{marker_color};"> {marker}</span></a>&nbsp;'
            )
        flush()
        body = ''.join(out) or '<p align="center">لا توجد آيات في هذه الصفحة</p>'
        if is_hafs:
            body = (
                f'<table width="100%" border="1" cellspacing="0" cellpadding="12" '
                f'style="border:1px solid {shamela_color}; border-collapse:collapse;">'
                f'<tr><td>{body}</td></tr></table>'
            )
        bar = self.browser.verticalScrollBar()
        pos = bar.value()
        page_changed = self._rendered_page != page
        family = html.escape(self.mushaf_font, quote=True)
        self.browser.setHtml(
            f"<html><body dir=\"rtl\" style=\"font-family:'{family}'; font-size:{fs}pt; "
            f'line-height:{flow_line_height}%; margin:0; padding:0; color:{reader_text};">{body}</body></html>'
        )
        # الصفحة الجديدة تبدأ دائمًا من أعلاها؛ إعادة رسم الصفحة نفسها (تحديد
        # آية/تغيير حجم أو ثيم) لا تقطع موضع القراءة الحالي.
        bar.setValue(bar.minimum() if page_changed else pos)
        self._rendered_page = page
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
        self.refresh_tafsir_typography()

    def set_mushaf_font(self, _index=None):
        if not hasattr(self, 'mushaf_font_combo'):
            return
        family = self.mushaf_font_combo.currentData()
        if family:
            self.mushaf_font = family
            self.settings.setValue('mushaf_font', family)
            self.render_page()
            self.refresh_tafsir_typography()

    def refresh_tafsir_typography(self):
        tf_key = getattr(self, 'tf_key', None)
        if tf_key in self.tafsir_cache and hasattr(self, 'tf_browser'):
            self.show_tafsir(self.tafsir_cache[tf_key], tf_key)
        tp_key = getattr(self, 'tp_key', None)
        if tp_key in self.tafsir_cache and hasattr(self, 'tp_browser'):
            self.show_tp(self.tafsir_cache[tp_key], tp_key)

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
            self.update_memo_audio_controls()
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
        self.update_memo_audio_controls()
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
        show_index = not rid.startswith('quran-')
        self.index_card.setVisible(show_index)
        self.btn_index.setText('إغلاق الفهرس' if show_index else '☰  الفهرس')
        self.populate_reciters()
        self._apply_responsive_layout()
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
        self.tf_surah = NoWheelComboBox()
        for s in SURAHS:
            self.tf_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.tf_surah.currentIndexChanged.connect(self.on_tf_surah)
        self.tf_ayah = NoWheelSpinBox()
        self.tf_ayah.setRange(1, 286)
        self.tf_ayah.valueChanged.connect(lambda _v: self.load_tafsir())
        self.tf_book = NoWheelComboBox()
        populate_tafsir_books(self.tf_book)
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
        self.tf_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        edition = self.tf_book.currentData()
        self._sync_tafsir_book(edition, 'tf_book')
        self.load_tafsir()

    def _tafsir_head(self, surah, ayah):
        t = THEMES[self.theme_name]
        return (
            f'<p align="center" style="font-size:{min(self.font_pt + 6, 50)}pt; line-height:175%; '
            f'margin:4px 0 2px;">{html.escape(AYAH_TEXT.get((surah, ayah), ""))} '
            f'<span style="font-size:{max(self.font_pt - 2, 11)}pt; color:{t["brand"]};">'
            f'﴿{ar(ayah)}﴾</span></p><p align="center" style="font-family:\'Noto Sans Arabic\'; '
            f'font-size:11pt; color:{t["muted"]}; margin:0 0 12px;">'
            f'{html.escape(SURAHS[surah - 1]["name"])} · الآية {ar(ayah)}</p>'
        )

    def load_tafsir(self):
        if not hasattr(self, 'tf_ayah'):
            return
        s = self.tf_surah.currentData() or 1
        a = self.tf_ayah.value()
        edition = self.tf_book.currentData()
        if not edition:
            return
        key = (edition, s, a)
        self.tf_key = key
        head = self._tafsir_head(s, a)
        if key in self.tafsir_cache:
            self.show_tafsir(self.tafsir_cache[key], key)
            return
        handled, text = self._offline_tafsir_text(key)
        if handled:
            self.show_tafsir(text, key)
            return
        self.tf_browser.setHtml(
            self._tafsir_document(head + '<p align="center">جارٍ تحميل التفسير…</p>')
        )
        reply = self.nam.get(tafsir_request(edition, s, a))
        reply.finished.connect(lambda: self.on_tafsir_reply(reply, key))

    def on_tafsir_reply(self, reply, key):
        text = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                payload = json.loads(bytes(reply.readAll()).decode('utf-8'))
                text = parse_tafsir_payload(key[0], payload)
            except (ValueError, TypeError, UnicodeDecodeError):
                text = None
        reply.deleteLater()
        if text is None:
            if key == getattr(self, 'tf_key', None):
                head = self._tafsir_head(key[1], key[2])
                self.tf_browser.setHtml(
                    self._tafsir_document(
                        head + '<p align="center">تعذّر تحميل التفسير؛ تحقّق من الاتصال.</p>'
                    )
                )
            return
        self.tafsir_cache[key] = text
        if key == getattr(self, 'tf_key', None):
            self.show_tafsir(text, key)

    def show_tafsir(self, text, key=None):
        key = key or getattr(self, 'tf_key', None)
        if key is None:
            return
        edition, surah, ayah = key
        label = dict(ALL_TAFSIR_EDITIONS).get(edition, self.tf_book.currentText())
        body = (
            self._tafsir_head(surah, ayah)
            + f'<h3 style="margin:8px 0;">{html.escape(label)}</h3>'
            + f'<p style="margin:0;">{self._tafsir_text_html(text)}</p>'
            + self._tafsir_source_footer(edition)
        )
        self.tf_browser.setHtml(self._tafsir_document(body))

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
        self.mn_combo = NoWheelComboBox()
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
            text_box = QVBoxLayout()
            text = QLabel(it['text'])
            text.setWordWrap(True)
            text.setStyleSheet("font-family: 'Amiri Quran'; font-size: 19px; line-height: 170%;")
            text_box.addWidget(text)
            references = [ev.get('reference', '') for ev in it.get('evidence', []) if ev.get('reference')]
            if references:
                source = QLabel('المصدر: ' + '؛ '.join(references))
                source.setWordWrap(True)
                source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                source.setStyleSheet('font-size: 11px; color: #6f756f;')
                text_box.addWidget(source)
            btn = QPushButton(f'{ar(n)} / {ar(it["count"])}')
            btn.setMinimumWidth(110)
            btn.clicked.connect(lambda _c=False, k=key, mx=it['count'], b=btn: self.bump_adhkar(k, mx, b))
            row.addLayout(text_box, 1)
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
        self.memo_surah = NoWheelComboBox()
        for s in SURAHS:
            self.memo_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        self.memo_from = NoWheelComboBox()
        self.memo_to = NoWheelComboBox()
        self.memo_repeat = NoWheelComboBox()
        for n in (1, 3, 5, 10):
            self.memo_repeat.addItem(ar(n), n)
        self.memo_repeat.setCurrentIndex(1)
        self.memo_level = NoWheelComboBox()
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
        self.btn_memo_play = QPushButton('▶ تشغيل مع التكرار')
        self.btn_memo_play.setObjectName('primary')
        self.btn_memo_play.clicked.connect(self.memo_play)
        self.btn_memo_pause = QPushButton('⏸ إيقاف مؤقت')
        self.btn_memo_pause.clicked.connect(self.memo_pause_resume)
        self.btn_memo_stop = QPushButton('■ إيقاف كامل')
        self.btn_memo_stop.clicked.connect(self.memo_stop)
        btn_save = QPushButton('حفظت هذا المقطع')
        btn_save.clicked.connect(self.memo_save_range)
        for b in (btn_hide, self.btn_memo_play, self.btn_memo_pause, self.btn_memo_stop, btn_save):
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
        self.update_memo_audio_controls()
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
        self.memo_status.setText('جارٍ تشغيل مقطع الحفظ')
        self.update_memo_audio_controls()
        self.play_index(0)

    def memo_pause_resume(self):
        if not self.playing or not self.queue_list:
            return
        if self.engine.paused:
            self.engine.resume()
            self.btn_play.setText('⏸  إيقاف مؤقت')
            self.memo_status.setText('تم استئناف التلاوة')
        else:
            self.engine.pause()
            self.btn_play.setText('▶  متابعة')
            self.memo_status.setText('التلاوة متوقفة مؤقتاً')
        self.update_memo_audio_controls()

    def memo_stop(self):
        if not self.playing or not self.queue_list:
            return
        self.stop_play('')
        self.memo_status.setText('تم إيقاف تلاوة الحفظ بالكامل')
        self.update_memo_audio_controls()

    def update_memo_audio_controls(self):
        if not hasattr(self, 'btn_memo_pause'):
            return
        active = bool(self.playing and self.queue_list)
        self.btn_memo_play.setEnabled(not active)
        self.btn_memo_pause.setEnabled(active)
        self.btn_memo_stop.setEnabled(active)
        paused = active and self.engine.paused
        self.btn_memo_pause.setText('▶ استئناف' if paused else '⏸ إيقاف مؤقت')

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
        self.dl_reciter = NoWheelComboBox()
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
        self.dl_surah = NoWheelComboBox()
        for s in SURAHS:
            self.dl_surah.addItem(f'{s["number"]}. {s["name"]}', s['number'])
        scope = QHBoxLayout()
        for widget in (self.dl_full, self.dl_one, self.dl_surah):
            scope.addWidget(widget)
        scope_w = QWidget()
        scope_w.setLayout(scope)
        self.dl_target = NoWheelComboBox()
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

    # ---------- متابعة الختمة التلقائية ----------
    def build_wird(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(heading('متابعة الختمة', 'يسجل سراج القراءة تلقائياً ولا يفرض عدداً يومياً'))

        progress_card = card()
        pl = QVBoxLayout(progress_card)
        pl.setContentsMargins(20, 18, 20, 18)
        self.wird_text = QLabel()
        self.wird_text.setWordWrap(True)
        self.wird_text.setStyleSheet('font-size: 18px; font-weight: 600;')
        self.khatma_progress_bar = QProgressBar()
        self.khatma_progress_bar.setRange(0, TOTAL_PAGES)
        self.khatma_progress_bar.setTextVisible(True)
        self.khatma_habits = QLabel()
        self.khatma_habits.setWordWrap(True)
        self.khatma_habits.setObjectName('muted')
        pl.addWidget(self.wird_text)
        pl.addWidget(self.khatma_progress_bar)
        pl.addWidget(self.khatma_habits)
        lay.addWidget(progress_card)

        row = QHBoxLayout()
        self.btn_wird_read = QPushButton('📖 متابعة الختمة')
        self.btn_wird_read.setObjectName('primary')
        self.btn_wird_read.clicked.connect(self.start_wird)
        self.khatma_page = NoWheelSpinBox()
        self.khatma_page.setRange(1, TOTAL_PAGES)
        self.khatma_page.setPrefix('صفحة المتابعة: ')
        self.btn_khatma_set = QPushButton('تصحيح الموضع')
        self.btn_khatma_set.clicked.connect(self.set_khatma_page)
        self.btn_wird_reset = QPushButton('↺ بدء ختمة جديدة')
        self.btn_wird_reset.clicked.connect(self.reset_wird)
        row.addWidget(self.btn_wird_read)
        row.addWidget(self.khatma_page)
        row.addWidget(self.btn_khatma_set)
        row.addWidget(self.btn_wird_reset)
        row.addStretch(1)
        lay.addLayout(row)

        reminder_card = card()
        rf = QFormLayout(reminder_card)
        rf.setContentsMargins(20, 18, 20, 18)
        enabled, when = reminder_config(self.settings)
        self.reminder_enabled = QCheckBox('تنبيه داخل التطبيق وإشعار النظام')
        self.reminder_enabled.setChecked(enabled)
        self.reminder_time = NoWheelTimeEdit()
        self.reminder_time.setDisplayFormat('HH:mm')
        self.reminder_time.setTime(QTime.fromString(valid_time(when), 'HH:mm'))
        self.reminder_status = QLabel(self.settings.value('reminder/system_status', '', type=str))
        self.reminder_status.setObjectName('muted')
        self.reminder_status.setWordWrap(True)
        self.reminder_enabled.toggled.connect(self.on_reminder_settings)
        self.reminder_time.timeChanged.connect(lambda _value: self.on_reminder_settings())
        rf.addRow('التذكير', self.reminder_enabled)
        rf.addRow('وقت التذكير اليومي', self.reminder_time)
        rf.addRow('', self.reminder_status)
        lay.addWidget(reminder_card)

        note = QLabel('تُسجّل الصفحة تلقائياً بعد بقائها معروضة ١٠ ثوانٍ. الانتقال إلى نتيجة بعيدة لا يتخطى صفحات الختمة غير المقروءة.')
        note.setWordWrap(True)
        note.setObjectName('muted')
        lay.addWidget(note)
        lay.addStretch(1)
        return w

    def render_wird(self):
        info = khatma_progress(self.settings, self.page)
        pointer = info['pointer']
        self.khatma_page.blockSignals(True)
        self.khatma_page.setValue(pointer)
        self.khatma_page.blockSignals(False)
        self.khatma_progress_bar.setValue(info['read'])
        self.khatma_progress_bar.setFormat(f'{ar(info["read"])} من {ar(TOTAL_PAGES)} — {ar(f"{info["percent"]:.1f}")}%')
        self.wird_text.setText(
            f'صفحة المتابعة التالية: {ar(pointer)} · المتبقي {ar(info["left"])} صفحة · '
            f'الختمات المكتملة: {ar(len(info["finished"]))}'
        )
        today = reading_count(self.settings)
        average = habit_average(self.settings)
        streak = reading_streak(self.settings)
        finish = estimated_finish(self.settings, self.page)
        estimate = finish.strftime('%Y-%m-%d').translate(ARABIC_DIGITS) if finish else 'يُحسب بعد بدء القراءة'
        avg_text = f'{average:.1f}'.translate(ARABIC_DIGITS) if average else '—'
        self.khatma_habits.setText(
            f'المسجّل اليوم: {ar(today)} صفحة · متوسط عادتك في أيام القراءة: {avg_text} صفحة · '
            f'السلسلة: {ar(streak)} يوم · الإتمام المتوقع حسب عادتك: {estimate}'
        )

    def start_wird(self):
        pointer = khatma_progress(self.settings, self.page)['pointer']
        self.go_page(pointer)
        self.show_view('reader')
        self.schedule_reading_record()
        if hasattr(self, 'khatma_banner'):
            self.khatma_banner.hide()

    def set_khatma_page(self):
        set_khatma_pointer(self.settings, self.khatma_page.value())
        self.render_wird()
        self.statusBar().showMessage('تم تصحيح موضع متابعة الختمة', 4000)

    def reset_wird(self):
        answer = QMessageBox.question(
            self, 'بدء ختمة جديدة',
            'هل تريد بدء ختمة جديدة من الصفحة الأولى؟ لن تُحذف إحصاءات القراءة السابقة.'
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        start_new_khatma(self.settings)
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

    # ---------- تتبّع القراءة والإحصائيات ----------
    def days(self):
        return reading_counts(self.settings)

    def schedule_reading_record(self):
        if not hasattr(self, 'reading_timer'):
            return
        self.reading_pending_page = self.page
        self.reading_timer.start()

    def count_page_visit(self):
        return self.commit_reading_page()

    def commit_reading_page(self):
        page = int(getattr(self, 'reading_pending_page', self.page))
        if page != self.page or self.stack.currentWidget() is not self.views.get('reader'):
            return None
        result = record_reading(self.settings, page)
        if result.get('completed'):
            self.statusBar().showMessage('تمت الختمة، بارك الله فيك. بدأت متابعة ختمة جديدة.', 9000)
        if hasattr(self, 'khatma_banner'):
            self.khatma_banner.hide()
        if hasattr(self, 'wird_text'):
            self.render_wird()
        return result

    def streak(self, _days=None):
        return reading_streak(self.settings)

    def initialize_reminders(self):
        enabled, when = reminder_config(self.settings)
        ok, message = configure_system_reminder(enabled, when)
        self.settings.setValue('reminder/system_status', message)
        self.settings.sync()
        if not ok:
            self.statusBar().showMessage('تعذّرت جدولة إشعار النظام؛ سيبقى التنبيه داخل التطبيق.', 7000)
        self.update_khatma_reminder()

    def update_khatma_reminder(self):
        if not hasattr(self, 'khatma_banner'):
            return
        enabled, when = reminder_config(self.settings)
        now = datetime.datetime.now()
        due = now.strftime('%H:%M') >= when
        if enabled and due and reading_count(self.settings) == 0:
            pointer = khatma_progress(self.settings, self.page)['pointer']
            self.khatma_banner_label.setText(f'حان وقت متابعة ختمتك من صفحة {ar(pointer)}')
            self.khatma_banner.show()
        else:
            self.khatma_banner.hide()

    def on_reminder_settings(self):
        enabled = self.reminder_enabled.isChecked()
        when = self.reminder_time.time().toString('HH:mm')
        save_reminder_config(self.settings, enabled, when)
        ok, message = configure_system_reminder(enabled, when)
        self.reminder_status.setText(message if ok else 'تعذّرت جدولة النظام؛ التنبيه داخل التطبيق ما زال متاحاً')
        self.update_khatma_reminder()

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
                             ('bookmarks', 'صفحات محفوظة'), ('wird', 'ختمات مكتملة')):
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
        self.st_cards['wird'].setText(ar(len(khatma_progress(self.settings, self.page)['finished'])))

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
        self.theme_combo = NoWheelComboBox()
        self.theme_combo.addItem('فاتح', 'light')
        self.theme_combo.addItem('داكن', 'dark')
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(self.theme_name))
        self.theme_combo.currentIndexChanged.connect(self.on_theme_change)
        self.font_spin = NoWheelSpinBox()
        self.font_spin.setRange(14, 44)
        self.font_spin.setValue(self.font_pt)
        self.font_spin.valueChanged.connect(self.set_font)
        self.mushaf_font_combo = NoWheelComboBox()
        available = set(QFontDatabase.families())
        for family, label in MUSHAF_FONTS:
            if family in available:
                self.mushaf_font_combo.addItem(label, family)
        if not self.mushaf_font_combo.count():
            self.mushaf_font_combo.addItem('أميري قرآن — الافتراضي', 'Amiri Quran')
        font_index = self.mushaf_font_combo.findData(self.mushaf_font)
        self.mushaf_font_combo.setCurrentIndex(font_index if font_index >= 0 else 0)
        self.mushaf_font_combo.currentIndexChanged.connect(self.set_mushaf_font)
        f1.addRow('الوضع', self.theme_combo)
        f1.addRow('خط المصحف والتفسير', self.mushaf_font_combo)
        f1.addRow('حجم خط المصحف والتفسير', self.font_spin)
        lay.addWidget(c1)

        c2 = card()
        f2 = QFormLayout(c2)
        f2.setContentsMargins(20, 18, 20, 18)
        self.riwaya_combo = NoWheelComboBox()
        for rid, name in HAFS_EDITIONS + OTHER_RIWAYAT:
            self.riwaya_combo.addItem(name, rid)
        self.riwaya_combo.setCurrentIndex(self.riwaya_combo.findData(self.riwaya_id))
        self.riwaya_combo.currentIndexChanged.connect(self.on_riwaya)
        f2.addRow('الرواية والرسم', self.riwaya_combo)
        lay.addWidget(c2)

        c3 = card()
        cl3 = QVBoxLayout(c3)
        cl3.setContentsMargins(20, 18, 20, 18)
        about = QLabel(f'{APP_NAME_AR} {APP_VERSION} — {APP_DESCRIPTION_AR}')
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
        answer = QMessageBox.question(self, 'تأكيد', 'مسح الإحصائيات والمحفوظات وتتبع الختمة والأذكار؟')
        if answer != QMessageBox.StandardButton.Yes:
            return
        clear_tracking(self.settings)
        for key in ('bookmarks', 'adhkar'):
            self.settings.remove(key)
        self.settings.sync()
        self.render_page()
        if hasattr(self, 'wird_text'):
            self.render_wird()

    def apply_theme(self):
        self.setStyleSheet(qss(THEMES[self.theme_name]))
        self.render_page()
        self.refresh_tafsir_typography()

    def open_updates(self):
        """يجعل التحديث ظاهرًا من الشريط الجانبي ويفتح فحص القناة الموقّعة مباشرةً."""
        self.show_view('settings')
        self.upd_status.setText('جارٍ فحص تحديثات سراج…')
        QTimer.singleShot(0, lambda: self.check_updates(manual=True))

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
            self.upd_status.setText('جارٍ التحقق من الترقيعات الداخلية الموقّعة…')
        req = QNetworkRequest(QUrl(f'{PATCH_MANIFEST}?t={int(time.time())}'))
        req.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                         QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self._patch_update_checked(reply, manual))

    def _patch_update_checked(self, reply, manual):
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        data = bytes(reply.readAll()) if ok else b''
        reply.deleteLater()
        try:
            manifest = json.loads(data.decode('utf-8')) if data else {}
        except (ValueError, UnicodeError):
            manifest = {}
        available = manifest.get('available') is True
        try:
            runtime_api = int(manifest.get('runtime_api', -1))
        except (TypeError, ValueError):
            runtime_api = -1
        signature_ok = bool(available and verify_update_manifest(manifest, UPDATE_PUBLIC_KEY))
        newer = version_tuple(manifest.get('version')) > version_tuple(APP_VERSION)
        valid = bool(
            signature_ok
            and manifest.get('schema') == 1
            and manifest.get('kind') == 'siraj-patch-channel'
            and manifest.get('product') == 'siraj-quran-linux'
            and manifest.get('channel') == 'stable'
            and runtime_api == RUNTIME_API
            and newer
        )
        asset = (manifest.get('assets') or {}).get('patch') if valid else None
        if isinstance(asset, dict):
            url = str(asset.get('url', ''))
            digest = str(asset.get('sha256', '')).lower()
            try:
                size = int(asset.get('size', 0) or 0)
            except (TypeError, ValueError):
                size = 0
            valid = bool(
                url.startswith('https://github.com/')
                and url.split('?', 1)[0].lower().endswith('.sirajpatch')
                and re.fullmatch(r'[0-9a-f]{64}', digest)
                and 1000 < size <= 128 * 1024 * 1024
            )
        else:
            valid = False
        if valid:
            self.update_busy = False
            self.update_info = {
                'kind': 'patch', 'version': str(manifest['version']), 'asset': asset,
                'notes': manifest.get('release_notes', ''),
            }
            self.update_banner_label.setText(f'يتوفر ترقيع داخلي صغير {manifest["version"]}')
            self.update_banner.show()
            self.upd_status.setText(f'الترقيع {manifest["version"]} متاح — توقيعه صالح')
            self.btn_check_update.setText('تنزيل الترقيع الداخلي')
            return
        if available and (not signature_ok or runtime_api != RUNTIME_API):
            self.update_busy = False
            self.update_info = None
            if manual:
                self.upd_status.setText('رُفضت قناة الترقيع: التوقيع أو توافق المحرك غير صحيح')
            return
        self._request_full_update(manual)

    def _request_full_update(self, manual):
        if manual:
            self.upd_status.setText('لا يوجد ترقيع أحدث؛ جارٍ فحص التحديثات الكبيرة…')
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
            manifest = json.loads(data.decode('utf-8')) if data else {}
        except (ValueError, TypeError, AttributeError, UnicodeError):
            manifest = {}
        info = validated_update_info(manifest)
        newer = bool(info and version_tuple(info['version']) > version_tuple(APP_VERSION))
        if newer:
            self.update_info = {'kind': 'full', **info}
            self.update_banner_label.setText(f'يتوفر تحديث كبير {info["version"]}')
            self.update_banner.show()
            self.upd_status.setText(f'الإصدار {info["version"]} متاح — حزمة كاملة موقّعة')
            self.btn_check_update.setText('تحميل التحديث الكبير')
            return
        self.update_info = None
        self.update_banner.hide()
        self.btn_check_update.setText('تحقق من التحديث')
        if manual:
            if manifest.get('available') is True and not verify_update_manifest(manifest, UPDATE_PUBLIC_KEY):
                self.upd_status.setText('رُفضت قناة التحديث: التوقيع الرقمي غير صحيح')
            else:
                self.upd_status.setText('أنت على أحدث نسخة' if ok and manifest else 'تعذّر الاتصال بالمستودع')

    def download_update(self):
        info = dict(self.update_info)
        kind = info.get('kind', 'full')
        asset = dict(info.get('asset') or {}) if kind == 'patch' else info
        url = str(asset.get('url', ''))
        file_name = Path(asset.get('file_name') or QUrl(url).fileName()).name
        if kind == 'patch':
            valid_name = file_name.lower().endswith('.sirajpatch')
            root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
            target_dir = Path(root or Path.home() / '.cache' / 'siraj') / 'updates'
        else:
            valid_name = re.fullmatch(r'Siraj-Quran-[0-9A-Za-z.-]+-linux-x86_64\.AppImage', file_name) is not None
            target_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
                              or Path.home() / 'Downloads')
        if not valid_name:
            self.upd_status.setText('رابط التحديث غير صالح')
            return
        target_dir.mkdir(parents=True, exist_ok=True)
        self.upd_target = target_dir / file_name
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        temp = self.upd_target.with_suffix(self.upd_target.suffix + '.part')
        temp.unlink(missing_ok=True)
        try:
            stream = temp.open('wb')
        except OSError as exc:
            self.upd_status.setText('تعذّر إنشاء ملف التنزيل المؤقت')
            self.statusBar().showMessage(str(exc), 7000)
            return
        reply = self.nam.get(req)
        # لا تسمح لـQt بتجميع الحزمة الكبيرة كاملة في الذاكرة؛ نفرّغها إلى القرص تدريجيًا.
        reply.setReadBufferSize(1024 * 1024)
        self.upd_stream = {
            'reply': reply,
            'file': stream,
            'temp': temp,
            'hasher': hashlib.sha256(),
            'size': 0,
            'write_error': None,
        }
        reply.readyRead.connect(lambda: self._update_ready_read(reply))
        reply.downloadProgress.connect(self._update_progress)
        reply.finished.connect(lambda: self._update_downloaded(reply, info, asset))
        self.upd_status.setText('جارٍ تنزيل الترقيع…' if kind == 'patch' else 'جارٍ تنزيل التحديث الكبير…')
        self.btn_check_update.setEnabled(False)

    def _update_ready_read(self, reply):
        state = self.upd_stream
        if not state or state.get('reply') is not reply or state.get('write_error'):
            return
        chunk = bytes(reply.readAll())
        if not chunk:
            return
        try:
            written = state['file'].write(chunk)
            if written != len(chunk):
                raise OSError('short write while saving update')
            state['hasher'].update(chunk)
            state['size'] += len(chunk)
        except OSError as exc:
            state['write_error'] = exc
            reply.abort()

    def _update_progress(self, got, total):
        if total > 0:
            self.upd_status.setText(f'جارٍ التنزيل… {got * 100 // total}%')

    def _update_downloaded(self, reply, info, asset):
        state = self.upd_stream
        self.upd_stream = None
        self.btn_check_update.setEnabled(True)
        if not state or state.get('reply') is not reply:
            reply.deleteLater()
            self.upd_status.setText('تعذّر تتبع ملف التحديث المؤقت')
            return
        self.upd_stream = state
        self._update_ready_read(reply)
        self.upd_stream = None
        try:
            state['file'].flush()
            os.fsync(state['file'].fileno())
        except OSError as exc:
            state['write_error'] = state.get('write_error') or exc
        finally:
            state['file'].close()
        ok = reply.error() == QNetworkReply.NetworkError.NoError and not state.get('write_error')
        reply.deleteLater()
        expected_size = int(asset.get('size', 0))
        expected_digest = str(asset.get('sha256', '')).lower()
        if not ok or state['size'] != expected_size or state['hasher'].hexdigest() != expected_digest:
            state['temp'].unlink(missing_ok=True)
            self.upd_status.setText('رُفض التحديث: تعذّر التنزيل أو الحجم أو SHA-256 غير صحيح')
            return
        temp = state['temp']
        if info.get('kind') == 'patch':
            temp.replace(self.upd_target)
            try:
                manifest = install_patch_archive(
                    self.upd_target,
                    product='siraj-quran-linux',
                    runtime_api=RUNTIME_API,
                    bundled_version=APP_VERSION,
                    public_key_path=UPDATE_PUBLIC_KEY,
                )
            except (OSError, ValueError) as exc:
                self.upd_target.unlink(missing_ok=True)
                self.upd_status.setText('رُفض الترقيع الداخلي: توقيعه أو ملفاته غير صحيحة')
                self.statusBar().showMessage(str(exc), 7000)
                return
            self.upd_target.unlink(missing_ok=True)
            self.upd_status.setText(f'ثُبّت الترقيع {manifest["version"]} بأمان؛ سيعمل بعد إعادة التشغيل')
            answer = QMessageBox.question(
                self, 'الترقيع جاهز',
                'اكتمل تثبيت الترقيع الصغير والتحقق من كل ملف. هل تريد إعادة تشغيل سراج الآن؟',
            )
            if answer == QMessageBox.StandardButton.Yes:
                executable = os.environ.get('APPIMAGE') or sys.executable
                subprocess.Popen([executable], close_fds=True)
                QApplication.quit()
            return
        temp.chmod(0o755)
        temp.replace(self.upd_target)
        self.upd_status.setText(f'تم تنزيل الحزمة الكبيرة والتحقق منها: {self.upd_target}')
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.upd_target.parent)))

    def closeEvent(self, event):  # noqa: N802
        state = self.upd_stream
        self.upd_stream = None
        if state:
            try:
                state['reply'].abort()
                state['file'].close()
            except (OSError, RuntimeError):
                pass
            state['temp'].unlink(missing_ok=True)
        self.offline_tafsir.close()
        self.settings.setValue('geometry', self.saveGeometry())
        super().closeEvent(event)


def _hard_exit(code):
    """إنهاء وضع الاختبار بعد طباعة النتيجة. على ويندوز TerminateProcess يتجاوز انهيار تحرير المكتبات وقت الإغلاق."""
    sys.stdout.flush()
    sys.stderr.flush()
    if sys.platform.startswith('win'):
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.GetCurrentProcess.argtypes = []
        k32.TerminateProcess.restype = wintypes.BOOL
        k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        if k32.TerminateProcess(k32.GetCurrentProcess(), code):
            os._exit(code)  # لا يُصل إليه عادةً: TerminateProcess ينهي العملية
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
        local_a, tafsir_a = win.offline_tafsir.lookup('ar.muyassar', 1, 1)
        local_b, tafsir_b = win.offline_tafsir.lookup('qp:301', 2, 255)
        info = {
            'page': win.page,
            'textLength': len(text),
            'surahs': win.combo_surah.count(),
            'reciters': win.reciter_combo.count(),
            'riwaya': win.riwaya_id,
            'hasMushaf': 'الفاتح' in text or '﴿' in text or 'ال' in text,
            'offlineTafsir': bool(local_a and tafsir_a and local_b and tafsir_b),
            'tafsirEditions': len(win.offline_tafsir.editions),
        }
        ok = (
            info['textLength'] > 200
            and info['surahs'] == 114
            and info['reciters'] >= 1
            and info['offlineTafsir']
            and info['tafsirEditions'] == len(ALL_TAFSIR_EDITIONS)
        )
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


def run_reminder_notification(app):
    settings = app_settings()
    enabled, _when = reminder_config(settings)
    if not enabled or reading_count(settings) > 0:
        return 0
    pointer = khatma_progress(settings, settings.value('page', 1, type=int))['pointer']
    title = 'سراج — متابعة الختمة'
    message = f'لم تُسجّل قراءة اليوم. تابع ختمتك من صفحة {ar(pointer)}.'
    try:
        result = subprocess.run(
            ['notify-send', '--app-name=سراج', '--icon', str(ICON), title, message],
            check=False, timeout=8,
        )
        if result.returncode == 0:
            return 0
    except (OSError, subprocess.SubprocessError):
        pass
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(QIcon(str(ICON)) if ICON.exists() else QIcon(), app)
        tray.setToolTip(title)
        tray.show()
        tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 12_000)
        app._siraj_reminder_tray = tray
        QTimer.singleShot(14_000, app.quit)
        return app.exec()
    QMessageBox.information(None, title, message)
    return 0


def main():
    configure_runtime_streams()
    import faulthandler
    faulthandler.enable(file=sys.stderr, all_threads=True)
    if '--selftest' in sys.argv:
        print('stage: start', file=sys.stderr, flush=True)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(f'{APP_NAME_AR} — {APP_DESCRIPTION_AR}')
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName('mosalah30688')
    app.setDesktopFileName(APP_ID)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    register_bundled_fonts()
    app.setFont(QFont('Noto Sans Arabic', 11))
    if '--remind' in sys.argv:
        return run_reminder_notification(app)
    win = Main()
    win.show()
    if '--selftest' in sys.argv or os.environ.get('MUSHAF_SELFTEST') == '1':
        run_selftest(app, win)
    if '--audiotest' in sys.argv:
        run_audiotest(app, win)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
