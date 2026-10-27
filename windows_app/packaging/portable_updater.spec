# -*- mode: python ; coding: utf-8 -*-
"""ملف واحد صغير لتحديث النسخة المحمولة بعد إغلاق سراج."""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(ROOT / 'portable_updater.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SirajPortableUpdater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / 'assets' / 'siraj.ico'),
    version=str(ROOT / 'packaging' / 'version_info.txt'),
    uac_admin=False,
    uac_uiaccess=False,
)
