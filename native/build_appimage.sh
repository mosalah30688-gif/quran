#!/usr/bin/env bash
# يبني المصحف كـ AppImage لينكس x86_64. الاستخدام: ./build_appimage.sh <version>
set -euo pipefail
VERSION="${1:?الإصدار مطلوب}"
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
rm -rf build dist AppDir
python3 -m PyInstaller --noconfirm --windowed --name mushaf \
  --add-data "data:data" --add-data "fonts:fonts" \
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets \
  --exclude-module PySide6.QtWebEngineQuick --exclude-module PySide6.Qt3DCore \
  --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml --exclude-module PySide6.QtPdf \
  --exclude-module PySide6.QtCharts --exclude-module PySide6.QtDataVisualization \
  --exclude-module PySide6.QtDesigner --exclude-module PySide6.QtSvg \
  mushaf.py
mkdir -p AppDir/usr/bin
cp -r dist/mushaf/* AppDir/usr/bin/
cp packaging/AppRun AppDir/AppRun
cp packaging/mushaf.desktop AppDir/mushaf.desktop
cp packaging/mushaf.png AppDir/mushaf.png
if [ ! -x appimagetool ]; then
  curl -fsSL -o appimagetool https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x appimagetool
fi
ARCH=x86_64 ./appimagetool --appimage-extract-and-run AppDir "Mushaf-${VERSION}-x86_64.AppImage"
ls -la "Mushaf-${VERSION}-x86_64.AppImage"
