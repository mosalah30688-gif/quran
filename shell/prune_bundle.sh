#!/usr/bin/env bash
# يحذف الملفات اللي التطبيق مش محتاجها من حزمة PySide6 (ترجمات Qt، لغات Chromium الزايدة، أدوات المطورين).
set -euo pipefail
DIST="$1"
QT="$DIST/_internal/PySide6/Qt"
rm -rf "$QT/translations"
rm -rf "$QT/resources/qtwebengine_devtools_resources.pak"
if [ -d "$QT/translations" ] || [ -d "$QT/qtwebengine_locales" ]; then :; fi
if [ -d "$QT/resources/qtwebengine_locales" ]; then
  find "$QT/resources/qtwebengine_locales" -name '*.pak' ! -name 'ar.pak' ! -name 'en-US.pak' ! -name 'en-GB.pak' -delete
fi
find "$DIST" -name '*.pak' -path '*qtwebengine_locales*' ! -name 'ar.pak' ! -name 'en-US.pak' ! -name 'en-GB.pak' -delete 2>/dev/null || true
du -sh "$DIST"
