'use strict';

/*
 * تسليم التحديث الداخلي: لا يتوقف على مضيف واحد، ورقم الإصدار المعروض يتبع
 * الواجهة المطبَّقة لا ملف الـAPK المثبَّت (وإلا ظهر رقم قديم بعد التحديث).
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(ROOT, file), 'utf8');

test('التحديث: مرايا متعددة لمضيف القناة وملاذ أخير عبر واجهة GitHub', () => {
  const app = read('app.js');
  assert.match(app, /const UPDATE_MIRRORS = \[/);
  assert.match(app, /raw\.githack\.com\/mosalah30688-gif\/quran\/main\/update\//);
  assert.match(app, /const UPDATE_API = 'https:\/\/api\.github\.com\/repos\/mosalah30688-gif\/quran\/contents\/update\/'/);
  assert.match(app, /async function fetchUpdateFile\(name\)/);
  assert.match(app, /for \(const base of UPDATE_MIRRORS\)/);
  assert.match(app, /Accept: 'application\/vnd\.github\.raw'/);
  // مهلة زمنية حتى لا يتعلّق التنزيل بلا نهاية على شبكة بطيئة
  assert.match(app, /const UPDATE_TIMEOUT_MS = 20000;/);
  assert.match(app, /new AbortController\(\)/);
});

test('التحديث: كل مسارات القراءة تمر عبر الجالب الموحّد', () => {
  const app = read('app.js');
  assert.match(app, /const manifest = JSON\.parse\(await fetchUpdateFile\('manifest\.json'\)\);/);
  assert.match(app, /const m = JSON\.parse\(await fetchUpdateFile\('manifest\.json'\)\);/);
  assert.match(app, /txt = await fetchUpdateFile\(f\);/);
  // لم يبقَ أي fetch مباشر إلى مضيف واحد داخل مسار التحديث
  assert.doesNotMatch(app, /fetch\(UPDATE_BASE \+ f \+ '\?t='/);
  assert.doesNotMatch(app, /fetch\(UPDATE_BASE \+ 'manifest\.json\?t='/);
});

test('التحديث: رقم الإصدار والبناء المعروضان يتبعان الواجهة المطبَّقة', () => {
  const app = read('app.js');
  assert.match(app, /const appliedWebVersion = \(\) => String\(\(storedUpdate\(\) \|\| \{\}\)\.version \|\| ''\);/);
  assert.match(app, /function syncAppliedIdentity\(\)/);
  assert.match(app, /if \(version\) window\.APP_BUNDLE_VERSION = version;/);
  assert.match(app, /if \(build > Number\(window\.APP_BUILD_NUMBER \|\| 0\)\) window\.APP_BUILD_NUMBER = build;/);
  assert.match(app, /\$\('#verVal'\)\.textContent = currentVersion\(\);/);
  assert.match(app, /`بناء \$\{toArabicDigits\(effectiveBuild\(\)\)\}`/);
  assert.match(app, /'أنت على أحدث نسخة \(' \+ currentVersion\(\)/);
  // سكربت الإقلاع كذلك يضبط الهوية عند تطبيق ترقيع (للنسخ التي تحمله)
  const html = read('index.html');
  assert.match(html, /if \(up\.version\) window\.APP_BUNDLE_VERSION = String\(up\.version\);/);
  assert.match(html, /if \(overlayBuild > 0\) window\.APP_BUILD_NUMBER = overlayBuild;/);
});

test('التحديث: رسالة الفشل تذكر السبب بدل نص عام', () => {
  const app = read('app.js');
  assert.match(app, /تعذّر التحديث \(' \+ String\(\(e && e\.message\) \|\| 'network'\)\.slice\(0, 40\)/);
});
