/* القرآن الكريم - مصحف صفحة بصفحة (ترقيم مصحف المدينة - 604 صفحة)
 * المصادر: api.alquran.cloud (النص والتلاوات والتفسير)
 */
(() => {
  'use strict';

  const API = 'https://api.alquran.cloud/v1';
  const TOTAL_PAGES = 604;

  // بداية كل جزء (سورة، آية) - مُتحقق منها عبر الـ API
  const JUZ_START = [
    [1, 1], [2, 142], [2, 253], [3, 93], [4, 24], [4, 148], [5, 82], [6, 111], [7, 88], [8, 41],
    [9, 93], [11, 6], [12, 53], [15, 1], [17, 1], [18, 75], [21, 1], [23, 1], [25, 21], [27, 56],
    [29, 46], [33, 31], [36, 28], [39, 32], [41, 47], [46, 1], [51, 31], [58, 1], [67, 1], [78, 1],
  ];

  const RECITERS = [
    ['ar.alafasy', 'مشاري العفاسي'],
    ['ar.abdurrahmaansudais', 'عبدالرحمن السديس'],
    ['ar.mahermuaiqly', 'ماهر المعيقلي'],
    ['ar.husary', 'محمود خليل الحصري'],
    ['ar.husarymujawwad', 'الحصري (المجود)'],
    ['ar.hudhaify', 'علي الحذيفي'],
    ['ar.shaatree', 'أبو بكر الشاطري'],
    ['ar.abdulsamad', 'عبدالباسط عبدالصمد'],
    ['ar.saoodshuraym', 'سعود الشريم'],
    ['ar.muhammadayyoub', 'محمد أيوب'],
    ['ar.muhammadjibreel', 'محمد جبريل'],
    ['ar.abdullahbasfar', 'عبدالله بصفر'],
    ['ar.ahmedajamy', 'أحمد العجمي'],
    ['ar.hanirifai', 'هاني الرفاعي'],
    ['ar.ibrahimakhbar', 'إبراهيم الأخضر'],
    ['ar.aymanswoaid', 'أيمن سويد'],
    ['ar.parhizgar', 'شهريار پرهيزكار'],
  ];
  const BASIC_TAFSIRS = [
    ['ar.muyassar', 'التفسير الميسر (مجمع الملك فهد)'],
    ['ar.jalalayn', 'تفسير الجلالين'],
    ['ar.baghawi', 'تفسير البغوي'],
    ['ar.qurtubi', 'تفسير القرطبي'],
    ['ar.miqbas', 'تنوير المقباس'],
  ];
  let TAFSIRS = [...BASIC_TAFSIRS];
  let tafsirCatalog = null;
  let tafsirPack = { ready: false, downloading: false, bytes: 0, freeBytes: 0 };

  // قراء الروايات الثلاث من MP3Quran: ملف لكل سورة بلا توقيت للآيات، فتعمل السورة كاملة ثم تتوقف.
  const RIW_RECITERS = {
    warsh: [
      ['warsh_abdulbasit', 'عبدالباسط عبدالصمد', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/abdulbasit-abdulsamad/r2/' }],
      ['warsh_husary', 'محمود خليل الحصري', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/mahmoud-husary/r3/' }],
    ],
    qalun: [
      ['qalun_husary', 'محمود خليل الحصري', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/mahmoud-husary/r5/' }],
      ['qalun_hudhaify', 'علي الحذيفي', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/ali-hudhaifi/r2/' }],
    ],
    duri: [
      ['duri_husary', 'محمود خليل الحصري', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/mahmoud-husary/r4/' }],
    ],
    shubah: [
      ['shubah_deeban', 'أحمد ديبان', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/ahmad-deeban/r2/' }],
      ['shubah_saber', 'صابر عبدالحكم', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/saber-abdulhakam/r7/' }],
      ['shubah_hudhaify', 'علي الحذيفي', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/ali-hudhaifi/r3/' }],
    ],
    susi: [
      ['susi_sufi', 'عبدالرشيد صوفي', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/abdulrasheed-sufi/r2/' }],
    ],
    bazzi: [
      ['bazzi_deeban', 'أحمد ديبان', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/ahmad-deeban/r4/' }],
      ['bazzi_kameny', 'عكاشة كميني', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/okasha-kameny/r2/' }],
    ],
    qunbul: [
      ['qunbul_deeban', 'أحمد ديبان', { type: 'surah', base: 'https://cdn.mp3quran.net/audio/ahmad-deeban/r3/' }],
    ],
  };
  // قارئ الرواية الحالي (أو null إن لم يكن الاختيار متاحاً لهذه الرواية)
  const riwEntry = () => (RIW_RECITERS[settings.riwaya] || []).find(([id]) => id === settings.reciter) || null;
  const riwAudioOk = () => isRiw() && !!riwEntry();
  const riwSurahOnly = () => isRiw() && riwEntry()?.[2].type === 'surah';

  const DEFAULTS = {
    riwaya: 'quran-uthmani', reciter: 'ar.alafasy', tafsir: 'ar.muyassar',
    surahReciter: 0, surahMode: 'sync', surahAudio: true,
    translation: '', font: 'Scheherazade New', size: 26, tajweed: false, dark: false,
    tajweedScopes: {},
  };
  const VIEW_TITLES = { listen: 'استماع', reader: 'المصحف', tafsir: 'التفسير', memo: 'وضع الحفظ', wird: 'الورد', stats: 'الإحصائيات', adhkar: 'الأذكار', search: 'البحث', bookmarks: 'المحفوظات', settings: 'الإعدادات', about: 'عن التطبيق', tajweed: 'أحكام التجويد', meanings: 'المعاني', prayer: 'مواقيت الصلاة', qibla: 'القبلة والبوصلة' };
  const Cap = window.Capacitor || null;

  // قائمة القراء المتوفرة بتلاوة كاملة للسورة (ملف واحد لكل سورة) من mp3quran.
  let SURAH_RECITERS = [];

  // قواعد التجويد بحسب رموز مصدر quran-tajweed في alquran.cloud (الاسم، الشرح)
  const TJ_RULES = {
    h: ['همزة الوصل', 'تُنطق في أول الكلام فقط، وتسقط في الوصل.'],
    l: ['لام شمسية', 'لا تُنطق اللام، وتُدغم في الحرف الشمسي بعدها.'],
    s: ['حرف غير ملفوظ', 'حرف مكتوب ولا يُنطق في هذا الموضع.'],
    n: ['مد طبيعي', 'يُمد الصوت حركتين.'],
    p: ['مد جائز', 'يُمد الصوت حركتين أو أربعاً أو ست حركات.'],
    m: ['مد لازم', 'يُمد الصوت ست حركات ولا يجوز قصره.'],
    o: ['مد واجب متصل', 'يُمد الصوت أربع أو خمس حركات.'],
    q: ['قلقلة', 'نبرة ارتداد خفيفة عند سكون أحد حروف (قطب جد).'],
    c: ['إخفاء شفوي', 'إخفاء الميم الساكنة عند الباء، مع غنة.'],
    f: ['إخفاء', 'إخفاء النون الساكنة أو التنوين مع غنة.'],
    w: ['إدغام شفوي', 'إدغام الميم الساكنة في ميم بعدها، مع غنة.'],
    i: ['إقلاب', 'قلب النون الساكنة أو التنوين ميماً عند الباء، مع غنة.'],
    a: ['إدغام بغنة', 'إدغام النون الساكنة أو التنوين في (ي ن م و) مع غنة.'],
    u: ['إدغام بلا غنة', 'إدغام النون الساكنة أو التنوين في (ل ر) بلا غنة.'],
    d: ['إدغام متجانسين', 'حرفان من مخرج واحد، يُدغم الأول في الثاني.'],
    b: ['إدغام متقاربين', 'حرفان متقاربان في المخرج، يُدغم الأول في الثاني.'],
    g: ['غنة', 'صوت من الخيشوم يُمد حركتين.'],
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // أيقونات Fluent 3D متجهية خفيفة؛ تبقى واضحة في شريط الهاتف والتابلت.
  const FLUENT_ICONS = {
    book: '<path d="M2.5 4h7.2c1.2 0 2 .5 2.3 1.4v15c-.8-.8-1.7-1.2-2.8-1.2H2.5z" fill="url(#paper)" stroke="#765b31"/><path d="M21.5 4h-7.2c-1.2 0-2 .5-2.3 1.4v15c.8-.8 1.7-1.2 2.8-1.2h6.7z" fill="url(#blue)" stroke="#164675"/><path d="M12 5.4v15" stroke="#d3a93f"/><path d="M4.5 6.2h5" stroke="#fff" opacity=".7"/>',
    tafsir: '<path d="M3 5.2c3-1.2 6-.8 9 1.2 3-2 6-2.4 9-1.2v14c-3-1-6-.6-9 1.3-3-1.9-6-2.3-9-1.3z" fill="url(#paper)" stroke="#80693e"/><path d="M12 6.4v14" stroke="#b58a32"/><path d="M5 8h5M5 10.5h4M14 8h5M14 10.5h4" stroke="#477aa5" stroke-linecap="round"/><path d="M16 14l1 1.3 1.7-.2-.9 1.4.7 1.5-1.6-.4-1 1.3-.2-1.7-1.5-.6 1.5-.7z" fill="url(#gold)"/>',
    stats: '<rect x="2.5" y="12" width="5" height="9" rx="1.3" fill="url(#blue)"/><rect x="9.5" y="5" width="5" height="16" rx="1.3" fill="url(#green)"/><rect x="16.5" y="8.5" width="5" height="12.5" rx="1.3" fill="url(#gold)"/><path d="M3.8 9.5l4.2-3.2 3.6 1.2 5.5-4" fill="none" stroke="#ed5267" stroke-width="1.6"/><path d="M17 3.5l1.8-.6-.3 1.9" fill="none" stroke="#ed5267" stroke-width="1.3"/>',
    memo: '<path d="M4 2h12l4 4v16H4z" fill="url(#paper)" stroke="#79623d"/><path d="M16 2v4h4" fill="#e7cb8d"/><path d="M7 8h9M7 11h7M7 14h5" stroke="#7893aa"/><path d="M8 20l1-3 8-8 2 2-8 8z" fill="url(#green)"/><path d="M17 9l1-1c.5-.5 1.2-.5 1.7 0l.3.3c.5.5.5 1.2 0 1.7l-1 1z" fill="url(#gold)"/>',
    wird: '<rect x="2.5" y="4" width="19" height="17" rx="2.2" fill="url(#paper)" stroke="#745e3d"/><path d="M2.5 6.2A2.2 2.2 0 0 1 4.7 4h14.6a2.2 2.2 0 0 1 2.2 2.2V9h-19z" fill="url(#blue)"/><path d="M7 2v4M17 2v4" stroke="#d8ad4b" stroke-width="2"/><path d="M6.5 14.5l3.1 3 7.8-7.1" fill="none" stroke="#13946d" stroke-width="2.3" stroke-linecap="round"/>',
    bookmarks: '<path d="M3 4h16a2 2 0 0 1 2 2v13H5a2 2 0 0 1-2-2z" fill="url(#blue)" stroke="#164675"/><path d="M5 6h12a2 2 0 0 1 2 2v9H6c-.4 0-.7.1-1 .3z" fill="url(#paper)"/><path d="M13 3h4.5v10L15.2 11 13 13z" fill="url(#red)"/><path d="M7 8h5M7 10.5h4" stroke="#7b91a2"/>',
    listen: '<path d="M3.5 14.5V12a8.5 8.5 0 0 1 17 0v2.5" fill="none" stroke="#2f6f8f" stroke-width="2.2" stroke-linecap="round"/><rect x="2.5" y="13" width="5" height="8" rx="2" fill="url(#blue)" stroke="#164675"/><rect x="16.5" y="13" width="5" height="8" rx="2" fill="url(#blue)" stroke="#164675"/>',
    tajweed: '<path d="M12 2C6 2 2 6 2 11.2 2 17 7 21 13 21h1c1.8 0 3-1 3-2.5 0-1.6-1.2-2.5-2.8-2.5H13c-1 0-1.8-.8-1.8-1.7 0-1 .8-1.8 2-1.8H16c3.4 0 6-2.1 6-5C22 4.3 18 2 12 2z" fill="url(#violet)" stroke="#48236c"/><circle cx="6" cy="8" r="1.7" fill="#ff5863"/><circle cx="10" cy="5.5" r="1.7" fill="#ffbe3d"/><circle cx="14.5" cy="5.5" r="1.7" fill="#43ce7a"/><circle cx="18" cy="8.5" r="1.7" fill="#4ebeff"/>',
    words: '<path d="M2.5 3h11A2.5 2.5 0 0 1 16 5.5v5A2.5 2.5 0 0 1 13.5 13H8l-4 3 .8-3H2.5A2.5 2.5 0 0 1 0 10.5v-5A2.5 2.5 0 0 1 2.5 3z" fill="url(#blue)"/><path d="M11 12h8.5a2.5 2.5 0 0 1 2.5 2.5v3A2.5 2.5 0 0 1 19.5 20h-2l.6 2-3-2H11a2.5 2.5 0 0 1-2.5-2.5v-3A2.5 2.5 0 0 1 11 12z" fill="url(#green)"/><path d="M3 6h9M3 9h6M12 15h7M12 17.5h5" stroke="#fff" stroke-linecap="round"/>',
    adhkar: '<path d="M12 2c-5.5 0-9.5 4.3-9.5 9.5 0 4.7 3.3 8.4 7.6 9.3" fill="none" stroke="#d2a94b"/><g fill="url(#green)" stroke="#075044"><circle cx="12" cy="2" r="1.8"/><circle cx="6.8" cy="3.6" r="1.8"/><circle cx="3.3" cy="7.7" r="1.8"/><circle cx="3.2" cy="13" r="1.8"/><circle cx="6.3" cy="17.4" r="1.8"/><circle cx="11" cy="20" r="1.8"/></g><path d="M18.8 14.5l1.3 2.5-1.1 1.2 1.5 3.7-2.2.8-1.4-3.7-1.5-.2.4-2.7z" fill="url(#gold)"/>',
    about: '<circle cx="12" cy="12" r="9.5" fill="url(#blue)" stroke="#164675"/><circle cx="12" cy="12" r="7.1" fill="url(#paper)" stroke="#b08b43"/><circle cx="12" cy="8.5" r="2.2" fill="url(#gold)"/><path d="M7.8 17.2c.6-3 2.1-4.6 4.2-4.6s3.6 1.6 4.2 4.6" fill="url(#green)" stroke="#075044"/><path d="M6.2 5.6a8 8 0 0 1 8.8-1.7" fill="none" stroke="#fff" stroke-linecap="round" opacity=".7"/>',
    settings: '<path d="M9.8 2h4.4l.7 2.5 2.1 1.2 2.5-.7 2.2 3.8-1.8 1.9v2.6l1.8 1.9-2.2 3.8-2.5-.7-2.1 1.2-.7 2.5H9.8l-.7-2.5L7 18.3l-2.5.7-2.2-3.8 1.8-1.9v-2.6L2.3 8.8 4.5 5 7 5.7l2.1-1.2z" fill="url(#metal)" stroke="#506375"/><circle cx="12" cy="12" r="4.1" fill="url(#blue)"/><circle cx="12" cy="12" r="1.8" fill="#fff" opacity=".9"/>',
  };
  function fluentIcon(name) {
    const body = FLUENT_ICONS[name] || FLUENT_ICONS.book;
    return `<svg viewBox="0 0 24 24" role="img" focusable="false"><defs>
      <linearGradient id="blue" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#71d7ff"/><stop offset="1" stop-color="#2375d8"/></linearGradient>
      <linearGradient id="green" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#62e0ad"/><stop offset="1" stop-color="#08785c"/></linearGradient>
      <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffe68a"/><stop offset="1" stop-color="#c88316"/></linearGradient>
      <linearGradient id="paper" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fffdf2"/><stop offset="1" stop-color="#e8d4a6"/></linearGradient>
      <linearGradient id="violet" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#d69cff"/><stop offset="1" stop-color="#7042c2"/></linearGradient>
      <linearGradient id="red" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ff8190"/><stop offset="1" stop-color="#c42d45"/></linearGradient>
      <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#eef5fa"/><stop offset="1" stop-color="#879dad"/></linearGradient>
    </defs>${body}</svg>`;
  }
  function renderFluentIcons(root = document) {
    $$('.ic[data-icon]', root).forEach((node) => { node.innerHTML = fluentIcon(node.dataset.icon); });
  }

  // ---------- التخزين المحلي ----------
  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem('quran:' + key); return v === null ? fallback : JSON.parse(v); }
      catch { return fallback; }
    },
    set(key, value) { try { localStorage.setItem('quran:' + key, JSON.stringify(value)); } catch {} },
  };
  const settings = Object.assign({}, DEFAULTS, store.get('settings', {}));
  // 1.4.9+: خط Amiri Quran كان يفصل حركات الضبط عن حروفها في المتصفح، فننقل من بقي
  // على هذا الخط الافتراضي القديم إلى الخط الأوضح مرة واحدة، مع احترام أي اختيار لاحق.
  if (!settings.fontFix149) {
    if (settings.font === 'Amiri Quran') settings.font = 'Scheherazade New';
    settings.fontFix149 = true;
    store.set('settings', settings);
  }
  // الإعدادات المحفوظة من إصدارات أقدم قد تشير إلى خيارات حفص المحذوفة؛ نرجع لحفص عن عاصم
  const VALID_RIWAYAT = ['quran-uthmani', 'warsh', 'qalun', 'duri', 'shubah', 'susi', 'bazzi', 'qunbul'];
  if (!VALID_RIWAYAT.includes(settings.riwaya)) settings.riwaya = 'quran-uthmani';
  const savedTajweedScopes = settings.tajweedScopes && typeof settings.tajweedScopes === 'object'
    && !Array.isArray(settings.tajweedScopes) ? settings.tajweedScopes : {};
  settings.tajweedScopes = {};
  ['quran-uthmani', 'quran-simple', 'quran-uthmani-min', 'quran-tajweed', 'warsh', 'qalun', 'duri', 'shubah', 'susi', 'bazzi', 'qunbul']
    .forEach((settingId) => {
      const value = savedTajweedScopes[settingId];
      if (typeof value === 'string'
          && /^[a-z0-9][a-z0-9._-]*(\/[a-z0-9][a-z0-9._-]*){3}$/.test(value)) {
        settings.tajweedScopes[settingId] = value;
      }
    });
  const saveSettings = () => store.set('settings', settings);
  const allowedFonts = new Set(['Amiri Quran', 'Amiri', 'Noto Naskh Arabic', 'Scheherazade New']);
  if (!allowedFonts.has(settings.font)) settings.font = DEFAULTS.font;
  settings.size = Math.min(44, Math.max(18, Number(settings.size) || DEFAULTS.size));
  // 1.4.13: أُلغيت مفاتيح «الشاشة والصوت» من الإعدادات؛ السلوك صار افتراضيًا دائمًا،
  // فنحذف أي قيمة قديمة محفوظة حتى لا توقف التشغيل في الخلفية عند من فعّلها سابقًا.
  delete settings.keepAwake;
  delete settings.backgroundAudio;
  // ترحيل آمن للطبعات التي حُجبت لعدم اكتمال سجل الحقوق، مع إبقاء بقية بيانات المستخدم.
  if (!TAFSIRS.some(([id]) => id === settings.tafsir) && !/^qp:\d+$/.test(settings.tafsir)) settings.tafsir = DEFAULTS.tafsir;
  const allowedTranslations = new Set(['', 'en.sahih', 'fr.hamidullah', 'ur.jalandhry', 'tr.diyanet']);
  if (!allowedTranslations.has(settings.translation)) settings.translation = '';
  saveSettings();

  // ---------- السياق والعادات المحلية (اختياري وبلا شبكة) ----------
  const SmartContextAPI = window.SirajSmartContext || null;
  const SmartServicesAPI = window.SirajSmartServices || null;
  const TajweedLearningAPI = window.SirajTajweedLearning || null;
  const TajweedCurriculumLoaderAPI = window.SirajTajweedCurriculumLoader || null;
  const SMART_STATE_KEY = 'smart-context';
  const TAJWEED_LEARNING_KEY = 'tajweed-learning';
  const SMART_NATIVE_KEY = 'smart-native';
  let smartEngine = SmartContextAPI
    ? new SmartContextAPI.SmartContextEngine(store.get(SMART_STATE_KEY, null)) : null;
  let tajweedLearningEngine = TajweedLearningAPI
    ? new TajweedLearningAPI.TajweedLearningEngine(store.get(TAJWEED_LEARNING_KEY, null)) : null;
  const smartNativeSaved = store.get(SMART_NATIVE_KEY, null) || {};
  let smartNative = { enabled: !!smartNativeSaved.enabled, nextAt: Number(smartNativeSaved.nextAt) || 0 };
  let smartDeviceSignals = {};
  let smartNativeTimer = null;
  let smartPendingNativeAction = '';
  let smartAppReady = false;
  let smartSaveTimer = null;
  let smartSuggestionTimer = null;
  let smartCurrent = null;
  let smartSessionStartedAt = Date.now();
  let smartLastInteractionAt = Date.now();

  function persistSmartContext(immediate = false) {
    if (!smartEngine) return;
    clearTimeout(smartSaveTimer);
    const save = () => store.set(SMART_STATE_KEY, smartEngine.snapshot());
    if (immediate) save();
    else smartSaveTimer = setTimeout(save, 250);
  }

  function smartRecord(event, options = {}) {
    if (!smartEngine || !smartEngine.config.enabled) return null;
    const saved = smartEngine.record(event);
    if (!saved) return null;
    persistSmartContext(!!options.immediate);
    if (!options.silent) {
      queueSmartSuggestion(1400);
      queueSmartNativeSync(2200);
    }
    return saved;
  }

  // ---------- الحالة ----------
  let surahs = [];
  let localHafs = null;
  let localTajweed = [];
  let tajweedLearningCatalog = null;
  let tajweedScopeRegistry = null;
  let tajweedRuntimeCurricula = [];
  let tajweedCurriculumLoadErrors = [];
  let tajweedLearningCards = [];
  const emptyTajweedSession = () => ({
    queue: [], index: 0, revealed: false, answered: 0,
    ratings: { again: 0, hard: 0, good: 0, easy: 0 },
    quizCorrect: null, quizTotal: 0, quizCorrectCount: 0,
  });
  let tajweedSession = emptyTajweedSession();
  const hafsPages = { uthmani: new Map(), simple: new Map() };
  const hafsByRef = { uthmani: new Map(), simple: new Map() };
  const tajweedByRef = new Map();
  const pageByRef = new Map();
  const globalByRef = new Map();
  const cache = new Map();          // JSON محلل من الأصول المحلية أو طلبات الشبكة الاختيارية
  const textCache = new Map();      // النص الخام مطلوب للتحقق من بصمات حزم التجويد
  const pageCache = new Map();      // صفحات جاهزة (مُعالجة)
  const audio = new Audio();
  // سرعة التلاوة تُحفظ على الجهاز
  const PLAY_RATES = [0.75, 1, 1.25, 1.5, 2];
  let playRate = Number(store.get('playRate', 1));
  if (!PLAY_RATES.includes(playRate)) playRate = 1;
  audio.playbackRate = playRate;
  audio.preload = 'auto';

  const state = { page: 0, pg: null, sel: null, selSurah: 1, renderToken: 0 };
  const play = { active: false, label: '', cur: null, nextFn: null, prevFn: null, repeatCount: 1, repeatLeft: 1 };
  let memo = { ayahs: [], hidden: true, label: '' };
  let index = { mode: 'surah', surah: 1 };
  let suppressTrack = false;

  // ---------- أدوات ----------
  const toArabicDigits = (s) => String(s).replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[d]);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clean = (s) => String(s ?? '').replace(/\uFEFF/g, '');
  const surahName = (s) => surahs[s - 1]?.name || '';
  const surahNameShort = (s) => {
    const parts = (surahs[s - 1]?.name || '').trim().split(/\s+/);
    return parts.length > 1 && /^س/.test(parts[0]) ? parts.slice(1).join(' ') : parts.join(' ');
  };

  function juzOf(s, a) {
    let j = 1;
    for (let i = 0; i < JUZ_START.length; i++) {
      const [js, ja] = JUZ_START[i];
      if (s > js || (s === js && a >= ja)) j = i + 1; else break;
    }
    return j;
  }

  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove('show'), 1800);
  }

  const UPDATE_ASSET_DB = 'siraj-update-assets';
  const UPDATE_ASSET_STORE = 'assets';
  let updateAssetDbPromise = null;

  function safeLocalAssetName(url) {
    const value = String(url || '');
    if (/^[a-z][a-z0-9+.-]*:/i.test(value) || value.includes('?') || value.includes('#')) return '';
    const normalized = value.replace(/^\.\//, '');
    return (/^[a-z0-9][a-z0-9._-]*\.(?:html|js|json)$/i.test(normalized)
      || /^tajweed-curricula\/[a-z0-9][a-z0-9._-]*\.json$/.test(normalized))
      ? normalized : '';
  }

  function openUpdateAssetDb() {
    if (!window.indexedDB) return Promise.reject(new Error('IndexedDB unavailable'));
    if (updateAssetDbPromise) return updateAssetDbPromise;
    updateAssetDbPromise = new Promise((resolve, reject) => {
      const request = window.indexedDB.open(UPDATE_ASSET_DB, 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(UPDATE_ASSET_STORE)) {
          db.createObjectStore(UPDATE_ASSET_STORE, { keyPath: 'name' });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error('update asset database'));
      request.onblocked = () => reject(new Error('update asset database blocked'));
    });
    updateAssetDbPromise.catch(() => { updateAssetDbPromise = null; });
    return updateAssetDbPromise;
  }

  function waitForUpdateTransaction(transaction) {
    return new Promise((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error || new Error('update asset transaction'));
      transaction.onabort = () => reject(transaction.error || new Error('update asset transaction aborted'));
    });
  }

  async function readUpdateDataAsset(name, version) {
    const db = await openUpdateAssetDb();
    const transaction = db.transaction(UPDATE_ASSET_STORE, 'readonly');
    const request = transaction.objectStore(UPDATE_ASSET_STORE).get(name);
    const record = await new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error || new Error('update asset read'));
    });
    return record && record.version === version && typeof record.text === 'string'
      ? record.text : null;
  }

  async function replaceUpdateDataAssets(version, files) {
    const db = await openUpdateAssetDb();
    const transaction = db.transaction(UPDATE_ASSET_STORE, 'readwrite');
    const storeRef = transaction.objectStore(UPDATE_ASSET_STORE);
    storeRef.clear();
    Object.keys(files).forEach((name) => {
      storeRef.put({ name, version, text: files[name] });
    });
    await waitForUpdateTransaction(transaction);
  }

  async function clearUpdateDataAssets() {
    if (!window.indexedDB) return;
    try {
      const db = await openUpdateAssetDb();
      const transaction = db.transaction(UPDATE_ASSET_STORE, 'readwrite');
      transaction.objectStore(UPDATE_ASSET_STORE).clear();
      await waitForUpdateTransaction(transaction);
    } catch { /* الملفات القديمة غير فعالة بلا مؤشر التحديث المحلي */ }
  }

  function updateOverlayText(url) {
    const normalized = safeLocalAssetName(url);
    const files = window.SIRAJ_UPDATE_FILES;
    if (!normalized || !files || !Object.prototype.hasOwnProperty.call(files, normalized)) return null;
    return typeof files[normalized] === 'string' ? files[normalized] : null;
  }

  async function getTextAsset(url) {
    if (textCache.has(url)) return textCache.get(url);
    const normalized = safeLocalAssetName(url);
    const overlaid = updateOverlayText(url);
    if (overlaid !== null) {
      textCache.set(url, overlaid);
      return overlaid;
    }
    const dataFiles = Array.isArray(window.SIRAJ_UPDATE_DATA_FILES)
      ? window.SIRAJ_UPDATE_DATA_FILES : [];
    if (normalized && dataFiles.includes(normalized)) {
      const text = await readUpdateDataAsset(normalized, String(window.SIRAJ_UPDATE_VERSION || ''));
      if (!text || !text.trim()) throw new Error('missing update asset ' + normalized);
      textCache.set(url, text);
      return text;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const text = await res.text();
    if (!text.trim()) throw new Error('empty asset');
    textCache.set(url, text);
    return text;
  }

  async function getJSON(url) {
    if (cache.has(url)) return cache.get(url);
    const text = await getTextAsset(url);
    const json = JSON.parse(text);
    cache.set(url, json);
    return json;
  }

  const refKey = (s, a) => `${s}:${a}`;
  function indexHafsRows(kind, rows) {
    rows.forEach((row, i) => {
      const [s, a, page, text] = row;
      const item = { s, n: a, page, text: clean(text), g: i + 1, juz: juzOf(s, a) };
      if (!hafsPages[kind].has(page)) hafsPages[kind].set(page, []);
      hafsPages[kind].get(page).push(item);
      hafsByRef[kind].set(refKey(s, a), item);
      if (kind === 'uthmani') {
        pageByRef.set(refKey(s, a), page);
        globalByRef.set(refKey(s, a), i + 1);
      }
    });
  }

  async function loadBundledData() {
    // قائمة القراء الكاملة اختيارية: فشل تحميلها لا يمنع فتح المصحف.
    tryLoadSurahReciters();
    const [surahData, hafsData, tajweedData, catalog, learningCatalog, scopeRegistry] = await Promise.all([
      getJSON('surahs.json'), getJSON('quran-hafs.json'),
      getJSON('quran-tajweed.json'), getJSON('tafsir-catalog.json'),
      getJSON('tajweed-learning-catalog.json'),
      getJSON('tajweed-scope-registry.json'),
    ]);
    surahs = Array.isArray(surahData) ? surahData : [];
    localHafs = hafsData;
    localTajweed = Array.isArray(tajweedData) ? tajweedData : [];
    tajweedLearningCatalog = learningCatalog;
    tajweedScopeRegistry = scopeRegistry;
    tajweedRuntimeCurricula = [];
    tajweedCurriculumLoadErrors = [];
    if (TajweedCurriculumLoaderAPI && learningCatalog && scopeRegistry) {
      try {
        const catalogSha256 = await TajweedCurriculumLoaderAPI.sha256Text(
          await getTextAsset('tajweed-learning-catalog.json')
        );
        const baseErrors = [];
        const baseCurricula = Array.isArray(learningCatalog.curricula)
          ? learningCatalog.curricula.map((item) => {
            const display = TajweedCurriculumLoaderAPI.normalizeDisplay(item.display);
            const matchingLabels = new Set((scopeRegistry.settings || [])
              .filter((entry) => entry?.riwayah?.id === item?.scope?.riwayah)
              .map((entry) => entry.riwayah.labelAr));
            if (!display || matchingLabels.size !== 1 || !matchingLabels.has(display.riwayahAr)) {
              baseErrors.push({ artifact: 'tajweed-learning-catalog.json', code: 'DISPLAY_INVALID' });
              return null;
            }
            return Object.assign({}, item, { display,
              artifact: 'tajweed-learning-catalog.json', artifactSha256: catalogSha256,
            });
          }).filter(Boolean) : [];
        const independent = await TajweedCurriculumLoaderAPI.loadRegistryCurricula({
          registry: scopeRegistry,
          getText: getTextAsset,
        });
        tajweedRuntimeCurricula = [...baseCurricula, ...independent.curricula];
        tajweedCurriculumLoadErrors = [...baseErrors, ...independent.errors];
      } catch {
        tajweedRuntimeCurricula = [];
        tajweedCurriculumLoadErrors = [{ artifact: '', code: 'RUNTIME_GATE_FAILED' }];
      }
    }
    indexHafsRows('uthmani', localHafs.uthmani || []);
    indexHafsRows('simple', localHafs.simple || []);
    localTajweed.forEach((row) => tajweedByRef.set(refKey(row[0], row[1]), clean(row[3])));
    buildTajweedLearningCards();
    tafsirCatalog = catalog;
    // كل كتب الكتالوج تظهر في القائمة: الخمسة الأساسية تعمل عبر الشبكة،
    // والبقية تُقرأ من حزمة التفاسير المحلية بعد تنزيلها (٧٨ طبعة).
    const classical = (catalog.books || []).map((book) => [
      book.edition,
      `${book.name} — ${book.author} (ت ${toArabicDigits(book.author_death_hijri)}هـ)`,
    ]);
    TAFSIRS = [...BASIC_TAFSIRS, ...classical];
    if (!TAFSIRS.some(([id]) => id === settings.tafsir)) settings.tafsir = DEFAULTS.tafsir;
    saveSettings();
  }

  function ayahAudioUrl(reciter, s, a) {
    const bitrate = OFFLINE_SRC[reciter] || 128;
    const global = globalByRef.get(refKey(s, a));
    return global ? `https://cdn.islamic.network/quran/audio/${bitrate}/${reciter}/${global}.mp3` : null;
  }

  function renderTajweed(raw) {
    let s = esc(clean(raw));
    s = s.replace(/\[([a-z]+)(?::\d+)?\[([^\[\]]*)\]/g, '<span class="tj-$1">$2</span>');
    return s.replace(/\[|\]/g, '');
  }

  function renderIndependentTajweed(curriculum, surah, ayah, text) {
    if (!TajweedCurriculumLoaderAPI || !curriculum) return esc(text);
    const segments = TajweedCurriculumLoaderAPI.annotatedSegments(
      curriculum, surah, ayah, clean(text)
    );
    return segments.map((segment) => {
      if (!segment.rules.length) return esc(segment.text);
      const ids = segment.rules.map((rule) => rule.id).join(',');
      const names = segment.rules.map((rule) => rule.name).join('، ');
      const colors = [...new Set(segment.rules.map((rule) => rule.color)
        .filter((color) => /^#[0-9A-Fa-f]{6}$/.test(color)))];
      if (!colors.length) return esc(segment.text);
      let style = `color:${colors[0]};text-decoration:underline dotted ${colors[0]};text-underline-offset:.16em`;
      if (colors.length > 1) {
        const step = 100 / colors.length;
        const stops = colors.flatMap((color, index) => [
          `${color} ${(index * step).toFixed(2)}%`,
          `${color} ${((index + 1) * step).toFixed(2)}%`,
        ]).join(',');
        style += `;background-image:linear-gradient(90deg,${stops});background-repeat:no-repeat;background-size:100% 2px;background-position:0 100%`;
      }
      return `<span class="tj-independent-mark" data-tj-rules="${esc(ids)}" title="${esc(names)}" style="${style}">${esc(segment.text)}</span>`;
    }).join('');
  }

  const HAFS_BASMALAS = [
    'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
    'بِسۡمِ ٱللَّهِ ٱلرَّحۡمَٰنِ ٱلرَّحِيمِ',
    'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
  ];
  // البسملة المعروضة تُؤخذ من نص المصحف نفسه حتى تبقى مطابقة لرسمه (بما فيه علامات الضبط)
  const bismText = () => (hafsByRef.uthmani.get(refKey(1, 1)) || {}).text || HAFS_BASMALAS[0];
  const plainTajweed = (raw) => clean(raw).replace(/\[([a-z]+)(?::\d+)?\[([^\[\]]*)\]/g, '$2').replace(/\[|\]/g, '');
  function displayHafsSource(surah, ayah, raw) {
    // فصل بصري فقط: لا نغيّر استجابة المصدر ولا ترقيم الآية أو رابط التلاوة.
    const source = clean(raw).trim();
    if (ayah !== 1 || surah === 1 || surah === 9) return source;
    const plain = plainTajweed(source);
    if (!HAFS_BASMALAS.some((prefix) => plain.startsWith(prefix))) return source;
    const words = source.split(/\s+/);
    return words.slice(4).join(' ').trim();
  }
  function syncReaderLayout() {
    const hafs = !isRiw();
    const readerActive = curView === 'reader';
    document.body.classList.toggle('hafs-reader', hafs);
    document.body.classList.toggle('reader-view-active', readerActive);
    $('.wrap')?.classList.toggle('reader-wide', readerActive && hafs);
    refreshWakeLock();
    if (readerActive) wakeHintOnce();
  }

  // ---------- التنقل بين الأقسام ----------
  // سجل الأقسام: زر الرجوع يعيد خطوة واحدة للخلف داخل التطبيق
  const navStack = [];
  let curView = 'reader';
  function showView(name, opts = {}) {
    const previousView = curView;
    if (name !== curView && !opts.back) { navStack.push(curView); if (navStack.length > 30) navStack.shift(); }
    curView = name;
    $$('#tabs button').forEach((b) => b.classList.toggle('active', b.dataset.view === name));
    $$('.nav-end button[data-view]').forEach((b) => {
      const active = b.dataset.view === name || (name === 'about' && b.dataset.view === 'settings');
      b.classList.toggle('active', active);
    });
    $$('.tab-group').forEach((g) => g.querySelector('.group-btn').classList.toggle('active', !!g.querySelector(`[data-view="${name}"]`)));
    $('#tabs button.active')?.scrollIntoView({ inline: 'nearest', block: 'nearest' });
    $$('section.view').forEach((s) => s.classList.toggle('active', s.id === 'view-' + name));
    placePlayer(name);
    if (name === 'reader') updateChrome(); else $('#topTitle').textContent = VIEW_TITLES[name] || '';
    // زر الرجوع يظهر في كل الأقسام ما عدا المصحف
    $('#backBtn').hidden = name === 'reader';
    if (name === 'bookmarks') renderBookmarks();
    if (name === 'tafsir') renderTafsirView();
    if (name === 'wird') renderWird();
    if (name === 'stats') renderStats();
    // عدّاد دقائق القراءة يعمل داخل القارئ فقط
    if (name === 'reader') { readerActiveSince = Date.now(); } else { readerActiveSince = 0; }
    if (name === 'adhkar') renderAdhkarHome();
    if (name === 'tajweed') renderTajweedView();
    if (name === 'settings') syncIndexSelects();
    if (name === 'meanings') renderMeaningsView();
    if (name === 'memo') renderMemoReview();
    if (name === 'prayer' && window.SirajPrayerUI) window.SirajPrayerUI.refresh();
    if (name === 'qibla' && window.SirajPrayerUI) window.SirajPrayerUI.refreshQibla();
    syncReaderLayout();
    if (name === 'reader') requestAnimationFrame(syncReaderDockHeight);
    if (name !== previousView) {
      if (name === 'memo') smartRecord({ type: 'SERVICE_OPEN', service: 'memorization' });
      else if (name === 'tajweed') smartRecord({ type: 'OPEN_TAJWEED', service: 'tajweed' });
      else if (name === 'tafsir') smartRecord({ type: 'OPEN_TAFSIR', service: 'tafsir' });
    }
    if (name === 'settings' || name === 'about') hideSmartSuggestion();
    else queueSmartSuggestion(1800);
    $('#content').scrollTop = 0;
  }

  // مؤقّت دقائق القراءة
  setInterval(trackReadingMinutes, 30000);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) readerActiveSince = 0;
    else if (curView === 'reader') readerActiveSince = Date.now();
  });
  // أزرار الهدف اليومي والمشاركة
  $$('#wdGoalChoices button').forEach((btn) => {
    btn.addEventListener('click', () => {
      setWirdGoal(Number(btn.dataset.goal) || 0);
      toast(Number(btn.dataset.goal) > 0 ? `هدفك اليومي: ${toArabicDigits(btn.dataset.goal)} صفحة` : 'بلا هدف يومي ملزم');
    });
  });
  const shareBtn = $('#wdShare');
  shareBtn && shareBtn.addEventListener('click', shareWirdProgress);

  function popView() { showView(navStack.pop() || 'reader', { back: true }); }
  $('#backBtn').addEventListener('click', () => handleBack());
  $('#settingsBtn').addEventListener('click', () => showView('settings'));
  // روابط داخل الإعدادات تفتح تبويبي «مواقيت الصلاة» و«القبلة والبوصلة»
  document.addEventListener('click', (e) => {
    const link = e.target.closest('.settings-link[data-view]');
    if (!link) return;
    closeGroups();
    showView(link.dataset.view);
  });
  $('#settingsAboutBtn').addEventListener('click', () => showView('about'));
  function closeSide() { document.body.classList.remove('side-open'); }

  // القوائم المنسدلة للشريط: النافذة التي اختارها المستخدم تبقى دائمًا في الطبقة الأمامية.
  let activeGroup = null;
  function syncGroupMenuLayer() {
    const open = $$('.group-menu').some((menu) => !menu.hidden);
    document.body.classList.toggle('group-menu-open', open);
    if (!open) activeGroup = null;
  }
  function setGroupOpen(group, open, opts = {}) {
    const menu = group.querySelector('.group-menu');
    menu.hidden = !open;
    group.classList.toggle('is-open', open);
    group.querySelector('.group-btn').setAttribute('aria-expanded', String(open));
    if (open) {
      activeGroup = group;
      if (opts.focusFirst) requestAnimationFrame(() => menu.querySelector('button')?.focus({ preventScroll: true }));
    } else if (activeGroup === group) {
      activeGroup = null;
    }
    syncGroupMenuLayer();
  }
  function closeGroups(opts = {}) {
    const previous = activeGroup;
    $$('.tab-group').forEach((g) => setGroupOpen(g, false));
    if (opts.restoreFocus) previous?.querySelector('.group-btn')?.focus({ preventScroll: true });
  }
  $('#tabs').addEventListener('click', (e) => {
    const gb = e.target.closest('.group-btn');
    if (gb) {
      const g = gb.closest('.tab-group');
      const open = g.querySelector('.group-menu').hidden;
      closeGroups();
      if (open) setGroupOpen(g, true, { focusFirst: true });
      return;
    }
    // نوع من الأذكار: يفتح الأذكار مباشرة بدون صفحة اختيار وسيطة
    const cat = e.target.closest('[data-cat]');
    if (cat) { closeGroups(); showView('adhkar'); openAdhkarCat(cat.dataset.cat); closeSide(); return; }
    const b = e.target.closest('button[data-view]');
    if (!b) return;
    closeGroups();
    showView(b.dataset.view);
    closeSide();
  });
  document.addEventListener('click', (e) => { if (!e.target.closest('.tab-group')) closeGroups(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeGroups({ restoreFocus: true }); });
  $('#backdrop').addEventListener('click', closeSide);

  function applyTheme() {
    document.body.classList.toggle('dark', !!settings.dark);
    if ($('#setDark')) $('#setDark').checked = !!settings.dark;
  }
  $('#setDark').addEventListener('change', (e) => { settings.dark = e.target.checked; saveSettings(); applyTheme(); });

  // ---------- الفهرس: سورة / جزء / آية ----------
  async function loadSurahs() {
    if (!surahs.length) {
      try { surahs = (await getJSON(API + '/surah')).data; }
      catch { toast('تعذر تحميل فهرس السور المحلي.'); return; }
    }
    $('#memoSurah').innerHTML = surahs.map((s) => `<option value="${s.number}">${s.number}. ${esc(s.name)}</option>`).join('');
    renderIndex();
    syncPlayControls();
    setupDownloadUI();
  }

  // الفهرس: ثلاث قوائم منسدلة (السورة، الجزء، الآية) تنتقل للموضع المختار
  function fillAyahNums(surahNo) {
    const count = surahs[surahNo - 1]?.numberOfAyahs || 0;
    $('#idxAyahNum').innerHTML = Array.from({ length: count }, (_, i) => `<option value="${i + 1}">${toArabicDigits(i + 1)}</option>`).join('');
  }
  function syncIndexSelects() {
    if (!surahs.length) return;
    const cur = state.sel || { s: 1, n: 1, juz: 1 };
    $('#idxSurah').value = String(cur.s);
    $('#idxJuz').value = String(cur.juz || 1);
    fillAyahNums(cur.s);
    $('#idxAyahNum').value = String(cur.n);
  }
  function renderIndex() {
    if (!surahs.length) return;
    const sOpts = surahs.map((x) => `<option value="${x.number}">${x.number}. ${esc(x.name)}</option>`).join('');
    $('#idxSurah').innerHTML = sOpts;
    $('#idxJuz').innerHTML = JUZ_START.map((_, i) => `<option value="${i + 1}">الجزء ${toArabicDigits(i + 1)}</option>`).join('');
    syncIndexSelects();
  }
  $('#idxSurah').addEventListener('change', (e) => { fillAyahNums(Number(e.target.value)); goToAyah(Number(e.target.value), 1); closeSide(); });
  $('#idxJuz').addEventListener('change', (e) => {
    const [s, a] = JUZ_START[Number(e.target.value) - 1];
    goToAyah(s, a); closeSide();
  });
  $('#idxAyahNum').addEventListener('change', (e) => {
    goToAyah(Number($('#idxSurah').value), Number(e.target.value)); closeSide();
  });

  // ---------- تحميل الصفحات ----------
  // الصفحة = آيات من إصدارات متعددة (نص + تلاوة + تفسير + ترجمة اختيارية)
  // الروايات السبع (ورش، قالون، الدوري، شعبة، السوسي، البزي، قنبل): نص كل آية مع صفحتها من quran-riwayat.json
  const RIW_IDS = ['warsh', 'qalun', 'duri', 'shubah', 'susi', 'bazzi', 'qunbul'];
  const isRiw = () => RIW_IDS.includes(settings.riwaya);
  let riwAll = null;
  let riwPages = {};
  async function loadRiwaya(id) {
    if (!riwAll) {
      riwAll = (await getJSON('quran-riwayat.json')).riwayat || {};
    }
    if (!riwPages[id]) {
      const byPage = {};
      (riwAll[id] || []).forEach((row, idx) => {
        const [s, a, pg, text] = row;
        (byPage[pg] = byPage[pg] || []).push({ s, n: a, g: 1000000 + idx, page: pg, text: clean(text) });
      });
      riwPages[id] = byPage;
    }
    return riwPages[id];
  }

  async function loadPage(p) {
    if (p < 1 || p > TOTAL_PAGES) return null;
    const key = p + '|' + [settings.riwaya, settings.reciter, settings.tafsir, settings.translation, settings.tajweed, tafsirPack.ready].join('|');
    if (pageCache.has(key)) return pageCache.get(key);
    if (isRiw()) {
      const byPage = await loadRiwaya(settings.riwaya);
      const re = riwEntry();
      const urlOf = (x) => {
        if (!re) return null;
        if (re[2].only && !re[2].only.includes(x.s)) return null; // سور غير مسجلة لهذا القارئ
        if (re[2].type === 'surah') return re[2].base + String(x.s).padStart(3, '0') + '.mp3';
        return re[2].base + String(x.s).padStart(3, '0') + String(x.n).padStart(3, '0') + '.mp3';
      };
      const approvedCurriculum = settings.tajweed ? currentApprovedTajweedCurriculum() : null;
      const obj = { p, ayahs: (byPage[p] || []).map((x) => ({
        ...x,
        juz: juzOf(x.s, x.n),
        html: approvedCurriculum
          ? renderIndependentTajweed(approvedCurriculum, x.s, x.n, x.text)
          : esc(x.text),
        audio: urlOf(x),
        tafsir: '',
        tr: '',
      })) };
      pageCache.set(key, obj);
      return obj;
    }

    const kind = settings.riwaya === 'quran-simple' ? 'simple' : 'uthmani';
    const base = hafsPages[kind].get(p) || [];
    if (!base.length) throw new Error('bundled Hafs page is missing');

    let translated = [];
    if (settings.translation) {
      try { translated = (await getJSON(`${API}/page/${p}/${settings.translation}`)).data.ayahs || []; }
      catch { translated = []; }
    }

    let tafsirTexts = new Array(base.length).fill('');
    let localHandled = false;
    const plugin = getTafsirNative();
    if (tafsirPack.ready && plugin) {
      try {
        const result = await plugin.lookupBatch({
          edition: settings.tafsir,
          ayahs: base.map((a) => ({ surah: a.s, ayah: a.n })),
        });
        if (result && result.handled && Array.isArray(result.texts)) {
          localHandled = true;
          tafsirTexts = result.texts.map((text) => text || '');
        }
      } catch { localHandled = false; }
    }
    if (!localHandled && ONLINE_TAFSIRS.has(settings.tafsir)) {
      try {
        const rows = (await getJSON(`${API}/page/${p}/${settings.tafsir}`)).data.ayahs || [];
        tafsirTexts = rows.map((row) => row.text || '');
      } catch { tafsirTexts = new Array(base.length).fill(''); }
    }
    if (!localHandled && !ONLINE_TAFSIRS.has(settings.tafsir) && isClassicalTafsir(settings.tafsir)) {
      const edition = settings.tafsir;
      const bookId = tafsirBookId(edition);
      if (await bookIsStored(bookId)) {
        tafsirTexts = await Promise.all(base.map((a) => storedBookText(bookId, a.s, a.n)));
      } else {
        // الكتاب لا يُمنع أبدًا: يُجهَّز الآن ويظهر النص بعد لحظات.
        loadTafsirBook(bookId);
      }
    }

    const showTajweed = settings.riwaya === 'quran-tajweed' || settings.tajweed;
    const ayahs = base.map((a, i) => {
      const displaySource = displayHafsSource(a.s, a.n, a.text);
      const tajweedSource = showTajweed ? tajweedByRef.get(refKey(a.s, a.n)) : null;
      const markup = tajweedSource ? displayHafsSource(a.s, a.n, tajweedSource) : null;
      return {
        s: a.s,
        n: a.n,
        g: a.g,
        page: p,
        juz: a.juz,
        text: plainTajweed(displaySource),
        html: markup ? renderTajweed(markup) : esc(plainTajweed(displaySource)),
        audio: ayahAudioUrl(settings.reciter, a.s, a.n),
        tafsir: tafsirTexts[i] || '',
        tr: settings.translation ? (translated[i]?.text || '') : '',
      };
    });
    const obj = { p, ayahs, linesHtml: null };
    if (kind === 'uthmani') {
      const madani = await loadMadaniLines();
      obj.linesHtml = madani ? madaniLinesHtml(p, madani, showTajweed) : null;
    }
    pageCache.set(key, obj);
    return obj;
  }

  // ---------- تخطيط المصحف بأسطر ثابتة (رواية حفص فقط) ----------
  let madaniPromise = null;
  function loadMadaniLines() {
    if (!madaniPromise) madaniPromise = getJSON('quran-madani-lines.json').catch(() => { madaniPromise = null; return null; });
    return madaniPromise;
  }

  function tajweedWordsOf(item) {
    const src = tajweedByRef.get(refKey(item.s, item.n));
    if (!src) return null;
    const words = displayHafsSource(item.s, item.n, src).split(/\s+/).filter(Boolean);
    const plainCount = item.text.split(/\s+/).filter(Boolean).length;
    return words.length === plainCount ? words : null;
  }

  // كلمات السطر من بداية الآية (s:n:t) إلى نهايتها (s1:n1:t1)، والعلامة ۝ بعد آخر كلمة
  function madaniLineParts(fromRef, toRef, showTajweed) {
    let [s, n, t] = fromRef.split(':').map(Number);
    const [s1, n1, t1] = toRef.split(':').map(Number);
    const out = [];
    for (let guard = 0; guard < 400; guard++) {
      const item = hafsByRef.uthmani.get(refKey(s, n));
      if (!item) break;
      const words = item.text.split(/\s+/).filter(Boolean);
      const N = words.length;
      const tj = showTajweed ? tajweedWordsOf(item) : null;
      const last = (s === s1 && n === n1) ? t1 : N + 1;
      const pieces = [];
      for (let k = t; k <= last; k++) {
        if (k <= N) {
          const raw = words[k - 1];
          if (!tj && raw.startsWith('\u06de')) {
            pieces.push(`<span class="rub">\u06de</span>${esc(raw.slice(1))}`);
          } else {
            pieces.push(tj ? renderTajweed(tj[k - 1]) : esc(raw));
          }
        }
        else pieces.push(`<span class="end hafs-end" data-act="tafsir" data-g="${item.g}" title="الآية">۝${toArabicDigits(n)}</span>`);
      }
      if (pieces.length) out.push(`<span class="ay" data-g="${item.g}">${pieces.join(' ')}</span>`);
      if (s === s1 && n === n1) break;
      n += 1; t = 1;
      if (!hafsByRef.uthmani.get(refKey(s, n))) { s += 1; n = 1; }
    }
    return out.join(' ');
  }

  function madaniLinesHtml(p, data, showTajweed) {
    const lines = data.pages && data.pages[p - 1];
    if (!lines) return null;
    const surahOfNext = (i) => {
      for (let j = i; j < lines.length; j++) if (lines[j].k === 'text') return Number(lines[j].a.split(':')[0]);
      return 0;
    };
    const out = [];
    lines.forEach((ln, i) => {
      if (ln.k === 'sura') { out.push(`<div class="surah-banner">${esc(surahName(surahOfNext(i + 1)))}</div>`); return; }
      if (ln.k === 'bism') { out.push(`<div class="bism">${esc(bismText())}</div>`); return; }
      const parts = madaniLineParts(ln.a, ln.b, showTajweed);
      const style = ln.w ? ` style="width:${(ln.w * 100).toFixed(2)}%"` : '';
      out.push(`<div class="mline${ln.w ? ' short' : ''}"${style}>${parts}</div>`);
    });
    return out.join('');
  }

  // معامل تكبير خط مصحف حفص: الصفحة مضبوطة على عرض الشاشة، فحجم السطر محسوم هندسيًا؛
  // ولذلك يضرب المنطق حجم كل سطر في معامل التكبير المختار، فيكبر الخط فعليًا ويلتف
  // السطر الطويل إلى سطرين بدل أن يُعاد إلى حجمه الأول.
  const HAFS_BASE_SIZE = 26;
  const hafsZoom = () => {
    const size = Number(settings.size) || HAFS_BASE_SIZE;
    return Math.min(1.8, Math.max(1, size / HAFS_BASE_SIZE));
  };
  // قياس المصحف الموحّد: مقاس خط واحد لكل أسطر الصفحة (كما في مصحف المدينة/الشاملة).
  // نقيس أطول سطر عند مقاس مرجعي، ثم نستنتج المقاس الذي يملأ عرض الصفحة تمامًا،
  // ثم نضرب في معامل اختيار المستخدم — فيكبر الخط كله معًا بلا «جمل صغيرة وجمل كبيرة».
  const HAFS_REF_SIZE = 100;
  function userFontScale() {
    const size = Number(settings.size) || HAFS_BASE_SIZE;
    return Math.min(2.4, Math.max(0.72, size / HAFS_BASE_SIZE));
  }

  // عرض أطول سطر عند مقاس خط معيّن (بلا أي التفاف)، ثم بحث ثنائي على المقاس
  // الذي يملأ عرض الصفحة تمامًا. كل الأسطر تأخذ المقاس النهائي نفسه.
  function fitMadaniLines() {
    const body = $('#pageBody');
    if (!body) return;
    requestAnimationFrame(() => {
      if (!body.classList.contains('madani-lines')) return;
      const lines = [...body.querySelectorAll('.mline')];
      if (!lines.length) return;
      body.classList.remove('zoomed');
      const avail = Math.max(180, (body.clientWidth || 320) - 6);
      const widthAt = (size) => {
        body.style.setProperty('--quran-size', `${size}px`);
        body.classList.add('measuring');
        let max = 0;
        lines.forEach((el) => {
          const w = el.getBoundingClientRect().width;
          if (w > max) max = w;
        });
        body.classList.remove('measuring');
        return max;
      };
      let lo = 8;
      let hi = 80;
      for (let i = 0; i < 14; i += 1) {
        const mid = (lo + hi) / 2;
        if (widthAt(mid) > avail) hi = mid; else lo = mid;
      }
      const fitSize = lo;
      const scale = userFontScale();
      const size = Math.max(9, Math.min(90, fitSize * scale));
      body.style.setProperty('--quran-size', `${size.toFixed(2)}px`);
      // التكبير لا يمدّ الصفحة عرضيًا أبدًا: عند تجاوز مقاس الملاءمة نسمح للسطر
      // بالالتفاف بمقاس خط واحد لكل الصفحة، فتمتد الصفحة طوليًا فقط
      // وتبقى الكلمات داخل هوامش الورقة.
      const wrapping = scale > 1.001;
      body.classList.toggle('wrapping', wrapping);
      body.style.setProperty('--mushaf-w', wrapping ? '100%' : `${Math.ceil(widthAt(size))}px`);
      const pageBox = body.closest('.page') || body.parentElement;
      const navBar = document.querySelector('.navbar');
      const navTop = navBar ? navBar.getBoundingClientRect().top : (window.innerHeight || 640);
      const pageTop = pageBox ? pageBox.getBoundingClientRect().top : 0;
      const visibleH = Math.max(160, navTop - pageTop);
      const lineCount = Math.max(1, wrapping ? lines.length * scale : lines.length);
      const lh = wrapping ? 1.85 : Math.min(2.3, Math.max(1.5, visibleH / (lineCount * size)));
      body.style.setProperty('--mline-h', `${(size * lh).toFixed(2)}px`);
      if (typeof applyTajweedScale === 'function') applyTajweedScale();
    });
  }

  // ربط شريط حجم الخط في المصحف (يُستخدم نفس مفتاح الإعدادات size).
  function syncFontControl() {
    if ($('#setSize')) $('#setSize').value = String(Math.round(Number(settings.size) || HAFS_BASE_SIZE));
    if ($('#sizeVal')) $('#sizeVal').textContent = `${Math.round(Number(settings.size) || HAFS_BASE_SIZE)}px`;
  }
  function setFontSize(value, opts = {}) {
    const next = Math.min(44, Math.max(18, Math.round(Number(value) || HAFS_BASE_SIZE)));
    settings.size = next;
    document.documentElement.style.setProperty('--quran-size', `${next}px`);
    saveSettings();
    syncFontControl();
    fitMadaniLines();
  }

  if (document.fonts && document.fonts.ready) {
    // الخط يُحمّل بعد أول رسم؛ نعيد القياس بعده ليكون مقاس المصحف مضبوطًا من أول مرة.
    document.fonts.ready.then(() => fitMadaniLines());
    if (document.fonts.addEventListener) document.fonts.addEventListener('loadingdone', () => fitMadaniLines());
  }
  window.addEventListener('resize', () => fitMadaniLines());

  // رقم الصفحة لأي آية (من بيانات السورة)
  async function pageOfAyah(s, a) {
    const local = pageByRef.get(refKey(s, a));
    if (local) return local;
    const json = await getJSON(`${API}/surah/${s}/quran-uthmani`);
    return json.data.ayahs[a - 1].page;
  }

  async function findAyah(s, a) {
    const p = await pageOfAyah(s, a);
    const pg = await loadPage(p);
    return pg.ayahs.find((x) => x.s === s && x.n === a) || null;
  }
  // البحث عن آية في رواية ورش بترقيمها ومن صفحاتها (لا من API حفص)
  async function findRiwAyah(s, a) {
    await loadRiwaya('warsh');
    const row = (riwAll.warsh || []).find((r) => r[0] === s && r[1] === a);
    if (!row) return null;
    const pg = await loadPage(row[2]);
    return pg.ayahs.find((x) => x.s === s && x.n === a) || null;
  }

  // ---------- عرض الصفحة ----------
  async function showPage(p, opts = {}) {
    p = Math.min(TOTAL_PAGES, Math.max(1, p));
    const token = ++state.renderToken;
    let pg;
    try {
      pg = await loadPage(p);
    } catch {
      $('#pageBody').innerHTML = '<div class="muted" style="text-align:center;padding:30px">تعذر تحميل الصفحة. تحقق من الاتصال بالإنترنت.</div>';
      return;
    }
    if (token !== state.renderToken) return;

    state.page = p;
    state.pg = pg;
    let sel = null;
    if (opts.selG) sel = pg.ayahs.find((a) => a.g === opts.selG) || null;
    if (!sel) sel = pg.ayahs[0];
    state.sel = sel;
    state.selSurah = sel.s;

    renderPage(opts.dir);
    updateChrome();
    prefetchAround(p);
    if (opts.scroll === true || opts.dir) {
      requestAnimationFrame(() => {
        const content = $('#content');
        const header = $('.hdr');
        const stageTop = $('#stage').getBoundingClientRect().top;
        const headerBottom = header ? header.getBoundingClientRect().bottom : 0;
        const target = Math.max(0, content.scrollTop + stageTop - headerBottom - 8);
        content.scrollTo({ top: target, behavior: opts.dir ? 'smooth' : 'auto' });
      });
    }
    recordRead(p);
    recordWirdPage(p);
    recordSmartReadPage(p, sel);
    if (opts.save !== false) saveLast();
  }

  function renderPage(dir) {
    const pg = state.pg;
    if (pg.linesHtml) {
      $('#pageBody').classList.add('madani-lines');
      $('#pageBody').innerHTML = pg.linesHtml;
      fitMadaniLines();
    } else {
      $('#pageBody').classList.remove('madani-lines');
      renderFlowPage(pg);
    }
    const page = $('#page');
    page.classList.remove('flip-next', 'flip-prev');
    void page.offsetWidth;
    if (dir === 'next') page.classList.add('flip-next');
    if (dir === 'prev') page.classList.add('flip-prev');

    markSelection();
  }

  function renderFlowPage(pg) {
    let html = '';
    let openP = false;
    let lastS = 0;
    pg.ayahs.forEach((a) => {
      if (a.s !== lastS) {
        if (openP) { html += '</p>'; openP = false; }
        if (a.n === 1) {
          html += `<div class="surah-banner">${esc(surahName(a.s))}</div>`;
          if (a.s !== 1 && a.s !== 9) html += `<div class="bism">${esc(bismText())}</div>`;
        }
        html += '<p class="flow">';
        openP = true;
        lastS = a.s;
      }
      const marker = isRiw() ? toArabicDigits(a.n) : `۝${toArabicDigits(a.n)}`;
      const markerClass = isRiw() ? 'end' : 'end hafs-end';
      html += `<span class="ay" data-g="${a.g}">${a.html} <span class="${markerClass}" data-act="tafsir" data-g="${a.g}" title="الآية">${marker}</span></span> `;
    });
    if (openP) html += '</p>';
    $('#pageBody').innerHTML = html;
  }

  function markSelection() {
    $$('#pageBody .ay.sel').forEach((el) => el.classList.remove('sel'));
    $$('#pageBody .ay.playing').forEach((el) => el.classList.remove('playing'));
    if (state.sel) {
      $$(`#pageBody .ay[data-g="${state.sel.g}"]`).forEach((el) => el.classList.add('sel'));
    }
    if (play.cur) {
      $$(`#pageBody .ay[data-g="${play.cur.g}"]`).forEach((el) => el.classList.add('playing'));
    }
  }

  function updateChrome() {
    if (!state.pg || !state.sel) return;
    const pg = state.pg;
    const surahsOnPage = [...new Set(pg.ayahs.map((a) => a.s))];
    const juz = pg.ayahs[0].juz;
    $('#pgJuz').textContent = `الجزء ${toArabicDigits(juz)}`;
    $('#pgSurah').textContent = surahsOnPage.map((s) => surahNameShort(s)).join(' - ');
    $('#pgFoot').textContent = toArabicDigits(pg.p);
    $('#pageNo').textContent = toArabicDigits(pg.p);
    $('#pageNo').title = `صفحة ${toArabicDigits(pg.p)} من ${toArabicDigits(TOTAL_PAGES)}`;
    $('#pagerContext').textContent = `${surahNameShort(state.sel.s)} · الجزء ${toArabicDigits(state.sel.juz || juz)}`;
    $('#pPrevS').disabled = pg.p <= 1;
    $('#pNextS').disabled = pg.p >= TOTAL_PAGES;
    $('#topTitle').textContent = `${surahName(state.sel.s)} · الجزء ${toArabicDigits(state.sel.juz || juz)} · ص ${toArabicDigits(pg.p)}`;

    // قائمة اختيار الآية تتبع السورة المحددة
    syncPlayControls();
    const bm = isBookmarked(state.sel.s, state.sel.n);
    $('#btnBm').innerHTML = `${bm ? '★' : '☆'} <span>${bm ? 'محفوظة' : 'حفظ علامة'}</span>`;
    updateResumeBtn();
    renderIndex();
  }

  // أدوات التشغيل: السورة، الآية، الشيخ
  function syncPlayControls() {
    if (!surahs.length) return;
    const s = state.selSurah;
    const surahSel = $('#playSurah');
    if (!surahSel.options.length) {
      surahSel.innerHTML = surahs.map((x) => `<option value="${x.number}">${x.number}. ${esc(x.name)}</option>`).join('');
    }
    surahSel.value = String(s);
    const ayahSel = $('#playFrom');
    if (ayahSel.dataset.s !== String(s)) {
      const count = surahs[s - 1]?.numberOfAyahs || 0;
      let opts = '';
      for (let a = 1; a <= count; a++) opts += `<option value="${a}">${toArabicDigits(a)}</option>`;
      ayahSel.innerHTML = opts;
      ayahSel.dataset.s = String(s);
    }
    ayahSel.value = String(state.sel && state.sel.s === s ? state.sel.n : 1);
    $('#playReciter').value = settings.reciter;
  }

  function saveLast(light) {
    const s = state.sel;
    store.set('last', { p: state.page, s: s.s, a: s.n, g: s.g });
    if (light) return;
    renderLast();
    updateResumeBtn();
  }
  const getLast = () => store.get('last', null);

  function updateResumeBtn() {
    const last = getLast();
    const btn = $('#btnResume');
    if (!last || !last.p) { btn.style.display = 'none'; return; }
    btn.style.display = last.p === state.page ? 'none' : 'block';
    btn.innerHTML = `↩ <span>آخر موضع · ص ${toArabicDigits(last.p)}</span>`;
  }

  // ---------- التقليب ----------
  function nextPage() {
    if (state.page < TOTAL_PAGES) return turnTo(state.page + 1, true);
    return null;
  }
  function prevPage() {
    if (state.page > 1) return turnTo(state.page - 1, false);
    return null;
  }
  // تحميل الصفحتين المجاورتين مسبقًا ليصبح التقليب فوريًا
  function prefetchAround(p) {
    [p - 1, p + 1].forEach((q) => { if (q >= 1 && q <= TOTAL_PAGES) loadPage(q).catch(() => {}); });
  }

  $('#pNextS').addEventListener('click', nextPage);
  $('#pPrevS').addEventListener('click', prevPage);

  // التقليب بالأسهم: → السابقة، ← التالية (نفس اتجاه السحب)
  document.addEventListener('keydown', (e) => {
    if (!$('#view-reader').classList.contains('active')) return;
    if (e.target.matches('input, select, textarea')) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); prevPage(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); nextPage(); }
  });

  // ---------- تقليب الصفحة بالسحب ----------
  // سحب قصير ومباشر: الصفحة تتبع الإصبع مسافة محدودة ثم تستقر، وتُقلب صفحة واحدة فقط
  // عند تجاوز مسافة بسيطة أو عند سحب سريع، بلا حركة طويلة توحي بقلب عدة صفحات.
  // يمين ← الصفحة التالية، يسار ← السابقة.
  let drag = null;
  const stage = $('#stage');
  const pageEl = $('#page');
  const hasSelection = () => !!(window.getSelection && window.getSelection().toString().trim());
  const SWIPE_EASE = 'cubic-bezier(.2,.8,.25,1)';
  // الصفحة تتبع الإصبع واحدًا لواحد كما لو كانت ورقة حقيقية، فلا إحساس صناعي.
  const FLIP_RATIO = 0.15;    // نسبة عرض الصفحة الكافية للتقليب عند الإفلات
  const FLIP_DISTANCE = 16;   // أو مسافة صغيرة مع سرعة كافية
  const FLIP_VELOCITY = 0.11; // سحب سريع (بكسل/مللي ثانية)
  // الورقة تتبع الإصبع مع ميل بسيط حول الكعب لتعطي إحساس كتاب حقيقي بسرعة استجابة عالية.
  function setPageTransform() {
    pageEl.style.transition = 'none';
    pageEl.style.transform = '';
  }
  function clampDrag(dx) {
    const atEdge = (dx > 0 && state.page >= TOTAL_PAGES) || (dx < 0 && state.page <= 1);
    if (atEdge) return dx * 0.22;
    const limit = Math.max(120, stage.clientWidth * 0.75);
    return Math.max(-limit, Math.min(limit, dx));
  }
  // ---------- تقليب ثلاثي الأبعاد كما في الكتاب ----------
  // عند تغيير الصفحة نُبقي صورة الصفحة القديمة (أو الجديدة عند الرجوع) فوق الصفحة
  // الحقيقية ونديرها حول كعب الورقة بمنظور ثلاثي الأبعاد مع ظل متحرك.
  let turning = false;
  // انتقال فوري بين الصفحات: تبديل في نفس الإطار بلا حركة ولا طبقات
  async function turnTo(target, goNext) {
    if (turning || target < 1 || target > TOTAL_PAGES) return;
    turning = true;
    document.body.classList.add('page-turning');
    try {
      pageEl.style.transition = 'none';
      pageEl.style.transform = '';
      await showPage(target, { scroll: true });
    } finally {
      document.body.classList.remove('page-turning');
      turning = false;
    }
  }

  async function flipBySwipe(goNext) {
    pageEl.style.transition = 'none';
    pageEl.style.transform = '';
    const target = goNext ? state.page + 1 : state.page - 1;
    if (target < 1 || target > TOTAL_PAGES) return;
    await turnTo(target, goNext);
  }
  stage.addEventListener('pointerdown', (e) => {
    // الفأرة للتحديد الحر للنص؛ التقليب بالسحب خاص باللمس (والقلم)
    if (e.pointerType === 'mouse' || e.button > 0 || e.target.closest('button, select, input')) return;
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), dragging: false,
      hadSel: hasSelection(), lastX: e.clientX, lastT: performance.now(), v: 0 };
  });
  stage.addEventListener('pointermove', (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.dragging) {
      if (Math.abs(dx) < 8 || Math.abs(dx) < Math.abs(dy) * 1.15) return;
      // ضغط مطوّل لتحديد النص لا يُعد سحبًا
      if (hasSelection() && !drag.hadSel) { drag = null; return; }
      drag.dragging = true;
      window.getSelection()?.removeAllRanges();
      pageEl.classList.add('is-dragging');
    }
    const now = performance.now();
    drag.v = (e.clientX - drag.lastX) / Math.max(1, now - drag.lastT);
    drag.lastX = e.clientX; drag.lastT = now;
    setPageTransform(clampDrag(dx), false);
  });
  function endDrag(e) {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    const d = drag; drag = null;
    pageEl.classList.remove('is-dragging');
    if (!d.dragging) return;
    const dx = e.clientX - d.x;
    const goNext = dx > 0;
    const canMove = goNext ? state.page < TOTAL_PAGES : state.page > 1;
    const quick = Math.abs(d.v) >= FLIP_VELOCITY && Math.abs(dx) >= FLIP_DISTANCE;
    const far = Math.abs(dx) >= Math.min(stage.clientWidth * FLIP_RATIO, 140);
    if (!canMove || !(quick || far)) { setPageTransform(0, true); return; }
    flipBySwipe(goNext);
  }
  stage.addEventListener('pointerup', endDrag);
  stage.addEventListener('pointercancel', () => {
    if (!drag) return;
    drag = null;
    pageEl.classList.remove('is-dragging');
    setPageTransform(0, true);
  });

  // ---------- قائمة التحديد: نسخ · مشاركة · حكم التجويد · تفسير · معاني ----------
  const selMenu = $('#selMenu');
  let selCtx = null;
  let selTimer = 0;
  const hideSelMenu = () => { selMenu.hidden = true; selCtx = null; };
  // التحديد الحر بالكلمة: أي لمسة على حرف تحدد الكلمة كاملة، ويُرسم تظليل مدوّر بلون الجهاز
  const hlLayer = document.createElement('div');
  hlLayer.id = 'hlLayer';
  hlLayer.setAttribute('aria-hidden', 'true');
  pageEl.appendChild(hlLayer);
  function textIndexOf(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let text = '';
    let n;
    while ((n = walker.nextNode())) { nodes.push({ node: n, start: text.length }); text += n.nodeValue; }
    return { nodes, text };
  }
  function locateOffset(nodes, g, isEnd) {
    for (const { node, start } of nodes) {
      const len = node.nodeValue.length;
      if (isEnd ? (g > start && g <= start + len) : (g >= start && g < start + len)) return { node, offset: g - start };
    }
    const last = nodes[nodes.length - 1];
    return last ? { node: last.node, offset: last.node.nodeValue.length } : null;
  }
  function expandToWords(range) {
    const root = $('#pageBody');
    const { nodes, text } = textIndexOf(root);
    const pre = (container, offset) => { const r = document.createRange(); r.setStart(root, 0); r.setEnd(container, offset); return r.toString().length; };
    let s0 = pre(range.startContainer, range.startOffset);
    let e0 = pre(range.endContainer, range.endOffset);
    while (s0 > 0 && !/\s/.test(text[s0 - 1])) s0--;
    while (e0 < text.length && !/\s/.test(text[e0])) e0++;
    if (e0 <= s0) return null;
    const a0 = locateOffset(nodes, s0, false), b0 = locateOffset(nodes, e0, true);
    if (!a0 || !b0) return null;
    const r = document.createRange();
    r.setStart(a0.node, a0.offset);
    r.setEnd(b0.node, b0.offset);
    return r;
  }
  // تظليل حر: شريط واحد لكل سطر يغطي من أول الكلام المحدد لآخره في نفس السطر
  function drawHighlight(range) {
    const pr = pageEl.getBoundingClientRect();
    const rects = [...range.getClientRects()].filter((r) => r.width > 1 && r.height > 1)
      .sort((x, y) => x.top - y.top || x.left - y.left);
    const lines = [];
    rects.forEach((r) => {
      const mid = r.top + r.height / 2;
      const line = lines.find((l) => mid > l.top && mid < l.bottom);
      if (line) {
        line.left = Math.min(line.left, r.left); line.right = Math.max(line.right, r.right);
        line.top = Math.min(line.top, r.top); line.bottom = Math.max(line.bottom, r.bottom);
      } else {
        lines.push({ left: r.left, right: r.right, top: r.top, bottom: r.bottom });
      }
    });
    hlLayer.innerHTML = lines.map((l) => {
      const h = l.bottom - l.top;
      return `<i style="left:${l.left - pr.left - 2}px;top:${l.top - pr.top + h * 0.1}px;width:${l.right - l.left + 4}px;height:${h * 0.8}px"></i>`;
    }).join('');
  }
  function updateSelMenu() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount || !state.pg || !$('#pageBody').contains(sel.getRangeAt(0).commonAncestorContainer)) {
      hlLayer.innerHTML = ''; hideSelMenu(); return;
    }
    const range = sel.getRangeAt(0);
    const text = range.toString().trim();
    if (!text) { hlLayer.innerHTML = ''; hideSelMenu(); return; }
    drawHighlight(range);
    // أثناء السحب يتبع التظليل الإصبع فقط، والقائمة تظهر بعد رفع الإصبع
    if (selDragging) { selMenu.hidden = true; return; }
    selCtx = { text, range: range.cloneRange() };
    selMenu.hidden = false;
    const rect = range.getBoundingClientRect();
    const mw = selMenu.offsetWidth, mh = selMenu.offsetHeight;
    let left = rect.left + rect.width / 2 - mw / 2;
    left = Math.max(8, Math.min(window.innerWidth - mw - 8, left));
    // لا تغطية للرأس ولا لشريط التنقل: القائمة تبقى داخل مساحة الصفحة المرئية.
    const hdr = document.querySelector('.hdr');
    const navBar = document.querySelector('.navbar');
    const topBound = (hdr ? hdr.getBoundingClientRect().bottom : 8) + 8;
    const bottomBound = (navBar ? navBar.getBoundingClientRect().top : window.innerHeight) - 8;
    let top = rect.top - mh - 10;
    if (top < topBound) top = rect.bottom + 10;
    if (top + mh > bottomBound) top = Math.max(topBound, bottomBound - mh);
    selMenu.style.left = `${left}px`;
    selMenu.style.top = `${top}px`;
  }
  let selRaf = 0;
  let selDragging = false;
  document.addEventListener('selectionchange', () => {
    if (selRaf) return;
    selRaf = requestAnimationFrame(() => { selRaf = 0; updateSelMenu(); });
  });
  $('#pageBody').addEventListener('pointerdown', () => { selDragging = true; hideSelMenu(); });
  document.addEventListener('pointerup', () => {
    if (!selDragging) return;
    selDragging = false;
    requestAnimationFrame(updateSelMenu);
  });
  document.addEventListener('pointercancel', () => { selDragging = false; });
  window.addEventListener('scroll', hideSelMenu, { capture: true, passive: true });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hideSelMenu(); });

  function ayahOfRange(range) {
    const node = range.startContainer;
    const el = node.nodeType === 1 ? node : node.parentElement;
    const g = el?.closest('.ay')?.dataset.g;
    return (g && state.pg && state.pg.ayahs.find((x) => String(x.g) === g)) || state.sel;
  }
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); toast('تم النسخ'); }
    catch { toast('تعذر النسخ'); }
  }
  selMenu.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-act]');
    if (!btn || !selCtx) return;
    const { text, range } = selCtx;
    const act = btn.dataset.act;
    hideSelMenu();
    if (act === 'copy') return copyText(text);
    if (act === 'share') {
      if (navigator.share) return navigator.share({ text }).catch(() => {});
      return copyText(text);
    }
    const ayah = ayahOfRange(range);
    if (act === 'tajweed' && false) {
      const ids = new Set();
      $('#pageBody').querySelectorAll('[data-tj-rules]').forEach((el) => {
        if (range.intersectsNode(el)) el.dataset.tjRules.split(',').filter(Boolean).forEach((id) => ids.add(id));
      });
      if (ids.size) showIndependentTajweedPanel([...ids]);
      else {
        const codes = [...$('#pageBody').querySelectorAll('[class^="tj-"]')]
          .filter((el) => !el.dataset.tjRules && range.intersectsNode(el))
          .map((el) => (el.className.match(/tj-([a-z])/) || [])[1]).filter(Boolean);
        if (codes.length) showTajweedPanel(codes[0]);
        else toast('لا يوجد حكم تجويد في هذا التحديد');
      }
      return;
    }
    if (ayah) selectAyah(ayah);
    if (act === 'tafsir' && ayah) showTafsirPanel(ayah);
    if (act === 'meanings') showMeaningsPanel();
  });

  // ---------- اختيار الآية ----------
  $('#pageBody').addEventListener('click', (e) => {
    if (window.getSelection && window.getSelection().toString().trim()) return; // تحديد نص للنسخ
    const end = e.target.closest('.end');
    const ay = e.target.closest('.ay');
    if (!end && !ay) return;
    const g = Number((end || ay).dataset.g);
    const a = state.pg && state.pg.ayahs.find((x) => x.g === g);
    if (!a) return;
    selectAyah(a);
    // في التلاوة المتزامنة: لمس الآية ينقل التشغيل إليها فورًا
    if (play.active && syncReadingEnabled()) {
      playAyah(a);
      return;
    }
    // التفسير والترجمة يظهران من زر "التفسير" فقط. الكلمة الملونة تعرض قاعدة التجويد
    const independent = !end && e.target.closest('[data-tj-rules]');
    if (independent) {
      showIndependentTajweedPanel(independent.dataset.tjRules.split(',').filter(Boolean));
      return;
    }
    const tj = !end && e.target.closest('[class^="tj-"]');
    if (tj) showTajweedPanel((tj.className.match(/tj-([a-z])/) || [])[1]);
  });

  $('#playSurah').addEventListener('change', (e) => {
    const s = Number(e.target.value);
    state.selSurah = s;
    goToAyah(s, 1);
  });
  $('#playFrom').addEventListener('change', (e) => {
    goToAyah(Number($('#playSurah').value), Number(e.target.value));
  });
  if ($('#playSurahReciter')) $('#playSurahReciter').addEventListener('change', (e) => {
    settings.surahReciter = Number(e.target.value) || settings.surahReciter;
    saveSettings();
    toast('تغيّر قارئ السورة الكاملة.');
  });
  $('#playReciter').addEventListener('change', (e) => {
    onSettingChange('reciter', e.target.value);
  });

  $('#btnResume').addEventListener('click', () => {
    const last = getLast();
    if (last && last.p) showPage(last.p, { selG: last.g, save: false, scroll: true });
  });

  $('#btnBm').addEventListener('click', () => {
    if (!state.sel) return;
    toggleBookmark(state.sel.s, state.sel.n, surahNameShort(state.sel.s));
    updateChrome();
  });
  $('#btnTafsir').addEventListener('click', () => { if (state.sel) showTafsirPanel(state.sel); });

  // ---------- الانتقال إلى آية أو سورة أو جزء ----------
  async function goToAyah(s, a) {
    try {
      const ayah = await findAyah(s, a);
      if (!ayah) return;
      showView('reader');
      showPage(ayah.page, { selG: ayah.g, scroll: true });
    } catch {
      toast('تعذر الوصول إلى الآية. تحقق من الاتصال.');
    }
  }

  // ---------- التفسير ----------
  function missingTafsirText() {
    return 'لا يوجد نص خاص بهذه الآية في هذا الكتاب.';
  }
  const ONLINE_TAFSIRS = new Set(BASIC_TAFSIRS.map(([id]) => id));
  const tafsirAyahCache = new Map();

  // جلب تفسير آية واحدة من الشبكة عند الطلب — يعمل لأي وقت ولأي آية،
  // وهو ما كان يظهر سابقًا، ويعمل الآن لكل الآيات مباشرة.
  async function fetchOnlineTafsir(surah, ayah, edition) {
    const key = `${edition}:${surah}:${ayah}`;
    if (tafsirAyahCache.has(key)) return tafsirAyahCache.get(key);
    const data = await getJSON(`${API}/ayah/${surah}:${ayah}/${edition}`);
    const text = (data && data.data && data.data.text) || '';
    if (text) tafsirAyahCache.set(key, text);
    return text;
  }

  // ---------- كتب التفسير الإضافية من الموسوعة القرآنية ----------
  // كل كتاب يُطلب مرة واحدة عند اختياره (ملف مضغوط من الموسوعة القرآنية)،
  // ثم تُستخرج آياته وتُخزَّن على الجهاز، فتُقرأ بعدها فورًا وبلا إنترنت.
  const QP_BOOK_BASE = 'https://quranpedia.net/dumps/tafsir-book-';
  const tafsirBookState = new Map(); // bookId -> { state, percent }
  let tafsirIdbPromise = null;

  function tafsirIdb() {
    if (tafsirIdbPromise) return tafsirIdbPromise;
    tafsirIdbPromise = new Promise((resolve, reject) => {
      if (typeof indexedDB === 'undefined') { reject(new Error('no-idb')); return; }
      const req = indexedDB.open('siraj-tafsir-books', 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains('texts')) db.createObjectStore('texts');
        if (!db.objectStoreNames.contains('meta')) db.createObjectStore('meta');
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('idb-open'));
    });
    return tafsirIdbPromise;
  }

  async function idbRead(store, key) {
    const db = await tafsirIdb();
    return new Promise((resolve, reject) => {
      const req = db.transaction(store, 'readonly').objectStore(store).get(key);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function idbWrite(store, pairs) {
    if (!pairs.length) return;
    const db = await tafsirIdb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, 'readwrite');
      const bucket = tx.objectStore(store);
      pairs.forEach(([key, value]) => bucket.put(value, key));
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error('idb-abort'));
    });
  }

  function tafsirTextKey(bookId, s) { return `${bookId}:${s}`; }

  async function gzipText(text) {
    const stream = new CompressionStream('gzip');
    const writer = stream.writable.getWriter();
    writer.write(new TextEncoder().encode(text));
    writer.close();
    return new Uint8Array(await new Response(stream.readable).arrayBuffer());
  }

  async function gunzipText(bytes) {
    const stream = new DecompressionStream('gzip');
    const writer = stream.writable.getWriter();
    writer.write(bytes);
    writer.close();
    return new TextDecoder().decode(await new Response(stream.readable).arrayBuffer());
  }

  // سور الكتاب تُحفظ مضغوطة على الجهاز، وتُفكّ عند الحاجة فقط.
  const tafsirSurahCache = new Map(); // "book:surah" -> { ayah: text }
  async function storedSurah(bookId, surah) {
    const key = tafsirTextKey(bookId, surah);
    if (tafsirSurahCache.has(key)) return tafsirSurahCache.get(key);
    let map = null;
    try {
      const raw = await idbRead('texts', key);
      if (raw) map = JSON.parse(typeof raw === 'string' ? raw : await gunzipText(raw));
    } catch { map = null; }
    if (map) {
      if (tafsirSurahCache.size > 24) tafsirSurahCache.clear();
      tafsirSurahCache.set(key, map);
    }
    return map;
  }

  function bookHtmlToPlainText(html) {
    return String(html || '')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/(p|div|li|h[1-6])>/gi, '\n')
      .replace(/<[^>]*>/g, '')
      .replace(/&nbsp;/g, ' ')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&')
      .replace(/[ \t]+/g, ' ')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  function bookRowText(row) {
    const parts = Array.isArray(row && row.content) ? row.content : [];
    return parts
      .map((part) => (part && part.text ? bookHtmlToPlainText(part.text) : ''))
      .filter(Boolean)
      .join('\n\n');
  }

  // نهاية كائن JSON متوازن داخل نص متدفق، مع تجاهل الأقواس داخل النصوص.
  function jsonObjectEnd(text, start) {
    let depth = 0, inString = false, escaped = false;
    for (let i = start; i < text.length; i++) {
      const ch = text[i];
      if (inString) {
        if (escaped) escaped = false;
        else if (ch === '\\') escaped = true;
        else if (ch === '"') inString = false;
        continue;
      }
      if (ch === '"') inString = true;
      else if (ch === '{') depth++;
      else if (ch === '}') { depth--; if (!depth) return i; }
    }
    return -1;
  }

  function bookState(bookId) {
    return tafsirBookState.get(bookId) || { state: 'idle', percent: 0 };
  }

  function tafsirBookLoadingNote(bookId) {
    const st = bookState(bookId);
    if (st.state === 'error') {
      return /quota/i.test(st.message || '')
        ? 'المساحة على جهازك لا تكفي لهذا الكتاب؛ أفرغ مساحة ثم أعد اختياره.'
        : 'تعذّر تجهيز هذا الكتاب الآن؛ تحقّق من الاتصال ثم أعد اختياره.';
    }
    if (st.state === 'loading' && st.percent > 0) return `جاري تجهيز الكتاب… ${toArabicDigits(st.percent)}٪`;
    return 'جاري تجهيز الكتاب…';
  }

  function isClassicalTafsir(edition) { return /^qp:\d+$/.test(edition || ''); }
  function tafsirBookId(edition) { return Number(String(edition).slice(3)); }

  let tafsirBookTicker = null;
  function stopTafsirBookTicker() {
    if (tafsirBookTicker) clearInterval(tafsirBookTicker);
    tafsirBookTicker = null;
  }
  function refreshLoadingNotes() {
    const edition = settings.tafsir;
    if (!isClassicalTafsir(edition)) { stopTafsirBookTicker(); return; }
    const note = tafsirBookLoadingNote(tafsirBookId(edition));
    const body = $('#tafsirBody');
    const view = $('#tfTafsir');
    if (body && body.textContent && body.textContent.indexOf('جاري تجهيز') === 0) body.textContent = note;
    if (view && view.textContent && view.textContent.indexOf('جاري تجهيز') === 0) view.textContent = note;
  }
  function startTafsirBookTicker() {
    if (tafsirBookTicker) return;
    tafsirBookTicker = setInterval(refreshLoadingNotes, 600);
  }

  async function storedBookText(bookId, s, n) {
    const map = await storedSurah(bookId, s);
    return (map && map[n]) || '';
  }

  async function bookIsStored(bookId) {
    try {
      const meta = await idbRead('meta', bookId);
      return !!(meta && meta.ready);
    } catch { return false; }
  }

  // تجهيز كتاب كامل مرة واحدة: تنزيل مضغوط + استخراج الآيات + تخزينها على الجهاز.
  async function loadTafsirBook(bookId) {
    if (bookState(bookId).state === 'loading') return false;
    if (await bookIsStored(bookId)) {
      tafsirBookState.set(bookId, { state: 'ready', percent: 100 });
      return true;
    }
    tafsirBookState.set(bookId, { state: 'loading', percent: 0 });
    startTafsirBookTicker();
    let received = 0;
    let total = 0;
    let hugeBook = false;
    try {
      if (typeof DecompressionStream !== 'function' || typeof CompressionStream !== 'function') throw new Error('no-gunzip');
      const res = await fetch(`${QP_BOOK_BASE}${bookId}.json.gz`);
      if (!res.ok || !res.body) throw new Error(`http ${res.status}`);
      total = Number(res.headers.get('content-length')) || 0;
      hugeBook = total > 30 * 1024 * 1024;
      // مساحة حرة قبل البدء: النص بعد فكّ الضغط يقارب ضعف الملف المضغوط.
      try {
        if (navigator.storage && navigator.storage.persist) await navigator.storage.persist();
      } catch { /* تجاهل */ }
      const counter = new TransformStream({
        transform(chunk, controller) {
          received += chunk.byteLength;
          if (total) {
            const percent = Math.min(99, Math.round((received / total) * 100));
            if (percent !== bookState(bookId).percent) tafsirBookState.set(bookId, { state: 'loading', percent });
          }
          controller.enqueue(chunk);
        },
      });
      const reader = res.body.pipeThrough(counter).pipeThrough(new DecompressionStream('gzip')).getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let inAyahs = false;
      let rows = 0;
      let surah = 0;
      let bucket = {};
      const flush = async () => {
        if (!surah || !Object.keys(bucket).length) { bucket = {}; return; }
        const key = tafsirTextKey(bookId, surah);
        let existing = null;
        try { existing = await idbRead('texts', key); } catch { existing = null; }
        let map = bucket;
        if (existing) {
          // سورة مكرّرة في المصدر: ندمج النصوص بدل فقدانها.
          try { map = { ...JSON.parse(typeof existing === 'string' ? existing : await gunzipText(existing)), ...bucket }; } catch { map = bucket; }
        }
        const payload = JSON.stringify(map);
        // الكتب الضخمة تُحفظ نصًّا لتفادي ضغط مئات الميغابايت على حساب سرعة الفتح.
        await idbWrite('texts', [[key, hugeBook ? payload : await gzipText(payload)]]);
        tafsirSurahCache.set(key, map);
        bucket = {};
      };
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        if (!inAyahs) {
          const marker = buffer.indexOf('"ayahs"');
          if (marker < 0) { if (buffer.length > 400000) buffer = buffer.slice(-2000); continue; }
          const open = buffer.indexOf('[', marker);
          if (open < 0) continue;
          buffer = buffer.slice(open + 1);
          inAyahs = true;
        }
        let cursor = 0;
        for (;;) {
          let start = -1;
          for (let at = buffer.indexOf('{', cursor); at >= 0; at = buffer.indexOf('{', at + 1)) {
            if (/^\{\s*"surah"/.test(buffer.slice(at, at + 40))) { start = at; break; }
          }
          if (start < 0) break;
          const end = jsonObjectEnd(buffer, start);
          if (end < 0) break;
          try {
            const row = JSON.parse(buffer.slice(start, end + 1));
            const text = bookRowText(row);
            const rowSurah = Number(row.surah);
            if (rowSurah !== surah) { await flush(); surah = rowSurah; }
            if (text) bucket[row.ayah] = text;
            rows++;
          } catch { /* صف غير مكتمل أو مشوّه — نتجاوزه */ }
          cursor = end + 1;
        }
        buffer = buffer.slice(cursor);
      }
      await flush();
      if (!rows) throw new Error('empty-book');
      await idbWrite('meta', [[bookId, { ready: true, rows, storedAt: Date.now() }]]);
      tafsirBookState.set(bookId, { state: 'ready', percent: 100 });
      tafsirAyahCache.clear();
      pageCache.clear();
      stopTafsirBookTicker();
      refreshTafsirSurfaces();
      return true;
    } catch (error) {
      const message = String((error && error.message) || error);
      console.warn('tafsir-book', bookId, message);
      tafsirBookState.set(bookId, { state: 'error', percent: bookState(bookId).percent, message });
      stopTafsirBookTicker();
      refreshTafsirSurfaces();
      return false;
    }
  }

  // مضمون آية واحدة من الكتاب المختار، مع بدء تجهيز الكتاب عند أول طلب.
  async function tafsirForAyah(s, n, edition) {
    if (ONLINE_TAFSIRS.has(edition)) {
      try { return await fetchOnlineTafsir(s, n, edition); } catch { return ''; }
    }
    if (!isClassicalTafsir(edition)) return '';
    const bookId = tafsirBookId(edition);
    if (await bookIsStored(bookId)) return storedBookText(bookId, s, n);
    if (bookState(bookId).state !== 'loading') loadTafsirBook(bookId);
    else startTafsirBookTicker();
    return '';
  }

  // إعادة رسم مواضع عرض التفسير بعد أن يصبح الكتاب جاهزًا.
  function refreshTafsirSurfaces() {
    const panel = $('#tafsirPanel');
    if (panel && panel.classList.contains('show') && state.sel) showTafsirPanel(state.sel);
    const view = $('#view-tafsir');
    if (view && view.classList.contains('active')) renderTafsirView();
    if (state.sel) {
      showPage(state.page, { selG: state.sel.g, save: false }).catch(() => {});
    }
  }

  function showTafsirPanel(a) {
    const edition = settings.tafsir;
    const book = TAFSIRS.find((t) => t[0] === edition)?.[1] || '';
    $('#tafsirTitle').textContent = `${surahName(a.s)} - الآية ${toArabicDigits(a.n)}`;
    $('#tafsirAyah').textContent = a.text;
    $('#tafsirLabel').textContent = book || 'التفسير';
    $('#tafsirBody').textContent = a.tafsir || missingTafsirText();
    // النص غير جاهز؟ نجلبه الآن (شبكة أو تجهيز كتاب) بدل أن نترك المستخدم بلا تفسير.
    if (!a.tafsir) {
      const classical = isClassicalTafsir(edition);
      const bookId = classical ? tafsirBookId(edition) : 0;
      $('#tafsirBody').textContent = classical ? tafsirBookLoadingNote(bookId) : 'جاري تحميل التفسير…';
      if (classical) startTafsirBookTicker();
      tafsirForAyah(a.s, a.n, edition).then((text) => {
        const panel = $('#tafsirPanel');
        if (!panel || !panel.classList.contains('show') || settings.tafsir !== edition) return;
        if (text) {
          $('#tafsirBody').textContent = text;
          a.tafsir = text;
          if (classical) stopTafsirBookTicker();
        } else if (classical && bookState(bookId).state !== 'ready') {
          $('#tafsirBody').textContent = tafsirBookLoadingNote(bookId);
        } else {
          $('#tafsirBody').textContent = missingTafsirText();
        }
      }).catch(() => {
        $('#tafsirBody').textContent = 'تعذّر تحميل التفسير الآن؛ تحقّق من الاتصال.';
      });
    }
    const hasTr = !!settings.translation;
    $('#transLabel').style.display = hasTr ? 'block' : 'none';
    $('#tafsirTrans').style.display = hasTr ? 'block' : 'none';
    $('#tafsirTrans').textContent = hasTr ? (a.tr || 'لا توجد ترجمة لهذه الآية.') : '';
    $('#tjPanel').classList.remove('show');
    $('#meanPanel').classList.remove('show');
    $('#tafsirPanel').classList.add('show');
  }
  $('#tafsirClose').addEventListener('click', () => $('#tafsirPanel').classList.remove('show'));
  // أزرار حزمة التفاسير
  if ($('#tfPackBtn')) $('#tfPackBtn').addEventListener('click', () => startTafsirPackDownload());
  if ($('#tfPackCancel')) $('#tfPackCancel').addEventListener('click', () => cancelTafsirPackDownload());
  if ($('#tfPackDelete')) $('#tfPackDelete').addEventListener('click', () => deleteTafsirPack());

  // ---------- اختيار الآية بلا إعادة رسم كاملة ----------
  function selectAyah(a) {
    const surahChanged = state.selSurah !== a.s;
    state.sel = a;
    state.selSurah = a.s;
    markSelection();
    saveLast(true);
    refreshSelectionUI(surahChanged);
  }

  function refreshSelectionUI(surahChanged) {
    if (!state.pg || !state.sel) return;
    const pg = state.pg;
    $('#topTitle').textContent = `${surahName(state.sel.s)} · الجزء ${toArabicDigits(state.sel.juz || pg.ayahs[0].juz)} · ص ${toArabicDigits(pg.p)}`;
    $('#pagerContext').textContent = `${surahNameShort(state.sel.s)} · الجزء ${toArabicDigits(state.sel.juz || pg.ayahs[0].juz)}`;
    const bookmarked = isBookmarked(state.sel.s, state.sel.n);
    $('#btnBm').innerHTML = `${bookmarked ? '★' : '☆'} <span>${bookmarked ? 'محفوظة' : 'حفظ علامة'}</span>`;
    updateResumeBtn();
    syncPlayControls();
    if (surahChanged) renderIndex();
  }

  // ---------- نافذة التجويد ----------
  function showTajweedPanel(code) {
    const rule = TJ_RULES[code];
    if (!rule) return;
    $('#tjTitle').textContent = rule[0];
    $('#tjBody').textContent = rule[1];
    $('#tafsirPanel').classList.remove('show');
    $('#tjPanel').classList.add('show');
    $('#meanPanel').classList.remove('show');
  }

  function showIndependentTajweedPanel(ruleIds) {
    const curriculum = currentApprovedTajweedCurriculum();
    if (!curriculum || !Array.isArray(ruleIds)) return;
    const wanted = new Set(ruleIds);
    const rules = curriculum.rules.filter((rule) => wanted.has(rule.id));
    if (!rules.length) return;
    $('#tjTitle').textContent = rules.map((rule) => rule.name).join('، ');
    $('#tjBody').textContent = rules.map((rule) => `${rule.name}: ${rule.answer}`).join('\n\n');
    $('#tafsirPanel').classList.remove('show');
    $('#tjPanel').classList.add('show');
    $('#meanPanel').classList.remove('show');
  }
  $('#tjClose').addEventListener('click', () => $('#tjPanel').classList.remove('show'));

  // ---------- قسم التفسير ----------
  function renderTafsirView() {
    const a = state.sel;
    $('#tfBook').value = settings.tafsir;
    $('#tfTrans').value = settings.translation;
    if (!a) {
      $('#tfTitle').textContent = '';
      $('#tfArabic').textContent = '';
      $('#tfTafsir').textContent = '';
      $('#tfTransText').textContent = '';
      return;
    }
    $('#tfTitle').textContent = `${surahName(a.s)} - الآية ${toArabicDigits(a.n)}`;
    $('#tfArabic').textContent = a.text;
    $('#tfTafsir').textContent = a.tafsir || missingTafsirText();
    if (!a.tafsir) {
      const edition = settings.tafsir;
      const classical = isClassicalTafsir(edition);
      const bookId = classical ? tafsirBookId(edition) : 0;
      $('#tfTafsir').textContent = classical ? tafsirBookLoadingNote(bookId) : 'جاري تحميل التفسير…';
      if (classical) startTafsirBookTicker();
      tafsirForAyah(a.s, a.n, edition).then((text) => {
        if (settings.tafsir !== edition) return;
        if (text) {
          $('#tfTafsir').textContent = text;
          a.tafsir = text;
          if (classical) stopTafsirBookTicker();
        } else if (classical && bookState(bookId).state !== 'ready') {
          $('#tfTafsir').textContent = tafsirBookLoadingNote(bookId);
        } else {
          $('#tfTafsir').textContent = missingTafsirText();
        }
      }).catch(() => {
        $('#tfTafsir').textContent = 'تعذّر تحميل التفسير الآن؛ تحقّق من الاتصال.';
      });
    }
    $('#tfTransText').textContent = settings.translation ? (a.tr || 'لا توجد ترجمة لهذه الآية.') : 'بدون ترجمة مختارة.';
  }

  async function stepAyah(delta) {
    if (!state.sel) return;
    let s = state.sel.s, n = state.sel.n;
    if (delta > 0) {
      if (n < (surahs[s - 1]?.numberOfAyahs || 0)) n++;
      else if (s < 114) { s++; n = 1; }
      else return;
    } else if (n > 1) {
      n--;
    } else if (s > 1) {
      s--; n = surahs[s - 1].numberOfAyahs;
    } else return;
    try {
      const ay = await findAyah(s, n);
      if (!ay) return;
      await showPage(ay.page, { selG: ay.g });
      renderTafsirView();
    } catch {
      toast('تعذر تحميل الآية. تحقق من الاتصال.');
    }
  }
  $('#tfPrev').addEventListener('click', () => stepAyah(-1));
  $('#tfNext').addEventListener('click', () => stepAyah(1));
  $('#tfBook').addEventListener('change', (e) => onSettingChange('tafsir', e.target.value));
  $('#tfTrans').addEventListener('change', (e) => onSettingChange('translation', e.target.value));

  // ---------- زر الرجوع في الأندرويد ----------
  let capApp = null;
  function getCapApp() {
    if (!capApp && hasNativePlugin('App') && Cap.registerPlugin) capApp = Cap.registerPlugin('App');
    return capApp;
  }
  let exitArmedAt = 0;
  function handleBack() {
    if (document.body.classList.contains('group-menu-open')) { closeGroups({ restoreFocus: true }); return; }
    if ($('#tafsirPanel').classList.contains('show')) { $('#tafsirPanel').classList.remove('show'); return; }
    if ($('#tjPanel').classList.contains('show')) { $('#tjPanel').classList.remove('show'); return; }
    if (document.body.classList.contains('side-open')) { closeSide(); return; }
    if (navStack.length) { popView(); return; }
    if (curView !== 'reader') { showView('reader', { back: true }); return; }
    if (Date.now() - exitArmedAt < 2000) { const app = getCapApp(); if (app) app.exitApp(); return; }
    exitArmedAt = Date.now();
    toast('اضغط مرة أخرى للخروج');
  }

  // ---------- أدوات الأندرويد للتحميل إلى مجلد الجهاز ----------
  function isNative() { return !!(Cap && Cap.isNativePlatform && Cap.isNativePlatform()); }
  function hasNativePlugin(name) { return !!(isNative() && Cap.isPluginAvailable && Cap.isPluginAvailable(name)); }
  function nativeCall(plugin, method, opts) { return Cap.nativePromise(plugin, method, opts || {}); }
  let tafsirNative = null;
  let reminderNative = null;
  let smartDeviceNative = null;
  function getTafsirNative() {
    if (!hasNativePlugin('TafsirStore')) return null;
    if (!tafsirNative && Cap.registerPlugin) tafsirNative = Cap.registerPlugin('TafsirStore');
    return tafsirNative;
  }
  function getReminderNative() {
    if (!hasNativePlugin('Reminder')) return null;
    if (!reminderNative && Cap.registerPlugin) reminderNative = Cap.registerPlugin('Reminder');
    return reminderNative;
  }
  function getSmartDeviceNative() {
    if (!hasNativePlugin('SmartDevice')) return null;
    if (!smartDeviceNative && Cap.registerPlugin) smartDeviceNative = Cap.registerPlugin('SmartDevice');
    return smartDeviceNative;
  }
  function bytesToBase64(bytes) {
    let bin = '';
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  }
  function base64ToBlob(b64, type) {
    const bin = atob(b64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return new Blob([arr], { type });
  }

  // ---------- التشغيل ----------
  function formatAudioTime(value) {
    const seconds = Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
    const minutes = Math.floor(seconds / 60);
    return toArabicDigits(`${minutes}:${String(seconds % 60).padStart(2, '0')}`);
  }

  function syncAudioTimeline() {
    const seek = $('#audioSeek');
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    const current = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
    seek.max = String(duration || 0);
    seek.style.setProperty('--p', duration ? `${Math.min(100, (current / duration) * 100).toFixed(2)}%` : '0%');
    seek.value = String(duration ? Math.min(current, duration) : 0);
    seek.disabled = !duration;
    $('#audioCurrent').textContent = formatAudioTime(current);
    $('#audioDuration').textContent = formatAudioTime(duration);
  }

  // المشغل عنصر واحد يتنقل بين موضعين: داخل قسم الاستماع، وشريط المصحف السفلي
  function placePlayer(name) {
    const player = $('#player');
    const slot = name === 'listen' ? $('#listenPlayerSlot') : $('#readerDock');
    if (player && slot && player.parentNode !== slot) slot.prepend(player);
  }

  function syncMediaSession() {
    if (!('mediaSession' in navigator) || !play.active || !play.cur) return;
    try {
      const name = surahName(play.cur.s) || `سورة ${play.cur.s}`;
      navigator.mediaSession.metadata = new MediaMetadata({
        title: `${name} · الآية ${play.cur.n}`,
        artist: play.label || 'القرآن الكريم',
        album: 'المصحف',
      });
      navigator.mediaSession.playbackState = audio.paused ? 'paused' : 'playing';
    } catch { /* المتصفح لا يدعم بيانات الإشعار */ }
  }

  // ---------- إبقاء الشاشة مضاءة ----------
  // الشاشة لا تُطفأ أثناء القراءة أو التلاوة، ويُترك ذلك تلقائيًا عند إخفاء الصفحة
  // أو إغلاق التطبيق؛ لا يوجد مفتاح للمستخدم.
  const wake = { sentinel: null, wanted: false };
  const wakeSupported = () => typeof navigator !== 'undefined' && 'wakeLock' in navigator;
  // الشاشة تبقى مضاءة ما دام التطبيق مفتوحًا (قراءة أو تلاوة)، وتعود طبيعية عند إغلاقه.
  function wakeWantedNow() {
    if (document.hidden) return false;
    const playing = play.active && !audio.paused;
    return playing || curView === 'reader';
  }
  async function releaseWakeLock() {
    wake.wanted = false;
    const sentinel = wake.sentinel;
    wake.sentinel = null;
    if (sentinel) { try { await sentinel.release(); } catch { /* أُطلق مسبقًا */ } }
  }
  async function refreshWakeLock() {
    const wanted = wakeWantedNow();
    wake.wanted = wanted;
    if (!wakeSupported()) return;
    if (!wanted) { await releaseWakeLock(); return; }
    if (wake.sentinel && !wake.sentinel.released) return;
    try {
      wake.sentinel = await navigator.wakeLock.request('screen');
      wake.sentinel.addEventListener('release', () => { wake.sentinel = null; });
    } catch { wake.sentinel = null; }
  }
  let wakeHintShown = false;
  function wakeHintOnce() {
    if (wakeHintShown || wakeSupported()) return;
    wakeHintShown = true;
    toast('جهازك لا يدعم منع إطفاء الشاشة من التطبيق؛ اضبط مدة الشاشة من إعدادات الهاتف.');
  }

  // ---------- الصوت في الخلفية ----------
  // لا يوجد سؤال ولا مفتاح: التلاوة تستمر تلقائيًا عند مغادرة التطبيق أو إطفاء الشاشة،
  // وتنتهي تمامًا عند إغلاق التطبيق.

  // ---------- تشغيل التلاوة في خدمة أندرويد (يستمر بعد إغلاق التطبيق) ----------
  // الطبقة الويب تُسلّم قائمة الآيات إلى الخدمة الأمامية عند خروج المستخدم،
  // فتكمل التلاوة من ملفاتها الخاصة حتى لو أُغلقت واجهة التطبيق.
  let nativeAudioActive = false;
  const nativeAudio = () => (hasNativePlugin('QuranAudio') && Cap.registerPlugin
    ? Cap.registerPlugin('QuranAudio') : null);
  async function nativeQueueFrom(start, limit = 30) {
    const items = [];
    let node = start;
    for (let i = 0; i < limit && node; i++) {
      const url = typeof node.audio === 'string' && /^https?:/i.test(node.audio) ? node.audio : '';
      if (url) items.push({ url, title: `${surahNameShort(node.s)} · ${node.n}` });
      node = play.nextFn ? await play.nextFn(node).catch(() => null) : null;
    }
    return items;
  }
  async function handOffToNative() {
    const api = nativeAudio();
    if (!api || nativeAudioActive) return false;
    if (!play.active || !play.cur || audio.paused) return false;
    const items = await nativeQueueFrom(play.cur);
    if (!items.length) return false;
    try {
      await api.start({ items, index: 0, rate: playRate });
      nativeAudioActive = true;
      audio.pause();
      return true;
    } catch {
      return false;
    }
  }
  async function takeBackFromNative() {
    const api = nativeAudio();
    if (!api || !nativeAudioActive) return;
    nativeAudioActive = false;
    try { await api.stop(); } catch { /* الخدمة متوقفة أصلًا */ }
    if (play.active && play.cur) playAyah(play.cur);
  }
  document.addEventListener('visibilitychange', () => {
    refreshWakeLock();
    if (!hasNativePlugin('QuranAudio')) return;
    if (document.hidden) handOffToNative();
    else takeBackFromNative();
  });
  if (hasNativePlugin('QuranAudio') && Cap.registerPlugin) {
    try {
      Cap.registerPlugin('QuranAudio').addListener('stopped', () => {
        // الخدمة توقفت (إغلاق التطبيق أو نهاية القائمة): نُبقي حالة الواجهة متسقة
        nativeAudioActive = false;
        if (!play.active) audio.pause();
      });
    } catch { /* لا يوجد جسر */ }
  }

  function setPlayerUI() {
    $('#player').classList.toggle('show', play.active);
    $('#player').classList.toggle('is-playing', play.active && !audio.paused);
    $('#pSpeed').textContent = `${playRate}×`;
    syncMediaSession();
    refreshWakeLock();
    if (play.active && play.cur) {
      $('#playerInfo').textContent = `${play.label} · الآية ${toArabicDigits(play.cur.n)}` +
        (play.repeatCount > 1
          ? ` · تكرار ${toArabicDigits(play.repeatCount - play.repeatLeft + 1)} من ${toArabicDigits(play.repeatCount)}`
          : '');
    }
    const bodyEl = $('#pageBody');
    if (bodyEl) bodyEl.classList.toggle('syncing', Boolean(play.active && syncReadingEnabled()));
    const paused = audio.paused;
    $('#pToggle').textContent = paused ? '▶' : '⏸';
    $('#pToggle').setAttribute('aria-label', paused ? 'تشغيل التلاوة' : 'إيقاف التلاوة مؤقتًا');
    $('#btnPlaySurah').classList.toggle('is-playing', play.active);
    $('.reader-play-label').textContent = play.active ? 'تشغيل من المحدد' : 'تشغيل السورة';
    syncAudioTimeline();
    requestAnimationFrame(syncReaderDockHeight);
  }

  let smartLastPlayedRef = '';
  let smartLastPlayedAt = 0;
  function recordSmartRecitation(a) {
    if (!a) return;
    const ref = `${a.s}:${a.n}`;
    const now = Date.now();
    if (ref === smartLastPlayedRef && now - smartLastPlayedAt < 10 * 60 * 1000) return;
    smartLastPlayedRef = ref;
    smartLastPlayedAt = now;
    smartRecord({
      type: 'PLAY_RECITATION',
      service: 'recitation',
      context: { page: Number(a.page || state.page), riwayah: settings.riwaya, source: 'player' },
    });
  }

  // ---------- تلاوة السورة كاملة (ملف واحد للسورة) ----------
  function tryLoadSurahReciters() {
    getJSON('quran-reciters.json').then((data) => {
      SURAH_RECITERS = Array.isArray(data?.items) ? data.items : [];
      syncSurahReciterSelect();
    }).catch(() => { SURAH_RECITERS = []; syncSurahReciterSelect(); });
  }

  function surahReciterEntry() {
    if (!SURAH_RECITERS.length) return null;
    const found = SURAH_RECITERS.find((r) => String(r.id) === String(settings.surahReciter));
    if (found) return found;
    const afasy = SURAH_RECITERS.find((r) => r.name.includes('العفاسي'));
    const chosen = afasy || SURAH_RECITERS[0];
    settings.surahReciter = chosen.id;
    saveSettings();
    return chosen;
  }

  function surahAudioUrl(entry, surah) {
    if (!entry || !entry.server) return null;
    return entry.server + String(surah).padStart(3, '0') + '.mp3';
  }

  function syncSurahReciterSelect() {
    const select = $('#playSurahReciter');
    if (!select) return;
    if (!SURAH_RECITERS.length) {
      select.innerHTML = '<option value="">قائمة القراء غير متاحة الآن</option>';
      return;
    }
    const current = surahReciterEntry();
    select.innerHTML = SURAH_RECITERS
      .map((r) => `<option value="${r.id}">${r.name}</option>`).join('');
    select.value = String(current.id);
    refreshPickReciterName();
    if ($('#surahReciterCount')) {
      $('#surahReciterCount').textContent = `${toArabicDigits(SURAH_RECITERS.length)} قارئًا برواياتهم — تلاوة كاملة لكل سورة`;
    }
  }


  // ===== مكتبة القرّاء: بحث + مفضلة =====
  function voiceFavs() {
    try { return JSON.parse(store.get('voice-favs') || '{}') || {}; } catch { return {}; }
  }
  function isFavReciter(id) { return (voiceFavs().reciters || []).includes(String(id)); }
  function toggleFavReciter(id) {
    const all = voiceFavs();
    const list = Array.isArray(all.reciters) ? all.reciters.slice() : [];
    const key = String(id);
    const at = list.indexOf(key);
    if (at >= 0) list.splice(at, 1); else list.push(key);
    all.reciters = list;
    store.set('voice-favs', JSON.stringify(all));
    return at < 0;
  }

  function syncReciterName() {
    return (RECITERS.find(([id]) => id === settings.reciter) || [null, ''])[1];
  }
  function fullSurahMode() {
    return settings.surahMode === 'full' && !isRiw();
  }
  function refreshPickReciterName() {
    const label = $('#pickSurahReciterName');
    if (!label) return;
    if (fullSurahMode()) {
      const entry = surahReciterEntry();
      label.textContent = entry ? entry.name : 'اختر القارئ';
    } else {
      label.textContent = `آية بآية · ${syncReciterName() || 'القارئ المتزامن'}`;
    }
  }
  function pickSyncMode() {
    settings.surahMode = 'sync';
    saveSettings();
    closeVoiceSheet();
    refreshPickReciterName();
    toast('تلاوة متزامنة آية بآية');
  }

  function renderVoiceList() {
    const list = $('#voiceList');
    if (!list) return;
    const q = ($('#voiceSearch') && $('#voiceSearch').value || '').trim();
    const current = surahReciterEntry();
    const rows = SURAH_RECITERS.filter((r) => !q
      || r.name.includes(q) || String(r.rewaya || '').includes(q) || String(r.family || '').includes(q));
    rows.sort((a, b) => {
      const fa = isFavReciter(a.id) ? 0 : 1;
      const fb = isFavReciter(b.id) ? 0 : 1;
      if (fa !== fb) return fa - fb;
      return 0;
    });
    const syncRow = `
      <div class="voice-row${!fullSurahMode() ? ' is-current' : ''}">
        <span class="voice-star" aria-hidden="true"></span>
        <button class="voice-row-main" data-pick-sync="1">
          <strong>تلاوة متزامنة آية بآية</strong>
          <span class="muted">${esc(syncReciterName() || 'القارئ المتزامن')}</span>
        </button>
      </div>`;
    list.innerHTML = syncRow + rows.map((r) => `
      <div class="voice-row${current && String(current.id) === String(r.id) ? ' is-current' : ''}" data-id="${r.id}">
        <button class="voice-star${isFavReciter(r.id) ? ' on' : ''}" data-star="${r.id}" aria-label="مفضلة" title="مفضلة">★</button>
        <button class="voice-row-main" data-pick="${r.id}">
          <strong>${esc(r.name)}</strong>
          <span class="muted">${esc(r.rewaya || 'حفص عن عاصم')}</span>
        </button>
      </div>`).join('');
    const count = $('#voiceCount');
    if (count) count.textContent = `${toArabicDigits(rows.length)} من ${toArabicDigits(SURAH_RECITERS.length)}`;
  }

  function openVoiceSheet() {
    const sheet = $('#voiceSheet');
    if (!sheet) return;
    sheet.hidden = false;
    const search = $('#voiceSearch');
    if (search) { search.value = ''; setTimeout(() => search.focus(), 60); }
    renderVoiceList();
  }
  function closeVoiceSheet() {
    const sheet = $('#voiceSheet');
    if (sheet) sheet.hidden = true;
  }
  function pickReciter(id) {
    settings.surahReciter = id;
    settings.surahMode = 'full';
    saveSettings();
    syncSurahReciterSelect();
    refreshPickReciterName();
    closeVoiceSheet();
    const entry = surahReciterEntry();
    if (entry) toast(`القارئ: ${entry.name}`);
  }

  if ($('#pickSurahReciter')) $('#pickSurahReciter').addEventListener('click', openVoiceSheet);
  if ($('#voiceSheetClose')) $('#voiceSheetClose').addEventListener('click', closeVoiceSheet);
  if ($('#voiceSheet')) $('#voiceSheet').addEventListener('click', (e) => { if (e.target.id === 'voiceSheet') closeVoiceSheet(); });
  if ($('#voiceSearch')) $('#voiceSearch').addEventListener('input', renderVoiceList);
  if ($('#voiceList')) $('#voiceList').addEventListener('click', (e) => {
    const star = e.target.closest('[data-star]');
    if (star) { toggleFavReciter(star.dataset.star); renderVoiceList(); return; }
    if (e.target.closest('[data-pick-sync]')) { pickSyncMode(); return; }
    const pick = e.target.closest('[data-pick]');
    if (pick) pickReciter(pick.dataset.pick);
  });

  // تحميل مسبق للسورة التالية أثناء التشغيل، فلا تكون هناك فجوة بين السور
  const preloadPool = new Map();
  function preloadSurahAudio(url) {
    if (!url || preloadPool.has(url)) return;
    try {
      const probe = new Audio();
      probe.preload = 'auto';
      probe.muted = true;
      probe.src = url;
      preloadPool.set(url, probe);
      if (preloadPool.size > 3) {
        const oldest = preloadPool.keys().next().value;
        const el = preloadPool.get(oldest);
        if (el) { el.removeAttribute('src'); el.load(); }
        preloadPool.delete(oldest);
      }
    } catch { /* لا شيء */ }
  }

  async function playSurahFull(surah, options = {}) {
    const entry = surahReciterEntry();
    const url = surahAudioUrl(entry, surah);
    if (!url) { toast('لا تتوفر تلاوة كاملة لهذه السورة الآن.'); return; }
    const first = await findAyah(surah, 1).catch(() => null);
    const label = `سورة ${surahNameShort(surah)} — ${entry.name}`;
    play.label = label;
    play.repeatCount = 1;
    play.repeatLeft = 1;
    play.follow = false;
    play.nextFn = async (cur) => {
      if (!cur || cur.s >= 114) return null;
      const next = cur.s + 1;
      const firstNext = await findAyah(next, 1).catch(() => null);
      return {
        s: next, n: 1, g: `${next}:1`, text: '', page: firstNext ? firstNext.page : null,
        audio: surahAudioUrl(entry, next), fromSurah: true,
      };
    };
    if (options.scroll !== false && first && first.page && first.page !== state.page) {
      await showPage(first.page, { selG: first.g, save: false, scroll: false });
    }
    await playAyah({
      s: surah, n: 1, g: `${surah}:1`, text: '',
      page: first ? first.page : null, audio: url, fromSurah: true,
    });
    if (surah < 114) preloadSurahAudio(surahAudioUrl(entry, surah + 1));
  }


  // ---------- التلاوة المتزامنة: آية بآية بلا حاجة لتوقيتات ----------
  // ملفات الآيات متاحة للقرّاء المعلنين في OFFLINE_SRC (CDN) أو المحمّلين على الجهاز.
  function ayahSyncAvailable() {
    return Boolean(OFFLINE_SRC[settings.reciter]);
  }

  function syncReadingEnabled() {
    return !isRiw() && ayahSyncAvailable();
  }

  // تمرير الشاشة إلى الآية الجارية وإبرازها
  function focusSyncedAyah() {
    const body = $('#pageBody');
    if (!body) return;
    body.classList.toggle('syncing', Boolean(play.active && syncReadingEnabled()));
    if (!play.active || !syncReadingEnabled()) return;
    const el = body.querySelector('.ay.playing');
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const stageRect = (stage || body).getBoundingClientRect();
    const outside = rect.top < stageRect.top + 60 || rect.bottom > stageRect.bottom - 120;
    if (outside) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }

  // تحميل مسبق لملف الآية التالية لتفادي الفراغ بين الآيات
  let preloadEl = null;
  function preloadAyahAudio(s, n) {
    if (!OFFLINE_SRC[settings.reciter] || isRiw()) return;
    const url = ayahAudioUrl(settings.reciter, s, n);
    if (!url) return;
    if (!preloadEl) {
      preloadEl = new Audio();
      preloadEl.preload = 'auto';
    }
    try { preloadEl.src = url; } catch { /* تجاهل */ }
  }

  async function playAyah(a) {
    if (isRiw() && !riwAudioOk()) { toast('اختر قارئاً لهذه الرواية من الإعدادات'); return; }
    if (!a) { stopPlayback(); return; }
    play.cur = a;
    // تلاوة السورة كاملة تُقرأ من ملف السورة مباشرة، دون الرجوع لملفات الآيات.
    const local = a.fromSurah ? null : await localAudioUrl(settings.reciter, a.s, a.n).catch(() => null);
    if (!local && !a.audio) {
      toast('لا يوجد تسجيل لهذه الآية مع القارئ المختار');
      const nxt = await play.nextFn(a);
      return playAyah(nxt);
    }
    const prevObj = objUrl;
    objUrl = local;
    audio.src = local || a.audio;
    if (prevObj) URL.revokeObjectURL(prevObj);
    audio.play().catch(() => toast('تعذر تشغيل الصوت. اضغط تشغيل مرة أخرى.'));
    play.active = true;
    recordSmartRecitation(a);
    // تقليب الصفحة تلقائياً مع التلاوة
    if (a.page && a.page !== state.page && play.follow) {
      state.sel = a; state.selSurah = a.s;
      showPage(a.page, { selG: a.g, save: false, scroll: true });
    } else {
      markSelection();
      if (state.pg && state.pg.ayahs.some((x) => x.g === a.g)) {
        state.sel = a; state.selSurah = a.s; markSelection(); updateChrome();
      }
    }
    // التلاوة المتزامنة: إبراز الآية الجارية وتمرير الشاشة وتحسين تسلسل الصوت
    focusSyncedAyah();
    if (syncReadingEnabled() && !a.fromSurah) preloadAyahAudio(a.s, a.n + 1);
    store.set('last', { p: a.page || state.page, s: a.s, a: a.n, g: a.g });
    renderLast();
    setPlayerUI();
  }

  // بدء تشغيل السورة: ملف واحد كامل ما لم يكن المستخدم يريد آيةً آية
  async function startSurahPlay(s, n) {
    if (isRiw() && !riwAudioOk()) { toast('اختر قارئاً لهذه الرواية من الإعدادات'); return; }
    // التلاوة المتزامنة تتقدّم على ملف السورة الكاملة لأنها تضيء الآية الجارية
    const syncReady = syncReadingEnabled();
    const wantFull = settings.surahAudio !== false && !isRiw() && SURAH_RECITERS.length
      && (fullSurahMode() || !syncReady);
    if (wantFull) return playSurahFull(s);
    if (!syncReady && !isRiw() && !OFFLINE_SRC[settings.reciter]) {
      toast('هذا القارئ ليس له ملفات آيات؛ اختر قارئًا من قائمة التحميل للتلاوة المتزامنة.');
    }
    const first = isRiw() ? await findRiwAyah(s, n) : await findAyah(s, n);
    if (riwSurahOnly()) toast('تلاوة السورة كاملة (لا يتوفر توقيت للآيات مع هذا القارئ)');
    if (!first) return;
    const recLabel = (RECITERS.find(([id]) => id === settings.reciter) || [null, ''])[1];
    const label = `سورة ${surahNameShort(s)}${recLabel ? ' · ' + recLabel : ''}${syncReady ? ' · آية بآية' : ''}`;
    play.label = label;
    play.repeatCount = 1; play.repeatLeft = 1;
    play.follow = true;
    play.nextFn = async (cur) => {
      if (riwSurahOnly()) return null; // ملف السورة كاملة: لا آية تالية
      const pg = await loadPage(cur.page);
      const idx = pg.ayahs.findIndex((x) => x.g === cur.g);
      let cand = idx >= 0 && idx + 1 < pg.ayahs.length ? pg.ayahs[idx + 1] : null;
      if (!cand && cur.page < TOTAL_PAGES) {
        const np = await loadPage(cur.page + 1);
        cand = np.ayahs[0] || null;
      }
      return cand && cand.s === cur.s ? cand : null;
    };
    play.prevFn = async (cur) => {
      if (riwSurahOnly()) return null;
      const pg = await loadPage(cur.page);
      const idx = pg.ayahs.findIndex((x) => x.g === cur.g);
      let cand = idx > 0 ? pg.ayahs[idx - 1] : null;
      if (!cand && cur.page > 1) {
        const pp = await loadPage(cur.page - 1);
        cand = pp.ayahs[pp.ayahs.length - 1] || null;
      }
      return cand && cand.s === cur.s ? cand : null;
    };
    play.active = true;
    await playAyah(first);
  }

  // تشغيل من مصفوفة (للحفظ)
  function startListPlay(list, label, repeat) {
    if (isRiw()) { toast('التلاوة متاحة لرواية حفص فقط حالياً'); return; }
    let i = 0;
    play.label = label;
    play.repeatCount = repeat; play.repeatLeft = repeat;
    play.follow = false;
    play.nextFn = async (cur) => {
      const idx = list.findIndex((x) => x.g === cur.g);
      return list[idx + 1] || null;
    };
    play.prevFn = async (cur) => {
      const idx = list.findIndex((x) => x.g === cur.g);
      return idx > 0 ? list[idx - 1] : null;
    };
    play.active = true;
    i = 0;
    playAyah(list[i]);
  }

  function stopPlayback() {
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    play.active = false;
    play.cur = null;
    setPlayerUI();
    if (state.pg) markSelection();
    $$('.ayah.playing').forEach((el) => el.classList.remove('playing'));
  }

  // تسجيل غير متوفر لآية (مثلاً نقص في الملف): ننتقل للآية التالية بدل التوقف
  audio.addEventListener('error', async () => {
    if (!play.active || !play.cur || !audio.getAttribute('src')) return;
    toast('لا يتوفر تسجيل لهذا المقطع مع القارئ المختار');
    playAyah(await play.nextFn(play.cur).catch(() => null));
  });

  audio.addEventListener('ended', async () => {
    if (!play.active || !play.cur) return;
    if (play.repeatLeft > 1) {
      play.repeatLeft--;
      audio.currentTime = 0;
      audio.play();
      setPlayerUI();
      return;
    }
    play.repeatLeft = play.repeatCount;
    const nxt = await play.nextFn(play.cur).catch(() => null);
    if (!nxt) { stopPlayback(); toast('انتهت التلاوة'); return; }
    playAyah(nxt);
  });
  audio.addEventListener('play', setPlayerUI);
  audio.addEventListener('pause', setPlayerUI);
  audio.addEventListener('timeupdate', syncAudioTimeline);
  audio.addEventListener('loadedmetadata', syncAudioTimeline);
  audio.addEventListener('durationchange', syncAudioTimeline);
  audio.addEventListener('emptied', syncAudioTimeline);

  $('#audioSeek').addEventListener('input', (e) => {
    const value = Number(e.target.value);
    if (Number.isFinite(value) && Number.isFinite(audio.duration)) audio.currentTime = value;
    syncAudioTimeline();
  });

  // يقيس الرصيف كاملًا (التنقل + المشغل عند ظهوره) حتى لا يغطي آخر سطر من المصحف.
  function syncReaderDockHeight() {
    const dock = $('#readerDock');
    if (!dock) return;
    const height = Math.ceil(dock.getBoundingClientRect().height);
    if (height > 0) document.documentElement.style.setProperty('--reader-dock-h', `${height}px`);
  }
  if (window.ResizeObserver) new ResizeObserver(syncReaderDockHeight).observe($('#readerDock'));
  window.addEventListener('resize', syncReaderDockHeight, { passive: true });
  requestAnimationFrame(syncReaderDockHeight);

  // أزرار إشعار الوسائط في Android (تشغيل/إيقاف/التالي/السابق) تعمل حتى والتطبيق في الخلفية
  if ('mediaSession' in navigator) {
    const handlers = {
      play: () => { $('#pToggle').click(); },
      pause: () => { $('#pToggle').click(); },
      nexttrack: () => { if (play.active && play.nextFn) play.nextFn(); },
      previoustrack: () => { if (play.active && play.prevFn) play.prevFn(); },
    };
    Object.entries(handlers).forEach(([action, fn]) => {
      try { navigator.mediaSession.setActionHandler(action, fn); } catch { /* إجراء غير مدعوم */ }
    });
    navigator.mediaSession.setPositionState?.bind(navigator.mediaSession);
  }

  $('#pSpeed').addEventListener('click', () => {
    const i = PLAY_RATES.indexOf(playRate);
    playRate = PLAY_RATES[(i + 1) % PLAY_RATES.length];
    audio.playbackRate = playRate;
    store.set('playRate', playRate);
    $('#pSpeed').textContent = `${playRate}×`;
  });

  // اختصارات لوحة المفاتيح أثناء التلاوة (لا تتعارض مع الكتابة في الحقول)
  document.addEventListener('keydown', (e) => {
    if (!play.active || e.ctrlKey || e.metaKey || e.altKey) return;
    const tag = (e.target && e.target.tagName) || '';
    if (/INPUT|TEXTAREA|SELECT/.test(tag) || e.target?.isContentEditable) return;
    if (e.code === 'Space') {
      e.preventDefault();
      $('#pToggle').click();
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const delta = e.key === 'ArrowRight' ? 5 : -5;
      if (Number.isFinite(audio.duration)) audio.currentTime = Math.max(0, Math.min(audio.duration, audio.currentTime + delta));
    }
  });

  if ('mediaSession' in navigator) {
    const handlers = {
      play: () => audio.play().catch(() => {}),
      pause: () => audio.pause(),
      stop: stopPlayback,
      previoustrack: async () => { if (play.active && play.cur) playAyah(await play.prevFn(play.cur).catch(() => null)); },
      nexttrack: async () => { if (play.active && play.cur) playAyah(await play.nextFn(play.cur).catch(() => null)); },
    };
    Object.entries(handlers).forEach(([action, fn]) => {
      try { navigator.mediaSession.setActionHandler(action, fn); } catch { /* غير مدعوم */ }
    });
  }

  $('#pToggle').addEventListener('click', () => {
    if (!play.active) return;
    if (audio.paused) audio.play().catch(() => toast('تعذر استئناف التلاوة'));
    else audio.pause();
  });
  $('#pNext').addEventListener('click', async () => {
    if (!play.active || !play.cur) return;
    playAyah(await play.nextFn(play.cur).catch(() => null));
  });
  $('#pPrev').addEventListener('click', async () => {
    if (!play.active || !play.cur) return;
    playAyah(await play.prevFn(play.cur).catch(() => null));
  });
  $('#pStop').addEventListener('click', stopPlayback);

  $('#btnPlaySurah').addEventListener('click', async () => {
    const button = $('#btnPlaySurah');
    const n = Number($('#playFrom').value) || 1;
    const s = Number($('#playSurah').value) || state.selSurah;
    button.disabled = true;
    $('.reader-play-label').textContent = 'جارٍ التحضير…';
    try {
      await startSurahPlay(s, n);
    } catch {
      toast('تعذر بدء التلاوة');
    } finally {
      button.disabled = false;
      setPlayerUI();
    }
  });

  // ---------- الحفظ ----------
  async function fetchSurahForMemo(n) {
    // وضع الرواية: آيات الرواية نفسها من quran-riwayat.json (بترقيمها وصفحاتها)
    if (isRiw()) {
      await loadRiwaya(settings.riwaya);
      return (riwAll[settings.riwaya] || []).map((r, idx) => ({ r, idx })).filter((x) => x.r[0] === n).map(({ r, idx }) => ({
        s: n, n: r[1], g: 1000000 + idx, page: r[2],
        html: esc(clean(r[3])), audio: null, tafsir: '', tr: '',
      }));
    }
    const riwId = settings.riwaya;
    const recId = settings.reciter;
    const ids = [riwId, recId, settings.tafsir].filter(Boolean);
    if (settings.translation) ids.push(settings.translation);
    const json = await getJSON(`${API}/surah/${n}/editions/${ids.join(',')}`);
    const byId = {};
    json.data.forEach((ed) => { byId[ed.edition.identifier] = ed; });
    const base = byId[riwId];
    return base.ayahs.map((a, i) => ({
      s: n, n: a.numberInSurah, g: a.number, page: a.page,
      html: esc(clean(a.text)),
      audio: recId ? (byId[recId]?.ayahs[i]?.audio || null) : null,
      tafsir: byId[settings.tafsir]?.ayahs[i]?.text || '',
      tr: settings.translation ? (byId[settings.translation]?.ayahs[i]?.text || '') : '',
    }));
  }

  async function loadMemo() {
    const n = Number($('#memoSurah').value);
    const from = Math.max(1, parseInt($('#memoFrom').value, 10) || 1);
    const to = parseInt($('#memoTo').value, 10) || from;
    const box = $('#memoText');
    box.innerHTML = '<div class="muted">جارٍ التحميل...</div>';
    try {
      const all = await fetchSurahForMemo(n);
      const start = Math.min(from, all.length), end = Math.min(Math.max(to, start), all.length);
      memo.ayahs = all.slice(start - 1, end);
      memo.label = `حفظ ${surahNameShort(n)} ${start}-${end}`;
      memo.s = n; memo.start = start; memo.end = end;
      renderMemo();
    } catch {
      box.innerHTML = '<div class="muted">تعذر التحميل.</div>';
    }
  }

  // إخفاء الكلمات: اختيار ثابت لكل كلمة حتى لا تتغير عند إعادة العرض
  const MEMO_PCT = [0, 25, 50, 75, 100];
  function memoWordHidden(s, n, i, pct) {
    if (pct >= 100) return true;
    return ((i * 37 + n * 11 + s * 13) % 100) < pct;
  }
  function renderMemo() {
    const level = Number($('#memoLevel').value) || 0;
    const pct = MEMO_PCT[level];
    $('#memoText').innerHTML = memo.ayahs.map((a) => {
      if (pct === 0) {
        return `
      <div class="ayah ${memo.hidden ? 'hidden-text' : ''}" data-g="${a.g}">
        <span class="txt">${a.html}</span>
        <span class="end">${toArabicDigits(a.n)}</span>
      </div>`;
      }
      const words = plainAyah(a.html).split(' ').filter(Boolean);
      const html = words.map((w, i) => `<span class="mw-w ${memoWordHidden(a.s, a.n, i, pct) ? 'h' : ''}">${esc(w)}</span>`).join(' ');
      return `
      <div class="ayah" data-g="${a.g}">
        <span class="txt">${html}</span>
        <span class="end">${toArabicDigits(a.n)}</span>
      </div>`;
    }).join('') || '<div class="muted">حدد مقطعاً ثم اضغط تحميل.</div>';
  }
  $('#memoLevel').addEventListener('change', renderMemo);

  // المراجعة المتباعدة: كل مقطع يُحفظ يعود بعد يوم، ثم كلما أُتقن تتباعد المدة
  const MEMO_GAPS = [1, 3, 7, 14, 30, 60];
  const MEMO_PROG_KEY = 'memo-progress';
  const memoKey = (s, a, b) => `${s}:${a}-${b}`;
  const addDaysKey = (key, n) => { const d = new Date(key + 'T12:00:00'); d.setDate(d.getDate() + n); return dateKey(d); };
  function getMemoProgress() { return store.get(MEMO_PROG_KEY, {}); }
  function saveMemoProgress(p) { store.set(MEMO_PROG_KEY, p); }

  $('#btnMemoSaved').addEventListener('click', () => {
    if (!memo.ayahs.length || !memo.s) return toast('حمّل المقطع أولاً');
    const prog = getMemoProgress();
    const k = memoKey(memo.s, memo.start, memo.end);
    if (!prog[k]) prog[k] = { s: memo.s, from: memo.start, to: memo.end, step: 0, due: addDaysKey(todayKey(), 1) };
    saveMemoProgress(prog);
    smartRecord({
      type: 'START_MEMORIZATION', service: 'memorization',
      context: { count: memo.ayahs.length, source: 'memo' },
    });
    toast('سيعود المقطع للمراجعة غداً');
    renderMemoReview();
  });

  function renderMemoReview() {
    const prog = getMemoProgress();
    const today = todayKey();
    const items = Object.entries(prog).map(([k, v]) => ({ k, ...v }));
    const due = items.filter((x) => x.due <= today).sort((a, b) => a.due.localeCompare(b.due));
    const later = items.length - due.length;
    const rows = due.map((x) => `
      <div class="wird-line" data-k="${esc(x.k)}">
        <span>${esc(surahNameShort(x.s))} ${toArabicDigits(x.from)}-${toArabicDigits(x.to)}</span>
        <span class="row">
          <button class="btn small" data-act="ok">أتقنتها</button>
          <button class="btn small ghost" data-act="again">أعيدها</button>
          <button class="btn small ghost" data-act="open">فتح</button>
        </span>
      </div>`).join('');
    $('#memoDue').innerHTML = due.length
      ? rows + (later ? `<div style="margin-top:8px">مراجعات قادمة: ${toArabicDigits(later)}</div>` : '')
      : (items.length ? `لا توجد مراجعة اليوم. المراجعات القادمة: ${toArabicDigits(later)}` : 'لم تُحفظ مقاطع بعد. بعد الحفظ اضغط "حفظت هذا المقطع".');
  }
  $('#memoDue').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const row = btn.closest('[data-k]');
    const prog = getMemoProgress();
    const item = prog[row.dataset.k];
    if (!item) return;
    if (btn.dataset.act === 'ok') {
      item.step = Math.min(MEMO_GAPS.length - 1, (item.step || 0) + 1);
      item.due = addDaysKey(todayKey(), MEMO_GAPS[item.step]);
      saveMemoProgress(prog);
      smartRecord({
        type: 'COMPLETE_MEMORIZATION', service: 'memorization',
        context: { count: Math.max(1, Number(item.to) - Number(item.from) + 1), source: 'mastered' },
      });
      renderMemoReview();
    } else if (btn.dataset.act === 'again') {
      item.step = 0;
      item.due = addDaysKey(todayKey(), 1);
      saveMemoProgress(prog);
      smartRecord({
        type: 'COMPLETE_MEMORIZATION', service: 'memorization',
        context: { count: Math.max(1, Number(item.to) - Number(item.from) + 1), source: 'repeat' },
      });
      renderMemoReview();
    } else if (btn.dataset.act === 'open') {
      $('#memoSurah').value = String(item.s);
      $('#memoFrom').value = String(item.from);
      $('#memoTo').value = String(item.to);
      loadMemo();
    }
  });
  $('#memoText').addEventListener('click', (e) => {
    const w = e.target.closest('.mw-w.h');
    if (w) { w.classList.toggle('shown'); return; }
  });
  $('#btnMemoLoad').addEventListener('click', loadMemo);
  $('#btnMemoHide').addEventListener('click', () => { memo.hidden = !memo.hidden; renderMemo(); });
  $('#btnMemoPlay').addEventListener('click', () => {
    if (!memo.ayahs.length) return toast('حمّل المقطع أولاً');
    startListPlay(memo.ayahs, memo.label, Number($('#memoRepeat').value));
  });
  $('#memoText').addEventListener('click', (e) => {
    const ayah = e.target.closest('.ayah');
    if (ayah && memo.hidden) ayah.classList.toggle('hidden-text');
  });

  // ---------- العلامات وآخر موضع ----------
  const getBookmarks = () => store.get('bookmarks', []);
  const isBookmarked = (s, a) => getBookmarks().some((b) => b.s === s && b.a === a);
  function toggleBookmark(s, a, name) {
    let list = getBookmarks();
    if (isBookmarked(s, a)) {
      list = list.filter((b) => !(b.s === s && b.a === a));
      toast('أزيلت العلامة');
    } else {
      list.push({ s, a, name });
      toast('تمت إضافة العلامة');
    }
    store.set('bookmarks', list);
  }

  function renderBookmarks() {
    const list = getBookmarks();
    $('#bookmarkList').innerHTML = list.length ? list.map((b) => `
      <div class="row" style="justify-content:space-between;margin:6px 0">
        <span>${esc(b.name)} - الآية ${b.a}</span>
        <button class="btn small" data-go-s="${b.s}" data-go-a="${b.a}">فتح</button>
      </div>`).join('') : '<div class="muted">لا توجد علامات بعد.</div>';
  }
  $('#bookmarkList').addEventListener('click', (e) => {
    const b = e.target.closest('[data-go-s]');
    if (b) { goToAyah(Number(b.dataset.goS), Number(b.dataset.goA)); showView('reader'); }
  });

  function renderLast() {
    const last = getLast();
    if (!last) return;
    $('#lastRead').innerHTML = `<div class="row" style="justify-content:space-between">
      <span>${esc(surahName(last.s))} - الآية ${last.a} - صفحة ${toArabicDigits(last.p || '')}</span>
      <button class="btn small" id="btnGoLast">متابعة</button></div>`;
  }
  $('#lastRead').addEventListener('click', (e) => {
    if (!e.target.closest('#btnGoLast')) return;
    const last = getLast();
    if (last && last.p) { showView('reader'); showPage(last.p, { selG: last.g, save: false, scroll: true }); }
  });

  // ---------- الإعدادات ----------
  // قائمة القراء تتبع الرواية: ورش تعرض قراء ورش فقط، وحفص تعرض قراء حفص
  function syncReciters() {
    const list = isRiw() ? RIW_RECITERS[settings.riwaya] : RECITERS;
    if (!list || !list.some(([id]) => id === settings.reciter)) settings.reciter = list ? list[0][0] : DEFAULTS.reciter;
    const opts = list.map(([id, name]) => `<option value=\"${id}\">${name}</option>`).join('');
    $('#setReciter').innerHTML = opts;
    $('#playReciter').innerHTML = opts;
    $('#setReciter').value = settings.reciter;
    $('#playReciter').value = settings.reciter;
  }

  function syncTajweedScopeSelector() {
    const row = $('#setTajweedScopeRow');
    const select = $('#setTajweedScope');
    const note = $('#setTajweedScopeNote');
    const candidates = TajweedCurriculumLoaderAPI ? tajweedCurriculaForSetting() : [];
    const shouldShow = candidates.length > 1 || candidates.some((item) => item.display);
    row.hidden = !shouldShow;
    if (!shouldShow) {
      select.innerHTML = '';
      note.textContent = '';
      return;
    }
    const selectedKey = candidates.length === 1
      ? TajweedCurriculumLoaderAPI.scopeKey(candidates[0].scope)
      : (settings.tajweedScopes[settings.riwaya] || '');
    const placeholder = candidates.length > 1
      ? '<option value="">اختر الطريق والوجه والطبعة…</option>' : '';
    select.innerHTML = placeholder + candidates.map((curriculum) => {
      const key = TajweedCurriculumLoaderAPI.scopeKey(curriculum.scope);
      const stateLabel = curriculum.status === 'APPROVED' ? 'مراجع علميًا' : 'قيد المراجعة';
      return `<option value="${esc(key)}">${esc(curriculumScopeLabel(curriculum))} — ${stateLabel}</option>`;
    }).join('');
    select.disabled = candidates.length === 1;
    select.value = selectedKey;
    const selected = candidates.find((curriculum) =>
      TajweedCurriculumLoaderAPI.scopeKey(curriculum.scope) === selectedKey);
    note.textContent = selected
      ? `${selected.displayName}؛ لا يختلط تقدمها أو علاماتها بأي طريق أو وجه آخر.`
      : 'يلزم اختيار نطاق كامل قبل عرض التعلم أو ألوان التجويد.';
  }

  function tafsirOptionsHtml() {
    // كل كتب التفسير في قائمة واحدة، كلها متاحة: الخمسة الأساسية من الشبكة،
    // وباقي الكتب تُجهَّز عند اختيارها لمرة واحدة ثم تُقرأ من الجهاز بلا إنترنت.
    return TAFSIRS.map(([id, name]) => `<option value="${id}">${name}</option>`).join('');
  }
  function fillSettings() {
    $('#setRiwaya').value = settings.riwaya;
    syncReciters();
    syncTajweedScopeSelector();
    $('#setTafsir').innerHTML = tafsirOptionsHtml();
    $('#setTafsir').value = settings.tafsir;
    $('#setTranslation').value = settings.translation;
    $('#tfBook').innerHTML = $('#setTafsir').innerHTML;
    $('#tfBook').value = settings.tafsir;
    $('#tfTrans').innerHTML = $('#setTranslation').innerHTML;
    $('#tfTrans').value = settings.translation;
    $('#setFont').value = settings.font;
    $('#setSize').value = settings.size;
    $('#sizeVal').textContent = settings.size + 'px';
    if ($('#setTajweed')) $('#setTajweed').checked = !!settings.tajweed;
    fillSmartSettings();
    applyTypography();
    syncFontControl();
  }
  function applyTypography() {
    document.documentElement.style.setProperty('--quran-size', settings.size + 'px');
    document.documentElement.style.setProperty('--quran-font', `"${settings.font}"`);
  }

  function onSettingChange(key, value) {
    settings[key] = value;
    if (key === 'riwaya') {
      syncReciters();
      syncTajweedScopeSelector();
    }
    saveSettings();
    document.body.classList.toggle('riw', isRiw());
    syncReaderLayout();
    if (key === 'reciter') { $('#setReciter').value = value; $('#playReciter').value = value; }
    if (key === 'tafsir') { $('#setTafsir').value = value; $('#tfBook').value = value; }
    if (key === 'translation') { $('#setTranslation').value = value; $('#tfTrans').value = value; }
    if (key === 'riwaya' && curView === 'tajweed') renderTajweedView();
    if (key === 'tajweed' && value && isRiw() && !currentApprovedTajweedCurriculum()) {
      toast('لا توجد طبقة ألوان معتمدة لهذا النطاق؛ سيبقى نص المصحف بلا تلوين.');
    }
    pageCache.clear();
    if (state.sel) {
      showPage(state.page, { selG: state.sel.g, save: false }).then(() => {
        if ($('#view-tafsir').classList.contains('active')) renderTafsirView();
      });
    }
  }
  $('#setRiwaya').addEventListener('change', (e) => onSettingChange('riwaya', e.target.value));
  $('#setTajweedScope').addEventListener('change', (e) => {
    const selectedKey = e.target.value;
    const valid = tajweedCurriculaForSetting().some((curriculum) => TajweedCurriculumLoaderAPI
      && TajweedCurriculumLoaderAPI.scopeKey(curriculum.scope) === selectedKey);
    if (valid) settings.tajweedScopes[settings.riwaya] = selectedKey;
    else delete settings.tajweedScopes[settings.riwaya];
    saveSettings();
    syncTajweedScopeSelector();
    pageCache.clear();
    if (curView === 'tajweed') renderTajweedView();
    if (settings.tajweed && isRiw() && !currentApprovedTajweedCurriculum()) {
      toast('هذا النطاق غير معتمد للألوان بعد؛ سيبقى نص المصحف بلا تلوين.');
    }
    if (state.sel) showPage(state.page, { selG: state.sel.g, save: false });
  });
  $('#setReciter').addEventListener('change', (e) => onSettingChange('reciter', e.target.value));
  $('#setTafsir').addEventListener('change', (e) => onSettingChange('tafsir', e.target.value));
  $('#setTranslation').addEventListener('change', (e) => onSettingChange('translation', e.target.value));
  if ($('#setTajweed')) $('#setTajweed').addEventListener('change', (e) => onSettingChange('tajweed', e.target.checked));
  $('#setFont').addEventListener('change', (e) => {
    settings.font = e.target.value;
    saveSettings();
    applyTypography();
  });
  $('#setSize').addEventListener('input', (e) => {
    setFontSize(e.target.value);
    $('#sizeVal').textContent = (Number(settings.size) || HAFS_BASE_SIZE) + 'px';
    applyTypography();
  });

  // ---------- التحميل للاستماع بدون إنترنت ----------
  // ---------- تحديث التطبيق من GitHub (بدون إعادة تحزيم) ----------
  const UPDATE_KEY = 'quran-update';
  const UPDATE_BASE = 'https://raw.githubusercontent.com/mosalah30688-gif/quran/main/update/';
  const storedUpdate = () => { try { return JSON.parse(localStorage.getItem(UPDATE_KEY) || 'null'); } catch (e) { return null; } };
  // رقم الإصدار الظاهر ثابت (1.0.0) بين التحديثات الصغيرة، والمعيار الفعلي هو رقم البناء.
  const currentVersion = () => window.SIRAJ_UPDATE_VERSION || window.APP_BUNDLE_VERSION || '1.0.0';
  const currentBuild = () => Number(window.APP_BUILD_NUMBER) || 0;

  // رقم بناء الـAPK المثبَّت (لا رقم بناء الواجهة): التحديث الداخلي قد يرفع رقم الواجهة
  // فوق رقم الـAPK، فيظن التطبيق أنه أحدث من الملف ولا يعرض ترقيته أبدًا.
  let apkNativeCode = 0;
  function installedApkCode() {
    return apkNativeCode > 0 ? apkNativeCode : currentBuild();
  }
  function resolveApkCode() {
    if (!hasNativePlugin('ApkUpdater')) return Promise.resolve(apkNativeCode);
    return nativeCall('ApkUpdater', 'getVersion')
      .then((r) => {
        const code = Number(r && r.code);
        if (Number.isFinite(code) && code > 0) apkNativeCode = code;
        return apkNativeCode;
      })
      .catch(() => apkNativeCode);
  }
  function renderUpdateCard() {
    $('#verVal').textContent = window.APP_BUNDLE_VERSION || '1.0.0';
    if ($('#buildVal')) $('#buildVal').textContent = `بناء ${toArabicDigits(currentBuild())}`;
    $('#btnRestore').hidden = !storedUpdate();
    if (hasNativePlugin('ApkUpdater')) {
      nativeCall('ApkUpdater', 'getVersion').then((r) => {
        if (r?.version) $('#verVal').textContent = r.version;
      }).catch(() => {});
    }
  }
  // مقارنة أرقام الإصدارات: 1.0.10 أحدث من 1.0.9
  function newerVersion(a, b) {
    const pa = String(a).split('.').map(Number), pb = String(b).split('.').map(Number);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
      const x = pa[i] || 0, y = pb[i] || 0;
      if (x !== y) return x > y;
    }
    return false;
  }

  function validUpdateManifestFiles(files) {
    if (!Array.isArray(files) || !files.includes('index.html') || !files.includes('app.js')
        || files.length > 128 || new Set(files).size !== files.length) return false;
    return files.every((name) => safeLocalAssetName(name) === name);
  }

  async function verifyDownloadedUpdateFile(name, text, hashes) {
    const hasHashManifest = hashes && typeof hashes === 'object' && !Array.isArray(hashes);
    const expected = hasHashManifest && typeof hashes[name] === 'string' ? hashes[name] : '';
    const isData = name.endsWith('.json');
    if ((isData || hasHashManifest) && !/^[0-9a-f]{64}$/.test(expected)) {
      throw new Error('missing update hash');
    }
    if (!expected) return;
    if (!TajweedCurriculumLoaderAPI) {
      throw new Error('bad update hash');
    }
    const actual = await TajweedCurriculumLoaderAPI.sha256Text(text);
    if (actual !== expected) throw new Error('update hash mismatch');
  }

  // نسخة كاملة (APK): تُنزَّل وتُفتح نافذة التثبيت عند المستخدم
  async function installNewApk(apk, st) {
    const perm = await nativeCall('ApkUpdater', 'canInstall');
    if (!perm || !perm.allowed) {
      await nativeCall('ApkUpdater', 'openInstallPermission');
      st.textContent = 'اسمح بالتثبيت من هذا التطبيق، ثم اضغط التحديث مرة أخرى.';
      return;
    }
    st.textContent = 'جاري تنزيل الإصدار ' + apk.version + '...';
    // النسخة الكاملة تحمل واجهتها، فنزيل التحديث الداخلي السابق حتى لا يغطي عليها
    localStorage.removeItem(UPDATE_KEY);
    localStorage.removeItem('quran-update-pending');
    await clearUpdateDataAssets();
    await nativeCall('ApkUpdater', 'downloadAndInstall', { url: apk.url, sha256: apk.sha256 || '' });
    st.textContent = 'اضغط تثبيت في النافذة لإكمال التحديث.';
  }

  async function checkForUpdate() {
    const btn = $('#btnUpdate'), st = $('#updStatus');
    btn.disabled = true;
    st.textContent = 'جاري البحث عن تحديث...';
    try {
      const mres = await fetch(UPDATE_BASE + 'manifest.json?t=' + Date.now(), { cache: 'no-store' });
      if (!mres.ok) throw new Error('manifest');
      const manifest = await mres.json();
      if (!manifest.version || !validUpdateManifestFiles(manifest.files)) throw new Error('bad manifest');
      const manifestBuild = Number(manifest.build) || 0;
      // نسخة كاملة أحدث على الهاتف؟ تُثبَّت بدل تحديث الواجهة وحدها
      if (manifest.apk && manifest.apk.url && manifest.apk.version && hasNativePlugin('ApkUpdater')) {
        const apkCode = Number(manifest.apk.code) || 0;
        await resolveApkCode();
        if (apkCode && apkCode > installedApkCode()) {
          await installNewApk(manifest.apk, st);
          btn.disabled = false;
          return;
        }
      }
      // لا نطبّق ترقية واجهة مساوية أو أقدم من النسخة المضمّنة؛ هذا يمنع الرجوع إلى إصدار قديم.
      if (!(manifestBuild > currentBuild())) {
        st.textContent = 'أنت على أحدث نسخة (' + window.APP_BUNDLE_VERSION + ' · بناء ' + toArabicDigits(currentBuild()) + ')';
        btn.disabled = false;
        return;
      }
      st.textContent = 'جاري تنزيل التحديث (بناء ' + toArabicDigits(manifestBuild) + ')…';
      const shellFiles = Object.create(null);
      const dataFiles = Object.create(null);
      for (const f of manifest.files) {
        const r = await fetch(UPDATE_BASE + f + '?t=' + Date.now(), { cache: 'no-store' });
        if (!r.ok) throw new Error('file ' + f);
        const txt = await r.text();
        if (!txt.trim()) throw new Error('empty ' + f);
        await verifyDownloadedUpdateFile(f, txt, manifest.sha256);
        if (f.endsWith('.json')) dataFiles[f] = txt;
        else shellFiles[f] = txt;
      }
      await replaceUpdateDataAssets(manifest.version, dataFiles);
      localStorage.setItem(UPDATE_KEY, JSON.stringify({
        version: manifest.version,
        build: manifestBuild,
        files: shellFiles,
        dataFiles: Object.keys(dataFiles),
      }));
      st.textContent = 'تم التنزيل والتحقق، جاري تطبيق التحديث...';
      setTimeout(() => location.reload(), 400);
    } catch (e) {
      st.textContent = 'تعذّر التحديث. تأكد من الاتصال بالإنترنت وحاول مرة أخرى.';
      btn.disabled = false;
    }
  }
  $('#btnUpdate').addEventListener('click', checkForUpdate);
  $('#btnRestore').addEventListener('click', async () => {
    localStorage.removeItem(UPDATE_KEY);
    localStorage.removeItem('quran-update-pending');
    await clearUpdateDataAssets();
    location.reload();
  });
  renderUpdateCard();

  // ---------- المواقيت والأذان والقبلة ----------
  if (window.SirajPrayerUI) {
    try {
      window.SirajPrayerUI.init({ toast, onNavigate: showView });
    } catch (e) {
      console.warn('prayer ui init failed', e);
    }
  }

  function publicUpdateFeatures(manifest) {
    const technicalTerms = ['ed25519', 'sha-256', 'sha256', 'runtime', 'appimage', 'portable', 'ترقيع', 'توقيع', 'موقّع', 'حزمة', 'محرك'];
    return (Array.isArray(manifest?.features) ? manifest.features : []).slice(0, 5).map((item) => (
      typeof item === 'string' ? item.trim().replace(/\s+/g, ' ') : ''
    )).filter((item, index, items) => (
      item && item.length <= 120 && items.indexOf(item) === index
      && !technicalTerms.some((term) => item.toLocaleLowerCase('ar').includes(term))
    ));
  }

  // فحص هادئ عند فتح التطبيق: يظهر الإصدار ثم الميزات الجديدة فقط، بلا تفاصيل فنية.
  async function silentUpdateCheck() {
    try {
      const mres = await fetch(UPDATE_BASE + 'manifest.json?t=' + Date.now(), { cache: 'no-store' });
      if (!mres.ok) return;
      const m = await mres.json();
      let availableVersion = '';
      if (m.apk?.url && m.apk?.version && hasNativePlugin('ApkUpdater')) {
        const apkCode = Number(m.apk.code) || 0;
        await resolveApkCode();
        if (apkCode && apkCode > installedApkCode()) availableVersion = m.apk.version;
      }
      if (!availableVersion && m.build && Number(m.build) > currentBuild()) {
        availableVersion = m.version;
      }
      const features = publicUpdateFeatures(m);
      if (!availableVersion || !features.length) return;
      $('#updBannerText').textContent = 'يتوفر تحديث جديد لسراج — الإصدار ' + availableVersion
        + '\nالجديد:' + features.map((feature) => '\n• ' + feature).join('');
      $('#updBannerBtn').onclick = () => { $('#updBanner').hidden = true; showView('settings'); checkForUpdate(); };
      $('#updBannerX').onclick = () => { $('#updBanner').hidden = true; };
      $('#updBanner').hidden = false;
    } catch (e) { /* بلا إنترنت أو بلا ملف: نتجاهل بهدوء */ }
  }
  silentUpdateCheck();

  // ---------- تنزيل مكتبة التفاسير الكاملة (اختياري، خارج الـ APK) ----------
  const formatBytes = (n) => {
    const value = Number(n) || 0;
    if (value >= 1024 ** 3) return (value / 1024 ** 3).toFixed(1) + ' ج.ب';
    if (value >= 1024 ** 2) return (value / 1024 ** 2).toFixed(0) + ' م.ب';
    return (value / 1024).toFixed(0) + ' ك.ب';
  };
  // تنزيل اختياري مرة واحدة لمكتبة التفاسير كاملة، ثم تعمل دون إنترنت.
  function renderTafsirPackStatus() {
    const card = $('#tfPackCard');
    if (!card) return;
    if (!tafsirPack.supported) { card.hidden = true; return; }
    card.hidden = false;
    const percent = tafsirPack.total ? Math.min(100, (tafsirPack.bytes / tafsirPack.total) * 100) : 0;
    if ($('#tfPackFill')) $('#tfPackFill').style.width = `${tafsirPack.ready ? 100 : percent}%`;
    if ($('#tfPackStatus')) {
      $('#tfPackStatus').textContent = tafsirPack.ready
        ? 'حزمة التفاسير جاهزة على جهازك، وكل الطبعات تعمل دون إنترنت.'
        : tafsirPack.downloading
          ? `جاري التنزيل: ${formatBytes(tafsirPack.bytes)} من ${formatBytes(tafsirPack.total)} (${Math.round(percent)}٪) — يمكنك المتابعة داخل التطبيق.`
          : `لم تُنزَّل بعد. الحجم ${formatBytes(tafsirPack.total)}، ويُستحسن اتصال Wi‑Fi ومساحة كافية.`;
    }
    if ($('#tfPackBtn')) {
      $('#tfPackBtn').hidden = tafsirPack.ready;
      $('#tfPackBtn').disabled = tafsirPack.downloading;
      $('#tfPackBtn').textContent = tafsirPack.downloading ? 'جاري التنزيل…' : 'نزّل حزمة التفاسير';
    }
    if ($('#tfPackCancel')) $('#tfPackCancel').hidden = !tafsirPack.downloading;
    if ($('#tfPackDelete')) $('#tfPackDelete').hidden = !tafsirPack.ready;
  }

  let tafsirPackPoll = null;
  async function startTafsirPackDownload() {
    const plugin = getTafsirNative();
    if (!plugin) return;
    toast('بدأ تنزيل حزمة التفاسير؛ يمكنك استخدام التطبيق أثناء التنزيل.');
    plugin.download().catch(() => {});
    if (tafsirPackPoll) clearInterval(tafsirPackPoll);
    tafsirPackPoll = setInterval(() => {
      plugin.status().then((status) => {
        tafsirPack = {
          supported: true,
          ready: !!status.ready,
          downloading: !!status.downloading,
          bytes: Number(status.bytes) || 0,
          total: Number(status.total) || 0,
          freeBytes: Number(status.freeBytes) || 0,
        };
        renderTafsirPackStatus();
        if (tafsirPack.ready || !tafsirPack.downloading) {
          clearInterval(tafsirPackPoll);
          tafsirPackPoll = null;
          pageCache.clear();
          fillSettings();
          if (tafsirPack.ready) toast('تم تنزيل حزمة التفاسير. اختر أي كتاب من القائمة.');
        }
      }).catch(() => {});
    }, 2000);
  }
  async function cancelTafsirPackDownload() {
    const plugin = getTafsirNative();
    if (plugin) { try { await plugin.cancel(); } catch { /* تجاهل */ } }
    toast('أُوقف التنزيل؛ ما نُزّل محفوظ ويُستكمل لاحقًا.');
    refreshTafsirPackStatus();
  }
  async function deleteTafsirPack() {
    const plugin = getTafsirNative();
    if (plugin) { try { await plugin.delete(); } catch { /* تجاهل */ } }
    settings.tafsir = DEFAULTS.tafsir;
    saveSettings();
    await refreshTafsirPackStatus();
    toast('حُذفت حزمة التفاسير من الجهاز.');
  }
  async function refreshTafsirPackStatus() {
    const plugin = getTafsirNative();
    if (!plugin) {
      tafsirPack = { ready: false, downloading: false, bytes: 0, total: 0, freeBytes: 0, supported: false };
      renderTafsirPackStatus();
      fillSettings();
      return;
    }
    try {
      const status = await plugin.status();
      tafsirPack = {
        supported: true,
        ready: !!status.ready,
        downloading: !!status.downloading,
        bytes: Number(status.bytes) || 0,
        total: Number(status.total) || 0,
        freeBytes: Number(status.freeBytes) || 0,
      };
    } catch {
      tafsirPack = { supported: true, ready: false, downloading: false, bytes: 0, total: 0, freeBytes: 0 };
    }
    pageCache.clear();
    renderTafsirPackStatus();
    fillSettings();
  }

  // مصدر تنزيل حفص هو CDN المعلن لخدمة AlQuran Cloud / Islamic Network؛ القيمة معدل البت لكل طبعة.
  const OFFLINE_SRC = {
    'ar.alafasy': 128,
    'ar.abdurrahmaansudais': 192,
    'ar.mahermuaiqly': 128,
    'ar.husary': 128,
    'ar.husarymujawwad': 128,
    'ar.hudhaify': 128,
    'ar.shaatree': 128,
    'ar.abdulsamad': 64,
    'ar.saoodshuraym': 64,
    'ar.muhammadayyoub': 128,
    'ar.muhammadjibreel': 128,
    'ar.abdullahbasfar': 64,
    'ar.ahmedajamy': 128,
    'ar.hanirifai': 192,
    'ar.ibrahimakhbar': 32,
    'ar.aymanswoaid': 64,
    'ar.parhizgar': 48,
  };
  const IDB_NAME = 'quran-offline';
  let dbPromise = null;
  let objUrl = null;
  const dl = { running: false, cancel: false };

  function openDB() {
    if (!dbPromise) {
      dbPromise = new Promise((res, rej) => {
        const r = indexedDB.open(IDB_NAME, 1);
        r.onupgradeneeded = () => { r.result.createObjectStore('audio'); r.result.createObjectStore('meta'); };
        r.onsuccess = () => res(r.result);
        r.onerror = () => rej(r.error);
      });
    }
    return dbPromise;
  }
  async function idbReq(store, mode, fn) {
    const d = await openDB();
    return new Promise((res, rej) => {
      const t = d.transaction(store, mode);
      const req = fn(t.objectStore(store));
      t.oncomplete = () => res(req ? req.result : undefined);
      t.onerror = () => rej(t.error);
    });
  }
  const idbGet = (store, key) => idbReq(store, 'readonly', (st) => st.get(key));
  const idbPut = (store, key, val) => idbReq(store, 'readwrite', (st) => st.put(val, key));
  const idbDel = (store, key) => idbReq(store, 'readwrite', (st) => st.delete(key));
  const idbKeys = (store) => idbReq(store, 'readonly', (st) => st.getAllKeys());

  const audioKey = (reciter, s, n) => `${reciter}|${s}|${n}`;
  const pad3 = (x) => String(x).padStart(3, '0');
  const folderSupported = () => hasNativePlugin('FolderPicker') || typeof window.showDirectoryPicker === 'function';

  async function getDirHandle() {
    try { return (await idbGet('meta', 'dirHandle')) || null; } catch { return null; }
  }

  // رابط تشغيل محلي لآية محفوظة (من المجلد أولاً ثم من التخزين داخل التطبيق)
  async function localAudioUrl(reciter, s, n) {
    if (hasNativePlugin('FolderPicker')) {
      const uri = store.get('folderUri', null);
      if (uri) {
        try {
          const r = await nativeCall('FolderPicker', 'readFile', { uri, path: `${reciter}/${s}/${n}.mp3` });
          if (r && r.data) return URL.createObjectURL(base64ToBlob(r.data, 'audio/mpeg'));
        } catch { /* غير موجود في المجلد */ }
      }
    }
    const dir = await getDirHandle();
    if (dir && (await dir.queryPermission({ mode: 'read' })) === 'granted') {
      try {
        const sub = await (await dir.getDirectoryHandle(reciter)).getDirectoryHandle(String(s));
        const file = await (await sub.getFileHandle(`${n}.mp3`)).getFile();
        return URL.createObjectURL(file);
      } catch { /* غير موجود في المجلد */ }
    }
    const blob = await idbGet('audio', audioKey(reciter, s, n));
    return blob ? URL.createObjectURL(blob) : null;
  }

  async function hasLocal(target, root, reciter, s, n) {
    if (target === 'folder' && root && root.native) {
      try {
        const r = await nativeCall('FolderPicker', 'exists', { uri: root.uri, path: `${reciter}/${s}/${n}.mp3` });
        return !!(r && r.exists);
      } catch { return false; }
    }
    if (target === 'folder') {
      try {
        const sub = await (await root.getDirectoryHandle(reciter)).getDirectoryHandle(String(s));
        await sub.getFileHandle(`${n}.mp3`);
        return true;
      } catch { return false; }
    }
    return !!(await idbGet('audio', audioKey(reciter, s, n)));
  }

  async function saveToFolder(root, reciter, s, n, blob) {
    if (root && root.native) {
      const b64 = bytesToBase64(new Uint8Array(await blob.arrayBuffer()));
      await nativeCall('FolderPicker', 'writeFile', { uri: root.uri, path: `${reciter}/${s}/${n}.mp3`, data: b64 });
      return;
    }
    const sub = await (await root.getDirectoryHandle(reciter, { create: true })).getDirectoryHandle(String(s), { create: true });
    const fh = await sub.getFileHandle(`${n}.mp3`, { create: true });
    const w = await fh.createWritable();
    await w.write(blob);
    await w.close();
  }

  function selectedScope() {
    return document.querySelector('input[name=dlScope]:checked')?.value || 'full';
  }

  function refsForScope() {
    const nums = selectedScope() === 'full' ? surahs.map((x) => x.number) : [Number($('#dlSurahSel').value)];
    const refs = [];
    nums.forEach((s) => {
      const c = surahs[s - 1]?.numberOfAyahs || 0;
      for (let n = 1; n <= c; n++) refs.push({ s, n });
    });
    return refs;
  }

  function globalAyahNumber(s, n) {
    let number = n;
    for (let i = 0; i < s - 1; i++) number += Number(surahs[i]?.numberOfAyahs || 0);
    return number;
  }

  function updateEstimate() {
    const refs = refsForScope();
    const mb = refs.length * 0.1;
    const size = mb < 1 ? 'أقل من ميجابايت' : `نحو ${Math.round(mb)} ميجابايت`;
    const scopeTxt = selectedScope() === 'full' ? 'المصحف كاملاً' : `سورة ${surahNameShort(Number($('#dlSurahSel').value))}`;
    $('#dlEstimate').textContent = `${scopeTxt}: ${refs.length} آية، حجم تقريبي ${size}.`;
  }

  async function runDownload() {
    if (dl.running) return;
    const reciter = $('#dlReciter').value;
    const bitrate = OFFLINE_SRC[reciter];
    if (!bitrate) return toast('هذا القارئ غير متاح للتحميل');
    const target = $('#dlTarget').value;
    const refs = refsForScope();
    if (!refs.length) return;

    let root = null;
    if (target === 'folder') {
      if (!folderSupported()) return toast('مجلد الجهاز غير متاح هنا، اختر داخل التطبيق');
      if (hasNativePlugin('FolderPicker')) {
        let uri = store.get('folderUri', null);
        if (!uri) {
          try { const r = await nativeCall('FolderPicker', 'pickFolder'); uri = r && r.uri; } catch { uri = null; }
          if (!uri) return toast('لم يتم اختيار مجلد');
          store.set('folderUri', uri);
        }
        root = { native: true, uri };
      } else {
        root = await getDirHandle();
        try {
          if (!root) {
            root = await window.showDirectoryPicker({ mode: 'readwrite' });
            await idbPut('meta', 'dirHandle', root);
          }
          if ((await root.requestPermission({ mode: 'readwrite' })) !== 'granted') return toast('لم يُمنح إذن الكتابة في المجلد');
        } catch { return toast('تم إلغاء اختيار المجلد'); }
      }
    } else if (navigator.storage?.persist) {
      navigator.storage.persist().catch(() => {});
    }

    dl.running = true; dl.cancel = false;
    $('#btnDownload').disabled = true;
    $('#btnCancelDl').disabled = false;
    const bar = $('#dlBar');
    bar.style.display = 'block'; bar.max = refs.length; bar.value = 0;

    const queue = refs.slice();
    let done = 0, saved = 0, skipped = 0, failed = 0;
    const update = () => {
      bar.value = done;
      $('#dlProgress').textContent = `${done} من ${refs.length} · محفوظ ${saved} · موجود ${skipped} · فشل ${failed}`;
    };
    const worker = async () => {
      while (queue.length && !dl.cancel) {
        const r = queue.shift();
        try {
          if (await hasLocal(target, root, reciter, r.s, r.n)) {
            skipped++;
          } else {
            const ayahNumber = globalAyahNumber(r.s, r.n);
            const res = await fetch(`https://cdn.islamic.network/quran/audio/${bitrate}/${reciter}/${ayahNumber}.mp3`);
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const blob = await res.blob();
            if (target === 'folder') await saveToFolder(root, reciter, r.s, r.n, blob);
            else await idbPut('audio', audioKey(reciter, r.s, r.n), blob);
            saved++;
          }
        } catch { failed++; }
        done++;
        update();
      }
    };
    update();
    await Promise.all(Array.from({ length: 6 }, worker));

    dl.running = false;
    $('#btnDownload').disabled = false;
    $('#btnCancelDl').disabled = true;
    toast(dl.cancel ? 'تم إيقاف التحميل' : 'انتهى التحميل');
    refreshStored();
  }

  async function refreshStored() {
    const reciter = $('#dlReciter').value;
    const keys = ((await idbKeys('audio').catch(() => [])) || []).filter((k) => k.startsWith(reciter + '|'));
    const perSurah = {};
    keys.forEach((k) => { const s = k.split('|')[1]; perSurah[s] = (perSurah[s] || 0) + 1; });
    const complete = Object.keys(perSurah).filter((s) => perSurah[s] >= (surahs[Number(s) - 1]?.numberOfAyahs || Infinity)).length;
    const dir = await getDirHandle();
    $('#dlStored').textContent = `داخل التطبيق: ${keys.length} آية، ${complete} سورة مكتملة لهذا القارئ.` +
      (dir ? ` المجلد المختار: ${dir.name}` : (store.get('folderUri', null) ? ' المجلد المختار على الجهاز.' : ''));
  }

  async function deleteAppAudio() {
    const reciter = $('#dlReciter').value;
    const keys = ((await idbKeys('audio').catch(() => [])) || []).filter((k) => k.startsWith(reciter + '|'));
    for (const k of keys) await idbDel('audio', k);
    toast(`حُذف ${keys.length} ملف من التطبيق`);
    refreshStored();
  }

  function setupDownloadUI() {
    const supported = Object.keys(OFFLINE_SRC);
    $('#dlReciter').innerHTML = RECITERS.filter(([id]) => supported.includes(id))
      .map(([id, name]) => `<option value="${id}">${name}</option>`).join('');
    $('#dlReciter').value = supported.includes(settings.reciter) ? settings.reciter : supported[0];
    $('#dlSurahSel').innerHTML = surahs.map((x) => `<option value="${x.number}">${x.number}. ${esc(x.name)}</option>`).join('');
    const folderOpt = $('#dlTarget option[value=folder]');
    if (folderOpt && !folderSupported()) folderOpt.remove();
    $('#dlNote').textContent = folderSupported()
      ? 'مجلد الجهاز يُختار مرة واحدة ويُحفظ، والملفات تُرتّب داخله: القارئ / رقم السورة / رقم الآية.'
      : '';
    updateEstimate();
    refreshStored();
  }

  $('#dlReciter').addEventListener('change', refreshStored);
  $('#dlSurahSel').addEventListener('change', updateEstimate);
  $$('input[name=dlScope]').forEach((r) => r.addEventListener('change', () => {
    $('#dlSurahSel').disabled = selectedScope() === 'full';
    updateEstimate();
  }));
  $('#btnDownload').addEventListener('click', runDownload);
  $('#btnCancelDl').addEventListener('click', () => { dl.cancel = true; });
  $('#btnDeleteDl').addEventListener('click', deleteAppAudio);

  try {
    const backListenerApp = getCapApp();
    if (backListenerApp && backListenerApp.addListener) {
      const r = backListenerApp.addListener('backButton', handleBack);
      if (r && r.catch) r.catch(() => {});
    }
  } catch { /* الإضافة غير موجودة في هذه النسخة، يبقى الرجوع الافتراضي */ }

  // ---------- البحث في القرآن (داخل التطبيق) ----------
  const SR_PAGE = 40;
  let srMatches = [];
  let srShown = 0;
  let srWords = [];
  let srIndex = null;
  const srEsc = (w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/[اأإآ]/g, '[اأإآ]').replace(/[يى]/g, '[يى]');
  // تجاهل التشكيل والتطويل، وتوحيد الألف والياء، ليتطابق البحث مع أي كتابة
  const srNorm = (x) => String(x || '')
    .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED\u0640\ufeff]/g, '')
    .replace(/[أإآٱ]/g, 'ا')
    .replace(/ى/g, 'ي');

  // فهرس الآيات يُحمَّل مرة واحدة عند أول بحث، ثم يعمل بدون اتصال
  async function loadSearchIndex() {
    if (srIndex) return srIndex;
    const j = await getJSON('quran-search.json');
    srIndex = j.ayahs.map(([s, a, t]) => ({ s, a, t, n: srNorm(t) }));
    return srIndex;
  }

  async function searchQuran(q) {
    const idx = await loadSearchIndex();
    const nq = srNorm(q);
    return idx.filter((x) => x.n.includes(nq));
  }

  async function runSearch() {
    const q = $('#srQuery').value.trim().replace(/\s+/g, ' ');
    if (q.length < 2) { toast('اكتب حرفين على الأقل'); return; }
    srWords = q.split(' ').filter(Boolean);
    $('#srInfo').textContent = 'جاري البحث...';
    $('#srResults').innerHTML = '';
    $('#srMoreRow').hidden = true;
    try {
      srMatches = await searchQuran(q);
    } catch {
      srMatches = [];
      $('#srInfo').textContent = 'تعذّر فتح البحث، حاول مرة أخرى.';
      return;
    }
    if (!srMatches.length) { $('#srInfo').textContent = 'لا توجد نتائج لهذه الكلمة.'; return; }
    $('#srInfo').textContent = 'عدد النتائج: ' + toArabicDigits(srMatches.length);
    srShown = 0;
    renderSearchMore();
  }

  function highlightWords(text) {
    const t = clean(text);
    if (!srWords.length) return esc(t);
    const re = new RegExp('(' + srWords.map(srEsc).join('|') + ')');
    return t.split(re).map((part, i) => (i % 2 ? '<mark class="sr-hit">' + esc(part) + '</mark>' : esc(part))).join('');
  }

  function renderSearchMore() {
    const chunk = srMatches.slice(srShown, srShown + SR_PAGE);
    $('#srResults').insertAdjacentHTML('beforeend', chunk.map((m) => `
      <div class="card sr-item" data-s="${m.s}" data-a="${m.a}">
        <div class="row" style="justify-content:space-between">
          <b>${esc(surahNameShort(m.s))}</b>
          <span class="muted">الآية ${toArabicDigits(m.a)}</span>
        </div>
        <div class="sr-text">${highlightWords(m.t)}</div>
      </div>`).join(''));
    srShown += chunk.length;
    const left = srMatches.length - srShown;
    $('#srMoreRow').hidden = left <= 0;
    $('#srMore').textContent = 'عرض المزيد (' + toArabicDigits(left) + ')';
  }

  $('#srBtn').addEventListener('click', runSearch);
  $('#srQuery').addEventListener('keydown', (e) => { if (e.key === 'Enter') runSearch(); });
  $('#srMore').addEventListener('click', renderSearchMore);
  $('#srResults').addEventListener('click', (e) => {
    const card = e.target.closest('.sr-item');
    if (!card) return;
    goToAyah(Number(card.dataset.s), Number(card.dataset.a));
    showView('reader');
  });

  // ---------- تعلم التجويد المحلي بالمراجعة المتباعدة ----------
  function currentTajweedRegistryEntry() {
    if (tajweedScopeRegistry?.fallbackPolicy !== 'FORBIDDEN_BETWEEN_SCOPES') return null;
    const entries = tajweedScopeRegistry?.settings;
    if (!Array.isArray(entries)) return null;
    return entries.find((entry) => Array.isArray(entry.settingIds)
      && entry.settingIds.includes(settings.riwaya)) || null;
  }

  function sameTajweedScope(left, right) {
    if (!TajweedLearningAPI) return false;
    const leftScope = TajweedLearningAPI.normalizeScope(left);
    const rightScope = TajweedLearningAPI.normalizeScope(right);
    return !!leftScope && !!rightScope
      && TajweedLearningAPI.scopeKey(leftScope) === TajweedLearningAPI.scopeKey(rightScope);
  }

  function tajweedCurriculaForSetting(settingId = settings.riwaya) {
    return Array.isArray(tajweedRuntimeCurricula)
      ? tajweedRuntimeCurricula.filter((item) => Array.isArray(item.appliesToSettings)
        && item.appliesToSettings.includes(settingId))
      : [];
  }

  function curriculumScopeLabel(curriculum) {
    if (curriculum?.display) {
      return `${curriculum.display.tariqAr} · ${curriculum.display.wajhAr} · ${curriculum.display.editionAr}`;
    }
    return curriculum?.displayName || '';
  }

  function currentTajweedCurriculum() {
    const entry = currentTajweedRegistryEntry();
    if (!entry || !Array.isArray(entry.curricula) || !Array.isArray(tajweedRuntimeCurricula)) return null;
    // لا نختار طريقًا أو وجهًا ضمنيًا عند تعدد الحزم.
    const candidate = TajweedCurriculumLoaderAPI?.selectCurriculum(
      tajweedRuntimeCurricula,
      settings.riwaya,
      settings.tajweedScopes[settings.riwaya] || '',
    );
    if (!candidate) return null;
    const pointer = entry.curricula.find((item) => item?.artifact === candidate.artifact
      && item.sha256 === candidate.artifactSha256
      && item.status === candidate.status
      && item.publishableAsApproved === candidate.publishableAsApproved
      && sameTajweedScope(item.scope, candidate.scope));
    return pointer ? candidate : null;
  }

  function currentApprovedTajweedCurriculum() {
    const curriculum = currentTajweedCurriculum();
    return curriculum?.status === 'APPROVED'
      && curriculum.publishableAsApproved === true
      && curriculum.annotationIndex instanceof Map
      ? curriculum : null;
  }

  function firstTajweedExample(code) {
    const escaped = String(code).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`\\[${escaped}(?::\\d+)?\\[([^\\[\\]]*)\\]`);
    for (const row of localTajweed) {
      const raw = clean(row[3]);
      const match = pattern.exec(raw);
      if (!match) continue;
      return {
        text: plainTajweed(match[1]).trim(),
        ayahText: plainTajweed(raw).trim(),
        surah: Number(row[0]),
        ayah: Number(row[1]),
      };
    }
    return null;
  }

  function buildTajweedLearningCards() {
    tajweedLearningCards = [];
    const curricula = tajweedRuntimeCurricula;
    if (!Array.isArray(curricula) || !TajweedLearningAPI) return;
    curricula.forEach((curriculum) => {
      const scope = TajweedLearningAPI.normalizeScope(curriculum.scope);
      if (!scope || !Array.isArray(curriculum.rules)) return;
      curriculum.rules.forEach((rule) => {
        const example = rule.example || (rule.tagCode ? firstTajweedExample(rule.tagCode) : null);
        const learning = rule.learning && typeof rule.learning === 'object' ? rule.learning : {};
        const category = /^[a-z0-9][a-z0-9_.-]*$/.test(learning.categoryId || '')
          ? learning.categoryId : 'general';
        const categoryName = typeof learning.categoryNameAr === 'string'
          && learning.categoryNameAr.trim() ? learning.categoryNameAr.trim() : 'أساسيات التجويد';
        const level = Math.min(3, Math.max(1, Number(learning.level) || 1));
        const baseOrder = (Number(rule.order) || 0) * 10;
        const shared = {
          baseId: rule.id,
          scope,
          name: rule.name,
          tagCode: typeof rule.tagCode === 'string' ? rule.tagCode : '',
          color: /^#[0-9A-Fa-f]{6}$/.test(rule.color || '') ? rule.color : '',
          example,
          category,
          categoryName,
          level,
          curriculumId: curriculum.id,
          reviewStatus: curriculum.status,
        };
        // نحافظ على معرّف البطاقة الأصلية كي لا يضيع تقدم المستخدمين الحاليين.
        tajweedLearningCards.push({
          ...shared,
          id: rule.id,
          order: baseOrder + 1,
          stage: 1,
          activityType: 'learn',
          prerequisites: [],
          prompt: rule.prompt,
          answer: rule.answer,
        });
        if (!example) return;
        tajweedLearningCards.push({
          ...shared,
          id: `${rule.id}.recognize`,
          order: baseOrder + 2,
          stage: 2,
          activityType: 'recognize',
          prerequisites: [rule.id],
          name: 'تمييز الحكم من المثال',
          prompt: 'ما الحكم التجويدي الملوّن في هذا المثال؟ اختر الإجابة ثم راجع الشرح.',
          answer: `الحكم هو «${rule.name}». ${rule.answer}`,
        });
        tajweedLearningCards.push({
          ...shared,
          id: `${rule.id}.apply`,
          order: baseOrder + 3,
          stage: 3,
          activityType: 'apply',
          prerequisites: [`${rule.id}.recognize`],
          name: `تطبيق «${rule.name}»`,
          prompt: `اقرأ المثال وطبّق حكم «${rule.name}»، ثم اشرح طريقة الأداء بصوتك قبل كشف الجواب.`,
          answer: rule.answer,
        });
      });
    });
  }

  function cardsForCurriculum(curriculum) {
    if (!curriculum || !TajweedLearningAPI) return [];
    const key = TajweedLearningAPI.scopeKey(curriculum.scope);
    return tajweedLearningCards.filter((card) => TajweedLearningAPI.scopeKey(card.scope) === key);
  }

  function coloredTajweedExample(card) {
    if (!card?.example) return '';
    const marker = card.color
      ? `style="color:${card.color}"`
      : `class="tj-${esc(card.tagCode)}"`;
    return `<span ${marker}>${esc(card.example.text)}</span>`;
  }

  function persistTajweedLearning() {
    if (tajweedLearningEngine) store.set(TAJWEED_LEARNING_KEY, tajweedLearningEngine.snapshot());
  }

  const TAJWEED_INTENSITY = Object.freeze({
    gentle: { newPerDay: 3, reviewsPerDay: 10 },
    balanced: { newPerDay: 5, reviewsPerDay: 20 },
    intensive: { newPerDay: 10, reviewsPerDay: 40 },
  });
  const TAJWEED_ACTIVITY_LABELS = Object.freeze({
    learn: 'تعلّم الحكم', recognize: 'تمييز من المثال', apply: 'تطبيق عملي',
  });

  function tajweedIntensityName() {
    if (!tajweedLearningEngine) return 'balanced';
    const config = tajweedLearningEngine.config;
    return Object.keys(TAJWEED_INTENSITY).find((name) => {
      const profile = TAJWEED_INTENSITY[name];
      return config.newPerDay === profile.newPerDay && config.reviewsPerDay === profile.reviewsPerDay;
    }) || 'balanced';
  }

  function tajweedPlanText(plan) {
    const counts = { weak: 0, due: 0, fresh: 0 };
    plan.forEach((item) => {
      if (item.reason === 'weak-review') counts.weak += 1;
      else if (item.kind === 'review') counts.due += 1;
      else counts.fresh += 1;
    });
    const parts = [];
    if (counts.weak) parts.push(`${toArabicDigits(counts.weak)} موضع يحتاج تثبيتًا`);
    if (counts.due) parts.push(`${toArabicDigits(counts.due)} مراجعة مستحقة`);
    if (counts.fresh) parts.push(`${toArabicDigits(counts.fresh)} نشاط جديد`);
    return parts.length
      ? `الخطة التكيفية: ${parts.join('، ')}. يبدأ سراج بالأضعف ثم المستحق ثم الجديد.`
      : 'لا توجد أنشطة مستحقة الآن؛ سيظهر النشاط التالي في موعده المحلي.';
  }

  function tajweedCategoryLabels(cards) {
    const labels = new Map();
    cards.forEach((card) => {
      if (!labels.has(card.category)) labels.set(card.category, card.categoryName || 'أساسيات التجويد');
    });
    return labels;
  }

  function renderTajweedView() {
    const registryEntry = currentTajweedRegistryEntry();
    const curriculum = currentTajweedCurriculum();
    const selectedLabel = $('#setRiwaya').selectedOptions[0]?.textContent || settings.riwaya;
    $('#tjLearningCard').hidden = true;
    if (!TajweedLearningAPI || !tajweedLearningEngine || !tajweedLearningCatalog || !tajweedScopeRegistry) {
      $('#tjLearningScope').textContent = selectedLabel;
      $('#tjLearningWarning').textContent = 'جارٍ تحميل طبقة التعلم المحلية…';
      $('#tjStartLearning').disabled = true;
      $('#tjList').innerHTML = '';
      return;
    }
    if (!curriculum) {
      const available = tajweedCurriculaForSetting();
      const needsScopeChoice = available.length > 1
        && !available.some((item) => TajweedLearningAPI
          && TajweedLearningAPI.scopeKey(item.scope) === settings.tajweedScopes[settings.riwaya]);
      const entryArtifacts = new Set((Array.isArray(registryEntry?.curricula)
        ? registryEntry.curricula : []).map((pointer) => pointer?.artifact).filter(Boolean));
      const hasUnloadedPointer = tajweedCurriculumLoadErrors.some((failure) =>
        entryArtifacts.has(failure.artifact));
      const blockedReason = needsScopeChoice
        ? 'توجد عدة طرق أو أوجه مستقلة؛ اختر النطاق الكامل من الإعدادات قبل بدء التعلم.'
        : (hasUnloadedPointer
          ? 'تعذّر التحقق من بصمة حزمة التجويد أو ربطها النصي؛ حُجبت الطبقة احترازيًا.'
          : (registryEntry?.blockedReasonAr
            || 'فشل التحقق من سجل نطاق التجويد؛ حُجبت الطبقة احترازيًا.'));
      $('#tjLearningScope').textContent = `${selectedLabel} · الطريق والوجه والطبعة: غير مثبتة`;
      $('#tjReviewBadge').textContent = registryEntry?.status === 'BLOCKED_NO_APPROVED_CORPUS'
        ? 'محجوب لغياب المصدر المعتمد' : 'محجوب احترازيًا';
      $('#tjLearningWarning').textContent = blockedReason;
      $('#tjDueCount').textContent = '٠';
      $('#tjLearningCount').textContent = '٠';
      $('#tjMatureCount').textContent = '٠';
      $('#tjAccuracy').textContent = '٠٪';
      $('#tjMastery').textContent = '٠٪';
      $('#tjWeakCount').textContent = '٠';
      $('#tjUnlockedCount').textContent = '٠';
      $('#tjPathProgress').textContent = '٠ من ٠ نشاط';
      $('#tjPathFill').style.width = '0%';
      $('#tjPlanExplanation').textContent = blockedReason;
      $('#tjWeakAreas').textContent = '';
      $('#tjIntensity').disabled = true;
      $('#tjStartLearning').disabled = true;
      $('#tjResetLearning').disabled = true;
      $('#tjSessionSummary').hidden = true;
      $('#tjLearningEmpty').textContent = 'يلزم مصدر مستقل يحدد الرواية والطريق والوجه والطبعة، ثم مراجعة بشرية مؤهلة واعتماد نشر ثانٍ.';
      $('#tjList').innerHTML = '<div class="muted">لا تُعرض أحكام حفص أو أي طبقة عامة بدلًا من نطاق هذا المصحف.</div>';
      return;
    }

    const cards = cardsForCurriculum(curriculum);
    const stats = tajweedLearningEngine.stats(curriculum.scope);
    const pathStats = tajweedLearningEngine.pathStats(cards, curriculum.scope);
    const plan = tajweedLearningEngine.plan(cards, curriculum.scope);
    const scopeId = TajweedLearningAPI.scopeKey(curriculum.scope);
    if ($('#tjSessionSummary').dataset.scope && $('#tjSessionSummary').dataset.scope !== scopeId) {
      $('#tjSessionSummary').hidden = true;
    }
    $('#tjLearningScope').textContent = curriculum.display
      ? `${curriculum.display.riwayahAr} · ${curriculum.display.tariqAr} · ${curriculum.display.wajhAr} · ${curriculum.display.editionAr}`
      : `${curriculum.displayName} · الطريق: ${curriculum.scope.tariq} · الوجه: ${curriculum.scope.wajh}`;
    $('#tjReviewBadge').textContent = curriculum.status === 'APPROVED'
      ? 'مراجع علميًا' : 'قيد المراجعة العلمية';
    $('#tjLearningWarning').textContent = curriculum.scopeWarning;
    $('#tjDueCount').textContent = toArabicDigits(stats.due);
    $('#tjLearningCount').textContent = toArabicDigits(pathStats.learning);
    $('#tjMatureCount').textContent = toArabicDigits(pathStats.mastered);
    $('#tjAccuracy').textContent = toArabicDigits(Math.round(stats.accuracy * 100)) + '٪';
    $('#tjMastery').textContent = toArabicDigits(Math.round(pathStats.mastery * 100)) + '٪';
    $('#tjWeakCount').textContent = toArabicDigits(pathStats.weak);
    $('#tjUnlockedCount').textContent = toArabicDigits(pathStats.unlocked);
    $('#tjPathProgress').textContent = `${toArabicDigits(pathStats.introduced)} من ${toArabicDigits(pathStats.total)} نشاط`;
    $('#tjPathFill').style.width = `${Math.round(pathStats.mastery * 100)}%`;
    $('#tjIntensity').disabled = false;
    $('#tjIntensity').value = tajweedIntensityName();
    $('#tjPlanExplanation').textContent = tajweedPlanText(plan);
    const categoryLabels = tajweedCategoryLabels(cards);
    const weakCategories = pathStats.categories.filter((category) => category.weak > 0);
    $('#tjWeakAreas').textContent = weakCategories.length
      ? `يحتاج تثبيتًا: ${weakCategories.map((category) => `${categoryLabels.get(category.id)} (${toArabicDigits(category.weak)})`).join('، ')}`
      : (pathStats.introduced ? 'لا توجد مجموعة ضعيفة الآن؛ تستمر المراجعة حسب المواعيد.' : 'ابدأ بالمفاهيم الأساسية، ثم يفتح التمييز والتطبيق تدريجيًا.');
    $('#tjStartLearning').disabled = !plan.length;
    $('#tjResetLearning').disabled = !stats.total;
    $('#tjLearningEmpty').textContent = plan.length
      ? `جلسة اليوم: ${toArabicDigits(plan.length)} نشاط موزع بين الفهم والتمييز والتطبيق.`
      : (stats.nextDueAt > Date.now()
        ? `لا توجد مراجعة الآن. الموعد التالي: ${new Date(stats.nextDueAt).toLocaleString('ar-EG')}.`
        : 'اكتملت أنشطة اليوم وفق مستوى الكثافة المختار.');

    const referenceCards = cards.filter((card) => card.activityType === 'learn');
    const learningProgress = tajweedLearningEngine.snapshot().progress;
    const groups = new Map();
    referenceCards.forEach((card) => {
      if (!groups.has(card.category)) groups.set(card.category, []);
      groups.get(card.category).push(card);
    });
    $('#tjList').innerHTML = [...groups.entries()].map(([category, items]) => `
      <section class="tj-rule-group">
        <h4>${esc(categoryLabels.get(category))}</h4>
        ${items.map((card) => {
          const example = card.example
            ? `<div class="muted" style="margin-top:4px">مثال: ${coloredTajweedExample(card)} — ${esc(surahName(card.example.surah))} ${toArabicDigits(card.example.ayah)}</div>`
            : '';
          const introduced = cards.filter((activity) => activity.baseId === card.baseId)
            .filter((activity) => {
              const normalized = TajweedLearningAPI.normalizeCard(activity);
              return normalized && learningProgress[normalized.key];
            }).length;
          const total = cards.filter((activity) => activity.baseId === card.baseId).length;
          return `<div class="wird-line"><span><strong>${esc(card.name)}</strong><div class="muted">${esc(card.answer)}</div>${example}</span><small class="smart-badge">${toArabicDigits(introduced)}/${toArabicDigits(total)} مراحل</small></div>`;
        }).join('')}
      </section>`).join('');
  }

  function renderTajweedLearningCard() {
    const item = tajweedSession.queue[tajweedSession.index];
    if (!item) {
      finishTajweedSession(true);
      return;
    }
    const card = item.card;
    tajweedSession.revealed = false;
    tajweedSession.quizCorrect = null;
    $('#tjLearningCard').hidden = false;
    $('#tjCardProgress').textContent = `النشاط ${toArabicDigits(tajweedSession.index + 1)} من ${toArabicDigits(tajweedSession.queue.length)} · ${item.kind === 'review' ? 'مراجعة' : 'جديد'}`;
    $('#tjCardStage').textContent = TAJWEED_ACTIVITY_LABELS[card.activityType] || 'تعلّم';
    $('#tjCardTitle').textContent = card.name;
    $('#tjCardPrompt').textContent = card.prompt;
    $('#tjCardExample').innerHTML = card.example
      ? `${coloredTajweedExample(card)}<div class="muted">${esc(surahName(card.example.surah))} — الآية ${toArabicDigits(card.example.ayah)}</div>`
      : '<span class="muted">لا يوجد مثال موسوم في المصدر الحالي.</span>';
    $('#tjCardAnswerText').textContent = card.answer;
    $('#tjCardAnswer').hidden = true;
    $('#tjQuizFeedback').textContent = '';
    const curriculum = currentTajweedCurriculum();
    const options = card.activityType === 'recognize' && curriculum
      ? TajweedLearningAPI.recognitionOptions(card, cardsForCurriculum(curriculum)) : [];
    $('#tjQuizChoices').hidden = !options.length;
    $('#tjQuizChoices').innerHTML = options.map((option) => `
      <button class="tj-choice" data-tj-option="${esc(option.id)}">${esc(option.label)}</button>`).join('');
    $('#tjRevealAnswer').textContent = options.length ? 'لا أعرف — إظهار الإجابة' : 'إظهار الشرح';
    $('#tjRevealAnswer').hidden = false;
    $('#tjLearningCard').querySelectorAll('[data-tj-rating]').forEach((button) => {
      button.disabled = false;
    });
  }

  function revealTajweedAnswer(fromQuiz = false) {
    const item = tajweedSession.queue[tajweedSession.index];
    if (!item || tajweedSession.revealed) return;
    const isRecognition = item.card.activityType === 'recognize' && !$('#tjQuizChoices').hidden;
    if (isRecognition && !fromQuiz) {
      tajweedSession.quizCorrect = false;
      tajweedSession.quizTotal += 1;
      $('#tjQuizFeedback').textContent = 'سُجلت «لا أعرف». راجع الإجابة وستعود قريبًا للتثبيت.';
      $('#tjQuizChoices').querySelectorAll('[data-tj-option]').forEach((button) => {
        button.disabled = true;
        if (button.dataset.tjOption === item.card.baseId) button.classList.add('correct');
      });
    }
    tajweedSession.revealed = true;
    $('#tjCardAnswer').hidden = false;
    $('#tjRevealAnswer').hidden = true;
    if (isRecognition && tajweedSession.quizCorrect === false) {
      $('#tjLearningCard').querySelectorAll('[data-tj-rating]').forEach((button) => {
        button.disabled = button.dataset.tjRating !== 'again';
      });
    }
  }

  function startTajweedSession() {
    const curriculum = currentTajweedCurriculum();
    if (!curriculum || !tajweedLearningEngine) return;
    const queue = tajweedLearningEngine.plan(cardsForCurriculum(curriculum), curriculum.scope);
    if (!queue.length) { toast('لا توجد مراجعات أو أنشطة جديدة الآن'); return; }
    tajweedSession = { ...emptyTajweedSession(), queue };
    $('#tjSessionSummary').hidden = true;
    renderTajweedLearningCard();
    $('#tjLearningCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function finishTajweedSession(completed) {
    const session = tajweedSession;
    const answered = session.answered;
    const curriculum = currentTajweedCurriculum();
    $('#tjLearningCard').hidden = true;
    tajweedSession = emptyTajweedSession();
    if (answered) {
      const successful = session.ratings.good + session.ratings.easy;
      const quizText = session.quizTotal
        ? ` · تمييز صحيح ${toArabicDigits(session.quizCorrectCount)} من ${toArabicDigits(session.quizTotal)}` : '';
      $('#tjSessionSummaryTitle').textContent = completed ? 'اكتملت جلسة التجويد' : 'ملخص الجلسة حتى الآن';
      $('#tjSessionSummaryText').textContent = `${toArabicDigits(answered)} نشاط · متقن ${toArabicDigits(successful)} · يحتاج إعادة ${toArabicDigits(session.ratings.again)}${quizText}`;
      $('#tjSessionSummary').dataset.scope = curriculum && TajweedLearningAPI
        ? TajweedLearningAPI.scopeKey(curriculum.scope) : '';
      $('#tjSessionSummary').hidden = false;
    }
    if (completed && answered) {
      smartRecord({
        type: 'COMPLETE_TAJWEED_LESSON', service: 'tajweed',
        context: { count: answered, source: 'adaptive_spaced_review' },
      });
      toast(`اكتملت جلسة من ${toArabicDigits(answered)} أنشطة`);
    }
    renderTajweedView();
  }

  $('#tjStartLearning').addEventListener('click', startTajweedSession);
  $('#tjEndLearning').addEventListener('click', () => finishTajweedSession(false));
  $('#tjRevealAnswer').addEventListener('click', () => revealTajweedAnswer(false));
  $('#tjSessionSummaryClose').addEventListener('click', () => { $('#tjSessionSummary').hidden = true; });
  $('#tjIntensity').addEventListener('change', (event) => {
    if (!tajweedLearningEngine || !TAJWEED_INTENSITY[event.target.value]) return;
    tajweedLearningEngine.configure(TAJWEED_INTENSITY[event.target.value]);
    persistTajweedLearning();
    renderTajweedView();
  });
  $('#tjLearningCard').addEventListener('click', (event) => {
    const option = event.target.closest('[data-tj-option]');
    const item = tajweedSession.queue[tajweedSession.index];
    if (option && item && !tajweedSession.revealed) {
      const correct = option.dataset.tjOption === item.card.baseId;
      tajweedSession.quizCorrect = correct;
      tajweedSession.quizTotal += 1;
      if (correct) tajweedSession.quizCorrectCount += 1;
      $('#tjQuizChoices').querySelectorAll('[data-tj-option]').forEach((button) => {
        button.disabled = true;
        if (button.dataset.tjOption === item.card.baseId) button.classList.add('correct');
        else if (button === option) button.classList.add('wrong');
      });
      $('#tjQuizFeedback').textContent = correct
        ? 'إجابة صحيحة. راجع طريقة الأداء ثم قيّم ثباتك.'
        : 'ليست هذه الإجابة. ظهر الحكم الصحيح وستعود البطاقة قريبًا.';
      revealTajweedAnswer(true);
      return;
    }
    const button = event.target.closest('[data-tj-rating]');
    if (!button || button.disabled || !tajweedSession.revealed || !tajweedLearningEngine || !item) return;
    let rating = button.dataset.tjRating;
    if (item.card.activityType === 'recognize' && tajweedSession.quizCorrect === false) rating = 'again';
    const reviewed = tajweedLearningEngine.review(item.card, rating);
    if (!reviewed) return;
    persistTajweedLearning();
    smartRecord({
      type: 'TAJWEED_ANSWER', service: 'tajweed',
      context: { rule: item.card.id, correct: rating !== 'again', source: rating },
    });
    tajweedSession.ratings[rating] += 1;
    tajweedSession.answered += 1;
    tajweedSession.index += 1;
    if (tajweedSession.index >= tajweedSession.queue.length) finishTajweedSession(true);
    else renderTajweedLearningCard();
  });
  $('#tjResetLearning').addEventListener('click', () => {
    const curriculum = currentTajweedCurriculum();
    if (!curriculum || !tajweedLearningEngine) return;
    if (!confirm('مسح تقدم تعلم التجويد لهذه الطبعة فقط؟')) return;
    tajweedLearningEngine.resetScope(curriculum.scope);
    persistTajweedLearning();
    $('#tjSessionSummary').hidden = true;
    renderTajweedView();
    toast('مُسح تقدم هذه الطبعة');
  });

  // ---------- معاني الكلمات (من الموسوعة القرآنية) ----------
  let meanData = null;
  let meanToken = 0;
  async function loadMeanings() {
    if (meanData) return meanData;
    meanData = (await getJSON('quran-meanings.json')).ayahs || {};
    return meanData;
  }
  function showMeaningsPanel() {
    const a = state.sel;
    if (!a) { toast('اضغط على الآية أولاً'); return; }
    const token = ++meanToken;
    $('#meanTitle').textContent = `${surahName(a.s)} - الآية ${toArabicDigits(a.n)}`;
    $('#meanAyah').textContent = plainAyah(a.html);
    $('#meanBody').innerHTML = '<div class="muted">جاري التحميل...</div>';
    $('#tjPanel').classList.remove('show');
    $('#tafsirPanel').classList.remove('show');
    $('#meanPanel').classList.add('show');
    loadMeanings().then((all) => {
      if (token !== meanToken) return;
      const items = all[`${a.s}:${a.n}`] || [];
      $('#meanBody').innerHTML = items.length
        ? items.map(([book, words]) => `<div class="pop-label">${esc(book)}</div>` +
            words.map(([t, m]) => `<div class="mw"><b>${esc(t)}</b>${esc(m)}</div>`).join('')).join('')
        : '<div class="muted">لا توجد معانٍ لكلمات هذه الآية.</div>';
    }).catch(() => {
      if (token === meanToken) $('#meanBody').textContent = 'تعذّر تحميل المعاني، حاول مرة أخرى.';
    });
  }
  $('#btnMeanings').addEventListener('click', showMeaningsPanel);
  let mnToken = 0;
  function renderMeaningsView() {
    const sel = $('#mnSurah');
    if (!sel.options.length) sel.innerHTML = surahs.map((x) => `<option value="${x.number}">${x.number}. ${esc(x.name)}</option>`).join('');
    if (state.sel) sel.value = String(state.sel.s);
    renderMeaningsList();
  }
  function renderMeaningsList() {
    const s = Number($('#mnSurah').value) || 1;
    const info = surahs[s - 1];
    const out = $('#mnList');
    if (!info) return;
    const token = ++mnToken;
    out.innerHTML = '<div class="muted">جاري التحميل...</div>';
    loadMeanings().then((all) => {
      if (token !== mnToken) return;
      let html = '';
      for (let n = 1; n <= info.numberOfAyahs; n++) {
        const items = all[`${s}:${n}`];
        if (!items || !items.length) continue;
        html += `<div class="card"><strong>${esc(info.name)} - الآية ${toArabicDigits(n)}</strong>` +
          items.map(([book, words]) => `<div class="pop-label">${esc(book)}</div>` +
            words.map(([t, m]) => `<div class="mw"><b>${esc(t)}</b>${esc(m)}</div>`).join('')).join('') + '</div>';
      }
      out.innerHTML = html || '<div class="muted">لا توجد معانٍ مسجلة لهذه السورة.</div>';
    }).catch(() => { if (token === mnToken) out.innerHTML = '<div class="muted">تعذّر تحميل المعاني، حاول مرة أخرى.</div>'; });
  }
  $('#mnSurah').addEventListener('change', renderMeaningsList);
  $('#meanClose').addEventListener('click', () => $('#meanPanel').classList.remove('show'));

  // ---------- مشاركة الآية كصورة ----------
  const IMG_W = 1080, IMG_H = 1350;
  let imgBlob = null, imgUrl = null, imgName = 'ayah.png';
  let imgFont = null;
  function loadImgFont() {
    if (!imgFont) {
      const f = new FontFace('AmiriQuranImg', 'url(fonts/AmiriQuran-arabic.woff2)');
      imgFont = f.load().then((ff) => { document.fonts.add(ff); return ff; }).catch(() => null);
    }
    return imgFont;
  }
  const plainAyah = (html) => clean(String(html || '').replace(/<[^>]+>/g, '')).replace(/[\u06DD\u06DE]\s*[\u0660-\u0669\u06F0-\u06F9\d]*/g, '').replace(/\s+/g, ' ').trim();

  // يرسم البطاقة: النص في المنتصف بالحجم الذي يتسع داخل الإطار، والسورة ورقم الآية في الأعلى والأسفل
  function drawAyahCard(text, surahLabel, ayahNo, hasFont) {
    const cv = document.createElement('canvas');
    cv.width = IMG_W; cv.height = IMG_H;
    const ctx = cv.getContext('2d');
    ctx.fillStyle = '#fbf7ec';
    ctx.fillRect(0, 0, IMG_W, IMG_H);
    ctx.strokeStyle = '#b8924a'; ctx.lineWidth = 6;
    ctx.strokeRect(36, 36, IMG_W - 72, IMG_H - 72);
    ctx.lineWidth = 2;
    ctx.strokeRect(56, 56, IMG_W - 112, IMG_H - 112);

    const family = hasFont ? '"AmiriQuranImg", serif' : 'serif';
    const maxW = IMG_W - 240;
    const maxH = 860;
    let size = 96, lines = [];
    ctx.direction = 'rtl';
    for (; size >= 40; size -= 4) {
      ctx.font = size + 'px ' + family;
      lines = []; let cur = '';
      text.split(' ').forEach((w) => {
        const t = cur ? cur + ' ' + w : w;
        if (ctx.measureText(t).width <= maxW) cur = t; else { lines.push(cur); cur = w; }
      });
      if (cur) lines.push(cur);
      if (lines.length * size * 1.9 <= maxH) break;
    }
    const lh = size * 1.9;
    const startY = IMG_H / 2 - ((lines.length - 1) * lh) / 2;
    ctx.fillStyle = '#1d1d1b';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    lines.forEach((l, i) => ctx.fillText(l, IMG_W / 2, startY + i * lh));

    ctx.fillStyle = '#8a6d2f';
    ctx.font = '54px ' + family;
    ctx.fillText(surahLabel, IMG_W / 2, 200);
    ctx.font = '40px ' + family;
    ctx.fillText('﴿ ' + toArabicDigits(ayahNo) + ' ﴾', IMG_W / 2, IMG_H - 200);
    ctx.font = '36px ' + family;
    ctx.fillText('القرآن الكريم', IMG_W / 2, IMG_H - 130);
    return cv;
  }

  function closeImgModal() {
    $('#imgModal').hidden = true;
    if (imgUrl) { URL.revokeObjectURL(imgUrl); imgUrl = null; }
    imgBlob = null;
  }

  async function shareAyahImage() {
    const a = state.sel;
    if (!a) { toast('اضغط على الآية أولاً'); return; }
    const text = plainAyah(a.html);
    if (!text) { toast('تعذّر تجهيز نص الآية'); return; }
    const font = await loadImgFont();
    const cv = drawAyahCard(text, surahName(a.s), a.n, !!font);
    const blob = await new Promise((r) => cv.toBlob(r, 'image/png'));
    if (!blob) { toast('تعذّر إنشاء الصورة'); return; }
    closeImgModal();
    imgBlob = blob;
    imgUrl = URL.createObjectURL(blob);
    imgName = 'ayah-' + a.s + '-' + a.n + '.png';
    $('#imgPreview').src = imgUrl;
    $('#imgModal').hidden = false;
  }

  $('#btnShareImg').addEventListener('click', shareAyahImage);
  $('#imgClose').addEventListener('click', closeImgModal);
  $('#imgModal').addEventListener('click', (e) => { if (e.target.id === 'imgModal') closeImgModal(); });
  $('#imgSave').addEventListener('click', () => {
    if (!imgUrl) return;
    const link = document.createElement('a');
    link.href = imgUrl; link.download = imgName;
    document.body.appendChild(link); link.click(); link.remove();
  });
  $('#imgShare').addEventListener('click', async () => {
    if (!imgBlob) return;
    const file = new File([imgBlob], imgName, { type: 'image/png' });
    if (!navigator.share || !navigator.canShare || !navigator.canShare({ files: [file] })) {
      toast('المشاركة غير متاحة هنا، استخدم التنزيل');
      return;
    }
    try { await navigator.share({ files: [file], title: 'آية من القرآن الكريم' }); }
    catch (e) { if (e && e.name !== 'AbortError') toast('تعذّرت المشاركة، استخدم التنزيل'); }
  });

  // ---------- الأذكار ----------
  let adhkarCats = null;
  const ADH_KEY = 'adhkar-counts';
  async function loadAdhkar() {
    if (adhkarCats) return adhkarCats;
    adhkarCats = (await getJSON('adhkar.json')).categories || [];
    return adhkarCats;
  }
  // العدادات تبدأ من جديد كل يوم
  function getAdhCounts() {
    const s = store.get(ADH_KEY, null);
    if (!s || s.day !== todayKey()) return { day: todayKey(), c: {} };
    return s;
  }
  // الشاشة الأولى للأذكار: تعليمات فقط، والاختيار يكون من قائمة "أذكارك"
  function renderAdhkarHome() {
    $('#adhkarCat').hidden = true;
    $('#adhkarHome').hidden = false;
    $('#adhkarHome').innerHTML = '<div class="card muted">اختر نوع الأذكار من قائمة «أذكارك» في الشريط.</div>';
  }
  function renderAdhkarMenu(cats) {
    $('#adhkarMenu').innerHTML = cats.map((c) => `<button data-view="adhkar" data-cat="${esc(c.id)}"><span class="ic" data-icon="adhkar" aria-hidden="true"></span>${esc(c.name)}</button>`).join('');
    renderFluentIcons($('#adhkarMenu'));
  }
  loadAdhkar().then(renderAdhkarMenu).catch(() => { $('#adhkarMenu').innerHTML = '<div class="muted" style="padding:8px">تعذّر تحميل الأذكار.</div>'; });
  function openAdhkarCat(id, options = {}) {
    const cat = (adhkarCats || []).find((c) => c.id === id);
    if (!cat) return;
    if (options.track !== false && SmartServicesAPI) {
      smartRecord({
        type: 'SERVICE_OPEN', service: SmartServicesAPI.serviceForAdhkar(id),
        context: { category: id, source: 'adhkar' },
      });
    }
    const counts = getAdhCounts();
    $('#adhkarHome').hidden = true;
    $('#adhkarCat').hidden = false;
    $('#adhkarCat').innerHTML = `
      <div class="card">
        <div class="row" style="justify-content:space-between">
          <strong>${esc(cat.name)}</strong>
        </div>
      </div>
      ${cat.items.map((it, i) => {
        const key = id + ':' + i;
        const n = Math.min(it.count, counts.c[key] || 0);
        const done = n >= it.count;
        return `<div class="card adh-item ${done ? 'done' : ''}" data-key="${esc(key)}" data-count="${it.count}">
          <div>${esc(clean(it.text))}</div>
          <div class="row" style="justify-content:space-between;margin-top:8px">
            <button class="btn small adh-count" data-act="count">${toArabicDigits(n)} / ${toArabicDigits(it.count)}</button>
            <span class="muted">${done ? 'تم' : ''}</span>
          </div>
        </div>`;
      }).join('')}`;
  }
  $('#adhkarHome').addEventListener('click', (e) => {
    const b = e.target.closest('[data-cat]');
    if (b) openAdhkarCat(b.dataset.cat);
  });
  $('#adhkarCat').addEventListener('click', (e) => {
    const b = e.target.closest('[data-act="count"]');
    if (!b) return;
    const card = b.closest('[data-key]');
    const key = card.dataset.key, max = Number(card.dataset.count);
    const categoryId = key.split(':')[0];
    const category = (adhkarCats || []).find((item) => item.id === categoryId);
    const counts = getAdhCounts();
    const complete = () => !!(category && category.items.length && category.items.every((item, index) => (
      Number(counts.c[`${categoryId}:${index}`] || 0) >= Number(item.count)
    )));
    const wasComplete = complete();
    const cur = counts.c[key] || 0;
    // عند الإتمام: الضغطة التالية تعيد العداد للصفر
    counts.c[key] = cur >= max ? 0 : cur + 1;
    store.set(ADH_KEY, counts);
    if (!wasComplete && complete()) {
      const service = SmartServicesAPI ? SmartServicesAPI.serviceForAdhkar(categoryId) : 'adhkar';
      smartRecord({
        type: 'COMPLETE_ADHKAR', service,
        context: { category: categoryId, count: category.items.length, source: 'counter' },
      });
    }
    openAdhkarCat(categoryId, { track: false });
  });

  // ---------- إحصائيات القراءة ----------
  // كل صفحة يفتحها القارئ تُسجَّل في يوم فتحها، مرة واحدة لكل يوم
  const STATS_KEY = 'stats';
  const dayKeyAgo = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return dateKey(d); };
  function getStats() {
    const s = store.get(STATS_KEY, null);
    const out = s && s.days ? s : { days: {} };
    if (!out.minutes || typeof out.minutes !== 'object') out.minutes = {};
    return out;
  }
  // دقائق القراءة: تُحتسب عند بقاء القارئ نشطًا في صفحة من صفحات المصحف
  let readerActiveSince = 0;
  let lastCountedMinute = '';
  function trackReadingMinutes() {
    if (curView !== 'reader' || document.hidden) return;
    // القارئ هو الواجهة الافتراضية عند فتح التطبيق: نبدأ العدّ من أول فحص
    if (!readerActiveSince) { readerActiveSince = Date.now(); return; }
    const key = todayKey() + ':' + Math.floor(Date.now() / 60000);
    if (lastCountedMinute === key) return;
    lastCountedMinute = key;
    const st = getStats();
    st.minutes[todayKey()] = (st.minutes[todayKey()] || 0) + 1;
    store.set(STATS_KEY, st);
    if (curView === 'stats' || curView === 'wird') { renderStats(); renderWird(); }
  }
  function minutesToday() { return getStats().minutes[todayKey()] || 0; }
  function minutesTotal() {
    const m = getStats().minutes;
    return Object.values(m).reduce((n, v) => n + (Number(v) || 0), 0);
  }
  function recordRead(p) {
    const st = getStats();
    const k = todayKey();
    const arr = st.days[k] || [];
    if (arr.includes(p)) return;
    arr.push(p);
    st.days[k] = arr;
    store.set(STATS_KEY, st);
    if (curView === 'stats') renderStats();
  }
  let smartLastReadPage = 0;
  let smartLastReadAt = 0;
  function recordSmartReadPage(p) {
    const now = Date.now();
    if (smartLastReadPage === Number(p) && now - smartLastReadAt < 15 * 60 * 1000) return;
    smartLastReadPage = Number(p);
    smartLastReadAt = now;
    smartRecord({
      type: 'READ_PAGE',
      service: 'wird',
      context: { page: Number(p), riwayah: settings.riwaya, source: 'reader' },
    });
  }
  function renderStats() {
    const st = getStats();
    const count = (k) => (st.days[k] || []).length;
    const today = count(todayKey());
    let week = 0;
    for (let i = 0; i < 7; i++) week += count(dayKeyAgo(i));
    const readDays = Object.keys(st.days).filter((k) => count(k) > 0).length;
    // السلسلة: أيام متتالية فيها قراءة حتى اليوم، واليوم الحالي لا يكسرها إن لم يُقرأ بعد
    let streak = 0;
    let i = today > 0 ? 0 : 1;
    while (count(dayKeyAgo(i)) > 0 && streak < 3650) { streak++; i++; }
    const unique = new Set();
    Object.values(st.days).forEach((arr) => arr.forEach((p) => unique.add(p)));

    $('#stDay').textContent = toArabicDigits(today);
    $('#stWeek').textContent = toArabicDigits(week);
    $('#stDays').textContent = toArabicDigits(readDays);
    $('#stStreak').textContent = toArabicDigits(streak) + ' يوم';
    $('#stUnique').textContent = toArabicDigits(unique.size) + ' من ' + toArabicDigits(TOTAL_PAGES);

    const mToday = $('#stMinutesToday');
    if (mToday) mToday.textContent = toArabicDigits(minutesToday()) + ' دقيقة';
    const mTotal = $('#stMinutesTotal');
    if (mTotal) mTotal.textContent = toArabicDigits(minutesTotal()) + ' دقيقة';
    const stBadges = $('#stBadges');
    if (stBadges) {
      stBadges.innerHTML = wirdBadges().filter((b) => b.done).map((b) => `
        <div class="badge-card done"><span class="badge-mark">★</span><strong>${esc(b.name)}</strong><small>${esc(b.hint)}</small></div>`).join('')
        || '<p class="muted">لم تُفتح شارة بعد؛ اقرأ صفحة واحدة وستحصل على أول شارة.</p>';
    }
    const vals = [];
    for (let j = 6; j >= 0; j--) vals.push({ k: dayKeyAgo(j), n: count(dayKeyAgo(j)), j });
    const max = Math.max(1, ...vals.map((v) => v.n));
    $('#stBars').innerHTML = vals.map((v) => {
      const d = new Date(v.k + 'T12:00:00');
      const label = d.toLocaleDateString('ar-EG', { weekday: 'short' });
      return `<div class="bar-col">
        <span class="bar-n">${toArabicDigits(v.n)}</span>
        <div class="bar" style="height:${Math.max(2, (v.n / max) * 100)}%"></div>
        <span class="bar-d">${label}</span>
      </div>`;
    }).join('');
  }

  // ---------- الورد اليومي وتتبع الختمة بلا هدف إلزامي ----------
  const WIRD_KEY = 'wird';
  const dateKey = (d) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  const todayKey = () => dateKey(new Date());
  const dateAr = (d) => new Date(d + (String(d).length === 10 ? 'T12:00:00' : '')).toLocaleDateString('ar-EG', { day: 'numeric', month: 'long', year: 'numeric' });
  function getWird() {
    const w = store.get(WIRD_KEY, null) || {};
    const oldReminder = store.get('wird-reminder', null) || {};
    return {
      pointer: Math.min(TOTAL_PAGES, Math.max(1, Number(w.pointer) || 1)),
      startDate: w.startDate || todayKey(),
      finished: Array.isArray(w.finished) ? w.finished : [],
      reminderEnabled: w.reminderEnabled != null ? !!w.reminderEnabled : !!oldReminder.enabled,
      reminderTime: /^\d{2}:\d{2}$/.test(w.reminderTime || '') ? w.reminderTime : (/^\d{2}:\d{2}$/.test(oldReminder.time || '') ? oldReminder.time : '20:00'),
    };
  }
  function saveWird(w) { store.set(WIRD_KEY, w); }

  function readingHabit() {
    const st = getStats();
    const keys = Object.keys(st.days).filter((k) => (st.days[k] || []).length).sort();
    const recent = keys.slice(-30);
    const total = recent.reduce((n, k) => n + (st.days[k] || []).length, 0);
    const average = recent.length ? total / recent.length : 0;
    let streak = 0;
    const d = new Date();
    if (!(st.days[todayKey()] || []).length) d.setDate(d.getDate() - 1);
    for (let i = 0; i < 3650; i++) {
      if ((st.days[dateKey(d)] || []).length) { streak++; d.setDate(d.getDate() - 1); }
      else break;
    }
    return { average, streak, days: keys.length, today: (st.days[todayKey()] || []).length };
  }

  function renderWird() {
    const w = getWird();
    const habit = readingHabit();
    const avg = habit.average;
    const goal = wirdGoal();
    const base = goal > 0 ? goal : Math.max(1, avg);
    $('#wdDone').textContent = toArabicDigits(habit.today);
    $('#wdFill').style.width = habit.today ? Math.min(100, habit.today / base * 100) + '%' : '0%';
    const goalLine = $('#wdGoalLine');
    if (goalLine) {
      goalLine.textContent = goal > 0
        ? (habit.today >= goal ? 'أتممت وردك اليوم' : `بقي ${pagesAr(goal - habit.today)}`)
        : '';
      renderWirdRing(
        goal > 0 ? Math.min(1, habit.today / goal) : Math.min(1, habit.today / base),
        goal > 0 ? `${toArabicDigits(habit.today)}/${toArabicDigits(goal)}` : toArabicDigits(habit.today));
    }

    const readInKhatma = w.pointer - 1;
    const left = TOTAL_PAGES - readInKhatma;
    const pct = (readInKhatma / TOTAL_PAGES) * 100;
    $('#khNext').textContent = toArabicDigits(w.pointer);
    $('#khPct').textContent = toArabicDigits(pct.toFixed(1)) + '%';
    $('#khLeft').textContent = toArabicDigits(left);
    $('#khFill').style.width = pct + '%';
    if (avg > 0) {
      const endD = new Date();
      endD.setDate(endD.getDate() + Math.ceil(left / avg));
      $('#khEnd').textContent = dateAr(dateKey(endD));
      $('#wdHabit').textContent = toArabicDigits(avg.toFixed(1)) + ' صفحة/يوم قراءة';
    } else {
      $('#khEnd').textContent = 'يتضح بعد بدء القراءة';
      $('#wdHabit').textContent = '—';
    }
    $('#wdStreak').textContent = toArabicDigits(habit.streak) + ' يوم';
    $('#wdDays').textContent = toArabicDigits(habit.days);
    $('#wdKhCount').textContent = toArabicDigits(w.finished.length);
    $('#wdReminderEnabled').checked = w.reminderEnabled;
    $('#wdReminderTime').value = w.reminderTime;
    $('#wdReminderStatus').textContent = w.reminderEnabled ? `التذكير اليومي عند ${w.reminderTime}.` : 'التذكير متوقف.';
    $$('#wdGoalChoices button').forEach((btn) => {
      btn.classList.toggle('on', Number(btn.dataset.goal) === goal);
    });
    renderWirdBadges();
    const stMin = $('#wdMinutes');
    if (stMin) stMin.textContent = toArabicDigits(minutesToday()) + ' دقيقة اليوم';
    $('#wdHist').innerHTML = w.finished.length
      ? w.finished.slice().reverse().map((f, i) => `<div class="wird-line"><span>ختمة مكتملة</span><span class="muted">${dateAr(f.start)} — ${dateAr(f.end)}</span></div>`).join('')
      : '<div class="muted">لا توجد ختمات مكتملة بعد.</div>';
  }

  // صياغة عربية سليمة لعدد الصفحات
  function pagesAr(n) {
    const num = Math.abs(Number(n) || 0);
    if (num === 1) return 'صفحة واحدة';
    if (num === 2) return 'صفحتان';
    if (num >= 3 && num <= 10) return `${toArabicDigits(num)} صفحات`;
    return `${toArabicDigits(num)} صفحة`;
  }
  // ---------- الهدف اليومي الاختياري ----------
  function wirdGoal() {
    const n = Number(store.get('wird-goal', 0));
    return Number.isFinite(n) && n > 0 ? Math.min(40, Math.round(n)) : 0;
  }
  function setWirdGoal(n) {
    store.set('wird-goal', Math.max(0, Math.min(40, Math.round(Number(n) || 0))));
    renderWird();
  }

  // حلقة تقدّم اليوم (SVG)
  function renderWirdRing(ratio, label) {
    const box = $('#wdRing');
    if (!box) return;
    const r = 34, c = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(1, Number(ratio) || 0));
    box.innerHTML = `
      <svg viewBox="0 0 84 84" role="img" aria-label="تقدّم ورد اليوم">
        <circle cx="42" cy="42" r="${r}" fill="none" stroke="rgba(0,0,0,.08)" stroke-width="8"/>
        <circle cx="42" cy="42" r="${r}" fill="none" stroke="#c6922e" stroke-width="8" stroke-linecap="round"
          stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - pct)}" transform="rotate(-90 42 42)"/>
        <text x="42" y="47" text-anchor="middle" font-size="15" fill="currentColor" font-family="inherit">${label}</text>
      </svg>`;
  }

  // ---------- الشارات: تقدير لا شرط ----------
  function wirdBadges() {
    const st = getStats();
    const habit = readingHabit();
    const unique = new Set();
    Object.values(st.days).forEach((arr) => arr.forEach((p) => unique.add(p)));
    const w = getWird();
    const totalPages = Object.values(st.days).reduce((n, arr) => n + arr.length, 0);
    const minutes = minutesTotal();
    return [
      { id: 'first', name: 'أول صفحة', hint: 'افتح صفحة من المصحف', done: totalPages >= 1 },
      { id: 'week', name: 'أسبوع متصل', hint: '٧ أيام قراءة متتالية', done: habit.streak >= 7 },
      { id: 'month', name: 'شهر متصل', hint: '٣٠ يومًا متتالية', done: habit.streak >= 30 },
      { id: 'hundred', name: 'مئة صفحة', hint: '١٠٠ صفحة مقروءة', done: totalPages >= 100 },
      { id: 'fivehundred', name: 'خمس مئة', hint: '٥٠٠ صفحة مقروءة', done: totalPages >= 500 },
      { id: 'khatma', name: 'ختمة كاملة', hint: 'أتمم ختمة واحدة', done: w.finished.length >= 1 },
      { id: 'two', name: 'ختمتان', hint: 'ختمتان مكتملتان', done: w.finished.length >= 2 },
      { id: 'pages600', name: 'كل المصحف', hint: 'اقرأ ٦٠٤ صفحات مختلفة', done: unique.size >= TOTAL_PAGES },
      { id: 'hours', name: 'عشر ساعات', hint: '٦٠٠ دقيقة قراءة', done: minutes >= 600 },
      { id: 'minutes60', name: 'ساعة قراءة', hint: '٦٠ دقيقة قراءة', done: minutes >= 60 },
    ];
  }
  function renderWirdBadges() {
    const box = $('#wdBadges');
    if (!box) return;
    box.innerHTML = wirdBadges().map((b) => `
      <div class="badge-card${b.done ? ' done' : ''}" title="${esc(b.hint)}">
        <span class="badge-mark">${b.done ? '★' : '☆'}</span>
        <strong>${esc(b.name)}</strong>
        <small>${esc(b.hint)}</small>
      </div>`).join('');
  }

  // مشاركة التقدم
  async function shareWirdProgress() {
    const habit = readingHabit();
    const w = getWird();
    const text = `تقدّمي في سراج: ${toArabicDigits(habit.today)} صفحة اليوم · ${toArabicDigits(habit.streak)} يومًا متتاليًا · `
      + `${toArabicDigits(w.pointer - 1)} صفحة في الختمة الحالية · ${toArabicDigits(w.finished.length)} ختمة مكتملة.`;
    try {
      if (navigator.share) { await navigator.share({ text }); return; }
      await navigator.clipboard.writeText(text);
      toast('تم نسخ تقدّمك');
    } catch { toast('تعذّرت المشاركة'); }
  }

  // لا يتحرك مؤشر الختمة إلا عند فتح الصفحة التالية نفسها؛ فتح صفحة عشوائية لا يفسد التتبع.
  function recordWirdPage(p) {
    const w = getWird();
    if (Number(p) !== w.pointer) return;
    if (w.pointer >= TOTAL_PAGES) {
      w.finished.push({ start: w.startDate, end: todayKey() });
      w.finished = w.finished.slice(-50);
      w.pointer = 1;
      w.startDate = todayKey();
      toast('تمت الختمة، بارك الله فيك. بدأت ختمة جديدة');
    } else {
      w.pointer++;
    }
    saveWird(w);
    if (curView === 'wird') renderWird();
  }

  $('#wdGo').addEventListener('click', () => {
    const w = getWird();
    showView('reader');
    showPage(w.pointer, { scroll: true });
  });
  $('#wdFromLast').addEventListener('click', () => {
    const last = getLast();
    if (!last || !last.p) { toast('لا يوجد موضع محفوظ في المصحف بعد'); return; }
    const w = getWird();
    w.pointer = Math.min(TOTAL_PAGES, Math.max(1, Number(last.p)));
    saveWird(w);
    renderWird();
    toast('بدأ تتبع الختمة من آخر موضع');
  });
  $('#wdSetPage').addEventListener('click', () => {
    const row = $('#wdSetRow');
    row.hidden = !row.hidden;
    $('#wdPageIn').value = String(getWird().pointer);
  });
  function saveWirdPage() {
    const raw = $('#wdPageIn').value.trim();
    const p = Number(raw.replace(/[٠-٩]/g, (d) => '٠١٢٣٤٥٦٧٨٩'.indexOf(d)));
    if (!Number.isInteger(p) || p < 1 || p > TOTAL_PAGES) { toast('أدخل رقم صفحة بين 1 و604'); return; }
    const w = getWird();
    w.pointer = p;
    saveWird(w);
    $('#wdSetRow').hidden = true;
    renderWird();
    toast('حُفظ موضع الختمة');
  }
  $('#wdPageOk').addEventListener('click', saveWirdPage);
  $('#wdPageIn').addEventListener('keydown', (e) => { if (e.key === 'Enter') saveWirdPage(); });

  async function saveWirdReminder() {
    const w = getWird();
    w.reminderEnabled = $('#wdReminderEnabled').checked;
    w.reminderTime = $('#wdReminderTime').value || '20:00';
    saveWird(w);
    const plugin = getReminderNative();
    if (!plugin) {
      $('#wdReminderStatus').textContent = w.reminderEnabled ? 'سيظهر التذكير داخل التطبيق عندما يكون مفتوحًا.' : 'التذكير متوقف.';
      return;
    }
    try {
      if (!w.reminderEnabled) {
        await plugin.cancel();
        $('#wdReminderStatus').textContent = 'التذكير متوقف.';
      } else {
        const [hour, minute] = w.reminderTime.split(':').map(Number);
        const context = smartEngine?.config.enabled
          ? smartEngine.evaluate([], smartSignals()).context : null;
        const result = await plugin.schedule({
          hour, minute,
          title: 'سراج — ورد القرآن',
          body: 'موعد وردك اليوم. اقرأ ما تيسر دون إلزام.',
          respectSafety: !!smartEngine?.config.enabled,
          quietStart: smartEngine?.config.quietStart || '22:30',
          quietEnd: smartEngine?.config.quietEnd || '06:30',
          sleepStart: minuteClock(context?.sleepMinute == null ? 23 * 60 : context.sleepMinute),
          sleepEnd: minuteClock(context?.wakeMinute == null ? 7 * 60 : context.wakeMinute),
        });
        $('#wdReminderStatus').textContent = result?.exact === false ? 'ضُبط تذكير يومي تقريبي من النظام.' : 'ضُبط تذكير يومي من النظام.';
      }
    } catch {
      w.reminderEnabled = false;
      saveWird(w);
      $('#wdReminderEnabled').checked = false;
      $('#wdReminderStatus').textContent = 'تعذر تفعيل إذن الإشعارات. راجع أذونات التطبيق.';
    }
  }
  $('#wdReminderSave').addEventListener('click', saveWirdReminder);
  $('#wdReminderEnabled').addEventListener('change', saveWirdReminder);

  function checkInAppWirdReminder() {
    const w = getWird();
    if (!w.reminderEnabled) return;
    if (smartEngine?.config.enabled) {
      const context = smartEngine.evaluate([], smartSignals()).context;
      if (context.likelySleeping || context.quietHours) return;
    }
    const now = new Date();
    const current = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    const key = `wird-notified-${todayKey()}`;
    if (current >= w.reminderTime && !sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, '1');
      toast('موعد وردك اليوم — اقرأ ما تيسر دون إلزام');
    }
  }

  // بدء ختمة جديدة يحتاج ضغطتين لتجنب اللمس غير المقصود.
  let wdNewArmed = false;
  $('#wdNewKhatma').addEventListener('click', (e) => {
    const btn = e.currentTarget;
    if (!wdNewArmed) {
      wdNewArmed = true;
      btn.textContent = 'اضغط مرة أخرى للتأكيد';
      setTimeout(() => { wdNewArmed = false; btn.textContent = 'بدء ختمة جديدة'; }, 4000);
      return;
    }
    wdNewArmed = false;
    btn.textContent = 'بدء ختمة جديدة';
    const w = getWird();
    w.pointer = 1;
    w.startDate = todayKey();
    saveWird(w);
    renderWird();
    toast('بدأت ختمة جديدة');
  });

  // ---------- رفيق اليوم: اقتراحات محلية على الجهاز ----------
  let smartLastDecision = null;

  function smartCompletedServices(at = Date.now()) {
    const completed = new Set();
    if (!smartEngine) return completed;
    const targetDay = dateKey(new Date(at));
    const completionTypes = new Set([
      'SERVICE_COMPLETE', 'COMPLETE_MEMORIZATION', 'COMPLETE_ADHKAR',
      'COMPLETE_TAJWEED_LESSON', 'NOTIFICATION_COMPLETE', 'SUGGESTION_COMPLETE',
    ]);
    smartEngine.events.forEach((event) => {
      if (SmartContextAPI.dateKey(event.at) !== targetDay) return;
      if (event.type === 'READ_PAGE' && event.service === 'wird') completed.add('wird');
      if (completionTypes.has(event.type)) completed.add(event.service);
    });
    return completed;
  }

  function smartKnownServices() {
    if (!smartEngine) return [];
    return [...new Set(smartEngine.events
      .filter((event) => event.service && event.service !== 'app')
      .map((event) => event.service))];
  }

  function memoDueCount(at = Date.now()) {
    const targetDay = dateKey(new Date(at));
    return Object.values(getMemoProgress()).filter((item) => item && item.due <= targetDay).length;
  }

  function smartCandidateInput(at = Date.now()) {
    const habit = readingHabit();
    const wird = getWird();
    const targetDay = dateKey(new Date(at));
    const stats = getStats();
    return {
      readToday: (stats.days[targetDay] || []).length,
      wirdPointer: wird.pointer,
      readingAverage: habit.average,
      memoDue: memoDueCount(at),
      completedServices: [...smartCompletedServices(at)],
      knownServices: smartKnownServices(),
    };
  }

  function smartSignals() {
    const now = Date.now();
    const visible = document.visibilityState !== 'hidden';
    return {
      screenInteractive: visible ? true : !!smartDeviceSignals.screenInteractive,
      lastDeviceActiveAt: smartLastInteractionAt,
      busy: (play.active && !audio.paused) || !!document.querySelector('.panel-tafsir.show')
        || !!smartDeviceSignals.deviceLocked,
      powerSave: !!smartDeviceSignals.powerSave,
      charging: !!smartDeviceSignals.charging,
      batteryPercent: Number(smartDeviceSignals.batteryPercent),
      sessionDurationMs: Math.max(0, now - smartSessionStartedAt),
    };
  }

  function hideSmartSuggestion(clear = true) {
    const card = $('#smartSuggestion');
    if (card) card.hidden = true;
    if (clear) smartCurrent = null;
  }

  function primarySmartBlock(decision) {
    if (!decision) return null;
    if (decision.context?.likelySleeping) return 'LIKELY_SLEEPING';
    if (decision.context?.quietHours) return 'QUIET_HOURS';
    const priority = ['ENGINE_DISABLED', 'DAILY_CAP', 'COOLDOWN', 'BELOW_THRESHOLD'];
    for (const reason of priority) {
      if (decision.blocked?.some((item) => item.reason === reason)) return reason;
    }
    return null;
  }

  function fillSmartSettings() {
    const enabled = $('#setSmartEnabled');
    if (!enabled) return;
    if (!smartEngine || !SmartServicesAPI) {
      enabled.checked = false;
      enabled.disabled = true;
      $('#smartLocalStatus').textContent = 'رفيق اليوم غير متاح في هذه الحزمة.';
      return;
    }
    const cfg = smartEngine.config;
    enabled.disabled = false;
    enabled.checked = !!cfg.enabled;
    $('#smartQuietStart').value = cfg.quietStart;
    $('#smartQuietEnd').value = cfg.quietEnd;
    $('#smartDailyMax').value = String(cfg.maxDailyInterventions);
    $('#smartCooldown').value = String(cfg.cooldownMinutes);
    $('#smartRetention').value = String(cfg.retentionDays);
    const smartDevice = getSmartDeviceNative();
    $('#smartNativeRow').hidden = !smartDevice;
    $('#smartNativeRow').style.display = smartDevice ? 'flex' : 'none';
    $('#smartNativeStatus').hidden = !smartDevice;
    $('#setSmartNotifications').checked = !!smartNative.enabled;
    $('#setSmartNotifications').disabled = !cfg.enabled;
    if (smartDevice) {
      $('#smartNativeStatus').textContent = smartNative.enabled
        ? (smartNative.nextAt > Date.now()
          ? `الإشعار المحلي التالي مخطط بعد بوابات النوم والهدوء: ${new Date(smartNative.nextAt).toLocaleString('ar-EG')}.`
          : 'تذكيرات رفيق اليوم مفعّلة، ولا تذكير مناسب الآن.')
        : 'لا تُطلب صلاحية إشعارات Android إلا عند تفعيل هذا الخيار.';
    }
    $('#smartLocalStatus').textContent = cfg.enabled
      ? `مفعّل · ${toArabicDigits(smartEngine.events.length)} حدثًا تشغيليًا محدودًا محفوظًا محليًا لمدة ${toArabicDigits(cfg.retentionDays)} يومًا كحد أقصى.`
      : `متوقف؛ لا يسجّل أحداثًا جديدة ولا يعرض تذكيرات. السجل المحلي الحالي: ${toArabicDigits(smartEngine.events.length)}.`;
    if (!cfg.enabled) {
      $('#smartDecisionStatus').textContent = 'التفعيل اختياري، وبياناتك لا تغادر الجهاز.';
    } else if (smartLastDecision?.selected) {
      $('#smartDecisionStatus').textContent = 'آخر قرار: عُرض تذكير مع سبب ظاهر للمستخدم.';
    } else {
      const reason = primarySmartBlock(smartLastDecision);
      $('#smartDecisionStatus').textContent = reason
        ? `آخر قرار: ${SmartServicesAPI.describeBlock(reason)}`
        : 'لا توجد حاجة إلى تذكير الآن.';
    }
  }

  function queueSmartSuggestion(delay = 1200) {
    clearTimeout(smartSuggestionTimer);
    if (!smartEngine?.config.enabled || !SmartServicesAPI) return;
    smartSuggestionTimer = setTimeout(renderSmartSuggestion, Math.max(0, Number(delay) || 0));
  }

  function minuteClock(value) {
    const minute = ((Math.round(Number(value) || 0) % 1440) + 1440) % 1440;
    return `${String(Math.floor(minute / 60)).padStart(2, '0')}:${String(minute % 60).padStart(2, '0')}`;
  }

  async function refreshSmartDeviceSignals() {
    const plugin = getSmartDeviceNative();
    if (!plugin) return null;
    try {
      smartDeviceSignals = await plugin.getSignals();
      return smartDeviceSignals;
    } catch {
      smartDeviceSignals = {};
      return null;
    }
  }

  function queueSmartNativeSync(delay = 1800) {
    clearTimeout(smartNativeTimer);
    if (!smartNative.enabled || !smartEngine?.config.enabled || !getSmartDeviceNative()) return;
    smartNativeTimer = setTimeout(syncSmartNativeSchedule, Math.max(0, Number(delay) || 0));
  }

  async function syncSmartNativeSchedule() {
    const plugin = getSmartDeviceNative();
    if (!plugin || !smartNative.enabled || !smartEngine?.config.enabled || !SmartServicesAPI) return;
    const plan = SmartServicesAPI.planNextDecision(
      (at) => SmartServicesAPI.buildCandidates(smartCandidateInput(at), at),
      (candidates, at) => SmartContextAPI.chooseIntervention(
        candidates,
        smartEngine.events,
        { screenInteractive: false, lastDeviceActiveAt: smartLastInteractionAt, busy: false },
        at,
        smartEngine.config,
      ),
      { now: Date.now(), minDelayMinutes: 30, stepMinutes: 30, horizonHours: 30 },
    );
    if (!plan) {
      await plugin.cancel().catch(() => {});
      smartNative.nextAt = 0;
      store.set(SMART_NATIVE_KEY, smartNative);
      fillSmartSettings();
      return;
    }
    const candidate = plan.selection.candidate;
    const suggestionId = `native_${candidate.id}_${plan.at}`.slice(0, 64);
    const context = plan.context || {};
    try {
      const result = await plugin.schedule({
        at: plan.at,
        title: candidate.title || 'سراج',
        body: candidate.body || 'لديك متابعة مناسبة الآن.',
        service: candidate.service,
        suggestionId,
        target: candidate.action || '',
        quietStart: smartEngine.config.quietStart,
        quietEnd: smartEngine.config.quietEnd,
        sleepStart: minuteClock(context.sleepMinute == null ? 23 * 60 : context.sleepMinute),
        sleepEnd: minuteClock(context.wakeMinute == null ? 7 * 60 : context.wakeMinute),
      });
      smartNative.nextAt = Number(result?.nextAt) || plan.at;
      store.set(SMART_NATIVE_KEY, smartNative);
    } catch {
      smartNative.enabled = false;
      smartNative.nextAt = 0;
      store.set(SMART_NATIVE_KEY, smartNative);
      toast('تعذر جدولة الإشعار الذكي؛ راجع إذن الإشعارات.');
    }
    fillSmartSettings();
  }

  async function consumeSmartNativeFeedback() {
    const plugin = getSmartDeviceNative();
    if (!plugin || !smartEngine?.config.enabled) return;
    try {
      const result = await plugin.consumeFeedback();
      const events = Array.isArray(result?.events) ? result.events : [];
      const typeMap = {
        shown: 'SUGGESTION_SHOWN', open: 'SUGGESTION_OPEN',
        snooze: 'SUGGESTION_SNOOZE', dismiss: 'SUGGESTION_DISMISS',
      };
      events.forEach((item) => {
        const type = typeMap[item?.type];
        if (!type) return;
        smartEngine.record({
          type,
          service: item.service,
          at: Number(item.at),
          context: { notificationId: String(item.id || '').slice(0, 64), source: 'android' },
        });
        if (item.type === 'open' && item.target) smartPendingNativeAction = String(item.target);
      });
      if (events.length) {
        persistSmartContext(true);
        queueSmartNativeSync(2200);
      }
      if (smartAppReady && smartPendingNativeAction) {
        const action = smartPendingNativeAction;
        smartPendingNativeAction = '';
        await runSmartAction(action);
      }
    } catch { /* تبقى الواجهة المحلية عاملة إذا تعذر جسر Android */ }
  }

  function renderSmartSuggestion() {
    if (!smartEngine?.config.enabled || !SmartServicesAPI || document.hidden
        || curView === 'settings' || curView === 'about'
        || (play.active && !audio.paused)
        || !!document.querySelector('.panel-tafsir.show')
        || !$('#imgModal').hidden
        || document.body.classList.contains('group-menu-open')) {
      hideSmartSuggestion();
      fillSmartSettings();
      return;
    }
    const elapsed = Date.now() - smartSessionStartedAt;
    if (elapsed < 6000) {
      queueSmartSuggestion(6000 - elapsed);
      return;
    }
    const candidates = SmartServicesAPI.buildCandidates(smartCandidateInput(), Date.now());
    const decision = smartEngine.evaluate(candidates, smartSignals());
    smartLastDecision = decision;
    if (!decision.selected) {
      hideSmartSuggestion();
      fillSmartSettings();
      return;
    }
    const selected = decision.selected;
    const candidate = selected.candidate;
    const suggestionId = `${candidate.id}:${Date.now()}`.slice(0, 64);
    smartCurrent = { selection: selected, id: suggestionId };
    $('#smartSuggestionTitle').textContent = candidate.title || 'من رفيق اليوم';
    $('#smartSuggestionBody').textContent = candidate.body || '';
    $('#smartSuggestionOpen').textContent = candidate.cta || 'فتح';
    $('#smartSuggestionWhy').textContent = SmartServicesAPI.explainSelection(selected);
    $('#smartSuggestion').hidden = false;
    smartEngine.markShown(candidate, suggestionId, 'suggestion');
    persistSmartContext();
    fillSmartSettings();
  }

  async function runSmartAction(action) {
    if (action === 'open_wird') {
      const wird = getWird();
      showView('reader');
      await showPage(wird.pointer, { scroll: true });
      return;
    }
    if (String(action).startsWith('open_adhkar:')) {
      const category = String(action).split(':')[1];
      await loadAdhkar();
      showView('adhkar');
      openAdhkarCat(category);
      return;
    }
    if (action === 'open_memorization') { showView('memo'); return; }
    if (action === 'open_tajweed') { showView('tajweed'); return; }
    if (action === 'open_recitation') { showView('reader'); return; }
  }

  function recordSmartFeedback(action) {
    if (!smartEngine || !smartCurrent) return null;
    const current = smartCurrent;
    const recorded = smartEngine.feedback(
      current.selection.candidate.service, action, current.id, 'suggestion',
    );
    persistSmartContext();
    return { current, recorded };
  }

  $('#smartSuggestionOpen').addEventListener('click', async () => {
    const result = recordSmartFeedback('open');
    if (!result) return;
    const action = result.current.selection.candidate.action;
    hideSmartSuggestion();
    await runSmartAction(action);
  });
  $('#smartSuggestionLater').addEventListener('click', () => {
    recordSmartFeedback('snooze');
    hideSmartSuggestion();
    fillSmartSettings();
  });
  $('#smartSuggestionDismiss').addEventListener('click', () => {
    recordSmartFeedback('dismiss');
    hideSmartSuggestion();
    fillSmartSettings();
  });

  function smartConfigFromControls() {
    return {
      quietStart: $('#smartQuietStart').value || '22:30',
      quietEnd: $('#smartQuietEnd').value || '06:30',
      maxDailyInterventions: Number($('#smartDailyMax').value) || 3,
      cooldownMinutes: Number($('#smartCooldown').value) || 120,
      retentionDays: Number($('#smartRetention').value) || 35,
    };
  }

  $('#setSmartEnabled').addEventListener('change', (event) => {
    if (!smartEngine) return;
    smartEngine.configure({ ...smartConfigFromControls(), enabled: event.target.checked });
    persistSmartContext(true);
    if (smartEngine.config.enabled) {
      smartSessionStartedAt = Date.now();
      smartLastInteractionAt = Date.now();
      smartRecord({
        type: 'APP_OPEN', service: 'app',
        context: { riwayah: settings.riwaya, source: 'opt_in' },
      }, { silent: true });
      queueSmartSuggestion(6500);
      if (getWird().reminderEnabled && getReminderNative()) saveWirdReminder();
      toast('فُعّل رفيق اليوم');
    } else {
      clearTimeout(smartSuggestionTimer);
      clearTimeout(smartNativeTimer);
      hideSmartSuggestion();
      smartNative.enabled = false;
      smartNative.nextAt = 0;
      store.set(SMART_NATIVE_KEY, smartNative);
      getSmartDeviceNative()?.cancel().catch(() => {});
      if (getWird().reminderEnabled && getReminderNative()) saveWirdReminder();
      toast('توقف رفيق اليوم');
    }
    fillSmartSettings();
  });
  $('#setSmartNotifications').addEventListener('change', async (event) => {
    const plugin = getSmartDeviceNative();
    if (!plugin || !smartEngine?.config.enabled) {
      event.target.checked = false;
      return;
    }
    if (!event.target.checked) {
      smartNative.enabled = false;
      smartNative.nextAt = 0;
      store.set(SMART_NATIVE_KEY, smartNative);
      await plugin.cancel().catch(() => {});
      fillSmartSettings();
      return;
    }
    const permission = await plugin.requestNotifications().catch(() => ({ granted: false }));
    if (!permission?.granted) {
      event.target.checked = false;
      smartNative.enabled = false;
      store.set(SMART_NATIVE_KEY, smartNative);
      toast('لم يُمنح إذن الإشعارات');
      fillSmartSettings();
      return;
    }
    smartNative.enabled = true;
    store.set(SMART_NATIVE_KEY, smartNative);
    await refreshSmartDeviceSignals();
    await syncSmartNativeSchedule();
  });
  ['smartQuietStart', 'smartQuietEnd', 'smartDailyMax', 'smartCooldown', 'smartRetention']
    .forEach((id) => $(`#${id}`).addEventListener('change', () => {
      if (!smartEngine) return;
      smartEngine.configure(smartConfigFromControls());
      persistSmartContext(true);
      hideSmartSuggestion();
      queueSmartSuggestion(1800);
      queueSmartNativeSync(500);
      if (getWird().reminderEnabled && getReminderNative()) saveWirdReminder();
      fillSmartSettings();
    }));
  $('#smartDeleteData').addEventListener('click', () => {
    if (!smartEngine) return;
    if (!confirm('حذف سجل رفيق اليوم من هذا الجهاز؟ لن تُحذف قراءتك أو علاماتك أو إعدادات المصحف.')) return;
    smartEngine.reset();
    smartLastDecision = null;
    persistSmartContext(true);
    smartNative.enabled = false;
    smartNative.nextAt = 0;
    store.set(SMART_NATIVE_KEY, smartNative);
    getSmartDeviceNative()?.cancel().catch(() => {});
    hideSmartSuggestion();
    fillSmartSettings();
    toast('حُذف سجل رفيق اليوم');
  });

  function recordSmartSessionEnd() {
    if (!smartEngine?.config.enabled) return;
    const now = Date.now();
    if (now - (recordSmartSessionEnd.lastAt || 0) < 2000) return;
    recordSmartSessionEnd.lastAt = now;
    smartRecord({
      type: 'READING_SESSION_END', service: 'app',
      durationMs: Math.max(0, now - smartSessionStartedAt),
      context: { source: curView },
    }, { immediate: true, silent: true });
  }
  document.addEventListener('pointerdown', () => { smartLastInteractionAt = Date.now(); }, { passive: true });
  document.addEventListener('keydown', () => { smartLastInteractionAt = Date.now(); }, { passive: true });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      recordSmartSessionEnd();
      clearTimeout(smartSuggestionTimer);
      hideSmartSuggestion();
      queueSmartNativeSync(500);
    } else {
      smartSessionStartedAt = Date.now();
      smartLastInteractionAt = Date.now();
      refreshSmartDeviceSignals();
      consumeSmartNativeFeedback();
      smartRecord({
        type: 'APP_FOREGROUND', service: 'app',
        context: { riwayah: settings.riwaya, source: curView },
      }, { silent: true });
      queueSmartSuggestion(5000);
      queueSmartNativeSync(1800);
    }
  });
  window.addEventListener('pagehide', recordSmartSessionEnd);

  // ---------- التشغيل الأولي ----------
  renderFluentIcons();
  applyTheme();
  document.body.classList.toggle('riw', isRiw());
  syncReaderLayout();
  fillSettings();
  renderBookmarks();
  renderLast();
  renderWird();
  if (!smartEngine?.config.enabled && smartNative.enabled) {
    smartNative.enabled = false;
    smartNative.nextAt = 0;
    store.set(SMART_NATIVE_KEY, smartNative);
    getSmartDeviceNative()?.cancel().catch(() => {});
  }
  smartRecord({
    type: 'APP_OPEN', service: 'app',
    context: { riwayah: settings.riwaya, source: 'launch' },
  }, { silent: true });
  refreshSmartDeviceSignals();
  consumeSmartNativeFeedback();
  queueSmartSuggestion(6500);
  queueSmartNativeSync(2500);
  if (getWird().reminderEnabled && getReminderNative()) saveWirdReminder();
  checkInAppWirdReminder();
  setInterval(checkInAppWirdReminder, 60 * 1000);

  // القرآن والسور والتجويد وفهرس التفاسير أصول مضمّنة: يبدأ التطبيق دون شبكة.
  (async function initializeBundledData() {
    try {
      await loadBundledData();
      // لا يُعد التحديث ناجحًا قبل تحميل JSON والتحقق من حزم التجويد المقفلة.
      localStorage.removeItem('quran-update-pending');
    } catch {
      toast('تعذر فتح بعض بيانات المصحف المحلية.');
      if (localStorage.getItem('quran-update-pending')) {
        localStorage.removeItem(UPDATE_KEY);
        localStorage.removeItem('quran-update-pending');
        await clearUpdateDataAssets();
        location.reload();
        return;
      }
    }
    fillSettings();
    await refreshTafsirPackStatus();
    await loadSurahs();
    const last = getLast();
    if (last && last.p) {
      await showPage(last.p, { selG: last.g, save: false });
    } else {
      await showPage(1, { save: false });
    }
    smartAppReady = true;
    if (smartPendingNativeAction) {
      const action = smartPendingNativeAction;
      smartPendingNativeAction = '';
      await runSmartAction(action);
    }
  })();

  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
})();
