#!/usr/bin/env bash
# يبني سراج كملف AppImage محمول لنظام Linux x86_64.
set -euo pipefail

cd "$(dirname "$0")"
VERSION="${1:-$(python3 -c 'from version import APP_VERSION; print(APP_VERSION)')}"
EXPECTED_VERSION="$(python3 -c 'from version import APP_VERSION; print(APP_VERSION)')"
if [[ "$VERSION" != "$EXPECTED_VERSION" ]]; then
  echo "الإصدار المطلوب $VERSION لا يطابق إصدار التطبيق $EXPECTED_VERSION" >&2
  exit 1
fi
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "رقم إصدار غير صالح: $VERSION" >&2
  exit 1
fi

APP_ID="com.mosalah30688.siraj.quran"
OUTPUT="Siraj-Quran-${VERSION}-linux-x86_64.AppImage"
APPIMAGETOOL_VERSION="1.9.1"
APPIMAGETOOL_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-x86_64.AppImage"
RUNTIME_VERSION="20251108"
RUNTIME_SHA256="2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"
RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/${RUNTIME_VERSION}/runtime-x86_64"
RELEASE_DATE="${SOURCE_DATE_EPOCH:+$(date -u -d "@${SOURCE_DATE_EPOCH}" +%F)}"
RELEASE_DATE="${RELEASE_DATE:-$(date -u +%F)}"

rm -rf build dist AppDir release squashfs-root binary-license-report
python3 -m PyInstaller --noconfirm --clean --windowed --name siraj \
  --add-data "data:data" \
  --add-data "fonts:fonts" \
  --add-data "icon.png:." \
  --add-data "assets:assets" \
  --hidden-import _cffi_backend \
  --hidden-import main \
  launcher.py
bash ./prune_bundle.sh dist/siraj
python3 ../scripts/collect_linux_bundle_licenses.py \
  --toc build/siraj/COLLECT-00.toc \
  --bundle-root dist/siraj \
  --output binary-license-report \
  --fail-unmapped-system

# لا يجوز أن تعتمد حزمة Qt على مكتبة مفقودة وقت البناء.
QXCB="$(find dist/siraj -type f -name 'libqxcb.so' -print -quit)"
if [[ -z "$QXCB" ]]; then
  echo "لم يُعثر على Qt xcb platform plugin" >&2
  exit 1
fi
if ldd "$QXCB" | grep -q "not found"; then
  echo "مكتبات X11 المطلوبة بواسطة Qt غير مكتملة:" >&2
  ldd "$QXCB" | grep "not found" >&2
  exit 1
fi

mkdir -p \
  AppDir/usr/bin \
  AppDir/usr/share/applications \
  AppDir/usr/share/icons/hicolor/512x512/apps \
  AppDir/usr/share/metainfo \
  AppDir/usr/share/doc/siraj
cp -a dist/siraj/. AppDir/usr/bin/
cp packaging/AppRun AppDir/AppRun
chmod 0755 AppDir/AppRun AppDir/usr/bin/siraj

DESKTOP="${APP_ID}.desktop"
ICON="${APP_ID}.png"
APPDATA="${APP_ID}.appdata.xml"
cp "packaging/${DESKTOP}" "AppDir/${DESKTOP}"
cp "packaging/${DESKTOP}" "AppDir/usr/share/applications/${DESKTOP}"
cp icon.png "AppDir/${ICON}"
cp icon.png "AppDir/usr/share/icons/hicolor/512x512/apps/${ICON}"
ln -s "$ICON" AppDir/.DirIcon
sed -e "s/@VERSION@/${VERSION}/g" -e "s/@RELEASE_DATE@/${RELEASE_DATE}/g" \
  "packaging/${APPDATA}.in" > "AppDir/usr/share/metainfo/${APPDATA}"
cp ../LICENSE AppDir/usr/share/doc/siraj/LICENSE
cp THIRD_PARTY_NOTICES.md AppDir/usr/share/doc/siraj/THIRD_PARTY_NOTICES.md
python3 ../scripts/collect_python_licenses.py \
  --requirements mushaf_app/requirements.txt \
  --output mushaf_app/AppDir/usr/share/doc/siraj/licenses/python \
  --fail-missing
mkdir -p AppDir/usr/share/doc/siraj/licenses/fonts
cp fonts/*.txt AppDir/usr/share/doc/siraj/licenses/fonts/
cp -a binary-license-report AppDir/usr/share/doc/siraj/licenses/linux-binaries

if command -v desktop-file-validate >/dev/null 2>&1; then
  desktop-file-validate "AppDir/${DESKTOP}"
fi
if command -v appstreamcli >/dev/null 2>&1; then
  appstreamcli validate --no-net "AppDir/usr/share/metainfo/${APPDATA}"
fi

if [[ ! -f appimagetool-${APPIMAGETOOL_VERSION}-x86_64.AppImage ]]; then
  curl --fail --location --retry 5 --retry-all-errors \
    --output appimagetool-${APPIMAGETOOL_VERSION}-x86_64.AppImage \
    "$APPIMAGETOOL_URL"
fi
echo "${APPIMAGETOOL_SHA256}  appimagetool-${APPIMAGETOOL_VERSION}-x86_64.AppImage" | sha256sum --check --strict
chmod 0755 appimagetool-${APPIMAGETOOL_VERSION}-x86_64.AppImage

if [[ ! -f runtime-${RUNTIME_VERSION}-x86_64 ]]; then
  curl --fail --location --retry 5 --retry-all-errors \
    --output runtime-${RUNTIME_VERSION}-x86_64 \
    "$RUNTIME_URL"
fi
echo "${RUNTIME_SHA256}  runtime-${RUNTIME_VERSION}-x86_64" | sha256sum --check --strict

mkdir -p release
ARCH=x86_64 SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(date +%s)}" \
  ./appimagetool-${APPIMAGETOOL_VERSION}-x86_64.AppImage --appimage-extract-and-run \
  --runtime-file "runtime-${RUNTIME_VERSION}-x86_64" \
  AppDir "release/${OUTPUT}"
chmod 0755 "release/${OUTPUT}"
(
  cd release
  sha256sum "$OUTPUT" > SHA256SUMS.txt
)

ls -lh "release/${OUTPUT}" release/SHA256SUMS.txt
