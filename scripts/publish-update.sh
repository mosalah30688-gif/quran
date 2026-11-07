#!/usr/bin/env bash
# يجهز ترقية الواجهة وملفات JSON المقفلة، مع إبقاء قنوات APK وسطح المكتب الحالية.
# الاستخدام: bash scripts/publish-update.sh 1.4.5 "الميزة الأولى" "الميزة الثانية"
set -euo pipefail
VER="${1:?اكتب رقم الإصدار، مثال: 1.4.5}"
if [[ ! "$VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "رقم الإصدار يجب أن يكون بصيغة x.y.z" >&2
  exit 2
fi
shift
if (( $# < 1 )); then
  echo "اكتب ميزة جديدة واحدة على الأقل ليظهر إشعار «الجديد» للمستخدم." >&2
  exit 2
fi
cd "$(dirname "$0")/.."
python3 - "$VER" "$@" <<'PY'
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from scripts.product_copy import validate_update_features

version = sys.argv[1]
features = validate_update_features(sys.argv[2:])
if not features:
    raise SystemExit("at least one user-facing update feature is required")
root = Path.cwd()
update = root / "update"
update.mkdir(exist_ok=True)
manifest_path = update / "manifest.json"
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    manifest = {}
try:
    current_build = int((root / "BUILD_NUMBER").read_text(encoding="utf-8").strip())
except (FileNotFoundError, ValueError):
    current_build = 0
try:
    released_build = int(manifest.get("build") or 0)
except (TypeError, ValueError):
    released_build = 0
# تكرار النص مرفوض ما دام البناء نفسه؛ أما بناء جديد فله محتواه الجديد ولو تشابهت العناوين.
if manifest.get("features") == features and current_build <= released_build:
    raise SystemExit("update features must describe what is new, not repeat the current release")
base = [
    "index.html",
    "smart-context.js",
    "smart-services.js",
    "tajweed-learning.js",
    "tajweed-curriculum-loader.js",
    "tajweed-learning-catalog.json",
    "tajweed-scope-registry.json",
    "prayer-times.js",
    "prayer-data.js",
    "prayer-ui.js",
    "app.js",
]
curricula = sorted(
    str(path.relative_to(root)).replace("\\", "/")
    for path in (root / "tajweed-curricula").glob("*.json")
) if (root / "tajweed-curricula").is_dir() else []
bound_assets: set[str] = set()
for relative in curricula:
    package = json.loads((root / relative).read_text(encoding="utf-8"))
    asset = package.get("textBinding", {}).get("asset")
    if not isinstance(asset, str) or Path(asset).name != asset or not asset.endswith(".json"):
        raise SystemExit(f"unsafe curriculum text asset: {relative}")
    bound_assets.add(asset)
files = base + curricula + sorted(bound_assets - set(base))

# ملفات بيانات القرآن تُشحن في القناة دائمًا مع كل إصدار، لأن المستخدم الذي ينتقل
# من إصدار قديم مباشرة إلى هذا الإصدار لن يكون قد استلم تصحيح نص سابق؛ وبهذا يصل
# متن المصحف الصحيح إلى التطبيق المثبَّت من داخل التطبيق (IndexedDB) بلا APK جديد.
for name in ("quran-hafs.json", "quran-madani-lines.json"):
    source = root / name
    if not source.is_file():
        continue
    if name not in files:
        files.append(name)

stale_dir = update / "tajweed-curricula"
if stale_dir.exists():
    shutil.rmtree(stale_dir)
for relative in files:
    source = root / relative
    if not source.is_file():
        raise SystemExit(f"missing update source: {relative}")
    target = update / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

build_file = root / "BUILD_NUMBER"
build_number = int(build_file.read_text(encoding="utf-8").strip()) if build_file.is_file() else 0
previous_build = int(manifest.get("build") or 0)
if build_number < previous_build:
    raise SystemExit(f"BUILD_NUMBER {build_number} must not decrease (channel is at {previous_build})")
manifest["build"] = build_number
manifest["version"] = version
manifest["features"] = features
manifest["files"] = files
manifest["sha256"] = {
    relative: hashlib.sha256((update / relative).read_bytes()).hexdigest()
    for relative in files
}
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
echo "update ready: version $VER (SHA-256 locked JSON overlay)"
