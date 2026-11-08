/*
 * Siraj Prayer UI v1 — «المواقيت»
 *
 * واجهة مستقلة لمواقيت الصلاة والأذان والإقامة والقبلة، تعمل فوق SirajPrayerTimes
 * و SirajPrayerData. تخزّن إعدادها في localStorage تحت مفتاح واحد، ولا ترسل شيئًا
 * إلى أي خادم. تُهيّأ من app.js عبر SirajPrayerUI.init().
 */
(function (root) {
  'use strict';

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
  };

  const els = {};
  const state = {
    config: null,
    today: null,
    next: null,
    ticking: null,
    audio: null,
    playingId: null,
    adhanCache: new Map(),
    downloaded: new Set(),
    iqamaTimers: [],
    lastFired: '',
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

  async function cachedAdhanUrl(item) {
    if (typeof caches === 'undefined') return null;
    try {
      const cache = await caches.open(ADHAN_CACHE);
      const hit = await cache.match(item.url);
      if (!hit) return null;
      const blob = await hit.blob();
      return URL.createObjectURL(blob);
    } catch {
      return null;
    }
  }

  async function isAdhanDownloaded(item) {
    if (item && item.local) return true;
    if (typeof caches === 'undefined') return false;
    try {
      const cache = await caches.open(ADHAN_CACHE);
      return !!(await cache.match(item.url));
    } catch {
      return false;
    }
  }

  async function downloadAdhan(item, onProgress) {
    const response = await fetch(item.url, { mode: 'cors' });
    if (!response.ok) throw new Error('http ' + response.status);
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
    await cache.put(item.url, new Response(blob, { headers: { 'Content-Type': 'audio/mpeg' } }));
    if (onProgress) onProgress(1);
    return blob.size;
  }

  async function removeAdhan(item) {
    try {
      const cache = await caches.open(ADHAN_CACHE);
      await cache.delete(item.url);
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
    // 1) ملف محزوم داخل التطبيق (يعمل بلا إنترنت من أول تشغيل)
    // 2) ملف منزّل على الجهاز 3) البث من الشبكة كحل أخير
    const bundled = item.local || '';
    const local = bundled || await cachedAdhanUrl(item);
    audio.src = local || item.url;
    audio.volume = Math.min(1, Math.max(0, num(state.config.adhanVolume, 1)));
    state.playingId = item.id;
    renderAdhanState();
    try {
      await audio.play();
      if (!options.silent) toast(`أذان ${item.name}`);
    } catch {
      toast('تعذّر تشغيل الأذان؛ تحقّق من الصوت أو نزّل الأذان للاستخدام دون إنترنت.');
    }
    audio.onended = () => {
      state.playingId = null;
      renderAdhanState();
    };
    return true;
  }

  function stopAdhan() {
    const audio = getAudio();
    try { audio.pause(); audio.currentTime = 0; } catch { /* لا شيء يعمل */ }
    state.playingId = null;
    renderAdhanState();
  }

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

  function fireFor(key, table) {
    const stamp = `${new Date().toDateString()}:${key}`;
    if (state.lastFired === stamp) return;
    state.lastFired = stamp;
    const config = state.config;
    // في نسخة أندرويد يتولى النظام تشغيل الأذان والإقامة، فلا نكرر الصوت داخل الواجهة.
    const handledBySystem = hasBackgroundBridge() && bgState.scheduled > 0;
    if (config.adhanEnabled && !handledBySystem) {
      const id = key === 'fajr' ? config.fajrAdhanId : config.adhanId;
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
      if (diff >= 0 && diff < 0.25) fireFor(key, table);
      if (config.preMinutes > 0) {
        const pre = diff + config.preMinutes;
        if (pre >= 0 && pre < 0.25) {
          const stamp = `${new Date().toDateString()}:pre:${key}`;
          if (state.lastFired !== stamp) {
            state.lastFired = stamp;
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
    if (els.chip) {
      const left = Math.max(0, Math.round(info.minutesLeft));
      els.chip.textContent = `${info.name} · ${left >= 60 ? Math.floor(left / 60) + ':' + String(left % 60).padStart(2, '0') : left + ' د'}`;
    }
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

  async function renderAdhanList() {
    if (!els.adhanList) return;
    const config = state.config;
    const rows = await Promise.all(DATA.adhans.map(async (item) => {
      const downloaded = await isAdhanDownloaded(item);
      const selected = config.adhanId === item.id;
      const selectedFajr = config.fajrAdhanId === item.id;
      return `
        <div class="pt-adhan${selected ? ' is-selected' : ''}" data-id="${item.id}">
          <div class="pt-adhan-main">
            <strong>${item.name}</strong>
            <span class="muted">${item.region ? esc(item.region) + ' · ' : ''}${Math.round(item.seconds / 60)} د${item.fajr ? ' · أذان فجر' : ''} · ${item.local ? 'محلي' : (downloaded ? 'منزّل' : 'يحتاج تنزيل')}</span>
          </div>
          <div class="pt-adhan-actions">
            <button class="pt-mini" data-act="preview" data-id="${item.id}" title="تجربة">▶</button>
            <button class="pt-mini" data-act="download" data-id="${item.id}" title="${downloaded ? 'محفوظ على الجهاز' : 'تنزيل للاستخدام دون إنترنت'}">${downloaded ? '✓' : '⤓'}</button>
            <button class="pt-mini${selected ? ' on' : ''}" data-act="use" data-id="${item.id}" title="أذان الصلوات">أ</button>
            <button class="pt-mini${selectedFajr ? ' on' : ''}" data-act="use-fajr" data-id="${item.id}" title="أذان الفجر">ف</button>
          </div>
        </div>
      `;
    }));
    els.adhanList.innerHTML = `<div class="pt-adhan-summary">
        <span class="muted">${DATA.adhans.filter((i) => i.local).length} أذانًا محليًا جاهزًا دون إنترنت · ${DATA.adhans.filter((i) => !i.local).length} يحتاج تنزيلًا</span>
        <button class="btn small ghost" id="ptAdhanDownloadAll">تنزيل المتبقي</button>
      </div>` + rows.join('');
    const allBtn = els.adhanList.querySelector('#ptAdhanDownloadAll');
    if (allBtn) allBtn.addEventListener('click', downloadAllAdhans);
    els.adhanList.querySelectorAll('[data-act]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const item = adhanById(btn.dataset.id);
        const act = btn.dataset.act;
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
    els.preSelect && els.preSelect.addEventListener('change', (e) => {
      state.config.preMinutes = Number(e.target.value); saveConfig();
    });
    els.volumeRange && els.volumeRange.addEventListener('input', (e) => {
      state.config.adhanVolume = Number(e.target.value) / 100; saveConfig();
      if (state.audio) state.audio.volume = state.config.adhanVolume;
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
    els.chip = el('ptChip');
    els.nextName = el('ptNextName');
    els.nextAt = el('ptNextAt');
    els.countdown = el('ptCountdown');
    if (els.chip) {
      els.chip.hidden = false;
      els.chip.addEventListener('click', () => {
        if (typeof state.onNavigate === 'function') state.onNavigate('prayer');
      });
    }
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
    playBackgroundTest: (key) => { const cfg = state.config; const id = key === 'fajr' ? cfg.fajrAdhanId : cfg.adhanId; const item = adhanById(id) || {}; return bgCall('play', { prayer: key || 'fajr', label: PT.describe(key || 'fajr'), adhanId: id, url: item.url || '' }); },
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
