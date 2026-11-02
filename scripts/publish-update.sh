#!/usr/bin/env bash
# ينشر تحديثاً جديداً: ينسخ الواجهة ومحرك السياق إلى مجلد update ويكتب رقم الإصدار
# الاستخدام: bash scripts/publish-update.sh 1.0.4
set -euo pipefail
VER="${1:?اكتب رقم الإصدار، مثال: 1.0.4}"
cd "$(dirname "$0")/.."
mkdir -p update
cp index.html smart-context.js smart-services.js tajweed-learning.js tajweed-learning-catalog.json app.js update/
printf '{\n  "version": "%s",\n  "files": ["index.html", "smart-context.js", "smart-services.js", "tajweed-learning.js", "tajweed-learning-catalog.json", "app.js"]\n}\n' "$VER" > update/manifest.json
echo "update ready: version $VER"
