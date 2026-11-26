/*
 * Siraj Prayer UI v1 — «المواقيت»
 *
 * واجهة مستقلة لمواقيت الصلاة والأذان والإقامة والقبلة، تعمل فوق SirajPrayerTimes
 * و SirajPrayerData. تخزّن إعدادها في localStorage تحت مفتاح واحد، ولا ترسل شيئًا
 * إلى أي خادم. تُهيّأ من app.js عبر SirajPrayerUI.init().
 */
(function (root) {
  'use strict';


  // ==========================================================================
  // خوارزمية إطفاء الشاشة بعد انتهاء الأذان
  // --------------------------------------------------------------------------
  // المنطق أدناه صرف (بلا DOM وبلا مؤقتات) حتى يُختبر وحده في tests/idle-sleep.test.js،
  // ثم يستخدمه المُنسّق في نهاية الملف مع إشارات الاستخدام الحقيقية.
  //
  // المصطلحات:
  //  • إشارة استخدام: أي لمسة/ضغطة/تمرير، أو حركة ملموسة للهاتف.
  //  • نافذة النشاط activeMs: إن وقعت إشارة خلالها فالمستخدم يستخدم الهاتف الآن.
  //  • السكون stillMs: الهاتف مستقر (لا حركة) ⇒ لا أحد يحمله.
  //  • المهلة graceMs: تُحسب من لحظة انتهاء الأذان قبل السماح بالإطفاء.
  // ==========================================================================
  const SLEEP_DEFAULTS = Object.freeze({ enabled: true, graceMs: 30000, activeMs: 6000, stillMs: 2500 });

  // null و '' ليستا صفرًا هنا: تعنيان «لم يُضبط» فتُستعمل القيمة الافتراضية.
  function sleepNumber(value, fallback) {
    if (value === null || value === undefined || value === '') return fallback;
    return Number.isFinite(Number(value)) ? Number(value) : fallback;
  }

  function sleepTime(value) {
    const n = Number(value);
    return Number.isFinite(n) && n > 0 ? n : 0;
  }

  /** يطبّع إعدادات المستخدم إلى أرقام آمنة. */
  function sleepConfig(config) {
    const src = config && typeof config === 'object' ? config : {};
    return {
      enabled: src.enabled !== false,
      graceMs: Math.max(0, sleepNumber(src.graceMs, SLEEP_DEFAULTS.graceMs)),
      activeMs: Math.max(500, sleepNumber(src.activeMs, SLEEP_DEFAULTS.activeMs)),
      stillMs: Math.max(0, sleepNumber(src.stillMs, SLEEP_DEFAULTS.stillMs)),
    };
  }

  /**
   * القرار: هل ننتظر أم نطفئ الشاشة الآن؟
   *
   * «لحظة الترك» = الأحدث بين انتهاء الأذان وآخر إشارة استخدام؛ فكل لمسة تبدأ
   * المهلة من جديد، ولا يمكن أن تطفأ الشاشة والمستخدم يلمسها.
   *
   * @param {{adhanActive?:boolean, adhanEndedAt?:number, lastInteraction?:number,
   *          lastMotion?:number, motion?:boolean, screenOn?:boolean}} input إشارات اللحظة
   * @param {number} now الزمن الحالي بالمللي ثانية
   * @param {object} config إعدادات المستخدم
   * @returns {{action:'cancel'|'arm'|'wait'|'sleep', reason:string, waitMs:number, idleMs:number}}
   */
  function sleepDecision(input, now, config) {
    const cfg = sleepConfig(config);
    const at = sleepNumber(now, Date.now());
    const signal = input && typeof input === 'object' ? input : {};
    const endedAt = sleepTime(signal.adhanEndedAt);
    const lastUse = sleepTime(signal.lastInteraction);
    const leftAt = Math.max(endedAt, lastUse);
    const idleMs = endedAt ? Math.max(0, at - leftAt) : 0;
    const verdict = (action, reason, waitMs) => ({
      action,
      reason,
      waitMs: Math.max(0, Math.round(sleepNumber(waitMs, 0))),
      idleMs: Math.round(idleMs),
    });

    if (!cfg.enabled) return verdict('cancel', 'disabled');
    if (signal.adhanActive) return verdict('arm', 'adhan-playing');
    if (!endedAt) return verdict('arm', 'waiting-adhan');
    if (signal.screenOn === false) return verdict('cancel', 'screen-off');
    if (idleMs < cfg.graceMs) return verdict('wait', 'grace', cfg.graceMs - idleMs);
    if (signal.motion && cfg.stillMs > 0) {
      const lastMotion = sleepTime(signal.lastMotion);
      const sinceMotion = lastMotion ? at - lastMotion : Number.POSITIVE_INFINITY;
      if (sinceMotion < cfg.stillMs) return verdict('wait', 'moving', cfg.stillMs - sinceMotion);
    }
    return verdict('sleep', 'idle-after-adhan');
  }

  // --------------------------------------------------------------------------
  // المرحلة الثانية: إغلاق التطبيق بعد أن تُطفأ الشاشة ويبقى الهاتف مهجورًا.
  // الإغلاق لا يحدث أبدًا والشاشة مضاءة، ولا في وجود تلاوة تعمل، ولا قبل التأخير.
  // --------------------------------------------------------------------------
  const CLOSE_DEFAULTS = Object.freeze({ enabled: true, delayMs: 20000 });

  function closeConfig(config) {
    const src = config && typeof config === 'object' ? config : {};
    return {
      enabled: src.enabled !== false,
      delayMs: Math.max(0, sleepNumber(src.delayMs, CLOSE_DEFAULTS.delayMs)),
    };
  }

  /** @returns {{action:'cancel'|'wait'|'close', reason:string, waitMs:number, idleMs:number}} */
  function closeDecision(input, now, config) {
    const cfg = closeConfig(config);
    const at = sleepNumber(now, Date.now());
    const signal = input && typeof input === 'object' ? input : {};
    const sleptAt = sleepTime(signal.sleptAt);
    const lastUse = sleepTime(signal.lastInteraction);
    const leftAt = Math.max(sleptAt, lastUse);
    const idleMs = sleptAt ? Math.max(0, at - leftAt) : 0;
    const verdict = (action, reason, waitMs) => ({
      action,
      reason,
      waitMs: Math.max(0, Math.round(sleepNumber(waitMs, 0))),
      idleMs: Math.round(idleMs),
    });

    if (!cfg.enabled) return verdict('cancel', 'close-disabled');
    if (!sleptAt) return verdict('cancel', 'not-slept');
    if (signal.screenOn !== false) return verdict('cancel', 'screen-on');
    if (signal.audioPlaying) return verdict('wait', 'audio-playing');
    if (idleMs < cfg.delayMs) return verdict('wait', 'close-delay', cfg.delayMs - idleMs);
    return verdict('close', 'app-idle');
  }

  const SleepCore = {
    defaults: SLEEP_DEFAULTS,
    config: sleepConfig,
    decide: sleepDecision,
    closeDefaults: CLOSE_DEFAULTS,
    closeConfig,
    decideClose: closeDecision,
  };
  root.SirajIdleSleep = Object.assign(root.SirajIdleSleep || {}, SleepCore);
  if (typeof module !== 'undefined' && module.exports) module.exports = SleepCore;

  const PT = root.SirajPrayerTimes;
  const DATA = root.SirajPrayerData;
  if (!PT || !DATA) return;

  const KEY = 'quran:prayer';
  const ADHAN_CACHE = 'siraj-adhan-v1';
  const PRAYER_KEYS = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha'];
  const DEFAULTS = {
    cityIndex: -1,
    lat: DATA.cities[0].lat,
    lng: DATA.cities[0].lng,
    tz: DATA.cities[0].tz,
    cityName: DATA.cities[0].n,
    countryName: DATA.cities[0].c,
    method: DATA.cities[0].m,
    madhab: 'shafi',
    highLatitude: 'middle',
    adjustments: { fajr: 0, dhuhr: 0, asr: 0, maghrib: 0, isha: 0 },
    use24h: false,
    adhanEnabled: true,
    adhanId: 'haram-makkah',
    fajrAdhanId: 'fajr-makkah',
    adhanVolume: 1,
    preMinutes: 10,
    iqamaEnabled: true,
    iqamaMinutes: { fajr: 20, dhuhr: 15, asr: 15, maghrib: 10, isha: 15 },
    // إطفاء الشاشة بعد انتهاء الأذان حين يترك المستخدم الهاتف
    sleepAfterAdhan: true,
    sleepGraceSeconds: 30,
    sleepStill: true,
    // إغلاق التطبيق بعد أن تُطفأ الشاشة ويبقى الهاتف مهجورًا
    closeAfterAdhan: true,
    closeDelaySeconds: 20,
  };

  const els = {};
  // تهريب HTML آمن داخل هذا الملف (app.js يحتفظ بنسخته الخاصة)
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const state = {
    config: null,
    today: null,
    next: null,
    ticking: null,
    audio: null,
    playingId: null,
    adhanCache: new Map(),
    adhanFilter: '',
    adhanScreenOpen: false,
    adhanLive: false,
    downloaded: new Set(),
    iqamaTimers: [],
    lastFired: '',
    firedLoaded: false,
    toast: null,
    compass: { active: false, heading: null, raw: null, mode: '', offset: 0, handler: null, listening: false, fallback: false },
    altMethod: '',
    gpsWatch: null,
    gpsHeading: null,
    gpsLast: null,
    compassWatchdog: null,
    aqsaBearing: null,
  };

  const $ = (sel) => document.querySelector(sel);
  const el = (id) => document.getElementById(id);
  const num = (value, fallback) => (Number.isFinite(Number(value)) ? Number(value) : fallback);

  // ---------- التخزين ----------
  function loadConfig() {
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { saved = null; }
    const config = Object.assign({}, DEFAULTS, saved && typeof saved === 'object' ? saved : {});
    config.adjustments = Object.assign({}, DEFAULTS.adjustments, config.adjustments || {});
    config.iqamaMinutes = Object.assign({}, DEFAULTS.iqamaMinutes, config.iqamaMinutes || {});
    if (!DATA.adhans.some((a) => a.id === config.adhanId)) config.adhanId = DEFAULTS.adhanId;
    if (!DATA.adhans.some((a) => a.id === config.fajrAdhanId)) config.fajrAdhanId = DEFAULTS.fajrAdhanId;
    if (!PT.METHODS[config.method]) config.method = DEFAULTS.method;
    if (!PT.HIGH_LATITUDE[config.highLatitude]) config.highLatitude = DEFAULTS.highLatitude;
    state.config = config;
    return config;
  }

  function saveConfig() {
    try { localStorage.setItem(KEY, JSON.stringify(state.config)); } catch { /* مساحة ممتلئة */ }
    if (typeof syncBackground === 'function') syncBackground(false);
  }

  function toast(message) {
    if (typeof state.toast === 'function') state.toast(message);
    else if (els.hint) els.hint.textContent = message;
  }

  function offsetHours(tzName, date) {
    try {
      const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: tzName, timeZoneName: 'longOffset', hour: '2-digit',
      }).formatToParts(date);
      const raw = (parts.find((p) => p.type === 'timeZoneName') || {}).value || 'GMT+00:00';
      const match = /GMT([+-])(\d{2}):?(\d{2})?/.exec(raw);
      if (!match) return 0;
      const sign = match[1] === '-' ? -1 : 1;
      return sign * (Number(match[2]) + Number(match[3] || 0) / 60);
    } catch {
      return -date.getTimezoneOffset() / 60;
    }
  }

  function computeTimes(date) {
    const config = state.config;
    return PT.times({
      date,
      lat: config.lat,
      lng: config.lng,
      timezone: offsetHours(config.tz, date),
      method: config.method,
      madhab: config.madhab,
      highLatitude: config.highLatitude,
      adjustments: config.adjustments,
      isRamadan: false,
    });
  }

  function nextPrayer(date) {
    const config = state.config;
    return PT.next({
      date,
      lat: config.lat,
      lng: config.lng,
      timezone: offsetHours(config.tz, date),
      method: config.method,
      madhab: config.madhab,
      highLatitude: config.highLatitude,
      adjustments: config.adjustments,
    });
  }

  // ---------- الصوت ----------
  async function adhanSources() {
    if (state.adhanCache.size) return state.adhanCache;
    DATA.adhans.forEach((item) => state.adhanCache.set(item.id, item));
    return state.adhanCache;
  }

  function adhanById(id) {
    return DATA.adhans.find((item) => item.id === id) || DATA.adhans[0];
  }

  // المصادر المحتملة للأذان: الرابط الأساسي ثم مراياه. أي مصدر يعمل يُستخدم،
  // فلا يتوقف الأذان لأن مضيفًا واحدًا محجوب أو بطيء.
  function adhanSources(item) {
    const list = [];
    if (item && item.url) list.push(item.url);
    if (item && Array.isArray(item.mirrors)) {
      item.mirrors.forEach((url) => { if (url && !list.includes(url)) list.push(url); });
    }
    return list;
  }

  // فحص حقيقي لوجود الملف المحلي: نسخة وصلها تحديث الواجهة قبل ملفات الأذان
  // لا تحتوي الأذان المحزوم، فبدون هذا الفحص يظهر «محلي» ثم لا يعمل الصوت.
  const localReadyCache = new Map();
  async function localAdhanReady(item) {
    if (!item || !item.local) return false;
    if (localReadyCache.has(item.id)) return localReadyCache.get(item.id);
    let ok = true;
    try {
      // نعتبر الملف موجودًا إلا إن أكّد السيرفر غيابه (404). بعض بيئات WebView
      // لا تدعم HEAD فترد 405، ولا يصح اعتبار ذلك دليل غياب.
      const response = await fetch(item.local, { method: 'HEAD' });
      ok = !response || response.status !== 404;
    } catch {
      ok = true;
    }
    localReadyCache.set(item.id, ok);
    if (!ok) console.info('[adhan] الملف المحلي غير موجود، سيُستخدم المصدر الشبكي:', item.id);
    return ok;
  }

  async function cachedAdhanUrl(item) {
    if (typeof caches === 'undefined') return null;
    try {
      const cache = await caches.open(ADHAN_CACHE);
      for (const url of adhanSources(item)) {
        const hit = await cache.match(url);
        if (!hit) continue;
        const blob = await hit.blob();
        if (blob.size > 16384) return URL.createObjectURL(blob);
      }
      return null;
    } catch {
      return null;
    }
  }

  async function isAdhanDownloaded(item) {
    if (await localAdhanReady(item)) return true;
    if (typeof caches === 'undefined') return false;
    try {
      const cache = await caches.open(ADHAN_CACHE);
      for (const url of adhanSources(item)) {
        if (await cache.match(url)) return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  async function downloadAdhan(item, onProgress) {
    const sources = adhanSources(item);
    if (!sources.length) throw new Error('no source');
    let response = null;
    let usedUrl = '';
    let lastError = null;
    for (const url of sources) {
      try {
        const attempt = await fetch(url, { mode: 'cors', cache: 'no-store' });
        if (attempt.ok) { response = attempt; usedUrl = url; break; }
        lastError = new Error('http ' + attempt.status);
      } catch (error) {
        lastError = error;
      }
    }
    if (!response) throw lastError || new Error('all sources failed');
    const total = Number(response.headers.get('content-length')) || item.seconds * 16000;
    const reader = response.body && response.body.getReader ? response.body.getReader() : null;
    let received = 0;
    let blob;
    if (reader) {
      const chunks = [];
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        received += value.length;
        if (onProgress) onProgress(Math.min(0.99, received / total));
      }
      blob = new Blob(chunks, { type: 'audio/mpeg' });
    } else {
      blob = await response.blob();
    }
    const cache = await caches.open(ADHAN_CACHE);
    // نحفظ تحت كل المصادر حتى لا يهم أي رابط استُخدم في التنزيل ولا في التشغيل
    for (const url of adhanSources(item)) {
      try {
        if (url === usedUrl) await cache.put(url, new Response(blob, { headers: { 'Content-Type': 'audio/mpeg' } }));
        else await cache.put(url, new Response(blob, { headers: { 'Content-Type': 'audio/mpeg' } }));
      } catch { /* مساحة ممتلئة: يكفي مصدر واحد */ }
    }
    if (onProgress) onProgress(1);
    return blob.size;
  }

  async function removeAdhan(item) {
    try {
      const cache = await caches.open(ADHAN_CACHE);
      for (const url of adhanSources(item)) await cache.delete(url);
    } catch { /* لا شيء محفوظ */ }
  }

  function getAudio() {
    if (!state.audio) {
      state.audio = new Audio();
      state.audio.preload = 'none';
    }
    return state.audio;
  }

  async function playAdhan(id, options = {}) {
    const item = adhanById(id);
    const audio = getAudio();
    try { audio.pause(); } catch { /* لم يُشغّل بعد */ }
    audio.src = '';
    // 1) ملف محزوم داخل التطبيق (يعمل بلا إنترنت من أول تشغيل) — بشرط وجوده فعلًا
    // 2) ملف منزّل على الجهاز 3) البث من الشبكة عبر الرابط الأساسي ثم مراياه
    const candidates = [];
    if (await localAdhanReady(item)) candidates.push(item.local);
    const cached = await cachedAdhanUrl(item);
    if (cached) candidates.push(cached);
    adhanSources(item).forEach((url) => { if (!candidates.includes(url)) candidates.push(url); });
    audio.src = candidates[0] || '';
    audio.volume = Math.min(1, Math.max(0, num(state.config.adhanVolume, 1)));
    state.playingId = item.id;
    state.adhanLive = Boolean(options.prayerName);
    noteAdhanStarted();
    renderAdhanState();
    audio.ontimeupdate = renderAdhanScreenProgress;
    audio.onloadedmetadata = renderAdhanScreenProgress;
    openAdhanScreen({
      muezzinId: item.id,
      prayerName: options.prayerName || enteredPrayerLabel(),
      live: Boolean(options.prayerName),
    });
    renderAdhanScreenProgress();
    // تشغيل متدرّج: كل مصدر يفشل ننتقل إلى الذي بعده بدل الرسالة الصامتة
    let sourceIndex = 0;
    let gaveUp = false;
    const playSource = async () => {
      if (sourceIndex >= candidates.length) {
        if (!gaveUp) {
          gaveUp = true;
          toast('تعذّر تشغيل الأذان: كل المصادر غير متاحة الآن. جرّب التنزيل (⤓) عند وجود إنترنت.');
          noteAdhanEnded('error');
        }
        return;
      }
      const src = candidates[sourceIndex];
      sourceIndex += 1;
      audio.src = src;
      try {
        await audio.play();
        if (!options.silent && sourceIndex === 1) toast(`أذان ${item.name}`);
      } catch {
        if (sourceIndex < candidates.length) await playSource();
        else if (!gaveUp) {
          gaveUp = true;
          toast('تعذّر تشغيل الأذان: كل المصادر غير متاحة الآن. جرّب التنزيل (⤓) عند وجود إنترنت.');
          noteAdhanEnded('error');
        }
      }
    };
    await playSource();
    renderAdhanScreenProgress();
    audio.onended = () => {
      state.playingId = null;
      renderAdhanState();
      closeAdhanScreen();
      // خوارزمية الإطفاء تبدأ عدّها من هنا: انتهاء الأذان ثم سكون ثم إطفاء.
      noteAdhanEnded('ended');
    };
    audio.onerror = () => {
      // المصدر الحالي سقط (ملف ناقص أو مضيف محجوب) ⇒ التالي في القائمة
      if (!gaveUp) playSource();
    };
    return true;
  }



  // ---------- فتح شاشة الأذان إجباريًا من منبّه النظام ----------
  // أندرويد يفتح النشاط من intent ملء الشاشة، ثم نسحب الطلب هنا ونشغّل الأذان ونفتح الشاشة.
  let pendingCheckAt = 0;
  async function checkPendingNativeAdhan() {
    if (!hasBackgroundBridge()) return;
    const now = Date.now();
    if (now - pendingCheckAt < 1500) return;
    pendingCheckAt = now;
    try {
      const result = await bgCall('takePendingOpen');
      if (!result || !result.pending) return;
      const id = result.adhanId || state.config.adhanId;
      const label = result.label || PT.describe(result.prayer || 'dhuhr');
      state.pendingAdhan = { id, label };
      // نوقف تشغيل الخدمة الأصلية أولًا حتى لا يتكرر الصوت، ثم نتولى التشغيل داخل الشاشة
      try { await bgCall('stop'); } catch { /* الخدمة غير قائمة */ }
      playAdhan(id, { prayerName: label, live: true });
    } catch { /* الجسر غير متاح */ }
  }

  // ---------- شاشة الأذان: فيديو مسجد + مشغل عادي (إيقاف مؤقت/إيقاف/تخفيض/تعلية) ----------
  const adhanScreenEls = {};
  function adhanScreenRefs() {
    if (adhanScreenEls.root) return adhanScreenEls;
    const q = (id) => document.getElementById(id);
    adhanScreenEls.root = q('adhanScreen');
    adhanScreenEls.video = q('adhanVideo');
    adhanScreenEls.prayer = q('adhanPrayer');
    adhanScreenEls.kicker = q('adhanKicker');
    adhanScreenEls.progress = q('adhanProgress');
    adhanScreenEls.elapsed = q('adhanElapsed');
    adhanScreenEls.total = q('adhanTotal');
    adhanScreenEls.pause = q('adhanPause');
    adhanScreenEls.volume = q('adhanVolume');
    adhanScreenEls.volumeLine = q('adhanVolumeLine');
    return adhanScreenEls;
  }

  function clockText(seconds) {
    const value = Math.max(0, Math.round(Number(seconds) || 0));
    return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
  }

  function adhanVolumeValue() {
    return Math.min(1, Math.max(0, num(state.config && state.config.adhanVolume, 1)));
  }

  function renderAdhanVolume() {
    const refs = adhanScreenRefs();
    const percent = Math.round(adhanVolumeValue() * 100);
    if (refs.volume && refs.volume.value !== String(percent)) refs.volume.value = String(percent);
    if (refs.volumeLine) refs.volumeLine.textContent = `${percent}%`;
    if (els.volumeRange) els.volumeRange.value = String(percent);
  }

  function setAdhanVolume(value) {
    const next = Math.min(1, Math.max(0, value));
    if (!state.config) return;
    state.config.adhanVolume = next;
    if (state.audio) {
      try { state.audio.volume = next; } catch { /* لا شيء يُشغّل الآن */ }
    }
    renderAdhanVolume();
    saveConfig();
  }

  function renderAdhanScreenProgress() {
    const refs = adhanScreenRefs();
    const audio = state.audio;
    if (!refs.progress || !audio) return;
    const total = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : 0;
    const done = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
    refs.progress.style.width = total ? `${Math.min(100, (done / total) * 100).toFixed(1)}%` : '0%';
    if (refs.elapsed) refs.elapsed.textContent = clockText(done);
    if (refs.total) refs.total.textContent = total ? clockText(total) : '—';
    if (refs.pause) {
      const paused = audio.paused && Boolean(state.playingId);
      refs.pause.innerHTML = paused
        ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10-6.5z"/></svg>'
        : '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="5.5" width="3.6" height="13" rx="1.2"/><rect x="13.4" y="5.5" width="3.6" height="13" rx="1.2"/></svg>';
      refs.pause.setAttribute('aria-label', paused ? 'متابعة الأذان' : 'إيقاف مؤقت');
      refs.pause.title = paused ? 'متابعة' : 'إيقاف مؤقت';
      refs.pause.classList.toggle('primary', !paused);
    }
  }


  // الصلاة التي دخل وقتها الآن (وإلا القادمة) — لعنوان «حان الآن وقت …»
  function enteredPrayerLabel() {
    const table = state.today || computeTimes(new Date());
    if (table) {
      const nowHours = PT.minutesNow(new Date()) / 60;
      const entered = PRAYER_KEYS.filter((k) => Number.isFinite(table[k]) && table[k] <= nowHours).pop();
      if (entered) return `صلاة ${PT.describe(entered)}`;
    }
    return state.next ? `صلاة ${PT.describe(state.next.key)}` : 'الصلاة';
  }

  function openAdhanScreen(info = {}) {
    const refs = adhanScreenRefs();
    if (!refs.root) return;
    const prayerName = info.prayerName || enteredPrayerLabel();
    if (refs.kicker) refs.kicker.textContent = info.live ? 'حان الآن وقت' : 'أذان';
    if (refs.prayer) refs.prayer.textContent = prayerName;
    refs.root.classList.add('open');
    refs.root.setAttribute('aria-hidden', 'false');
    state.adhanScreenOpen = true;
    renderAdhanVolume();
    renderAdhanScreenProgress();
    if (refs.video) {
      try {
        refs.video.muted = true;
        const playing = refs.video.play();
        if (playing && typeof playing.catch === 'function') playing.catch(() => { /* الفيديو زخرفة فقط */ });
      } catch { /* بعض الأجهزة تمنع التشغيل التلقائي */ }
    }
  }

  function closeAdhanScreen() {
    const refs = adhanScreenRefs();
    if (!refs.root) return;
    refs.root.classList.remove('open');
    refs.root.setAttribute('aria-hidden', 'true');
    state.adhanScreenOpen = false;
    if (refs.video) {
      try { refs.video.pause(); } catch { /* لا شيء */ }
    }
  }

  function toggleAdhanPause() {
    const audio = state.audio;
    if (!audio) return;
    if (audio.paused) {
      const playing = audio.play();
      if (playing && typeof playing.catch === 'function') playing.catch(() => { /* المتصفح منع */ });
      toast('متابعة الأذان.');
    } else {
      try { audio.pause(); } catch { /* لا شيء */ }
      toast('أُوقف الأذان مؤقتًا.');
    }
    renderAdhanScreenProgress();
  }

  function wireAdhanScreen() {
    const refs = adhanScreenRefs();
    if (!refs.root || refs.root.dataset.wired === '1') return;
    refs.root.dataset.wired = '1';
    refs.root.querySelectorAll('[data-adhan-ctl]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const act = btn.dataset.adhanCtl;
        if (act === 'pause') toggleAdhanPause();
        if (act === 'stop') { stopAdhan(); toast('أُوقف الأذان.'); }
        if (act === 'lower') setAdhanVolume(adhanVolumeValue() - 0.1);
        if (act === 'raise') setAdhanVolume(adhanVolumeValue() + 0.1);
      });
    });
    const closeBtn = document.getElementById('adhanClose');
    if (closeBtn) closeBtn.addEventListener('click', closeAdhanScreen);
    if (refs.volume) {
      refs.volume.addEventListener('input', () => setAdhanVolume(Number(refs.volume.value) / 100));
    }
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && state.adhanScreenOpen) closeAdhanScreen();
    });
  }

  function stopAdhan() {
    const audio = getAudio();
    try { audio.pause(); audio.currentTime = 0; } catch { /* لا شيء يعمل */ }
    state.playingId = null;
    renderAdhanState();
    closeAdhanScreen();
    noteAdhanEnded('stopped');
  }


  // ---------- مُنسّق إطفاء الشاشة: من الإشارات إلى القرار إلى التنفيذ ----------
  // الجسر الأصلي: SirajScreenGuard (قدرات + قفل فوري + رفع علم إبقاء الشاشة).
  const SCREEN_PLUGIN = 'SirajScreenGuard';
  const MOTION_THRESHOLD = 0.45;   // تغيّر تسارع يُعد حركة يد/رفع للهاتف (م/ث²)
  const MOTION_STALE_MS = 6000;    // لا إشارات حركة حديثة ⇒ المستشعر غير متاح أو الهاتف ساكن

  const sleepState = {
    adhanActive: false,
    endedAt: 0,
    lastInteraction: Date.now(),
    lastMotion: 0,
    motionSeen: false,
    motion: false,
    screenOn: true,
    ticker: null,
    blocked: false,
    sleeping: false,
    last: { action: 'cancel', reason: 'idle', waitMs: 0, idleMs: 0 },
    admin: false,
    lockMethod: '',
    keepAwakeHeld: false,
    lastRenderAt: 0,
    sleptAt: 0,
    closeAt: 0,
    closeScheduled: false,
    closeWatchdog: null,
    closeReason: '',
    lastClose: { action: 'cancel', reason: 'not-slept', waitMs: 0, idleMs: 0 },
    wired: false,
  };

  function hasScreenGuard() {
    return !!(Cap && Cap.isPluginAvailable && Cap.isPluginAvailable(SCREEN_PLUGIN));
  }

  function screenCall(method, payload) {
    if (!hasScreenGuard() || !Cap.nativePromise) return Promise.resolve(null);
    return Cap.nativePromise(SCREEN_PLUGIN, method, payload || {}).catch(() => null);
  }

  function sleepConfigFromState() {
    const config = state.config || {};
    return {
      enabled: config.sleepAfterAdhan !== false,
      graceMs: Math.max(0, num(config.sleepGraceSeconds, 30)) * 1000,
      activeMs: SLEEP_DEFAULTS.activeMs,
      stillMs: config.sleepStill !== false ? SLEEP_DEFAULTS.stillMs : 0,
    };
  }

  function closeConfigFromState() {
    const config = state.config || {};
    return {
      enabled: config.closeAfterAdhan !== false,
      delayMs: Math.max(0, num(config.closeDelaySeconds, 20)) * 1000,
    };
  }

  function playbackActive() {
    const playback = root.SirajPlaybackState;
    return !!(playback && playback.playing);
  }

  function closeSnapshot() {
    return {
      sleptAt: sleepState.sleptAt,
      lastInteraction: sleepState.lastInteraction,
      screenOn: sleepState.screenOn,
      audioPlaying: playbackActive(),
    };
  }

  /** يجدول الإغلاق في الجسر الأصلي، أو يلغيه إن لم تعد الشروط قائمة. */
  function syncCloseSchedule() {
    const cfg = closeConfigFromState();
    const decision = closeDecision(closeSnapshot(), Date.now(), cfg);
    sleepState.lastClose = decision;
    if (!hasScreenGuard()) { sleepState.closeScheduled = false; return decision; }
    if (decision.action === 'close') {
      sleepState.closeScheduled = false;
      sleepState.closeReason = decision.reason;
      screenCall('closeNow', { kill: true, reason: decision.reason });
      return decision;
    }
    if (decision.action === 'wait' && decision.reason === 'close-delay') {
      sleepState.closeAt = Date.now() + decision.waitMs;
      if (!sleepState.closeScheduled) {
        sleepState.closeScheduled = true;
        screenCall('scheduleClose', { delayMs: decision.waitMs, kill: true });
        // شبكة أمان ثانية: إن تأخّر مؤقّت الجسر الأصلي (تجميد العملية) يُغلق من الويب.
        if (sleepState.closeWatchdog) clearTimeout(sleepState.closeWatchdog);
        sleepState.closeWatchdog = setTimeout(() => {
          sleepState.closeWatchdog = null;
          const again = closeDecision(closeSnapshot(), Date.now(), closeConfigFromState());
          sleepState.lastClose = again;
          if (again.action === 'close') screenCall('closeNow', { kill: true, reason: 'watchdog' });
        }, decision.waitMs + 1500);
      }
      return decision;
    }
    cancelScheduledClose();
    return decision;
  }

  function cancelScheduledClose() {
    sleepState.closeAt = 0;
    if (sleepState.closeWatchdog) {
      clearTimeout(sleepState.closeWatchdog);
      sleepState.closeWatchdog = null;
    }
    if (!sleepState.closeScheduled) return;
    sleepState.closeScheduled = false;
    if (hasScreenGuard()) screenCall('cancelClose', {});
  }

  function sleepSnapshot() {
    // المستشعر قد لا يعمل في بعض الأجهزة/الويب فيُعتمد على اللمس وحده.
    sleepState.motion = sleepState.motionSeen
      && (Date.now() - sleepState.lastMotion) < MOTION_STALE_MS;
    return {
      adhanActive: sleepState.adhanActive,
      adhanEndedAt: sleepState.endedAt,
      lastInteraction: sleepState.lastInteraction,
      lastMotion: sleepState.lastMotion,
      motion: sleepState.motion,
      screenOn: sleepState.screenOn,
    };
  }

  function sleepStatusText() {
    const cfg = sleepConfigFromState();
    if (!cfg.enabled) return 'إطفاء الشاشة التلقائي متوقف.';
    if (sleepState.adhanActive) return 'الأذان يعمل الآن؛ الشاشة تبقى مضاءة حتى ينتهي.';
    if (!sleepState.endedAt) return 'تُطفأ الشاشة تلقائيًا بعد انتهاء الأذان إن لم تُستخدم.';
    if (sleepState.blocked) {
      const closeLine = closeConfigFromState().enabled
        ? ' وسيُغلق التطبيق بعد قليل.'
        : '';
      return sleepState.lockMethod === 'admin'
        ? `أُطفئت الشاشة تلقائيًا بعد الأذان.${closeLine} المس الشاشة للمتابعة.`
        : `أُطلق إبقاء الشاشة بعد الأذان؛ ستقفل بمهلة الهاتف.${closeLine} المس للمتابعة.`;
    }
    const left = Math.max(0, Math.round((cfg.graceMs - sleepState.last.idleMs) / 1000));
    if (sleepState.last.action === 'wait' && sleepState.last.reason === 'grace') {
      return `الشاشة تُطفأ بعد ${left} ثانية إن لم تُستخدم.`;
    }
    if (sleepState.last.action === 'wait' && sleepState.last.reason === 'user-active') {
      return 'المستخدم يستخدم الهاتف الآن؛ الإطفاء مؤجّل.';
    }
    if (sleepState.last.action === 'wait' && sleepState.last.reason === 'moving') {
      return 'الهاتف يتحرك؛ الإطفاء مؤجّل حتى يستقر.';
    }
    return hasScreenGuard() && !sleepState.admin
      ? 'الشاشة تُترك لمهلة الهاتف. فعّل «إذن القفل» لإطفائها فورًا بعد الأذان.'
      : 'جاهز: تُطفأ الشاشة بعد الأذان إن لم تُستخدم.';
  }

  function renderSleepLine() {
    if (!els.sleepStatus) return;
    els.sleepStatus.textContent = sleepStatusText();
    if (els.sleepAdminBtn) {
      els.sleepAdminBtn.textContent = sleepState.admin ? 'إيقاف إذن القفل' : 'تفعيل إذن القفل';
    }
  }

  function noteInteraction(extraMs) {
    const now = Date.now();
    sleepState.lastInteraction = now + num(extraMs, 0);
    if (sleepState.closeScheduled || sleepState.closeAt) cancelScheduledClose();
    if (sleepState.blocked || sleepState.sleeping) wakeUpScreen();
    // رسم سطر الحالة مُخفَّف: لا نكتب في DOM مع كل لمسة.
    if (now - sleepState.lastRenderAt > 900) {
      sleepState.lastRenderAt = now;
      renderSleepLine();
    }
  }

  function wakeUpScreen() {
    sleepState.blocked = false;
    sleepState.sleeping = false;
    if (root.SirajWakeControl && root.SirajWakeControl.release) {
      try { root.SirajWakeControl.release(); } catch { /* لا شيء */ }
    }
    if (root.SirajWakeControl && root.SirajWakeControl.block) {
      try { root.SirajWakeControl.block(false); } catch { /* لا شيء */ }
    }
    if (hasScreenGuard() && !sleepState.keepAwakeHeld) {
      // نُبقي الشاشة مضاءة أثناء الاستخدام الفعلي كما كان التطبيق يفعل.
      sleepState.keepAwakeHeld = true;
      screenCall('setKeepAwake', { on: true });
    }
  }

  function holdWakeLockForAdhan(on) {
    sleepState.keepAwakeHeld = !!on;
    if (hasScreenGuard()) screenCall('setKeepAwake', { on: !!on });
    if (root.SirajWakeControl && root.SirajWakeControl.block && !on) {
      try { root.SirajWakeControl.block(false); } catch { /* لا شيء */ }
    }
  }

  async function performSleep(reason) {
    if (sleepState.blocked) return sleepState.last;
    sleepState.blocked = true;
    sleepState.last = sleepDecision(sleepSnapshot(), Date.now(), sleepConfigFromState());
    if (root.SirajWakeControl && root.SirajWakeControl.block) {
      try { root.SirajWakeControl.block(true); } catch { /* لا شيء */ }
    }
    sleepState.keepAwakeHeld = false;
    const result = await screenCall('lockNow', { reason });
    sleepState.lockMethod = result && result.method ? String(result.method) : (hasScreenGuard() ? 'no-admin' : 'web');
    sleepState.sleeping = true;
    if (result && result.ok) {
      // الشاشة أُطفئت بالفعل؛ الإشارات التالية ستأتي أيضًا من مستمع حالة الشاشة.
      sleepState.screenOn = false;
    }
    // المرحلة الثانية: بعد إطفاء الشاشة يبدأ مؤقت الإغلاق (يُلغى بأول لمسة أو إضاءة شاشة).
    sleepState.sleptAt = Date.now();
    syncCloseSchedule();
    renderSleepLine();
    return sleepState.last;
  }

  function stopSleepTicker() {
    if (sleepState.ticker) clearInterval(sleepState.ticker);
    sleepState.ticker = null;
  }

  function sleepTick() {
    const decision = sleepDecision(sleepSnapshot(), Date.now(), sleepConfigFromState());
    sleepState.last = decision;
    if (decision.action === 'sleep') {
      stopSleepTicker();
      performSleep(decision.reason);
      return;
    }
    if (decision.action === 'cancel' || decision.action === 'arm') {
      stopSleepTicker();
    }
    renderSleepLine();
  }

  function startSleepTicker() {
    if (sleepState.ticker) return;
    sleepState.ticker = setInterval(sleepTick, 1000);
    sleepTick();
  }

  /** يُنادى عند بدء أي أذان (داخل الشاشة أو من منبّه النظام). */
  function noteAdhanStarted() {
    sleepState.adhanActive = true;
    sleepState.endedAt = 0;
    sleepState.sleptAt = 0;
    cancelScheduledClose();
    sleepState.lastInteraction = Date.now();
    sleepState.last = sleepDecision(sleepSnapshot(), Date.now(), sleepConfigFromState());
    holdWakeLockForAdhan(true);
    renderSleepLine();
  }

  /** يُنادى عند انتهاء الأذان أو إيقافه: من هنا تبدأ المهلة. */
  function noteAdhanEnded(reason) {
    if (!sleepState.adhanActive && !sleepState.endedAt) return;
    sleepState.adhanActive = false;
    sleepState.endedAt = Date.now();
    sleepState.lastInteraction = Date.now();
    holdWakeLockForAdhan(false);
    if (sleepState.blocked) { sleepState.blocked = false; }
    root.SirajIdleSleepLastEnd = { reason: String(reason || 'ended'), at: sleepState.endedAt };
    renderSleepLine();
    startSleepTicker();
  }

  function refreshCapabilities() {
    return screenCall('capabilities', {}).then((caps) => {
      if (!caps) return null;
      sleepState.admin = !!caps.admin;
      sleepState.screenOn = caps.interactive !== false;
      renderSleepLine();
      return caps;
    });
  }

  function wireSleepSignals() {
    if (sleepState.wired || typeof document === 'undefined') return;
    sleepState.wired = true;
    const touch = () => noteInteraction(0);
    ['pointerdown', 'touchstart', 'keydown', 'wheel'].forEach((name) => {
      document.addEventListener(name, touch, { passive: true });
    });
    // أي إشارة استخدام تمدّد المهلة ٦ ثوانٍ إضافية كاملة من لحظة آخر لمسة.
    document.addEventListener('scroll', () => noteInteraction(0), { passive: true, capture: true });
    document.addEventListener('visibilitychange', () => {
      sleepState.screenOn = !document.hidden;
      if (!document.hidden) {
        noteInteraction(SLEEP_DEFAULTS.activeMs);
        // العودة من شاشة إذن القفل أو من إعدادات النظام: نعيد قراءة القدرات.
        refreshCapabilities();
      }
      renderSleepLine();
    });
    if (typeof window !== 'undefined' && window.addEventListener) {
      let previous = null;
      window.addEventListener('devicemotion', (event) => {
        const acc = event && (event.accelerationIncludingGravity || event.acceleration);
        if (!acc) return;
        const magnitude = Math.sqrt(
          Math.pow(num(acc.x, 0), 2) + Math.pow(num(acc.y, 0), 2) + Math.pow(num(acc.z, 0), 2));
        if (!Number.isFinite(magnitude)) return;
        sleepState.motionSeen = true;
        const delta = previous === null ? 0 : Math.abs(magnitude - previous);
        previous = magnitude;
        if (delta > MOTION_THRESHOLD) {
          sleepState.lastMotion = Date.now();
          noteInteraction(0);
        }
      }, { passive: true });
    }
    if (hasScreenGuard() && Cap.addListener) {
      try {
        Cap.addListener(SCREEN_PLUGIN, 'capabilities', (payload) => {
          sleepState.admin = !!(payload && payload.admin);
          renderSleepLine();
        });
      } catch { /* لا مستمع للجسر */ }
      try {
        Cap.addListener(SCREEN_PLUGIN, 'screen', (payload) => {
          const on = !payload || payload.interactive !== false;
          sleepState.screenOn = on;
          if (on) {
            sleepState.blocked = false;
            sleepState.sleeping = false;
            sleepState.sleptAt = 0;
            cancelScheduledClose();
            noteInteraction(SLEEP_DEFAULTS.activeMs);
          } else if (sleepState.blocked || sleepState.sleptAt) {
            // الشاشة أُطفئت فعلًا ⇒ يبدأ عدّاد الإغلاق من هذه اللحظة.
            if (!sleepState.sleptAt) sleepState.sleptAt = Date.now();
            syncCloseSchedule();
          }
          renderSleepLine();
        });
      } catch { /* لا مستمع للجسر */ }
    }
    refreshCapabilities();
  }

  async function toggleSleepAdmin() {
    if (!hasScreenGuard()) {
      toast('إطفاء الشاشة الفوري يحتاج تطبيق أندرويد مثبّتًا على الجهاز.');
      return;
    }
    if (sleepState.admin) {
      const result = await screenCall('revokeAdmin', {});
      sleepState.admin = !!(result && result.admin);
      toast(sleepState.admin ? 'إذن القفل ما زال مفعّلًا.' : 'أُوقف إذن القفل؛ تُترك الشاشة لمهلة الهاتف.');
    } else {
      const result = await screenCall('requestAdmin', {});
      sleepState.admin = !!(result && result.admin);
      toast('أكمل تفعيل «إذن القفل» في الشاشة التي ستفتح.');
    }
    renderSleepLine();
  }

  /** للاختبار اليدوي: نفّذ القرار فورًا كما لو انتهى الأذان ومرّت المهلة. */
  function simulateIdleSleep() {
    sleepState.adhanActive = false;
    sleepState.endedAt = Date.now() - Math.max(0, sleepConfigFromState().graceMs) - 1000;
    sleepState.lastInteraction = Date.now() - SLEEP_DEFAULTS.activeMs - 1000;
    sleepState.lastMotion = 0;
    sleepState.screenOn = true;
    return performSleep('simulated');
  }

  Object.assign(root.SirajIdleSleep, {
    start: noteAdhanStarted,
    end: noteAdhanEnded,
    touch: noteInteraction,
    status: () => ({
      ...sleepState.last,
      blocked: sleepState.blocked,
      admin: sleepState.admin,
      sleeping: sleepState.sleeping,
      sleptAt: sleepState.sleptAt,
      closeAt: sleepState.closeAt,
      closeScheduled: sleepState.closeScheduled,
      close: { ...sleepState.lastClose },
      text: sleepStatusText(),
    }),
    closeStatus: () => ({ ...sleepState.lastClose, closeAt: sleepState.closeAt, scheduled: sleepState.closeScheduled }),
    config: sleepConfigFromState,
    simulate: simulateIdleSleep,
    isSleeping: () => sleepState.blocked,
    admin: toggleSleepAdmin,
  });

  // نغمة الإقامة: قصيرة ومولّدة محليًا حتى لا تحتاج ملفًا

  // ---------- الجدولة أثناء فتح التطبيق ----------
  function scheduleChecks() {
    if (state.ticking) clearInterval(state.ticking);
    state.ticking = setInterval(tick, 15000);
    tick();
  }

  function minutesOf(seconds) {
    const mins = Math.round(seconds / 60);
    if (mins >= 60) return `${Math.floor(mins / 60)} س ${mins % 60 ? (mins % 60) + ' د' : ''}`.trim();
    return `${mins} دقيقة`;
  }

  // ذاكرة دائمة (localStorage) لما انطلق فعلًا: إغلاق التطبيق وفتحه لا يعيد الأذان
  const FIRED_KEY = 'siraj:adhan:fired';
  const ADHAN_WINDOW_HOURS = 3 / 60; // نافذة ثلاث دقائق فقط بدل خمس عشرة

  function dayKey(now = new Date()) {
    return `${now.getFullYear()}-${now.getMonth() + 1}-${now.getDate()}`;
  }

  function firedSet() {
    try {
      const raw = root.localStorage.getItem(FIRED_KEY);
      const list = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(list) ? list : []);
    } catch {
      return new Set();
    }
  }

  function wasFiredToday(stamp) {
    if (state.lastFired === stamp) return true;
    return firedSet().has(`${dayKey()}:${stamp}`);
  }

  function markFiredToday(stamp) {
    state.lastFired = stamp;
    try {
      const set = firedSet();
      set.add(`${dayKey()}:${stamp}`);
      root.localStorage.setItem(FIRED_KEY, JSON.stringify([...set].slice(-40)));
    } catch { /* التخزين محجوب: تبقى الحماية داخل الجلسة */ }
  }

  function fireFor(key, table) {
    if (wasFiredToday(key)) return;
    if (state.playingId) return; // أذان يعمل الآن: لا نبدأ آخر فوقه
    markFiredToday(key);
    const stamp = key;
    const config = state.config;
    // في نسخة أندرويد يتولى النظام تشغيل الأذان والإقامة، فلا نكرر الصوت داخل الواجهة.
    const handledBySystem = hasBackgroundBridge();
    if (config.adhanEnabled && !handledBySystem) {
      const id = key === 'fajr' ? config.fajrAdhanId : config.adhanId;
      // تجربة يدوية: العنوان يبقى «أذان» إلا إذا دخل وقت الصلاة فعلًا
      playAdhan(id);
    } else if (!config.adhanEnabled) {
      toast(`حان الآن وقت صلاة ${PT.describe(key)}`);
    }
    if (config.iqamaEnabled && !handledBySystem && PRAYER_KEYS.includes(key)) {
      const minutes = num(config.iqamaMinutes[key], 15);
      const timer = setTimeout(() => {
        // لا صوت إقامة: إشعار نصي فقط «قم إلى صلاتك»
        notifyLocal(`قم إلى صلاتك — حان وقت إقامة صلاة ${PT.describe(key)}`);
        toast(`قم إلى صلاتك — إقامة ${PT.describe(key)}`);
        renderTimes();
      }, Math.max(1, minutes) * 60000);
      state.iqamaTimers.push(timer);
    }
    renderTimes();
  }

  function tick() {
    if (!state.config || document.hidden) return;
    const now = new Date();
    const table = computeTimes(now);
    if (!table) return;
    // table بالساعات العشرية، فالآن يُحوَّل إلى ساعات أيضًا
    const hoursNow = PT.minutesNow(now) / 60;
    const config = state.config;
    PRAYER_KEYS.forEach((key) => {
      if (!Number.isFinite(table[key])) return;
      const diff = hoursNow - table[key];
      if (diff >= 0 && diff < ADHAN_WINDOW_HOURS) fireFor(key, table);
      if (config.preMinutes > 0 && !hasBackgroundBridge()) {
        const pre = diff + config.preMinutes;
        if (pre >= 0 && pre < 0.25) {
          const stamp = `pre:${key}`;
          if (!wasFiredToday(stamp)) {
            markFiredToday(stamp);
            speakReminder(`أذان ${PT.describe(key)} بعد ${config.preMinutes} دقيقة`);
            notifyLocal(`أذان ${PT.describe(key)} بعد ${config.preMinutes} دقائق`);
          }
        }
      }
    });
    renderHero();
    renderTimes();
  }


  // ---------- الأذان في الخلفية ----------
  // الطبقة الويب تحسب المواقيت، وتسلّم الجدول لخدمة أندرويد مرة واحدة،
  // فتشغّل الأذان في وقته ومنبّه الإقامة بعده ولو كان التطبيق مغلقًا.
  const Cap = (typeof window !== 'undefined' ? window : root).Capacitor || null;
  const BG_PLUGIN = 'AdhanBackground';
  const SENSORS_PLUGIN = 'SirajSensors';
  const BG_HORIZON_DAYS = 14;

  function hasBackgroundBridge() {
    return !!(Cap && Cap.isPluginAvailable && Cap.isPluginAvailable(BG_PLUGIN));
  }

  function hasSensors() {
    return !!(Cap && Cap.isPluginAvailable && Cap.isPluginAvailable(SENSORS_PLUGIN));
  }

  function sensorCall(method, payload) {
    if (!hasSensors() || !Cap.nativePromise) return Promise.resolve(null);
    return Cap.nativePromise(SENSORS_PLUGIN, method, payload || {}).catch(() => null);
  }

  function bgCall(method, payload) {
    if (!hasBackgroundBridge() || !Cap.nativePromise) return Promise.resolve(null);
    return Cap.nativePromise(BG_PLUGIN, method, payload || {}).catch(() => null);
  }

  // تاريخ اليوم في مدينة المستخدم (قد تختلف عن تاريخ الجهاز في منطقة أخرى)
  function cityParts(instant) {
    const tz = state.config.tz;
    try {
      const parts = new Intl.DateTimeFormat('en-CA', {
        timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
      }).formatToParts(instant);
      const pick = (type) => Number((parts.find((p) => p.type === type) || {}).value);
      return { y: pick('year'), m: pick('month'), d: pick('day') };
    } catch {
      return { y: instant.getFullYear(), m: instant.getMonth() + 1, d: instant.getDate() };
    }
  }

  // ساعات المدينة بعد منتصف ليل اليوم ← لحظة مطلقة بالميلي ثانية
  function cityEpoch(instant, hours) {
    const { y, m, d } = cityParts(instant);
    const offset = offsetHours(state.config.tz, instant);
    return Date.UTC(y, m - 1, d) - offset * 3600000 + Math.round(hours * 3600000);
  }

  // جدول المواقيت بالساعات العشرية؛ نحوّله هنا إلى لحظة مطلقة بالميلي ثانية
  function buildBackgroundSchedule() {
    const config = state.config;
    const events = [];
    const now = Date.now();
    const base = new Date();
    for (let day = 0; day < BG_HORIZON_DAYS; day += 1) {
      const date = new Date(base.getTime() + day * 86400000);
      const table = computeTimes(date);
      if (!table) continue;
      PRAYER_KEYS.forEach((key) => {
        const hours = table[key];
        if (!Number.isFinite(hours)) return;
        const at = cityEpoch(date, hours);
        if (at <= now + 60000) return;
        const adhanId = key === 'fajr' ? config.fajrAdhanId : config.adhanId;
        const item = adhanById(adhanId) || {};
        events.push({
          prayer: key,
          label: PT.describe(key),
          at,
          adhanId,
          url: item.url || '',
          urls: adhanSources(item).slice(0, 3),
          iqamaMinutes: Math.max(0, num(config.iqamaMinutes[key], 0)),
          preMinutes: Math.max(0, num(config.preMinutes, 0)),
        });
      });
    }
    events.sort((a, b) => a.at - b.at);
    return {
      events,
      settings: {
        adhanEnabled: !!config.adhanEnabled,
        iqamaEnabled: !!config.iqamaEnabled,
        preMinutes: num(config.preMinutes, 0),
        horizonDays: BG_HORIZON_DAYS,
        city: config.cityName || '',
        timezone: config.tz || '',
        version: 1,
      },
    };
  }

  let bgSyncTimer = null;
  let bgState = { scheduled: 0, exact: false, native: false };

  // تنبيه ما قبل الأذان منطوق داخل التطبيق (وإشعار إن كان مسموحًا)
  function speakReminder(text) {
    try {
      const synth = root.speechSynthesis;
      if (!synth) { toast(text); return; }
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = 'ar-SA';
      utter.rate = 0.95;
      synth.cancel();
      synth.speak(utter);
      toast(text);
    } catch {
      toast(text);
    }
  }

  function notifyLocal(text) {
    try {
      if (typeof root.Notification !== 'function') return;
      if (root.Notification.permission === 'granted') {
        new root.Notification('سراج', { body: text, tag: 'siraj-pre-adhan' });
      }
    } catch { /* الإشعارات غير مسموحة */ }
  }

  function syncBackground(immediate) {
    if (bgSyncTimer) clearTimeout(bgSyncTimer);
    const run = async () => {
      if (!hasBackgroundBridge()) {
        bgState = { scheduled: 0, exact: false, native: false };
        renderBackgroundStatus();
        return;
      }
      const payload = buildBackgroundSchedule();
      const result = await bgCall('configure', payload);
      ensureAdhanPermissions();
      bgState = {
        native: true,
        scheduled: result && Number.isFinite(Number(result.scheduled)) ? Number(result.scheduled) : payload.events.length,
        events: payload.events.length,
        exact: !!(result && result.exact),
        until: payload.events.length ? payload.events[payload.events.length - 1].at : 0,
      };
      renderBackgroundStatus();
    };
    if (immediate) run();
    else bgSyncTimer = setTimeout(run, 700);
  }

  /**
   * أذونات أذان الشاشة المقفولة: الإشعارات (وبدونها صوت فقط بلا شاشة)،
   * وملء الشاشة على أندرويد ١٤+، والمنبّهات الدقيقة. تُطلب مرة واحدة لكل جهاز.
   */
  let permissionsAsked = false;
  async function ensureAdhanPermissions(force = false) {
    if (!hasBackgroundBridge() || !state.config || !state.config.adhanEnabled) return;
    if (permissionsAsked && !force) return;
    permissionsAsked = true;
    const flags = (await bgCall('permissions')) || {};
    const askedBefore = (() => {
      try { return root.localStorage.getItem('siraj:adhan:asked') || ''; } catch { return ''; }
    })();
    const once = (key) => {
      if (askedBefore.includes(key)) return false;
      try { root.localStorage.setItem('siraj:adhan:asked', `${askedBefore}${key},`); } catch { /* محجوب */ }
      return true;
    };
    let changed = false;
    if (!flags.notifications) {
      await bgCall('requestNotifications');
      changed = true;
    }
    if (!flags.fullScreen && (force || once('fullscreen'))) {
      await bgCall('requestFullScreen');
      changed = true;
    }
    if (!flags.exactAlarms && (force || once('exact'))) {
      await bgCall('requestExactAlarms');
      changed = true;
    }
    if (changed) syncBackground(true);
  }

  function formatUntil(ms) {
    if (!ms) return '';
    try {
      return new Intl.DateTimeFormat('ar-EG', {
        timeZone: state.config.tz, day: 'numeric', month: 'long',
      }).format(new Date(ms));
    } catch {
      return new Date(ms).toLocaleDateString();
    }
  }

  function renderBackgroundStatus() {
    const hint = el('ptBgStatus');
    if (!hint) return;
    if (!bgState.native) {
      hint.textContent = 'الأذان يُشغَّل تلقائيًا في وقته داخل التطبيق. في نسخة أندرويد يعمل أيضًا عندما يكون التطبيق مغلقًا.';
      return;
    }
    if (!state.config.adhanEnabled && !state.config.iqamaEnabled) {
      hint.textContent = 'الأذان والإقامة متوقفان حاليًا؛ لن يعمل شيء في الخلفية.';
      return;
    }
    const parts = [];
    const count = Number(bgState.scheduled || 0).toLocaleString('ar-EG');
    if (state.config.adhanEnabled) parts.push(`الأذان مجدول في وقته (${count} موعدًا)`);
    if (state.config.iqamaEnabled) parts.push('وتنبيه الإقامة بعده');
    const until = formatUntil(bgState.until);
    hint.textContent = `${parts.join(' ')} حتى ${until} — يعمل والتطبيق مغلق، ويُجدَّد الجدول تلقائيًا.`
      + (bgState.exact ? '' : ' قد يتأخر دقائق لأن النظام لم يمنح إذن المنبّهات الدقيقة.');
  }

  // ---------- العرض ----------
  function prayerRows(table) {
    return PT.PRAYERS.map((key) => ({
      key,
      name: PT.describe(key),
      minutes: table ? table[key] : null,
      text: table ? PT.formatMinutes(table[key], state.config.use24h) : '—',
    }));
  }

  function renderHero() {
    if (!els.nextName) return;
    const info = nextPrayer(new Date());
    const table = computeTimes(new Date());
    state.next = info;
    if (!info) {
      els.nextName.textContent = '—';
      els.nextAt.textContent = 'اضبط موقعك لحساب المواقيت';
      els.countdown.textContent = '—';
      return;
    }
    els.nextName.textContent = `صلاة ${info.name}`;
    const when = new Date();
    when.setHours(0, 0, 0, 0);
    when.setMinutes(Math.round(info.at));
    els.nextAt.textContent = `${PT.formatMinutes(info.at, state.config.use24h)} · ${info.today ? 'اليوم' : 'غدًا'}`;
    const total = Math.max(1, info.minutesLeft);
    const hours = Math.floor(total / 60);
    const mins = Math.floor(total % 60);
    els.countdown.textContent = hours > 0 ? `${hours}:${String(mins).padStart(2, '0')}` : `${mins} د`;
    if (table) {
      const hoursNow = PT.minutesNow(new Date()) / 60;
      const prevKey = PRAYER_KEYS.filter((k) => Number.isFinite(table[k]) && table[k] <= hoursNow).pop();
      const from = prevKey ? table[prevKey] : 0;
      const span = Math.max(1, info.at - from);
      const percent = Math.min(100, Math.max(0, ((hoursNow - from) / span) * 100));
      els.bar.style.width = `${percent.toFixed(1)}%`;
    }
  }

  function renderTimes() {
    if (!els.times) return;
    const table = computeTimes(new Date());
    state.today = table;
    const nextKey = state.next ? state.next.key : null;
    els.times.innerHTML = prayerRows(table).map((row) => `
      <div class="pt-row${row.key === nextKey ? ' is-next' : ''}${row.key === 'sunrise' ? ' is-sunrise' : ''}">
        <span class="pt-name">${row.name}</span>
        <span class="pt-time">${row.text}</span>
        ${PRAYER_KEYS.includes(row.key) ? `<button class="pt-mini" data-pt-adhan="${row.key}" title="تشغيل الأذان">🔔</button>` : '<span></span>'}
      </div>
    `).join('');
    if (els.cityLine) {
      els.cityLine.textContent = `${state.config.cityName} — ${state.config.countryName} · ${PT.METHODS[state.config.method].name}`;
    }
    els.times.querySelectorAll('[data-pt-adhan]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.ptAdhan === 'fajr' ? state.config.fajrAdhanId : state.config.adhanId;
        playAdhan(id);
      });
    });
    renderIqamaLine();
  }

  function renderIqamaLine() {
    if (!els.iqamaLine) return;
    const config = state.config;
    if (!config.iqamaEnabled) { els.iqamaLine.textContent = 'تنبيه الإقامة متوقف.'; return; }
    const parts = PRAYER_KEYS.map((k) => `${PT.describe(k)} ${config.iqamaMinutes[k]}د`);
    els.iqamaLine.textContent = `إشعار «قم إلى صلاتك» بعد الأذان: ${parts.join(' · ')}`;
  }

  function renderAdhanState() {
    renderAdhanList();
  }

  // تنزيل كل الأذان غير المحزوم (يعمل بعدها دون إنترنت للأبد)
  async function downloadAllAdhans() {
    const pending = DATA.adhans.filter((item) => !item.local && !state.downloaded.has(item.id));
    if (!pending.length) { toast('كل الأذان متاح دون إنترنت بالفعل.'); return; }
    toast(`جاري تنزيل ${pending.length} أذانًا…`);
    let done = 0;
    for (const item of pending) {
      try {
        await downloadAdhan(item);
        state.downloaded.add(item.id);
        done += 1;
      } catch { /* نتجاوز الفاشل ونكمل */ }
    }
    toast(done ? `تم تنزيل ${done} أذانًا على الجهاز.` : 'تعذّر التنزيل؛ تحقّق من الاتصال.');
    renderAdhanList();
  }


  // مفضلة الأصوات مشتركة مع مكتبة القرّاء (مفتاح واحد في المتصفح)
  const FAV_KEY = 'voice-favs';
  function favState() {
    try { return JSON.parse(localStorage.getItem(FAV_KEY) || '{}') || {}; } catch { return {}; }
  }
  function isFavAdhan(id) {
    const list = favState().adhans;
    return Array.isArray(list) && list.includes(String(id));
  }
  function toggleFavAdhan(id) {
    const all = favState();
    const list = Array.isArray(all.adhans) ? all.adhans.slice() : [];
    const key = String(id);
    const at = list.indexOf(key);
    if (at >= 0) list.splice(at, 1); else list.push(key);
    all.adhans = list;
    try { localStorage.setItem(FAV_KEY, JSON.stringify(all)); } catch { /* مساحة ممتلئة */ }
  }

  async function renderAdhanList() {
    if (!els.adhanList) return;
    const config = state.config;
    // نتحقق مرة واحدة من الأذانات «المحزومة» فعلًا على هذا الجهاز (نسخة تحديث
    // وصلتها الواجهة قبل ملفات الأذان لا تحتويها) فلا نعرض «محلي» كذبًا.
    await Promise.all(DATA.adhans.filter((item) => item.local).map((item) => localAdhanReady(item)));
    const ordered = DATA.adhans.slice().sort((a, b) => (isFavAdhan(b.id) ? 1 : 0) - (isFavAdhan(a.id) ? 1 : 0));
    const rows = await Promise.all(ordered.map(async (item) => {
      const downloaded = await isAdhanDownloaded(item);
      const onDevice = item.local && localReadyCache.get(item.id) ? 'محلي' : (downloaded ? 'منزّل' : 'يحتاج تنزيل');
      const selected = config.adhanId === item.id;
      const selectedFajr = config.fajrAdhanId === item.id;
      return `
        <div class="pt-adhan${selected ? ' is-selected' : ''}" data-id="${item.id}" data-name="${esc(item.name)} ${esc(item.region || '')} ${esc(item.maqamLabel || '')} ${esc(item.maqam || '')}">
          <div class="pt-adhan-main">
            <strong>${item.name}</strong>
            <span class="muted">${item.maqamLabel ? `<b class="pt-maqam">${esc(item.maqamLabel)}</b> · ` : ''}${item.region ? esc(item.region) + ' · ' : ''}${Math.round(item.seconds / 60)} د${item.fajr ? ' · أذان فجر' : ''} · ${onDevice}</span>
          </div>
          <div class="pt-adhan-actions">
            <button class="pt-mini${isFavAdhan(item.id) ? ' on' : ''}" data-act="fav" data-id="${item.id}" title="مفضلة">★</button>
            <button class="pt-mini" data-act="preview" data-id="${item.id}" title="تجربة">▶</button>
            <button class="pt-mini" data-act="download" data-id="${item.id}" title="${downloaded ? 'محفوظ على الجهاز' : 'تنزيل للاستخدام دون إنترنت'}">${downloaded ? '✓' : '⤓'}</button>
            <button class="pt-mini${selected ? ' on' : ''}" data-act="use" data-id="${item.id}" title="أذان الصلوات">أ</button>
            <button class="pt-mini${selectedFajr ? ' on' : ''}" data-act="use-fajr" data-id="${item.id}" title="أذان الفجر">ف</button>
          </div>
        </div>
      `;
    }));
    els.adhanList.innerHTML = `<div class="pt-adhan-summary">
        <span class="muted">${DATA.adhans.filter((i) => i.local && localReadyCache.get(i.id)).length} أذانًا جاهزًا دون إنترنت · ${DATA.adhans.filter((i) => !(i.local && localReadyCache.get(i.id))).length} يحتاج تنزيلًا</span>
        <button class="btn small ghost" id="ptAdhanDownloadAll">تنزيل المتبقي</button>
      </div>
      <div class="pt-adhan-filter">
        <input id="ptAdhanSearch" type="search" inputmode="search" placeholder="ابحث باسم المؤذن أو المقام…" value="${esc(state.adhanFilter || '')}" aria-label="بحث المؤذنين والمقامات" />
        <span class="muted" id="ptAdhanCount">${DATA.adhans.length} مؤذنًا</span>
      </div>
      <div class="pt-adhan-chips" role="group" aria-label="تصفية المقامات">
        <button class="pt-chip${state.adhanFilter === 'مقام' ? ' is-on' : ''}" data-adhan-chip="maqam" type="button">مقامات العفاسي</button>
        <button class="pt-chip${state.adhanFilter === '' ? ' is-on' : ''}" data-adhan-chip="all" type="button">الكل</button>
      </div>` + rows.join('');
    const allBtn = els.adhanList.querySelector('#ptAdhanDownloadAll');
    if (allBtn) allBtn.addEventListener('click', downloadAllAdhans);
    const searchEl = els.adhanList.querySelector('#ptAdhanSearch');
    const countEl = els.adhanList.querySelector('#ptAdhanCount');
    const applyFilter = () => {
      const q = (state.adhanFilter || '').trim();
      let shown = 0;
      els.adhanList.querySelectorAll('.pt-adhan').forEach((row) => {
        const hit = !q || (row.dataset.name || '').includes(q);
        row.hidden = !hit;
        if (hit) shown += 1;
      });
      if (countEl) countEl.textContent = q ? `${shown} من ${DATA.adhans.length} مؤذنًا` : `${DATA.adhans.length} مؤذنًا`;
    };
    if (searchEl) {
      searchEl.addEventListener('input', () => { state.adhanFilter = searchEl.value; applyFilter(); });
    }
    els.adhanList.querySelectorAll('[data-adhan-chip]').forEach((chip) => {
      chip.addEventListener('click', () => {
        state.adhanFilter = chip.dataset.adhanChip === 'maqam' ? 'مقام' : '';
        renderAdhanList();
      });
    });
    applyFilter();
    els.adhanList.querySelectorAll('[data-act]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const item = adhanById(btn.dataset.id);
        const act = btn.dataset.act;
        if (act === 'fav') { toggleFavAdhan(item.id); renderAdhanList(); return; }
        if (act === 'preview') { playAdhan(item.id); return; }
        if (act === 'use') { state.config.adhanId = item.id; saveConfig(); renderAdhanList(); toast(`أذان الصلوات: ${item.name}`); return; }
        if (act === 'use-fajr') { state.config.fajrAdhanId = item.id; saveConfig(); renderAdhanList(); toast(`أذان الفجر: ${item.name}`); return; }
        if (act === 'download') {
          toast(`جاري تنزيل أذان ${item.name}…`);
          try {
            const size = await downloadAdhan(item);
            toast(`حُفظ الأذان على الجهاز (${(size / 1048576).toFixed(1)} ميجا) ويعمل دون إنترنت.`);
          } catch {
            toast('تعذّر تنزيل الأذان؛ تحقّق من الاتصال.');
          }
          renderAdhanList();
        }
      });
    });
  }

  function renderCities() {
    if (!els.citySelect) return;
    els.citySelect.innerHTML = DATA.cities
      .map((city, index) => `<option value="${index}">${city.n} — ${city.c}</option>`).join('');
    if (state.config.cityIndex >= 0) els.citySelect.value = String(state.config.cityIndex);
  }

  function setCity(index) {
    const city = DATA.cities[index];
    if (!city) return;
    state.config.cityIndex = index;
    state.config.lat = city.lat;
    state.config.lng = city.lng;
    state.config.tz = city.tz;
    state.config.cityName = city.n;
    state.config.countryName = city.c;
    state.config.method = city.m;
    saveConfig();
    syncControls();
    renderHero();
    renderTimes();
    toast(`تم ضبط الموقع على ${city.n}.`);
  }

  function syncControls() {
    const config = state.config;
    if (els.citySelect) els.citySelect.value = String(config.cityIndex >= 0 ? config.cityIndex : 0);
    if (els.methodSelect) els.methodSelect.value = config.method;
    if (els.madhabSelect) els.madhabSelect.value = config.madhab;
    if (els.highLat) els.highLat.value = config.highLatitude;
    if (els.adhanToggle) els.adhanToggle.checked = !!config.adhanEnabled;
    if (els.iqamaToggle) els.iqamaToggle.checked = !!config.iqamaEnabled;
    if (els.sleepToggle) els.sleepToggle.checked = config.sleepAfterAdhan !== false;
    if (els.sleepStill) els.sleepStill.checked = config.sleepStill !== false;
    if (els.sleepGrace) els.sleepGrace.value = String(Math.max(0, num(config.sleepGraceSeconds, 30)));
    if (els.closeToggle) els.closeToggle.checked = config.closeAfterAdhan !== false;
    if (els.closeDelay) els.closeDelay.value = String(Math.max(0, num(config.closeDelaySeconds, 20)));
    if (els.preSelect) els.preSelect.value = String(config.preMinutes);
    if (els.clock24) els.clock24.checked = !!config.use24h;
    if (els.volumeRange) els.volumeRange.value = String(Math.round(config.adhanVolume * 100));
    PRAYER_KEYS.forEach((key) => {
      const field = el(`ptIqama-${key}`);
      if (field) field.value = String(config.iqamaMinutes[key]);
      const adj = el(`ptAdj-${key}`);
      if (adj) adj.value = String(config.adjustments[key]);
    });
    renderIqamaLine();
    renderAdhanList();
  }

  // ---------- القبلة ----------
  function renderQibla() {
    if (!els.qiblaPanel) return;
    const q = PT.qibla(state.config.lat, state.config.lng);
    if (!q) return;
    const sun = PT.sunAzimuth({
      date: new Date(), lat: state.config.lat, lng: state.config.lng,
      timezone: offsetHours(state.config.tz, new Date()),
    });
    els.qiblaBearing.textContent = `${q.bearing.toFixed(1)}°`;
    els.qiblaDistance.textContent = `${Math.round(q.distance).toLocaleString('ar-EG')} كم إلى الكعبة`;
    els.qiblaCompass.style.transform = `rotate(${(-q.bearing).toFixed(1)}deg)`;
    if (!sun) {
      els.qiblaSun.textContent = 'لا يمكن حساب موضع الشمس الآن.';
    } else if (sun.altitude < 3) {
      els.qiblaSun.textContent = 'الشمس الآن تحت الأفق (ليل أو غروب)؛ استخدم البوصلة أو الإحداثيات، أو أعد المحاولة نهارًا.';
    } else {
      els.qiblaSun.textContent = `الشمس الآن على ${sun.azimuth.toFixed(0)}° وارتفاع ${sun.altitude.toFixed(0)}° — القبلة ${describeSunHint(q.bearing, sun.azimuth)}.`;
    }
    if (state.compass.heading == null && els.qiblaNeedle) {
      els.qiblaNeedle.style.transform = `rotate(${q.bearing.toFixed(1)}deg)`;
    }
  }

  function describeSunHint(bearing, azimuth) {
    const diff = ((bearing - azimuth + 540) % 360) - 180;
    if (Math.abs(diff) < 8) return 'أمامك مباشرة (القبلة في اتجاه الشمس)';
    if (diff > 0) return `على ${Math.abs(diff) > 90 ? 'يمينك' : 'يمينك قليلًا'} بمقدار ${Math.round(Math.abs(diff))}°`;
    return `على ${Math.abs(diff) > 90 ? 'يسارك' : 'يسارك قليلًا'} بمقدار ${Math.round(Math.abs(diff))}°`;
  }

  // لا نترك المستخدم أمام عقرب ثابت: إن لم تصل قراءة خلال ٢٫٥ ثانية نفتح الطرق البديلة.
  function armCompassWatchdog() {
    if (state.compassWatchdog) clearTimeout(state.compassWatchdog);
    state.compassWatchdog = setTimeout(() => {
      if (state.compass.heading == null) {
        enableFallbackDirection('لم يصل أي قراءة من حسّاس الاتجاه؛ استخدم إحدى الطرق البديلة بالأسفل.');
      }
    }, 2500);
  }
  function disarmCompassWatchdog() {
    if (state.compassWatchdog) clearTimeout(state.compassWatchdog);
    state.compassWatchdog = null;
  }

  async function startCompass() {
    armCompassWatchdog();
    if (hasSensors()) {
      const started = await sensorCall('startCompass');
      if (!started) {
        // لا يوجد أي حساس اتجاه: ننتقل إلى الاتجاه بالموقع والشمس.
        enableFallbackDirection('لا يوجد حسّاس اتجاه في هذا الهاتف؛ استخدم المعايرة بالشمس أو الاتجاه بالدرجات.');
        return;
      }
      state.compass.mode = (started && started.mode) || 'rotation';
      if (!state.compass.listening && Cap.registerPlugin) {
        state.compass.listening = true;
        Cap.registerPlugin(SENSORS_PLUGIN).addListener('heading', (event) => {
          const heading = Number(event && event.heading);
          if (!Number.isFinite(heading)) return;
          state.compass.raw = heading;
          state.compass.mode = event.mode || state.compass.mode;
          state.compass.heading = (heading + state.compass.offset + 720) % 360;
          state.compass.active = true;
          state.compass.fallback = false;
          disarmCompassWatchdog();
          updateCompass();
        });
      }
      toast('حرّك الهاتف على شكل ∞ لمعايرة البوصلة.');
      return;
    }
    const DeviceOrientation = root.DeviceOrientationEvent;
    if (!DeviceOrientation) {
      enableFallbackDirection('المتصفح لا يوفّر حسّاس اتجاه؛ استخدم المعايرة بالشمس أو الاتجاه بالدرجات.');
      return;
    }
    if (typeof DeviceOrientation.requestPermission === 'function') {
      try {
        const granted = await DeviceOrientation.requestPermission();
        if (granted !== 'granted') { toast('لم يُسمح باستخدام حساس الاتجاه.'); return; }
      } catch {
        toast('تعذّر طلب إذن حساس الاتجاه.');
        return;
      }
    }
    if (state.compass.handler) {
      root.removeEventListener('deviceorientationabsolute', state.compass.handler);
      root.removeEventListener('deviceorientation', state.compass.handler);
    }
    state.compass.handler = (event) => {
      const heading = event.webkitCompassHeading != null ? event.webkitCompassHeading
        : (event.alpha != null ? 360 - event.alpha : null);
      if (heading == null) return;
      state.compass.heading = heading;
      state.compass.active = true;
      state.compass.fallback = false;
      disarmCompassWatchdog();
      updateCompass();
    };
    root.addEventListener('deviceorientationabsolute', state.compass.handler, true);
    root.addEventListener('deviceorientation', state.compass.handler, true);
    armCompassWatchdog();
    toast('حرّك الهاتف على شكل ∞ لمعايرة البوصلة.');
  }

  // ---------- طرق تحديد القبلة بدون حسّاس بوصلة ----------
  // 1) الشمس والظل: سمت الشمس يُحسب فلكيًا من الموقع والوقت، فيُخبر المستخدم
  //    بمقدار الانحراف من الشمس/الظل مباشرة — لا يحتاج أي حسّاس.
  // 2) التنقل بالـGPS: اتجاه الحركة من الإحداثيات المتتابعة يعطي الشمال فعليًا.
  // 3) الدرجات: إدخال اتجاه معروف يدويًا.
  function normDelta(deg) {
    let d = deg % 360;
    if (d > 180) d -= 360;
    if (d < -180) d += 360;
    return d;
  }

  function qiblaBearing() {
    const q = PT.qibla(state.config.lat, state.config.lng);
    return q && Number.isFinite(q.bearing) ? q.bearing : null;
  }

  function selectAltMethod(method) {
    state.altMethod = method;
    document.querySelectorAll('.qibla-method').forEach((b) => {
      const on = b.dataset.method === method;
      b.classList.toggle('on', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    const panels = { sun: 'qiblaSunPanel', gps: 'qiblaGpsPanel', manual: 'qiblaManualPanel' };
    Object.entries(panels).forEach(([key, id]) => {
      const node = document.getElementById(id);
      if (node) node.hidden = key !== method;
    });
    if (method === 'sun') renderSunGuide();
    if (method === 'gps') renderGpsGuide();
    if (method === 'manual') stopGpsWatch();
    if (method !== 'gps') stopGpsWatch();
  }

  function renderSunGuide() {
    const head = document.getElementById('qiblaSunHead');
    const how = document.getElementById('qiblaSunHow');
    const data = document.getElementById('qiblaSunData');
    if (!head) return;
    const q = qiblaBearing();
    const sun = PT.sunAzimuth({
      date: new Date(), lat: state.config.lat, lng: state.config.lng,
      timezone: offsetHours(state.config.tz, new Date()),
    });
    if (q == null) { head.textContent = 'حدّد موقعك أولًا.'; return; }
    if (!sun) { head.textContent = 'تعذّر حساب موضع الشمس.'; return; }
    if (sun.altitude < 3) {
      head.textContent = 'الشمس قريبة من الأفق الآن (فجر/غروب/ليل).';
      if (how) how.textContent = 'انتظر ارتفاع الشمس أو استخدم طريقة «التنقل GPS» أو الدرجات.';
      if (data) data.textContent = `ارتفاع الشمس الآن ${sun.altitude.toFixed(1)}°.`;
      return;
    }
    // الزاوية بين الشمس والقبلة مقاسة في اتجاه عقارب الساعة من الشمس
    const fromSun = normDelta(q - sun.azimuth);
    const side = fromSun >= 0 ? 'يمينك' : 'يسارك';
    const abs = Math.abs(Math.round(fromSun));
    head.textContent = `أنت تواجه الشمس؟ القبلة على ${side} بمقدار ${abs}°`;
    if (how) {
      const shadowSide = fromSun >= 0 ? 'يسارك' : 'يمينك';
      how.textContent = `طريقة الظل: قف والشمس خلفك (ظلّك أمامك) فتكون القبلة على ${shadowSide} بمقدار ${abs}°. ولو كانت الشمس على وجهك فالقبلة على ${side} بمقدار ${abs}°.`;
    }
    if (data) {
      data.textContent = `سمت الشمس ${sun.azimuth.toFixed(0)}° · القبلة ${q.toFixed(0)}° · ارتفاع الشمس ${sun.altitude.toFixed(0)}° — يُحدَّث كل دقيقة.`;
    }
  }

  function renderGpsGuide() {
    const head = document.getElementById('qiblaGpsHead');
    const how = document.getElementById('qiblaGpsHow');
    if (!head) return;
    const q = qiblaBearing();
    if (q == null) { head.textContent = 'حدّد موقعك أولًا.'; return; }
    if (state.gpsHeading == null) {
      head.textContent = 'امشِ عشر خطوات في اتجاه ثابت…';
      if (how) how.textContent = 'بعد أول حركة حقيقية يظهر اتجاهك من الشمال، ثم نقول لك كم تنحرف عن القبلة. لا يحتاج أي حسّاس.';
      return;
    }
    const delta = normDelta(q - state.gpsHeading);
    const side = delta >= 0 ? 'يمينًا' : 'يسارًا';
    head.textContent = Math.abs(delta) <= 6
      ? 'أنت تسير نحو القبلة ✓'
      : `اتجاهك الآن ${Math.round(state.gpsHeading)}° — انحرف ${side} بمقدار ${Math.abs(Math.round(delta))}°`;
    if (how) how.textContent = `اتجاه سيرك من الـGPS ${Math.round(state.gpsHeading)}° · القبلة ${Math.round(q)}°. استمر بالمشي قليلًا لتثبيت القراءة.`;
  }

  function stopGpsWatch() {
    if (state.gpsWatch != null && root.navigator && root.navigator.geolocation) {
      root.navigator.geolocation.clearWatch(state.gpsWatch);
    }
    state.gpsWatch = null;
    state.gpsLast = null;
  }

  function bearingBetween(a, b) {
    const r = (v) => (v * Math.PI) / 180;
    const y = Math.sin(r(b.lng - a.lng)) * Math.cos(r(b.lat));
    const x = Math.cos(r(a.lat)) * Math.sin(r(b.lat)) - Math.sin(r(a.lat)) * Math.cos(r(b.lat)) * Math.cos(r(b.lng - a.lng));
    return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
  }

  function startGpsWatch() {
    if (!root.navigator || !root.navigator.geolocation) {
      toast('هذا الجهاز لا يدعم تحديد الموقع.');
      return;
    }
    stopGpsWatch();
    selectAltMethod('gps');
    state.gpsWatch = root.navigator.geolocation.watchPosition((pos) => {
      const c = pos.coords;
      if (Number.isFinite(c.heading) && c.speed > 0.6) {
        state.gpsHeading = c.heading;
      } else if (state.gpsLast && Number.isFinite(c.accuracy)) {
        const moved = bearingBetween(state.gpsLast, { lat: c.latitude, lng: c.longitude });
        const dist = Math.abs(c.latitude - state.gpsLast.lat) + Math.abs(c.longitude - state.gpsLast.lng);
        if (dist > 0.00004) state.gpsHeading = moved; // ~4 أمتار حركة كافية
      }
      state.gpsLast = { lat: c.latitude, lng: c.longitude };
      renderGpsGuide();
    }, () => toast('تعذّر قراءة الموقع؛ تحقّق من إذن الموقع.'), {
      enableHighAccuracy: true, maximumAge: 1000, timeout: 15000,
    });
  }

  let altBound = false;
  function renderAltMethods() {
    if (altBound) { selectAltMethod(state.altMethod || 'sun'); return; }
    altBound = true;
    document.querySelectorAll('.qibla-method').forEach((btn) => {
      btn.addEventListener('click', () => selectAltMethod(btn.dataset.method));
    });
    const start = document.getElementById('qiblaGpsStart');
    if (start) start.addEventListener('click', startGpsWatch);
    const stop = document.getElementById('qiblaGpsStop');
    if (stop) stop.addEventListener('click', () => { stopGpsWatch(); renderGpsGuide(); });
    const refresh = document.getElementById('qiblaSunRefresh');
    if (refresh) refresh.addEventListener('click', renderSunGuide);
    // اختيار تلقائي: الشمس نهارًا، GPS ليلًا — تُستبدل بالبوصلة إذا وُجدت.
    selectAltMethod(state.altMethod || (new Date().getHours() >= 5 && new Date().getHours() <= 18 ? 'sun' : 'gps'));
    setInterval(() => { if (state.altMethod === 'sun') renderSunGuide(); }, 60000);
  }

  function enableFallbackDirection(message) {
    state.compass.fallback = true;
    if (els.qiblaTurn) els.qiblaTurn.textContent = 'لا يوجد حسّاس بوصلة — اختر طريقة من الأسفل لتحديد القبلة.';
    const note = document.getElementById('qiblaFallbackNote');
    if (note) note.textContent = message || '';
    if (els.qiblaHeading) els.qiblaHeading.textContent = 'بلا حسّاس';
    renderQibla();
    renderAltMethods();
    // نرفع بطاقة الطرق البديلة فوق البوصلة حتى لا يبحث عنها المستخدم
    const view = document.getElementById('view-qibla');
    const card = document.getElementById('qiblaFallbackCard');
    if (view && card) {
      const head = view.querySelector('.card');
      if (head && head !== card) view.insertBefore(card, head.nextSibling);
      setTimeout(() => card.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 120);
    }
    toast('هاتفك بلا حسّاس بوصلة، فتحنا لك طرقًا بديلة.');
  }

  function calibrateTo(deg) {
    const raw = state.compass.raw;
    if (!Number.isFinite(raw)) {
      state.compass.heading = Number(deg) || 0;
      state.compass.active = true;
      updateCompass();
      return false;
    }
    state.compass.offset = (Number(deg) - raw + 720) % 360;
    state.compass.heading = (raw + state.compass.offset) % 360;
    updateCompass();
    return true;
  }

  function calibrateBySun() {
    const sun = PT.sunAzimuth({
      date: new Date(), lat: state.config.lat, lng: state.config.lng,
      timezone: offsetHours(state.config.tz, new Date()),
    });
    const note = document.getElementById('qiblaFallbackNote');
    if (!sun || sun.altitude < 3) {
      if (note) note.textContent = 'الشمس الآن قريبة من الأفق؛ انتظر النهار أو استخدم ضبط الدرجات.';
      toast('لا يمكن ضبط الاتجاه بالشمس الآن.');
      return;
    }
    calibrateTo(sun.azimuth);
    if (note) {
      note.textContent = `تم الضبط على الشمس (${sun.azimuth.toFixed(0)}°) — وجّه أعلى الهاتف نحو الشمس وقت الضغط ليكون الاتجاه صحيحًا.`;
    }
    toast('تمت المعايرة بالشمس.');
  }

  function calibrateManual() {
    const input = document.getElementById('qiblaManualDeg');
    const deg = input ? Number(input.value) : NaN;
    if (!Number.isFinite(deg) || deg < 0 || deg > 359) { toast('اكتب اتجاهًا بين 0 و359 درجة.'); return; }
    calibrateTo(deg);
    const note = document.getElementById('qiblaFallbackNote');
    if (note) note.textContent = `الاتجاه المضبوط: ${deg}° — أدر الهاتف بعد ذلك وسيتابع العقرب.`;
    toast('تم ضبط الاتجاه يدويًا.');
  }

  function updateCompass() {
    if (!els.qiblaDial || state.compass.heading == null) return;
    const q = PT.qibla(state.config.lat, state.config.lng);
    if (!q) return;
    const delta = ((q.bearing - state.compass.heading + 540) % 360) - 180;
    els.qiblaDial.style.transform = `rotate(${(-state.compass.heading).toFixed(1)}deg)`;
    els.qiblaNeedle.style.transform = `rotate(${q.bearing.toFixed(1)}deg)`;
    els.qiblaTurn.textContent = Math.abs(delta) < 4
      ? 'أنت تواجه القبلة الآن ✓'
      : `أدر الهاتف ${delta > 0 ? 'يمينًا' : 'يسارًا'} بمقدار ${Math.round(Math.abs(delta))}°`;
    if (els.qiblaHeading) els.qiblaHeading.textContent = `${Math.round(state.compass.heading)}°`;
  }

  function applyPosition(latitude, longitude) {
    let nearest = 0;
    let best = Infinity;
    DATA.cities.forEach((city, index) => {
      const d = (city.lat - latitude) ** 2 + ((city.lng - longitude) * Math.cos(latitude * Math.PI / 180)) ** 2;
      if (d < best) { best = d; nearest = index; }
    });
    state.config.lat = latitude;
    state.config.lng = longitude;
    state.config.cityIndex = nearest;
    state.config.cityName = DATA.cities[nearest].n;
    state.config.countryName = DATA.cities[nearest].c;
    state.config.tz = (function guessZone() {
      try { return Intl.DateTimeFormat().resolvedOptions().timeZone || DATA.cities[nearest].tz; }
      catch { return DATA.cities[nearest].tz; }
    })();
    saveConfig();
    syncControls();
    renderHero();
    renderTimes();
    renderQibla();
    refreshQiblaPlace();
    renderAltMethods();
    toast(`تم تحديد موقعك (${latitude.toFixed(2)}, ${longitude.toFixed(2)}) وضُبط على ${state.config.cityName}.`);
  }

  async function useGps() {
    toast('جاري تحديد موقعك…');
    // في نسخة أندرويد نطلب إذن الموقع من النظام مباشرة، وإلا فشل الطلب بصمت.
    if (hasSensors()) {
      const result = await sensorCall('getLocation');
      if (result && Number.isFinite(Number(result.lat)) && Number.isFinite(Number(result.lng))) {
        applyPosition(Number(result.lat), Number(result.lng));
        if (result.stale) toast('استُخدم آخر موقع معروف؛ جرّب في مكان مكشوف لدقة أعلى.');
        return;
      }
      toast('لم يُسمح بالوصول إلى الموقع أو هو مغلق؛ فعّل خدمة الموقع وامنح الإذن ثم أعد المحاولة.');
      return;
    }
    if (!navigator.geolocation) { toast('لا يتوفّر تحديد الموقع في هذا الجهاز.'); return; }
    navigator.geolocation.getCurrentPosition(
      (position) => applyPosition(position.coords.latitude, position.coords.longitude),
      () => toast('تعذّر تحديد الموقع؛ اختر مدينتك يدويًا من القائمة.'),
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 600000 },
    );
  }

  function setManualCoords() {
    const lat = num(els.coordLat.value, NaN);
    const lng = num(els.coordLng.value, NaN);
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
      toast('أدخل خط عرض بين -90 و90 وخط طول بين -180 و180.');
      return;
    }
    state.config.lat = lat;
    state.config.lng = lng;
    state.config.cityIndex = -1;
    state.config.cityName = 'موقع مخصّص';
    state.config.countryName = `${lat.toFixed(2)}, ${lng.toFixed(2)}`;
    saveConfig();
    renderHero();
    renderTimes();
    renderQibla();
    toast('حُفظ الموقع المخصّص.');
  }

  // ---------- التركيب ----------
  function bindEvents() {
    const sunBtn = document.getElementById('qiblaSunBtn');
    if (sunBtn) sunBtn.addEventListener('click', calibrateBySun);
    const northBtn = document.getElementById('qiblaNorthBtn');
    if (northBtn) northBtn.addEventListener('click', calibrateManual);
    if (els.citySelect) els.citySelect.addEventListener('change', (e) => setCity(Number(e.target.value)));
    els.gpsBtn && els.gpsBtn.addEventListener('click', useGps);
    els.manualBtn && els.manualBtn.addEventListener('click', setManualCoords);
    els.methodSelect && els.methodSelect.addEventListener('change', (e) => {
      state.config.method = e.target.value; saveConfig(); renderHero(); renderTimes();
    });
    els.madhabSelect && els.madhabSelect.addEventListener('change', (e) => {
      state.config.madhab = e.target.value; saveConfig(); renderHero(); renderTimes();
    });
    els.highLat && els.highLat.addEventListener('change', (e) => {
      state.config.highLatitude = e.target.value; saveConfig(); renderHero(); renderTimes();
    });
    els.clock24 && els.clock24.addEventListener('change', (e) => {
      state.config.use24h = e.target.checked; saveConfig(); renderHero(); renderTimes();
    });
    els.adhanToggle && els.adhanToggle.addEventListener('change', (e) => {
      state.config.adhanEnabled = e.target.checked; saveConfig();
      toast(e.target.checked ? 'تشغيل الأذان تلقائيًا مفعّل.' : 'تشغيل الأذان تلقائيًا متوقف.');
    });
    els.iqamaToggle && els.iqamaToggle.addEventListener('change', (e) => {
      state.config.iqamaEnabled = e.target.checked; saveConfig(); renderIqamaLine();
    });
    els.sleepToggle && els.sleepToggle.addEventListener('change', (e) => {
      state.config.sleepAfterAdhan = e.target.checked; saveConfig(); renderSleepLine();
      toast(e.target.checked ? 'إطفاء الشاشة بعد الأذان مفعّل.' : 'إطفاء الشاشة بعد الأذان متوقف.');
      if (!e.target.checked) { stopSleepTicker(); if (sleepState.blocked) wakeUpScreen(); }
    });
    els.sleepStill && els.sleepStill.addEventListener('change', (e) => {
      state.config.sleepStill = e.target.checked; saveConfig(); renderSleepLine();
    });
    els.sleepGrace && els.sleepGrace.addEventListener('change', (e) => {
      state.config.sleepGraceSeconds = Math.max(0, Math.min(600, num(e.target.value, 30)));
      e.target.value = String(state.config.sleepGraceSeconds);
      saveConfig(); renderSleepLine();
    });
    els.sleepAdminBtn && els.sleepAdminBtn.addEventListener('click', () => { toggleSleepAdmin(); });
    els.closeToggle && els.closeToggle.addEventListener('change', (e) => {
      state.config.closeAfterAdhan = e.target.checked;
      // الإغلاق فرع عن إطفاء الشاشة: تفعيله يُفعّل الإطفاء معه.
      if (e.target.checked && state.config.sleepAfterAdhan === false) {
        state.config.sleepAfterAdhan = true;
        if (els.sleepToggle) els.sleepToggle.checked = true;
      }
      saveConfig();
      if (!e.target.checked) cancelScheduledClose();
      renderSleepLine();
      toast(e.target.checked ? 'إغلاق التطبيق بعد الأذان مفعّل.' : 'إغلاق التطبيق بعد الأذان متوقف.');
    });
    els.closeDelay && els.closeDelay.addEventListener('change', (e) => {
      state.config.closeDelaySeconds = Math.max(0, Math.min(600, num(e.target.value, 20)));
      e.target.value = String(state.config.closeDelaySeconds);
      saveConfig(); cancelScheduledClose(); renderSleepLine();
    });
    els.preSelect && els.preSelect.addEventListener('change', (e) => {
      state.config.preMinutes = Number(e.target.value); saveConfig();
    });
    els.volumeRange && els.volumeRange.addEventListener('input', (e) => {
      setAdhanVolume(Number(e.target.value) / 100);
    });
    PRAYER_KEYS.forEach((key) => {
      const field = el(`ptIqama-${key}`);
      field && field.addEventListener('change', () => {
        state.config.iqamaMinutes[key] = Math.max(0, Math.min(60, num(field.value, 15)));
        saveConfig(); renderIqamaLine();
      });
      const adj = el(`ptAdj-${key}`);
      adj && adj.addEventListener('change', () => {
        state.config.adjustments[key] = Math.max(-30, Math.min(30, num(adj.value, 0)));
        saveConfig(); renderHero(); renderTimes();
      });
    });
    els.stopAdhan && els.stopAdhan.addEventListener('click', stopAdhan);
    wireAdhanScreen();
    checkPendingNativeAdhan();
    document.addEventListener('visibilitychange', () => { if (!document.hidden) checkPendingNativeAdhan(); });
    const screenBtn = el('ptAdhanScreen');
    screenBtn && screenBtn.addEventListener('click', () => {
      if (state.playingId) { openAdhanScreen({ muezzinId: state.playingId, live: Boolean(state.adhanLive) }); return; }
      const key = state.next ? state.next.key : 'dhuhr';
      const id = key === 'fajr' ? state.config.fajrAdhanId : state.config.adhanId;
      // تجربة يدوية: العنوان يبقى «أذان» إلا إذا دخل وقت الصلاة فعلًا
      playAdhan(id);
    });
    els.playNextAdhan && els.playNextAdhan.addEventListener('click', () => {
      const key = state.next ? state.next.key : 'dhuhr';
      playAdhan(key === 'fajr' ? state.config.fajrAdhanId : state.config.adhanId);
    });
    els.fajrAdhanBtn && els.fajrAdhanBtn.addEventListener('click', () => playAdhan(state.config.fajrAdhanId));
    els.compassBtn && els.compassBtn.addEventListener('click', startCompass);
    els.qiblaRefresh && els.qiblaRefresh.addEventListener('click', renderQibla);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) { renderHero(); renderTimes(); }
    });
  }

  function init(options = {}) {
    loadConfig();
    state.toast = options.toast || null;
    state.onNavigate = options.onNavigate || null;
    els.nextName = el('ptNextName');
    els.nextAt = el('ptNextAt');
    els.countdown = el('ptCountdown');
    els.bar = el('ptBar');
    els.times = el('ptTimes');
    els.cityLine = el('ptCityLine');
    els.citySelect = el('ptCity');
    els.gpsBtn = el('ptGps');
    els.methodSelect = el('ptMethod');
    els.madhabSelect = el('ptMadhab');
    els.highLat = el('ptHighLat');
    els.clock24 = el('ptClock24');
    els.adhanToggle = el('ptAdhanEnabled');
    els.adhanList = el('ptAdhanList');
    els.iqamaToggle = el('ptIqamaEnabled');
    els.iqamaLine = el('ptIqamaLine');
    els.preSelect = el('ptPre');
    els.volumeRange = el('ptVolume');
    els.stopAdhan = el('ptStop');
    els.playNextAdhan = el('ptPlayAdhan');
    els.fajrAdhanBtn = el('ptFajrAdhan');
    els.qiblaPanel = el('ptQiblaCard');
    els.qiblaBearing = el('ptQiblaBearing');
    els.qiblaDistance = el('ptQiblaDistance');
    els.qiblaCompass = el('ptQiblaCompass');
    els.qiblaSun = el('ptQiblaSun');
    els.qiblaDial = el('ptCompassDial');
    els.qiblaNeedle = el('ptCompassNeedle');
    els.qiblaTurn = el('ptCompassTurn');
    els.qiblaHeading = el('ptHeading');
    els.compassBtn = el('ptCompassStart');
    els.qiblaRefresh = el('ptQiblaRefresh');
    els.manualBtn = el('ptManual');
    els.coordLat = el('ptLat');
    els.coordLng = el('ptLng');
    els.methodNote = el('ptMethodNote');
    els.bgStatus = el('ptBgStatus');
    els.sleepToggle = el('ptSleepEnabled');
    els.sleepGrace = el('ptSleepGrace');
    els.sleepStill = el('ptSleepStill');
    els.sleepAdminBtn = el('ptSleepAdmin');
    els.sleepStatus = el('ptSleepStatus');
    els.closeToggle = el('ptCloseEnabled');
    els.closeDelay = el('ptCloseDelay');
    if (!els.times) return false;

    renderCities();
    if (els.methodSelect) {
      els.methodSelect.innerHTML = Object.entries(PT.METHODS)
        .map(([key, value]) => `<option value="${key}">${value.name}</option>`).join('');
    }
    if (els.highLat) {
      els.highLat.innerHTML = Object.entries(PT.HIGH_LATITUDE)
        .map(([key, value]) => `<option value="${key}">${value}</option>`).join('');
    }
    if (els.coordLat) els.coordLat.value = String(state.config.lat.toFixed(3));
    if (els.coordLng) els.coordLng.value = String(state.config.lng.toFixed(3));
    syncControls();
    bindEvents();
    renderHero();
    renderTimes();
    renderQibla();
    refreshQiblaPlace();
    renderAltMethods();
    scheduleChecks();
    syncBackground(true);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) syncBackground(false);
    });
    wireSleepSignals();
    renderSleepLine();
    return true;
  }

  // اسم المكان في تبويب القبلة المستقل
  function refreshQiblaPlace() {
    const node = document.getElementById('qiblaPlace');
    if (!node) return;
    const name = state.config.cityName || `${state.config.lat.toFixed(2)}°، ${state.config.lng.toFixed(2)}°`;
    const q = PT.qibla ? PT.qibla(state.config.lat, state.config.lng) : null;
    const bearing = q && Number.isFinite(q.bearing) ? `${Math.round(q.bearing)}°` : '—';
    node.textContent = `${name} · القبلة ${bearing} من الشمال`;
  }

  root.SirajPrayerUI = {
    init, refresh: () => { renderHero(); renderTimes(); renderQibla(); syncBackground(false); },
    refreshQibla: () => {
      renderQibla();
      refreshQiblaPlace();
      if (!document.getElementById('qiblaSunPanel').hidden) renderSunGuide();
      if (!document.getElementById('qiblaGpsPanel').hidden) renderGpsGuide();
    },
    playAdhan, stopAdhan, next: () => nextPrayer(new Date()),
    config: () => ({ ...state.config }),
    backgroundStatus: () => ({ ...bgState }),
    sleepStatus: () => root.SirajIdleSleep.status(),
    sleepSimulate: () => simulateIdleSleep(),
    playBackgroundTest: (key) => { const cfg = state.config; const id = key === 'fajr' ? cfg.fajrAdhanId : cfg.adhanId; const item = adhanById(id) || {}; return bgCall('play', { prayer: key || 'fajr', label: PT.describe(key || 'fajr'), adhanId: id, url: item.url || '' }); },
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
