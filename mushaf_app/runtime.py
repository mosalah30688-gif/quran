"""مساعدات بدء تشغيل سراج في جلسات Linux الرسومية."""

import os
import sys
from pathlib import Path

STARTUP_LOG_NAME = "siraj-startup.log"


def runtime_state_dir():
    """مجلد سجل بدء التشغيل وفق XDG، بعيدًا عن ملف AppImage نفسه."""
    root = os.environ.get("XDG_STATE_HOME")
    return (Path(root) if root else Path.home() / ".local" / "state") / "siraj"


def configure_runtime_streams():
    """يوفّر streams آمنة عند التشغيل من مدير الملفات بلا طرفية."""
    if sys.stdout is not None and sys.stderr is not None:
        return None
    try:
        log_dir = runtime_state_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        stream = (log_dir / STARTUP_LOG_NAME).open("a", encoding="utf-8", buffering=1)
    except OSError:
        stream = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    return stream
