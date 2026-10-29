#!/usr/bin/env bash
# ينسخ واجهة سراج وبيانات القرآن المحلية إلى مجلد www الذي يُغلّف داخل تطبيق Android.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf www
mkdir -p www/fonts
cp \
  index.html app.js manifest.json sw.js icon.png icon-192.png \
  quran-search.json quran-meanings.json adhkar.json quran-riwayat.json \
  quran-hafs.json quran-tajweed.json surahs.json tafsir-catalog.json \
  www/
cp \
  fonts/AmiriQuran-arabic.woff2 \
  fonts/Amiri-Regular.ttf fonts/AmiriQuran-Regular.ttf \
  fonts/NotoNaskhArabic-Variable.ttf fonts/ScheherazadeNew-Regular.ttf \
  fonts/OFL-LICENSE.txt fonts/OFL-Amiri.txt fonts/OFL-AmiriQuran.txt \
  fonts/OFL-NotoNaskhArabic.txt fonts/OFL-ScheherazadeNew.txt \
  www/fonts/
printf 'www ready: '
find www -mindepth 1 -maxdepth 1 -printf '%f\n' | sort | tr '\n' ' '
printf '\n'
