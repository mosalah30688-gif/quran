'use strict';

/*
 * خوارزمية إطفاء الشاشة بعد انتهاء الأذان.
 * الطبقة الأولى تُختبر هنا كمنطق صرف (بلا DOM)، والطبقة الثانية تربطها بالواجهة
 * وبالجسر الأصلي في أندرويد (SirajScreenGuard) وبحجب إبقاء الشاشة في app.js.
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const Sleep = require('../prayer-ui.js');
const read = (file) => fs.readFileSync(path.join(ROOT, file), 'utf8');

const NOW = 1_700_000_000_000;
const CFG = { enabled: true, graceMs: 30000, activeMs: 6000, stillMs: 2500 };

test('إطفاء الشاشة: لا يُطفئ أثناء الأذان', () => {
  const verdict = Sleep.decide({ adhanActive: true, lastInteraction: NOW }, NOW, CFG);
  assert.equal(verdict.action, 'arm');
  assert.equal(verdict.reason, 'adhan-playing');
});

test('إطفاء الشاشة: لا يُطفئ قبل انتهاء الأذان أصلًا', () => {
  const verdict = Sleep.decide({ adhanEndedAt: 0, lastInteraction: NOW }, NOW, CFG);
  assert.equal(verdict.action, 'arm');
  assert.equal(verdict.reason, 'waiting-adhan');
});

test('إطفاء الشاشة: المهلة تُحسب من لحظة انتهاء الأذان', () => {
  const early = Sleep.decide({ adhanEndedAt: NOW - 5000, lastInteraction: NOW - 5000 }, NOW, CFG);
  assert.equal(early.action, 'wait');
  assert.equal(early.reason, 'grace');
  assert.equal(early.waitMs, 25000);

  const late = Sleep.decide({ adhanEndedAt: NOW - 31000, lastInteraction: NOW - 31000 }, NOW, CFG);
  assert.equal(late.action, 'sleep');
  assert.equal(late.reason, 'idle-after-adhan');
  assert.equal(late.idleMs, 31000);
});

test('إطفاء الشاشة: أي لمسة تبدأ المهلة من جديد', () => {
  // انتهى الأذان قبل دقيقة، لكن آخر لمسة قبل ثانية ⇒ تعود المهلة كاملة
  const verdict = Sleep.decide({ adhanEndedAt: NOW - 60000, lastInteraction: NOW - 1000 }, NOW, CFG);
  assert.equal(verdict.action, 'wait');
  assert.equal(verdict.reason, 'grace');
  assert.equal(verdict.waitMs, 29000);
  assert.equal(verdict.idleMs, 1000);

  // لمسة أقدم من المهلة لا تمنع الإطفاء
  const idle = Sleep.decide({ adhanEndedAt: NOW - 60000, lastInteraction: NOW - 45000 }, NOW, CFG);
  assert.equal(idle.action, 'sleep');
});

test('إطفاء الشاشة: الهاتف المتحرك لا تُطفأ شاشته', () => {
  const moving = Sleep.decide({
    adhanEndedAt: NOW - 60000, lastInteraction: NOW - 60000,
    motion: true, lastMotion: NOW - 500,
  }, NOW, CFG);
  assert.equal(moving.action, 'wait');
  assert.equal(moving.reason, 'moving');

  const still = Sleep.decide({
    adhanEndedAt: NOW - 60000, lastInteraction: NOW - 60000,
    motion: true, lastMotion: NOW - 9000,
  }, NOW, CFG);
  assert.equal(still.action, 'sleep');
});

test('إطفاء الشاشة: تعطيل «لا تُطفئها ما دام يتحرك» يتجاهل إشارة الحركة', () => {
  const verdict = Sleep.decide({
    adhanEndedAt: NOW - 60000, lastInteraction: NOW - 60000,
    motion: true, lastMotion: NOW,
  }, NOW, { ...CFG, stillMs: 0 });
  assert.equal(verdict.action, 'sleep');
});

test('إطفاء الشاشة: شاشة مطفأة أو ميزة متوقفة ⇒ لا إجراء', () => {
  assert.equal(Sleep.decide({ adhanEndedAt: NOW - 60000, screenOn: false }, NOW, CFG).reason, 'screen-off');
  assert.equal(Sleep.decide({ adhanEndedAt: NOW - 60000 }, NOW, { ...CFG, enabled: false }).reason, 'disabled');
});

test('إطفاء الشاشة: الإعدادات غير الصالحة تُطبَّع إلى أرقام آمنة', () => {
  const cfg = Sleep.config({ graceMs: 'abc', activeMs: -5, stillMs: null });
  assert.equal(cfg.graceMs, 30000);
  assert.equal(cfg.activeMs, 500);
  assert.equal(cfg.stillMs, 2500);
  assert.equal(cfg.enabled, true);
  assert.equal(Sleep.config({ enabled: false }).enabled, false);
});

test('إطفاء الشاشة: يُربط ببدء الأذان وانتهائه داخل شاشة الأذان', () => {
  const ui = read('prayer-ui.js');
  // البداية عند تشغيل الأذان، والعدّ يبدأ من حدث الانتهاء أو الإيقاف أو الخطأ
  assert.match(ui, /state\.playingId = item\.id;[\s\S]{0,120}noteAdhanStarted\(\);/);
  assert.match(ui, /audio\.onended = \(\) => \{[\s\S]{0,240}noteAdhanEnded\('ended'\);/);
  assert.match(ui, /audio\.onerror = \(\) => noteAdhanEnded\('error'\);/);
  assert.match(ui, /function stopAdhan\(\)[\s\S]{0,320}noteAdhanEnded\('stopped'\);/);
  // إشارات الاستخدام: لمس وتمرير وحركة وحالة الشاشة
  ['pointerdown', 'touchstart', 'keydown', 'wheel'].forEach((name) => {
    assert.ok(ui.includes(`'${name}'`), `مستمع ${name}`);
  });
  assert.match(ui, /addEventListener\('devicemotion'/);
  assert.match(ui, /addListener\(SCREEN_PLUGIN, 'screen'/);
  // الجسر الأصلي والتنفيذ
  assert.match(ui, /const SCREEN_PLUGIN = 'SirajScreenGuard';/);
  assert.match(ui, /screenCall\('lockNow', \{ reason \}\)/);
  assert.match(ui, /screenCall\('setKeepAwake', \{ on: !!on \}\)/);
  assert.match(ui, /screenCall\('requestAdmin', \{\}\)/);
});

test('إطفاء الشاشة: إعدادات المستخدم تُحفظ وتظهر في واجهة المواقيت', () => {
  const html = read('index.html');
  ['ptSleepEnabled', 'ptSleepGrace', 'ptSleepStill', 'ptSleepAdmin', 'ptSleepStatus'].forEach((id) => {
    assert.ok(html.includes(`id="${id}"`), `حقل ${id}`);
  });
  const ui = read('prayer-ui.js');
  assert.match(ui, /sleepAfterAdhan: true/);
  assert.match(ui, /sleepGraceSeconds: 30/);
  assert.match(ui, /sleepStill: true/);
  assert.match(ui, /state\.config\.sleepAfterAdhan = e\.target\.checked;/);
  assert.match(ui, /state\.config\.sleepGraceSeconds = Math\.max\(0, Math\.min\(600/);
});

test('إطفاء الشاشة: app.js يتوقف عن طلب إبقاء الشاشة حين تقرّر الخوارزمية الإطفاء', () => {
  const app = read('app.js');
  assert.match(app, /function wakeBlocked\(\)/);
  assert.match(app, /window\.SirajIdleSleep\.isSleeping/);
  assert.match(app, /if \(wakeBlocked\(\)\) return false;/);
  assert.match(app, /window\.SirajWakeControl = \{/);
  assert.match(app, /release: \(\) => releaseWakeLock\(\)/);
});

test('إطفاء الشاشة: جسر أندرويد ومدير الجهاز مسجّلان في الحزمة', () => {
  const manifest = read('android/app/src/main/AndroidManifest.xml');
  assert.match(manifest, /android:name="\.SirajDeviceAdmin"/);
  assert.match(manifest, /android\.permission\.BIND_DEVICE_ADMIN/);
  assert.match(manifest, /android:resource="@xml\/siraj_device_admin"/);
  assert.match(manifest, /android\.app\.action\.DEVICE_ADMIN_ENABLED/);
  const policy = read('android/app/src/main/res/xml/siraj_device_admin.xml');
  assert.match(policy, /<force-lock \/>/);
  // سياسة واحدة فقط: لا محو بيانات ولا كلمات مرور
  assert.doesNotMatch(policy, /wipe-data|reset-password|force-lock-all/);
  const activity = read('android/app/src/main/java/com/quran/mushaf/MainActivity.java');
  assert.match(activity, /registerPlugin\(SirajScreenGuardPlugin\.class\)/);
  const plugin = read('android/app/src/main/java/com/quran/mushaf/SirajScreenGuardPlugin.java');
  assert.match(plugin, /@CapacitorPlugin\(name = "SirajScreenGuard"\)/);
  ['capabilities', 'requestAdmin', 'revokeAdmin', 'lockNow', 'setKeepAwake'].forEach((method) => {
    assert.match(plugin, new RegExp(`public void ${method}\\(PluginCall call\\)`), `دالة ${method}`);
  });
  assert.match(plugin, /ACTION_SCREEN_OFF/);
  assert.match(plugin, /FLAG_KEEP_SCREEN_ON/);
});
