#!/usr/bin/env bash
# ينشر تحديثاً جديداً: ينسخ index.html و app.js إلى مجلد update ويكتب رقم الإصدار
# الاستخدام: bash scripts/publish-update.sh 1.0.4
set -euo pipefail
VER="${1:?اكتب رقم الإصدار، مثال: 1.0.4}"
cd "$(dirname "$0")/.."
mkdir -p update
cp index.html app.js update/
printf '{\n  "version": "%s",\n  "files": ["index.html", "app.js"]\n}\n' "$VER" > update/manifest.json
echo "update ready: version $VER"
