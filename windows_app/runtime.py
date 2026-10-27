"""مسارات التشغيل والإعدادات للوضع المثبّت والوضع المحمول."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

try:
    from .version import PUBLISHER
except ImportError:  # تشغيل main.py مباشرة أثناء التطوير
    from version import PUBLISHER


def bundle_root() -> Path:
    """جذر الملفات المضمّنة داخل PyInstaller أو مجلد المصدر أثناء التطوير."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def executable_root() -> Path:
    """المجلد الذي يوجد فيه EXE؛ يختلف عن _MEIPASS في بناء PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_portable() -> bool:
    value = os.environ.get("SIRAJ_PORTABLE", "").strip().lower()
    return value in {"1", "true", "yes"} or (executable_root() / "portable.flag").exists()


def user_data_root() -> Path:
    if is_portable():
        root = executable_root() / "UserData"
    else:
        location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        root = Path(location) if location else Path.home() / ".siraj-quran"
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_settings() -> QSettings:
    """إعدادات INI بجانب النسخة المحمولة، وRegistry في النسخة المثبّتة.

    عند أول تشغيل للنسخة المثبّتة ننقل إعدادات تطبيق «المصحف» السابق كي لا تضيع
    العلامات والورد والإحصاءات، مع بقاء الإصدار الجديد مستقلاً في الاسم والترقيم.
    """
    if is_portable():
        path = user_data_root() / "settings.ini"
        return QSettings(str(path), QSettings.Format.IniFormat)

    settings = QSettings(PUBLISHER, "SirajQuran")
    if settings.value("migration/legacy_done", False, type=bool):
        return settings

    legacy = QSettings("mosalah30688", "Mushaf")
    if not settings.allKeys() and legacy.allKeys():
        for key in legacy.allKeys():
            settings.setValue(key, legacy.value(key))
    settings.setValue("migration/legacy_done", True)
    settings.sync()
    return settings


def cache_dir(name: str) -> Path:
    path = user_data_root() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def mode_label() -> str:
    return "محمول" if is_portable() else "مثبّت"
