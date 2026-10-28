# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build لسراج — Windows x64."""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

# لا يستخدم التطبيق WebEngine أو QML أو PDF؛ استبعادها يقلل الحجم ومساحة الهجوم.
EXCLUDES = [
    'PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DExtras',
    'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender',
    'PySide6.QtBluetooth', 'PySide6.QtCharts', 'PySide6.QtDataVisualization',
    'PySide6.QtGraphs', 'PySide6.QtLocation', 'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets', 'PySide6.QtNetworkAuth', 'PySide6.QtNfc',
    'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtPositioning',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuick3D',
    'PySide6.QtQuickControls2', 'PySide6.QtQuickWidgets', 'PySide6.QtRemoteObjects',
    'PySide6.QtScxml', 'PySide6.QtSensors', 'PySide6.QtSerialBus',
    'PySide6.QtSerialPort', 'PySide6.QtSpatialAudio', 'PySide6.QtSql',
    'PySide6.QtStateMachine', 'PySide6.QtTest', 'PySide6.QtTextToSpeech',
    'PySide6.QtVirtualKeyboard', 'PySide6.QtWebChannel', 'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineQuick', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebSockets',
]

a = Analysis(
    [str(ROOT / 'launcher.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'data'), 'data'),
        (str(ROOT / 'fonts'), 'fonts'),
        (str(ROOT / 'assets'), 'assets'),
    ],
    hiddenimports=['_cffi_backend', 'main'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Siraj',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'assets' / 'siraj.ico'),
    version=str(ROOT / 'packaging' / 'version_info.txt'),
    uac_admin=False,
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Siraj',
)
