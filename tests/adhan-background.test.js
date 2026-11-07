'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(ROOT, file), 'utf8');
const JAVA = 'android/app/src/main/java/com/quran/mushaf';

test('الأذان في الخلفية: خدمة أمامية ومستقبلان معلَنان في البيان', () => {
  const manifest = read('android/app/src/main/AndroidManifest.xml');
  assert.match(manifest, /android:name="\.AdhanService"[\s\S]*?foregroundServiceType="mediaPlayback"/);
  assert.match(manifest, /android:name="\.AdhanReceiver"/);
  assert.match(manifest, /android:name="\.AdhanBootReceiver"/);
  assert.match(manifest, /android\.permission\.SCHEDULE_EXACT_ALARM/);
  assert.match(manifest, /android\.permission\.FOREGROUND_SERVICE_MEDIA_PLAYBACK/);
  assert.match(manifest, /android\.intent\.action\.BOOT_COMPLETED/);
  assert.match(manifest, /android\.intent\.action\.TIMEZONE_CHANGED/);
});

test('الأذان في الخلفية: الجسر مسجَّل في النشاط الرئيسي', () => {
  const activity = read(`${JAVA}/MainActivity.java`);
  assert.match(activity, /registerPlugin\(AdhanPlugin\.class\)/);
  const plugin = read(`${JAVA}/AdhanPlugin.java`);
  assert.match(plugin, /@CapacitorPlugin\(name = "AdhanBackground"\)/);
  ['configure', 'status', 'play', 'stop', 'clear'].forEach((method) => {
    assert.match(plugin, new RegExp(`void ${method}\\(PluginCall call\\)`));
  });
});

test('الأذان في الخلفية: منبّهات دقيقة مع بديل حين يمنعها النظام', () => {
  const scheduler = read(`${JAVA}/AdhanScheduler.java`);
  assert.match(scheduler, /setExactAndAllowWhileIdle/);
  assert.match(scheduler, /canScheduleExactAlarms/);
  assert.match(scheduler, /setAndAllowWhileIdle/);
  assert.match(scheduler, /captureException|catch \(SecurityException/);
  assert.match(scheduler, /reschedule\(Context context\)/);
  const boot = read(`${JAVA}/AdhanBootReceiver.java`);
  assert.match(boot, /AdhanScheduler\.reschedule\(context\)/);
});

test('الأذان في الخلفية: التشغيل من الملف المحلي ثم الشبكة', () => {
  const service = read(`${JAVA}/AdhanService.java`);
  assert.match(service, /USAGE_ALARM/);
  assert.match(service, /AdhanScheduler\.audioPath/);
  assert.match(service, /MediaSessionCompat/);
  assert.match(service, /setAction\(ACTION_STOP\)/);
  const store = read(`${JAVA}/AdhanAudioStore.java`);
  assert.match(store, /getFilesDir\(\), "adhans"/);
  assert.match(store, /HttpURLConnection/);
});

test('الأذان في الخلفية: الواجهة تسلّم جدول أربعة عشر يومًا للجسر', () => {
  const ui = read('prayer-ui.js');
  assert.match(ui, /BG_PLUGIN = 'AdhanBackground'/);
  assert.match(ui, /BG_HORIZON_DAYS = 14/);
  assert.match(ui, /function buildBackgroundSchedule\(\)/);
  assert.match(ui, /bgCall\('configure', payload\)/);
  assert.match(ui, /function cityEpoch\(instant, hours\)/);
  assert.match(ui, /Math\.round\(hours \* 3600000\)/);
  assert.match(ui, /iqamaMinutes: Math\.max\(0, num\(config\.iqamaMinutes\[key\], 0\)\)/);
  assert.match(ui, /syncBackground\(true\)/);
  // لا تشغيل مزدوج: النظام يتولى الأذان حين يكون الجدول قائمًا
  assert.match(ui, /const handledBySystem = hasBackgroundBridge\(\) && bgState\.scheduled > 0;/);
});

test('الأذان في الخلفية: لا مفتاح تشغيل/إيقاف جديد للمستخدم', () => {
  const html = read('index.html');
  assert.match(html, /id="ptBgStatus"/);
  // السياسة: خلفية الصوت تعمل دائمًا، فلا يُضاف مفتاح لها في الواجهة
  assert.doesNotMatch(html, /id="pt[A-Za-z]*Background[A-Za-z]*"[^>]*type="checkbox"/);
  assert.doesNotMatch(html, /مفتاح الخلفية/);
  assert.doesNotMatch(read('prayer-ui.js'), /bgToggle|backgroundEnabled/);
});

test('الأذان في الخلفية: أرقام الإصدار والبناء متوافقة مع القناة', () => {
  const build = fs.readFileSync(path.join(ROOT, 'BUILD_NUMBER'), 'utf8').trim();
  const gradle = read('android/app/build.gradle');
  const html = read('index.html');
  const match = /versionCode\s+(\d+)/.exec(gradle);
  assert.ok(match, 'versionCode موجود في gradle');
  assert.equal(match[1], build, 'versionCode يساوي BUILD_NUMBER');
  assert.match(html, new RegExp(`APP_BUILD_NUMBER = ${build}`));
  assert.match(gradle, /versionName "1\.0\.0"/);
});

test('ترقية الـAPK تُقارن برقم بناء الملف المثبَّت لا برقم بناء الواجهة', () => {
  const app = read('app.js');
  const plugin = read(`${JAVA}/ApkUpdaterPlugin.java`);
  assert.match(plugin, /ret\.put\("code", code\)/);
  assert.match(plugin, /getLongVersionCode\(\)/);
  assert.match(app, /function installedApkCode\(\)/);
  assert.match(app, /function resolveApkCode\(\)/);
  assert.match(app, /apkCode > installedApkCode\(\)/);
  // لا يجوز أن يُقارن مؤشر الـAPK برقم بناء الواجهة، وإلا حجب التحديث الداخلي ترقية الملف
  assert.doesNotMatch(app, /apkCode > currentBuild\(\)/);
});
