#!/usr/bin/env bash
# ينسخ ملفات الواجهة إلى مجلد www الذي يُغلّف داخل تطبيق الأندرويد
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf www && mkdir -p www
cp index.html app.js manifest.json icon.png icon-192.png quran-search.json quran-meanings.json adhkar.json quran-riwayat.json www/
mkdir -p www/fonts && cp fonts/AmiriQuran-arabic.woff2 fonts/OFL-LICENSE.txt www/fonts/
printf 'www ready: '
find www -mindepth 1 -maxdepth 1 -printf '%f\n' | sort | tr '\n' ' '
printf '\n'
