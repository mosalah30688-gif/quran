#!/usr/bin/env bash
# ينسخ واجهة سراج وبيانات القرآن المحلية إلى مجلد www الذي يُغلّف داخل تطبيق Android.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf www
mkdir -p www/fonts www/legal
cp \
  index.html smart-context.js smart-services.js tajweed-learning.js tajweed-curriculum-loader.js app.js prayer-times.js prayer-data.js prayer-ui.js manifest.json sw.js icon.png icon-192.png \
  quran-search.json quran-meanings.json adhkar.json quran-riwayat.json \
  quran-hafs.json quran-madani-lines.json quran-tajweed.json tajweed-learning-catalog.json tajweed-scope-registry.json surahs.json tafsir-catalog.json quran-reciters.json \
  www/
cp \
  fonts/AmiriQuran-arabic.woff2 \
  fonts/Amiri-Regular.ttf fonts/AmiriQuran-Regular.ttf \
  fonts/NotoNaskhArabic-Variable.ttf fonts/ScheherazadeNew-Regular.ttf \
  fonts/OFL-LICENSE.txt fonts/OFL-Amiri.txt fonts/OFL-AmiriQuran.txt \
  fonts/OFL-NotoNaskhArabic.txt fonts/OFL-ScheherazadeNew.txt \
  www/fonts/
cp LICENSE LICENSE.ar.md NOTICE.md www/legal/
cp LICENSES/MIT-HISTORICAL.txt www/legal/
# الأذان المحلي: يُنسخ داخل الحزمة ليعمل بلا إنترنت
if compgen -G 'audio/adhans/*.mp3' >/dev/null; then
  mkdir -p www/audio/adhans
  cp audio/adhans/*.mp3 www/audio/adhans/
fi
# فيديو شاشة الأذان: داخل الحزمة ليعمل دون إنترنت
if compgen -G 'media/adhan/*' >/dev/null; then
  mkdir -p www/media/adhan
  cp media/adhan/* www/media/adhan/
fi
if compgen -G 'tajweed-curricula/*.json' >/dev/null; then
  mkdir -p www/tajweed-curricula
  cp tajweed-curricula/*.json www/tajweed-curricula/
fi
printf 'www ready: '
find www -mindepth 1 -maxdepth 1 -printf '%f\n' | sort | tr '\n' ' '
printf '\n'
