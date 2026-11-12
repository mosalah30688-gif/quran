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
const androidWorkflow = read('.github/workflows/android.yml');
const windowsWorkflow = read('.github/workflows/windows-v1.yml');
const linuxWorkflow = read('.github/workflows/linux-appimage.yml');
const updateFeatureReader = read('scripts/read_update_features.py');
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
  assert.match(sw, /siraj-shell-v\d+/);
});

test('madani page fitting: مقاس واحد لكل الصفحة وتمدد طولي فقط بلا خروج عن الهوامش', () => {
  assert.match(app, /querySelectorAll\('\.mline'\)/);
  assert.match(app, /const widthAt = \(size\) =>/);
  assert.match(app, /for \(let i = 0; i < 14; i \+= 1\)/);
  assert.match(app, /const size = Math\.max\(9, Math\.min\(90, fitSize \* scale\)\)/);
  // التكبير يفعّل الالتفاف بمقاس موحّد بدل مدّ الصفحة أفقيًا
  assert.match(app, /const wrapping = scale > 1\.001;/);
  assert.match(app, /body\.classList\.toggle\('wrapping', wrapping\)/);
  assert.match(app, /--mushaf-w', wrapping \? '100%'/);
  assert.match(html, /#pageBody\.madani-lines\.wrapping \.mline/);
  // حجم الخط داخل الإعدادات فقط (لا شريط في رأس المصحف)
  assert.match(html, /id="setSize"/);
  assert.doesNotMatch(html, /id="fontRange"/);
  assert.doesNotMatch(html, /id="fontInc"/);
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

test('every published update carries a concise what-is-new notification', () => {
  assert.match(app, /function publicUpdateFeatures\(manifest\)/);
  assert.match(app, /\\nالجديد:/);
  assert.match(app, /!availableVersion \|\| !features\.length/);
  // صار التحديث يُقاس برقم البناء لا برقم الإصدار الظاهر (1.0.0 ثابت بين التحديثات الصغيرة)
  assert.match(app, /Number\(m\.build\) > currentBuild\(\)/);
  assert.match(publish, /validate_update_features\(sys\.argv\[2:\]\)/);
  assert.match(publish, /manifest\["features"\] = features/);
  assert.match(publish, /manifest\.get\("features"\) == features/);
  assert.match(androidWorkflow, /UPDATE_FEATURES: \$\{\{ inputs\.features \}\}/);
  assert.doesNotMatch(androidWorkflow, /data\['features'\] = \['هوية أوضح/);
  assert.match(updateFeatureReader, /features_version != app_version/);
  for (const workflow of [windowsWorkflow, linuxWorkflow]) {
    assert.match(workflow, /scripts\/read_update_features\.py/);
    assert.match(workflow, /FEATURE_ARGS=\(\)/);
    assert.doesNotMatch(workflow, /--feature "هوية أوضح لسراج/);
  }
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
    'tjResetLearning', 'tjLearningStats', 'tjMastery', 'tjWeakCount',
    'tjUnlockedCount', 'tjPathFill', 'tjIntensity', 'tjQuizChoices',
    'tjSessionSummary',
  ]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(app, /new TajweedLearningAPI\.TajweedLearningEngine/);
  assert.match(app, /tajweedLearningEngine\.plan\(/);
  assert.match(app, /tajweedLearningEngine\.pathStats\(/);
  assert.match(app, /TajweedLearningAPI\.recognitionOptions\(/);
  assert.match(app, /activityType: 'recognize'/);
  assert.match(app, /activityType: 'apply'/);
  assert.match(app, /type: 'TAJWEED_ANSWER'/);
  assert.match(app, /type: 'COMPLETE_TAJWEED_LESSON'/);
  assert.match(app, /لا تُعرض أحكام حفص أو أي طبقة عامة/);
  assert.match(app, /tajweedLearningEngine\.resetScope/);
});

test('learning expansion preserves the existing colored reader and word explanations', () => {
  // الواجهة الجديدة تعرض الروايات الأربع في القائمة، وتُبقي ألوان التجويد كمفتاح مستقل.
  for (const value of ['quran-uthmani', 'warsh', 'qalun', 'duri']) {
    assert.match(html, new RegExp(`<option value="${value}">`));
  }
  // مفتاح «تفعيل ألوان التجويد» أُزيل من الإعدادات بطلب المستخدم، وبقيت طبقة التلوين نفسها.
  assert.ok(!/id="setTajweed"/.test(html));
  assert.match(html, /id="tjPanel"/);
  assert.match(html, /\.tj-n \{ color:/);
  assert.match(app, /function renderTajweed\(raw\)/);
  assert.match(app, /function showTajweedPanel\(code\)/);
  assert.match(app, /settings\.riwaya === 'quran-tajweed' \|\| settings\.tajweed/);
  assert.match(app, /if \(tj\) showTajweedPanel/);
});

test('tajweed catalogue is fail-closed until scholarly and path review', () => {
  const hafs = tajweedCatalog.curricula[0];
  assert.equal(hafs.status, 'PENDING_SCHOLARLY_REVIEW');
  assert.equal(hafs.publishableAsApproved, false);
  assert.equal(hafs.scope.tariq, 'source-unspecified');
  assert.equal(hafs.rules.length, 17);
  assert.deepEqual(hafs.pedagogy.activityStages, ['learn', 'recognize', 'apply']);
  assert.equal(hafs.pedagogy.planningPolicy, 'WEAK_FIRST_THEN_DUE_THEN_NEW');
  assert.ok(hafs.rules.every((rule) => rule.learning.activities.length === 3));
  assert.ok(hafs.rules.every((rule) => rule.learning.level >= 1 && rule.learning.level <= 3));
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
  // «رفيق اليوم» لا يطلب أي إذن حسّاس. إذن الموقع مخصّص لمواقيت الصلاة والقبلة فقط
  // (يُطلب من المستخدم عند الضغط على «حدّد موقعي»)، ولذلك نفصل بينهما في الفحص.
  assert.doesNotMatch(androidManifest, /READ_CONTACTS|RECORD_AUDIO|READ_SMS|ACCESS_BACKGROUND_LOCATION/);
  assert.doesNotMatch(smartPlugin, /ACCESS_FINE_LOCATION|ACCESS_COARSE_LOCATION|LocationManager/);
  assert.match(androidManifest, /ACCESS_COARSE_LOCATION/);
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

test('التظليل الحر: طبقة تظليل بلون ظاهر وقائمة لا تغطي الرأس ولا شريط التنقل', () => {
  assert.match(html, /#hlLayer i \{\s*position: absolute/);
  assert.match(html, /background: rgba\(15, 110, 90, \.26\)/);          // لون احتياطي صريح
  assert.match(html, /#pageBody \*::selection \{ background: rgba\(15, 110, 90, \.22\)/);
  assert.match(app, /function drawHighlight\(/);
  assert.match(app, /const topBound = \(hdr \? hdr\.getBoundingClientRect\(\)\.bottom : 8\) \+ 8;/);
  assert.match(app, /bottomBound/);
  assert.match(html, /min-width: 158px/);
});

test('كل كتب التفسير في قائمة واحدة متاحة بلا زر تنزيل ولا كلمة «محلية»', () => {
  // لا مجموعات ولا تعطيل: كل كتاب قابل للاختيار ويعمل مباشرة.
  assert.ok(app.includes('return TAFSIRS.map(([id, name]) => `<option value="${id}">${name}</option>`).join(\'\');'));
  assert.ok(!/optgroup/.test(app.slice(app.indexOf('function tafsirOptionsHtml'), app.indexOf('function fillSettings'))));
  assert.ok(!/كتب الحزمة المحلية|الحزمة المحلية|\(٧٣\)/.test(app));
  assert.match(app, /async function fetchOnlineTafsir\(surah, ayah, edition\)/);
  assert.match(app, /const ONLINE_TAFSIRS = new Set\(/);
  assert.match(app, /\['ar\.miqbas', 'تنوير المقباس'\]/);
  // كتب الموسوعة تُجهَّز عند أول اختيار ثم تُقرأ من الجهاز
  assert.match(app, /QP_BOOK_BASE = 'https:\/\/quranpedia\.net\/dumps\/tafsir-book-'/);
  assert.match(app, /async function loadTafsirBook\(bookId\)/);
  assert.match(app, /async function tafsirForAyah\(s, n, edition\)/);
  assert.match(app, /DecompressionStream\('gzip'\)/);
  assert.match(app, /indexedDB\.open\('siraj-tafsir-books', 1\)/);
});

test('مصحف أوضح: خط معرّض وخانة صفحة صغيرة وأزرار كلمات واضحة', () => {
  assert.match(html, /webkit-text-stroke-width: calc\(var\(--quran-size, 26px\) \* 0\.018\)/);
  assert.match(html, /max-width: 3\.6ch/);
  assert.match(html, /width: 3ch; text-align: center/);
  assert.match(html, /font-size: clamp\(12px, 3\.6vw, 14px\); font-weight: 800/);
  assert.match(app, /const FLIP_RATIO = 0\.15;/);
  assert.match(app, /const FLIP_VELOCITY = 0\.11;/);
  assert.doesNotMatch(app, /rotateY/);
});

test('سبع روايات للقراءة والاستماع مع قرّاء موثّقين', () => {
  const riwayat = JSON.parse(read('quran-riwayat.json')).riwayat;
  assert.deepEqual(Object.keys(riwayat).sort(),
    ['bazzi', 'duri', 'qalun', 'qunbul', 'shubah', 'susi', 'warsh']);
  for (const [id, rows] of Object.entries(riwayat)) {
    assert.ok(rows.length > 6000, `${id} rows missing`);
    assert.ok(rows.every((row) => row[2] >= 1 && row[2] <= 604), `${id} page out of range`);
  }
  assert.match(app, /const RIW_IDS = \['warsh', 'qalun', 'duri', 'shubah', 'susi', 'bazzi', 'qunbul'\]/);
  for (const id of ['shubah', 'susi', 'bazzi', 'qunbul']) {
    assert.match(app, new RegExp(`\\b${id}: \\[`));
    assert.match(html, new RegExp(`<option value="${id}">`));
  }
  // القرّاء المستخدمون لكل رواية جديدة
  for (const reciter of ['shubah_deeban', 'shubah_saber', 'shubah_hudhaify',
    'susi_sufi', 'bazzi_deeban', 'bazzi_kameny', 'qunbul_deeban']) {
    assert.match(app, new RegExp(`'${reciter}'`));
  }
});

test('التلاوة المتزامنة: الآية الجارية تضيء وتُمرَّر الشاشة إليها دون إنترنت', () => {
  const src = read('app.js');
  // الافتراضي مفعّل، ومفتاحه في الإعدادات
  assert.match(src, /function syncReadingEnabled\(\) \{\s*return !isRiw\(\) && ayahSyncAvailable\(\);/);
  const settings = read('index.html');
  assert.ok(!settings.includes('id="setSyncPlay"'), 'التلاوة المتزامنة إجبارية بلا مفتاح');
  assert.match(src, /function syncReadingEnabled\(\) \{\s*return !isRiw\(\) && ayahSyncAvailable\(\);/, 'التزامن يجب أن يكون إجباريًا');
  // منطق التزامن
  for (const fn of ['function syncReadingEnabled', 'function focusSyncedAyah', 'function preloadAyahAudio', 'function ayahSyncAvailable']) {
    assert.ok(src.includes(fn), `دالة مفقودة: ${fn}`);
  }
  // الإبراز والتمرير داخل القراءة
  assert.match(src, /classList\.toggle\('syncing'/);
  assert.match(src, /scrollIntoView\(\{ block: 'center', behavior: 'smooth' \}\)/);
  // لمس الآية ينقل التلاوة إليها في وضع التزامن
  assert.match(src, /if \(play\.active && syncReadingEnabled\(\)\) \{\s*playAyah\(a\);/);
  // ملف السورة الكاملة يبقى متاحًا عند إطفاء الخيار
  assert.match(src, /if \(!syncReady && settings\.surahAudio !== false/);
  // صوت الآية من الملف المحلي أولاً ثم الشبكة، مع تحميل مسبق للآية التالية
  assert.match(src, /preloadAyahAudio\(a\.s, a\.n \+ 1\)/);
  assert.match(src, /const local = a\.fromSurah \? null : await localAudioUrl/);
  // توهج ذهبي للآية الجارية
  assert.match(settings, /#pageBody\.syncing \.ay\.playing \{[^}]*rgba\(232,181,82/);
});

test('الورد والختمة: هدف اختياري وحلقة تقدّم ودقائق قراءة وشارات ومشاركة', () => {
  const src = read('app.js');
  const html = read('index.html');
  // الهدف: اختياري بالكامل، ولا يغلق شيئًا
  assert.ok(html.includes('id="wdGoalChoices"'), 'أزرار الهدف اليومي مفقودة');
  assert.ok(html.includes('id="wdShare"'), 'زر مشاركة التقدم مفقود');
  assert.ok(html.includes('بلا هدف'), 'خيار «بلا هدف» مطلوب');
  for (const fn of ['function wirdGoal', 'function setWirdGoal', 'function renderWirdRing',
    'function wirdBadges', 'function shareWirdProgress', 'function pagesAr', 'function trackReadingMinutes']) {
    assert.ok(src.includes(fn), `دالة مفقودة: ${fn}`);
  }
  // دقائق القراءة تُحتسب داخل القارئ فقط وتُخزَّن في الإحصاءات
  assert.match(src, /st\.minutes\[todayKey\(\)\]/);
  assert.match(src, /if \(name === 'reader'\) \{ readerActiveSince = Date\.now\(\); \}/);
  // لا بوابات ولا تعطيل
  assert.ok(html.includes('id="wdBadges"'), 'شبكة الشارات مفقودة');
  assert.doesNotMatch(src, /disabled\s*=\s*true[^\n]*wird/i);
  // الختمة والورد ما زالا يعملان تلقائيًا
  assert.match(src, /function recordWirdPage/);
  assert.match(src, /w\.finished\.push\(\{ start: w\.startDate/);
  // صياغة عربية سليمة
  assert.ok(src.includes("'صفحة واحدة'") && src.includes("'صفحتان'"));
});

test('انتقال فوري بين الصفحات بلا حركة ولا صوت ورق', () => {
  const src = read('app.js');
  const html = read('index.html');
  // لا حركة تقليب ولا طبقات
  assert.doesNotMatch(src, /function pageGhost/);
  assert.doesNotMatch(src, /function runTurn/);
  assert.doesNotMatch(html, /page-ghost/);
  assert.doesNotMatch(html, /rotateY/);
  assert.match(src, /async function turnTo\(target, goNext\)/);
  assert.match(src, /await showPage\(target, \{ scroll: true \}\)/);
  // ميزة صوت الورق أُلغيت بالكامل
  assert.doesNotMatch(src, /playPaperSound|paperSfx|paperSound/);
  assert.ok(!html.includes('setPaperSound'), 'مفتاح صوت الورق يجب أن يُحذف');
  assert.ok(!require('node:fs').existsSync(path.join(root, 'media/sfx')), 'ملفات صوت الورق يجب أن تُحذف');
  assert.ok(!read('sw.js').includes('media/sfx'), 'لا تخزين مسبق لأصوات الورق');
  // السحب يظل يعمل
  assert.match(src, /async function flipBySwipe/);
});
