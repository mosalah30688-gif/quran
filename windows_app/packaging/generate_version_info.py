"""يولّد Windows VERSIONINFO من windows_app/version.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("siraj_version", ROOT / "version.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
parts = [int(x) for x in module.APP_VERSION.split(".")]
while len(parts) < 4:
    parts.append(0)
version_tuple = tuple(parts[:4])
text = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple!r},
    prodvers={version_tuple!r},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040104B0',
        [StringStruct('CompanyName', '{module.PUBLISHER}'),
         StringStruct('FileDescription', '{module.APP_NAME_AR} — {module.APP_DESCRIPTION_AR}'),
         StringStruct('FileVersion', '{module.APP_VERSION}'),
         StringStruct('InternalName', 'Siraj'),
         StringStruct('LegalCopyright', 'Copyright © 2026 {module.PUBLISHER}'),
         StringStruct('OriginalFilename', 'Siraj.exe'),
         StringStruct('ProductName', '{module.APP_NAME_AR} - {module.APP_DESCRIPTION_AR}'),
         StringStruct('ProductVersion', '{module.APP_VERSION}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1025, 1200])])
  ]
)
"""
(ROOT / "packaging" / "version_info.txt").write_text(text, encoding="utf-8")
print(module.APP_VERSION)
