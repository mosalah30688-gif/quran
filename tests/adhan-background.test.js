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
  assert.ok(Number(match[1]) >= Number(build), 'versionCode لا يسبق BUILD_NUMBER');
  assert.match(html, new RegExp(`APP_BUILD_NUMBER = ${build}`));
  assert.match(gradle, /versionName "1\.5\.\d+"/);
  assert.match(gradle, /versionCode 163/);
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

test('الموقع والبوصلة: الإذن والحساسات عبر الجسر الأصلي لا عبر WebView', () => {
  const manifest = read('android/app/src/main/AndroidManifest.xml');
  assert.match(manifest, /android\.permission\.ACCESS_FINE_LOCATION/);
  const plugin = read(`${JAVA}/SirajSensorsPlugin.java`);
  assert.match(plugin, /@CapacitorPlugin\(\s*name = "SirajSensors"/);
  assert.match(plugin, /Manifest\.permission\.ACCESS_FINE_LOCATION/);
  assert.match(plugin, /requestPermissionForAlias\("location"/);
  assert.match(plugin, /TYPE_ROTATION_VECTOR/);
  assert.match(plugin, /notifyListeners\("heading"/);
  const activity = read(`${JAVA}/MainActivity.java`);
  assert.match(activity, /registerPlugin\(SirajSensorsPlugin\.class\)/);
  const ui = read('prayer-ui.js');
  assert.match(ui, /SENSORS_PLUGIN = 'SirajSensors'/);
  assert.match(ui, /sensorCall\('getLocation'\)/);
  assert.match(ui, /sensorCall\('startCompass'\)/);
});

test('التلاوة حسب السورة: كتالوج قراء كامل وملف واحد لكل سورة', () => {
  const catalog = JSON.parse(read('quran-reciters.json'));
  assert.ok(Array.isArray(catalog.items) && catalog.items.length >= 100, 'عدد القراء');
  catalog.items.forEach((item) => {
    assert.match(item.server, /^https:\/\/[a-z0-9.-]*mp3quran\.net\/[A-Za-z0-9._\/-]+\/$/);
    assert.equal(item.surahs, 114);
  });
  const app = read('app.js');
  assert.match(app, /function playSurahFull\(surah, options = \{\}\)/);
  assert.match(app, /settings\.surahAudio !== false && !isRiw\(\) && SURAH_RECITERS\.length/);
  assert.match(read('scripts/build-www.sh'), /quran-reciters\.json/);
  assert.match(read('scripts/publish-update.sh'), /quran-reciters\.json/);
  assert.match(read('sw.js'), /quran-reciters\.json/);
});

test('حزمة التفاسير ال٧٨ معروضة في الواجهة مع التنزيل', () => {
  const html = read('index.html');
  for (const id of ['tfPackCard', 'tfPackStatus', 'tfPackFill', 'tfPackBtn', 'tfPackCancel', 'tfPackDelete']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  const app = read('app.js');
  assert.match(app, /async function startTafsirPackDownload\(\)/);
  assert.match(app, /await plugin\.status\(\)/);
  // كل كتب الكتالوج في القائمة، لا الخمسة فقط
  assert.match(app, /const classical = \(catalog\.books \|\| \[\]\)\.map/);
});

test('الأذان محلي افتراضيًا: ملفات محزومة داخل التطبيق والباقي تنزيل', () => {
  const fs = require('node:fs');
  const catalog = JSON.parse(read('adhan-catalog.json'));
  const bundled = catalog.items.filter((i) => i.bundled);
  assert.ok(catalog.items.length >= 60, 'كل المؤذنين موجودون');
  assert.ok(bundled.length >= 18, 'الأذان المحلي الافتراضي');
  bundled.forEach((item) => {
    const asset = `android/app/src/main/assets/adhans/${item.id}.mp3`;
    const web = `audio/adhans/${item.id}.mp3`;
    assert.ok(fs.existsSync(asset) && fs.statSync(asset).size > 50_000, `ملف محزوم: ${item.id}`);
    assert.ok(fs.existsSync(web) && fs.statSync(web).size > 50_000, `ملف الويب: ${item.id}`);
  });
  const store = read('android/app/src/main/java/com/quran/mushaf/AdhanAudioStore.java');
  assert.match(store, /static String copyBundled\(/);
  assert.match(store, /getAssets\(\)\.open\("adhans\/"/);
  const ui = read('prayer-ui.js');
  assert.match(ui, /const bundled = item\.local \|\| '';/);
  assert.match(ui, /downloadAllAdhans/);
  assert.match(read('scripts/build-www.sh'), /audio\/adhans/);
  const data = read('prayer-data.js');
  assert.match(data, /"local": "audio\/adhans\//);
});

test('الإقامة إشعار «قم إلى صلاتك» بلا أي صوت إقامة', () => {
  const receiver = read(`${JAVA}/AdhanReceiver.java`);
  assert.match(receiver, /"قم إلى صلاتك"/);
  assert.doesNotMatch(read('prayer-ui.js'), /playIqamaTone/);
  assert.doesNotMatch(read('index.html'), /ptIqamaTone/);
});

test('تنبيه ما قبل الأذان: منبّه مجدول وإشعار صوتي بالدقائق', () => {
  const scheduler = read(`${JAVA}/AdhanScheduler.java`);
  assert.match(scheduler, /REQUEST_PRE = 41000/);
  assert.match(scheduler, /long preAt = at - preMinutes \* 60_000L;/);
  assert.match(scheduler, /preIntent\(context, i\)/);
  const receiver = read(`${JAVA}/AdhanReceiver.java`);
  assert.match(receiver, /ACTION_PRE_ADHAN/);
  assert.match(receiver, /"أذان " \+ label \+ " بعد " \+ minutes \+ " دقائق"/);
  const ui = read('prayer-ui.js');
  assert.match(ui, /function speakReminder\(text\)/);
  assert.match(ui, /preMinutes: 10,/);
});

test('البوصلة: سلسلة حساسات بديلة ومعايرة بالشمس وبالدرجات', () => {
  const plugin = read(`${JAVA}/SirajSensorsPlugin.java`);
  assert.match(plugin, /TYPE_ACCELEROMETER/);
  assert.match(plugin, /TYPE_MAGNETIC_FIELD/);
  assert.match(plugin, /TYPE_GYROSCOPE/);
  assert.match(plugin, /SensorManager\.getRotationMatrix\(/);
  assert.match(plugin, /emitCompositeHeading/);
  assert.match(plugin, /emitGyroHeading/);
  const ui = read('prayer-ui.js');
  assert.match(ui, /function calibrateBySun\(\)/);
  assert.match(ui, /function calibrateTo\(deg\)/);
  assert.match(ui, /enableFallbackDirection/);
  assert.match(read('index.html'), /id="qiblaSunBtn"/);
  assert.match(read('index.html'), /id="qiblaManualDeg"/);
});

test('تبويب القبلة مستقل ويُفتح من الإعدادات مع «مواقيت الصلاة»', () => {
  const html = read('index.html');
  assert.match(html, /<section class="view" id="view-qibla">/);
  assert.match(html, /class="settings-link" data-view="prayer"/);
  assert.match(html, /class="settings-link" data-view="qibla"/);
  assert.match(html, /مواقيت الصلاة/);
  assert.match(read('app.js'), /qibla: 'القبلة والبوصلة'/);
  assert.match(read('app.js'), /settings-link\[data-view\]/);
});

test('تقليب الصفحة ثلاثي الأبعاد سريع مع بقاء السحب', () => {
  const app = read('app.js');
  assert.match(app, /async function turnTo\(target, goNext\)/);
  assert.match(app, /function pageGhost\(node, zIndex\)/);
  assert.match(app, /perspective\(1300px\) rotateY/);
  assert.match(app, /await turnTo\(target, goNext\)/);
  assert.match(app, /stage\.addEventListener\('pointerdown'/);
  assert.match(read('index.html'), /\.page-ghost \{/);
});
