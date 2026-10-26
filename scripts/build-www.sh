#!/usr/bin/env bash
# ينسخ ملفات الواجهة إلى مجلد www الذي يُغلّف داخل تطبيق الأندرويد
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf www && mkdir -p www
cp index.html app.js manifest.json icon.png icon-192.png www/
echo "www ready: $(ls www | tr '\n' ' ')"
