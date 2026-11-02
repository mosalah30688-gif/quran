'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (name) => fs.readFileSync(path.join(root, name), 'utf8');

const app = read('app.js');
const html = read('index.html');
const context = read('smart-context.js');
const services = read('smart-services.js');
const tajweedLearning = read('tajweed-learning.js');
const tajweedLoader = read('tajweed-curriculum-loader.js');
const tajweedCatalog = JSON.parse(read('tajweed-learning-catalog.json'));
const build = read('scripts/build-www.sh');
const publish = read('scripts/publish-update.sh');
const sw = read('sw.js');
const androidManifest = read('android/app/src/main/AndroidManifest.xml');
const smartPlugin = read('android/app/src/main/java/com/quran/mushaf/SmartDevicePlugin.java');
const smartReceiver = read('android/app/src/main/java/com/quran/mushaf/SmartNotificationReceiver.java');
const reminderReceiver = read('android/app/src/main/java/com/quran/mushaf/ReminderReceiver.java');
const smartTimeWindow = read('android/app/src/main/java/com/quran/mushaf/SmartTimeWindow.java');

test('smart scripts load in dependency order before the application', () => {
  const fallback = html.slice(html.indexOf('if (!applied)'));
  const contextAt = fallback.indexOf("run(null, 'smart-context.js')");
  const servicesAt = fallback.indexOf("run(null, 'smart-services.js')");
  const tajweedAt = fallback.indexOf("run(null, 'tajweed-learning.js')");
  const loaderAt = fallback.indexOf("run(null, 'tajweed-curriculum-loader.js')");
  const appAt = fallback.indexOf("run(null, 'app.js')");
  assert.ok(contextAt >= 0 && servicesAt > contextAt && tajweedAt > servicesAt
    && loaderAt > tajweedAt && appAt > loaderAt);
});

test('opt-in and local privacy controls are visible and explicit', () => {
  for (const id of [
    'setSmartEnabled', 'setSmartNotifications', 'smartQuietStart', 'smartQuietEnd',
    'smartDailyMax', 'smartCooldown', 'smartRetention', 'smartDeleteData',
  ]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(html, /اختيارك صريح ويمكن إيقافه/);
  assert.match(html, /لا يقرأ الرسائل أو المواقع التي تزورها أو الحافظة/);
  assert.match(html, /لا يرسل ملف عادات إلى خادم/);
});

test('smart modules have no network primitive', () => {
  const source = context + '\n' + services + '\n' + tajweedLearning + '\n' + tajweedLoader;
  assert.doesNotMatch(source, /\bfetch\s*\(/);
  assert.doesNotMatch(source, /XMLHttpRequest|WebSocket|sendBeacon/);
});

test('UI records all integrated service families with bounded event names', () => {
  for (const event of [
    'APP_OPEN', 'APP_FOREGROUND', 'READING_SESSION_END', 'READ_PAGE',
    'PLAY_RECITATION', 'SERVICE_OPEN', 'COMPLETE_ADHKAR',
    'START_MEMORIZATION', 'COMPLETE_MEMORIZATION', 'OPEN_TAFSIR', 'OPEN_TAJWEED',
  ]) assert.match(app, new RegExp(`type: '${event}'`));
  assert.match(app, /new SmartContextAPI\.SmartContextEngine/);
  assert.match(app, /smartEngine\.snapshot\(\)/);
});

test('suggestion card exposes action, deferral, dismissal, and explanation', () => {
  for (const id of [
    'smartSuggestion', 'smartSuggestionOpen', 'smartSuggestionLater',
    'smartSuggestionDismiss', 'smartSuggestionWhy',
  ]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(app, /markShown\(candidate, suggestionId, 'suggestion'\)/);
  assert.match(app, /recordSmartFeedback\('open'\)/);
  assert.match(app, /recordSmartFeedback\('snooze'\)/);
  assert.match(app, /recordSmartFeedback\('dismiss'\)/);
});

test('sleep, quiet hours, caps, and cooldown remain hard gates', () => {
  assert.match(context, /if \(context\.likelySleeping\) return 'LIKELY_SLEEPING'/);
  assert.match(context, /if \(context\.quietHours\) return 'QUIET_HOURS'/);
  assert.match(context, /return 'DAILY_CAP'/);
  assert.match(context, /return 'COOLDOWN'/);
  assert.doesNotMatch(context, /allowDuringSleep|allowDuringQuiet/);
});

test('smart and tajweed engines are included in offline and update channels', () => {
  for (const source of [build, publish, sw]) {
    assert.match(source, /smart-context\.js/);
    assert.match(source, /smart-services\.js/);
    assert.match(source, /tajweed-learning\.js/);
    assert.match(source, /tajweed-curriculum-loader\.js/);
    assert.match(source, /tajweed-learning-catalog\.json/);
    assert.match(source, /tajweed-scope-registry\.json/);
  }
  assert.match(sw, /siraj-shell-v15/);
});

test('JSON update overlay is hashed, stored outside localStorage, and fail-closed', () => {
  assert.match(html, /SIRAJ_UPDATE_DATA_FILES/);
  assert.match(html, /SIRAJ_UPDATE_VERSION/);
  assert.match(app, /siraj-update-assets/);
  assert.match(app, /replaceUpdateDataAssets\(manifest\.version, dataFiles\)/);
  assert.match(app, /verifyDownloadedUpdateFile\(f, txt, manifest\.sha256\)/);
  assert.match(app, /missing update asset/);
  assert.match(app, /TajweedCurriculumLoaderAPI\.loadRegistryCurricula/);
  assert.match(publish, /hashlib\.sha256/);
  assert.match(publish, /tajweed-curricula/);
});

test('independent reader colors require an approved exact-scope curriculum', () => {
  assert.match(html, /id="setTajweedScopeRow"/);
  assert.match(html, /id="setTajweedScope"/);
  assert.match(app, /function syncTajweedScopeSelector\(\)/);
  assert.match(app, /normalizeDisplay\(item\.display\)/);
  assert.match(app, /اختر الطريق والوجه والطبعة/);
  assert.match(app, /settings\.tajweedScopes/);
  assert.match(app, /function currentApprovedTajweedCurriculum\(\)/);
  assert.match(app, /curriculum\?\.status === 'APPROVED'/);
  assert.match(app, /curriculum\.publishableAsApproved === true/);
  assert.match(app, /renderIndependentTajweed\(approvedCurriculum, x\.s, x\.n, x\.text\)/);
  assert.match(app, /showIndependentTajweedPanel/);
  assert.match(app, /data-tj-rules/);
  assert.match(app, /لا توجد طبقة ألوان معتمدة لهذا النطاق/);
  assert.match(html, /\.tj-independent-mark/);
});

test('tajweed spaced review is local, scoped, and wired to feedback events', () => {
  for (const id of [
    'tjStartLearning', 'tjLearningCard', 'tjRevealAnswer', 'tjCardAnswer',
    'tjResetLearning', 'tjLearningStats',
  ]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(app, /new TajweedLearningAPI\.TajweedLearningEngine/);
  assert.match(app, /type: 'TAJWEED_ANSWER'/);
  assert.match(app, /type: 'COMPLETE_TAJWEED_LESSON'/);
  assert.match(app, /لا تُعرض أحكام حفص أو أي طبقة عامة/);
  assert.match(app, /tajweedLearningEngine\.resetScope/);
});

test('tajweed catalogue is fail-closed until scholarly and path review', () => {
  const hafs = tajweedCatalog.curricula[0];
  assert.equal(hafs.status, 'PENDING_SCHOLARLY_REVIEW');
  assert.equal(hafs.publishableAsApproved, false);
  assert.equal(hafs.scope.tariq, 'source-unspecified');
  assert.equal(hafs.rules.length, 17);
  assert.deepEqual(tajweedCatalog.unavailable.map((item) => item.settingId).sort(),
    ['duri', 'qalun', 'warsh']);
});

test('Android smart notifications are separate opt-in and feed outcomes back locally', () => {
  assert.match(app, /requestNotifications\(\)/);
  assert.match(app, /planNextDecision/);
  assert.match(app, /consumeSmartNativeFeedback/);
  assert.match(app, /SmartContextAPI\.chooseIntervention/);
  assert.match(smartPlugin, /name = "SmartDevice"/);
  assert.match(smartPlugin, /consumeFeedback/);
  assert.match(smartReceiver, /SmartFeedbackStore\.record\(context, "shown"/);
  assert.match(androidManifest, /\.SmartNotificationReceiver/);
  assert.match(androidManifest, /\.SmartNotificationActionReceiver/);
});

test('native delivery repeats the sleep and quiet hard gates without sensitive permissions', () => {
  assert.match(smartReceiver, /SmartTimeWindow\.nextAllowedAt/);
  assert.match(reminderReceiver, /SmartTimeWindow\.nextAllowedAt/);
  assert.match(app, /respectSafety: !!smartEngine\?\.config\.enabled/);
  assert.match(smartTimeWindow, /contains\(minute, quietStart, quietEnd\)/);
  assert.match(smartTimeWindow, /contains\(minute, sleepStart, sleepEnd\)/);
  assert.doesNotMatch(androidManifest, /ACCESS_FINE_LOCATION|ACCESS_COARSE_LOCATION|READ_CONTACTS|RECORD_AUDIO/);
  assert.match(smartPlugin, /isInteractive\(\)/);
  assert.match(smartPlugin, /isKeyguardLocked\(\)/);
});

test('About remains the last settings control after adding smart settings', () => {
  const settings = html.match(/<section class="view" id="view-settings">([\s\S]*?)<\/section>/);
  assert.ok(settings);
  const smartAt = settings[1].indexOf('id="smartSettingsCard"');
  const aboutAt = settings[1].indexOf('id="settingsAboutBtn"');
  assert.ok(smartAt >= 0 && aboutAt > smartAt);
  assert.match(settings[1].slice(aboutAt), /<\/button>\s*$/);
});
