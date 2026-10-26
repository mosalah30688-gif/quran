#!/usr/bin/env python3
"""المصحف - تطبيق سطح المكتب.

نفس واجهة تطبيق الأندرويد (مجلد www) داخل نافذة أصلية لسطح المكتب:
- قائمة أصلية (ملف، عرض، مساعدة) واختصارات لوحة المفاتيح
- التكبير والتصغير وملء الشاشة، وحفظ حجم النافذة
- الروابط الخارجية تفتح في المتصفح الافتراضي
- ملفات التطبيق تُخدم من خادم محلي على منفذ ثابت، فيبقى تخزين التطبيق (المحفوظات والإعدادات) بين مرات التشغيل

تشغيل للتجربة:  python3 main.py
"""
import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = 'Mushaf'
APP_VERSION = '3.0.0'
FIXED_PORT = 47831  # ثابت حتى يبقى أصل localStorage ثابتاً بين مرات التشغيل

# إعدادات محرك Chromium لازم تتحط قبل ما QtWebEngine يبدأ.
# على لينكس بنعطّل تسريع الكرت لأنه كان بيسبب ارتعاش الشاشة في نسخ سابقة.
if sys.platform.startswith('linux') and 'QTWEBENGINE_CHROMIUM_FLAGS' not in os.environ:
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-gpu --autoplay-policy=no-user-gesture-required'
elif 'QTWEBENGINE_CHROMIUM_FLAGS' not in os.environ:
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--autoplay-policy=no-user-gesture-required'

from PySide6.QtCore import QSettings, QUrl  # noqa: E402
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox  # noqa: E402
from PySide6.QtWebEngineCore import QWebEnginePage  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402


def base_dir():
    if getattr(sys, 'frozen', False):
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    return Path(__file__).resolve().parent


WWW = base_dir() / 'www' if (base_dir() / 'www').exists() else base_dir().parent / 'www'
ICON = WWW / 'icon-192.png'


class QuietHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      '.woff2': 'font/woff2', '.js': 'text/javascript; charset=utf-8',
                      '.json': 'application/json; charset=utf-8', '.webmanifest': 'application/manifest+json'}

    def log_message(self, *_args):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


def start_server():
    """يبدأ خادم الملفات المحلي ويرجع المنفذ. لو المنفذ الثابت مشغول بنستخدم منفذ عشوائي."""
    handler = partial(QuietHandler, directory=str(WWW))
    try:
        server = ThreadingHTTPServer(('127.0.0.1', FIXED_PORT), handler)
    except OSError:
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.server_address[1]


class Page(QWebEnginePage):
    """الروابط الخارجية تفتح في المتصفح، والباقي يفضل داخل التطبيق."""

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):  # noqa: N802 (اسم Qt)
        if url.scheme() in ('http', 'https') and url.host() not in ('127.0.0.1', 'localhost'):
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    def createWindow(self, _window_type):  # noqa: N802
        # أي رابط يفتح نافذة جديدة يتعامل معاه acceptNavigationRequest
        return self


class Window(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.settings = QSettings('mosalah30688', APP_NAME)
        self.setWindowTitle('المصحف')
        if ICON.exists():
            self.setWindowIcon(QIcon(str(ICON)))

        self.view = QWebEngineView(self)
        self.view.setPage(Page(self.view))
        self.setCentralWidget(self.view)
        self.view.setZoomFactor(self.settings.value('zoom', 1.0, type=float))
        self.view.load(QUrl(url))

        self.build_menus()
        geo = self.settings.value('geometry')
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            self.resize(1280, 860)

    def build_menus(self):
        bar = self.menuBar()

        file_menu = bar.addMenu('ملف')
        reload_act = QAction('إعادة تحميل', self)
        reload_act.setShortcut(QKeySequence('F5'))
        reload_act.triggered.connect(self.view.reload)
        file_menu.addAction(reload_act)
        file_menu.addSeparator()
        quit_act = QAction('خروج', self)
        quit_act.setShortcut(QKeySequence('Ctrl+Q'))
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        view_menu = bar.addMenu('عرض')
        for label, shortcut, slot in (
            ('تكبير', 'Ctrl++', self.zoom_in),
            ('تصغير', 'Ctrl+-', self.zoom_out),
            ('الحجم الطبيعي', 'Ctrl+0', self.zoom_reset),
        ):
            act = QAction(label, self)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(slot)
            view_menu.addAction(act)
        view_menu.addSeparator()
        full_act = QAction('ملء الشاشة', self)
        full_act.setShortcut(QKeySequence('F11'))
        full_act.setCheckable(True)
        full_act.toggled.connect(lambda on: self.showFullScreen() if on else self.showNormal())
        view_menu.addAction(full_act)

        help_menu = bar.addMenu('مساعدة')
        about_act = QAction('عن المصحف', self)
        about_act.triggered.connect(self.show_about)
        help_menu.addAction(about_act)

    def zoom_in(self):
        self.set_zoom(self.view.zoomFactor() + 0.1)

    def zoom_out(self):
        self.set_zoom(self.view.zoomFactor() - 0.1)

    def zoom_reset(self):
        self.set_zoom(1.0)

    def set_zoom(self, value):
        value = min(max(round(value, 2), 0.5), 2.5)
        self.view.setZoomFactor(value)
        self.settings.setValue('zoom', value)

    def show_about(self):
        QMessageBox.about(self, 'عن المصحف', f'المصحف - سطح المكتب\nالإصدار {APP_VERSION}\n\n'
                          'نفس واجهة تطبيق الأندرويد داخل نافذة سطح المكتب.')

    def closeEvent(self, event):  # noqa: N802
        self.settings.setValue('geometry', self.saveGeometry())
        super().closeEvent(event)


def main():
    if not WWW.exists():
        print(f'مجلد الواجهة غير موجود: {WWW}', file=sys.stderr)
        return 1
    port = start_server()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName('mosalah30688')
    win = Window(f'http://127.0.0.1:{port}/index.html?desktop=1')
    win.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
