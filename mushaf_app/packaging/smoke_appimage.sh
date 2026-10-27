#!/usr/bin/env bash
# يشغّل AppImage بلا arguments تحت X11 افتراضيًا، كما يفعل النقر المزدوج.
set -euo pipefail

APPIMAGE="${1:?مسار AppImage مطلوب}"
APPIMAGE="$(realpath "$APPIMAGE")"
[[ -x "$APPIMAGE" ]] || { echo "AppImage ليس executable: $APPIMAGE" >&2; exit 1; }
command -v xdotool >/dev/null || { echo "xdotool مطلوب لاختبار نافذة التطبيق" >&2; exit 1; }
[[ -n "${DISPLAY:-}" ]] || { echo "DISPLAY غير مضبوط؛ شغّل الاختبار عبر xvfb-run" >&2; exit 1; }

WORK="$(mktemp -d)"
PID=""
cleanup() {
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT
mkdir -p "$WORK/config" "$WORK/data" "$WORK/cache" "$WORK/state"

LANG=C.UTF-8 \
LC_ALL=C.UTF-8 \
XDG_CONFIG_HOME="$WORK/config" \
XDG_DATA_HOME="$WORK/data" \
XDG_CACHE_HOME="$WORK/cache" \
XDG_STATE_HOME="$WORK/state" \
"$APPIMAGE" >"$WORK/stdout.log" 2>"$WORK/stderr.log" &
PID=$!

TITLE=""
for _ in $(seq 1 45); do
  if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID" || STATUS=$?
    echo "توقف AppImage قبل ظهور النافذة (exit ${STATUS:-0})" >&2
    cat "$WORK/stdout.log" >&2 || true
    cat "$WORK/stderr.log" >&2 || true
    exit 1
  fi
  WINDOW_ID="$(xdotool search --onlyvisible --name 'سراج' 2>/dev/null | head -n 1 || true)"
  if [[ -n "$WINDOW_ID" ]]; then
    TITLE="$(xdotool getwindowname "$WINDOW_ID" 2>/dev/null || true)"
  fi
  [[ "$TITLE" == *"سراج"* ]] && break
  sleep 1
done

if [[ "$TITLE" != *"سراج"* ]]; then
  echo "لم تظهر نافذة بعنوان سراج خلال 45 ثانية" >&2
  cat "$WORK/stdout.log" >&2 || true
  cat "$WORK/stderr.log" >&2 || true
  exit 1
fi
printf 'AppImage double-click window: %s\n' "$TITLE"

# لا ينبغي أن يكتب التشغيل الأول أي بيانات داخل الحزمة أو جوارها.
if find "$(dirname "$APPIMAGE")" -maxdepth 1 -type d -name 'UserData' -print -quit | grep -q .; then
  echo "عُثر على UserData بجوار AppImage" >&2
  exit 1
fi
