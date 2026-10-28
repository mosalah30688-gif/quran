#!/usr/bin/env python3
"""نقطة تشغيل Linux الثابتة: تتحقق من الترقيع ثم تشغّل التطبيق."""
from pathlib import Path
import sys

from patch_runtime import run_application
from version import APP_VERSION

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

if __name__ == "__main__":
    raise SystemExit(run_application(
        product="siraj-quran-linux",
        runtime_api=1,
        bundled_version=APP_VERSION,
        public_key_path=BASE / "assets" / "update_public_key.txt",
    ))
