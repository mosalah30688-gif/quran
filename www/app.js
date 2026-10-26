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
  ];
  const TAFSIRS = [
    ['ar.muyassar', 'التفسير الميسر (مجمع الملك فهد)'],
    ['ar.jalalayn', 'تفسير الجلالين'],
    ['ar.waseet', 'التفسير الوسيط'],
    ['ar.baghawi', 'تفسير البغوي'],
    ['ar.qurtubi', 'تفسير القرطبي'],
    ['ar.miqbas', 'تنوير المقباس'],
  ];

  const DEFAULTS = {
    riwaya: 'quran-uthmani', reciter: 'ar.alafasy', tafsir: 'ar.muyassar',
    translation: '', size: 26, tajweed: false, dark: false,
  };
  const VIEW_TITLES = { reader: 'المصحف', tafsir: 'التفسير', memo: 'وضع الحفظ', bookmarks: 'المحفوظات', settings: 'الإعدادات', about: 'عن التطبيق' };
  const Cap = window.Capacitor || null;

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

  // ---------- التخزين المحلي ----------
  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem('quran:' + key); return v === null ? fallback : JSON.parse(v); }
      catch { return fallback; }
    },
    set(key, value) { try { localStorage.setItem('quran:' + key, JSON.stringify(value)); } catch {} },
  };
  const settings = Object.assign({}, DEFAULTS, store.get('settings', {}));
  const saveSettings = () => store.set('settings', settings);

  // ---------- الحالة ----------
  let surahs = [];
  const cache = new Map();          // طلبات الـ API
  const pageCache = new Map();      // صفحات جاهزة (مُعالجة)
  const audio = new Audio();
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

  async function getJSON(url) {
    if (cache.has(url)) return cache.get(url);
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const json = await res.json();
    cache.set(url, json);
    return json;
  }

  function renderTajweed(raw) {
    let s = esc(clean(raw));
    s = s.replace(/\[([a-z]+)(?::\d+)?\[([^\[\]]*)\]/g, '<span class="tj-$1">$2</span>');
    return s.replace(/\[|\]/g, '');
  }

  // ---------- التنقل بين الأقسام ----------
  // سجل الأقسام: زر الرجوع يعيد خطوة واحدة للخلف داخل التطبيق
  const navStack = [];
  let curView = 'reader';
  function showView(name, opts = {}) {
    if (name !== curView && !opts.back) { navStack.push(curView); if (navStack.length > 30) navStack.shift(); }
    curView = name;
    $$('#tabs button').forEach((b) => b.classList.toggle('active', b.dataset.view === name));
    $$('section.view').forEach((s) => s.classList.toggle('active', s.id === 'view-' + name));
    if (name === 'reader') updateChrome(); else $('#topTitle').textContent = VIEW_TITLES[name] || '';
    // زر الرجوع يظهر في كل الأقسام ما عدا المصحف
    $('#backBtn').hidden = name === 'reader';
    if (name === 'bookmarks') renderBookmarks();
    if (name === 'tafsir') renderTafsirView();
    $('#content').scrollTop = 0;
  }
  function popView() { showView(navStack.pop() || 'reader', { back: true }); }
  $('#backBtn').addEventListener('click', () => handleBack());
  function closeSide() { document.body.classList.remove('side-open'); }

  $('#tabs').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-view]');
    if (!b) return;
    showView(b.dataset.view);
    closeSide();
  });
  $('#menuBtn').addEventListener('click', () => document.body.classList.toggle('side-open'));
  $('#backdrop').addEventListener('click', closeSide);

  function applyTheme() {
    document.body.classList.toggle('dark', !!settings.dark);
    $('#themeBtn').textContent = settings.dark ? '☀️' : '🌙';
  }
  $('#themeBtn').addEventListener('click', () => { settings.dark = !settings.dark; saveSettings(); applyTheme(); });

  // ---------- الفهرس: سورة / جزء / آية ----------
  async function loadSurahs() {
    try {
      surahs = (await getJSON(API + '/surah')).data;
    } catch {
      $('#indexList').innerHTML = '<div class="muted" style="padding:10px">تعذر تحميل الفهرس. تحقق من الاتصال بالإنترنت.</div>';
      return;
    }
    $('#memoSurah').innerHTML = surahs.map((s) => `<option value="${s.number}">${s.number}. ${esc(s.name)}</option>`).join('');
    renderIndex();
    syncPlayControls();
    setupDownloadUI();
  }

  function renderIndex() {
    const seg = index.mode;
    $$('#indexSeg button').forEach((b) => b.classList.toggle('on', b.dataset.mode === seg));
    $('#indexSearchWrap').style.display = seg === 'surah' ? 'block' : 'none';
    const list = $('#indexList');
    if (!surahs.length) return;
    const curS = state.sel ? state.sel.s : 1;
    const curJuz = state.sel ? state.sel.juz : 0;

    if (seg === 'surah') {
      const raw = $('#indexSearch').value.trim();
      const term = raw.toLowerCase();
      const items = surahs.filter((s) =>
        !term || String(s.number) === term || s.englishName.toLowerCase().includes(term) ||
        s.englishNameTranslation.toLowerCase().includes(term) || s.name.includes(raw));
      list.innerHTML = items.map((s) => `
        <div class="idx ${s.number === curS ? 'current' : ''}" data-s="${s.number}" data-a="1">
          <div class="n">${s.number}</div>
          <div>
            <div class="t">${esc(s.name)}</div>
            <div class="s">${esc(s.englishName)} · ${s.numberOfAyahs} آية · ${s.revelationType === 'Meccan' ? 'مكية' : 'مدنية'}</div>
          </div>
          <div class="badge">جـ ${juzOf(s.number, 1)}</div>
        </div>`).join('') || '<div class="muted" style="padding:10px">لا توجد نتائج.</div>';
    } else if (seg === 'juz') {
      list.innerHTML = JUZ_START.map(([s, a], i) => `
        <div class="idx ${curJuz === i + 1 ? 'current' : ''}" data-s="${s}" data-a="${a}">
          <div class="n">${i + 1}</div>
          <div>
            <div class="t">الجزء ${toArabicDigits(i + 1)}</div>
            <div class="s">يبدأ من ${esc(surahName(s))} آية ${a}</div>
          </div>
          <div class="badge"></div>
        </div>`).join('');
    } else {
      const sel = index.surah;
      const count = surahs[sel - 1]?.numberOfAyahs || 0;
      let grid = '';
      for (let a = 1; a <= count; a++) {
        grid += `<button data-a="${a}" class="${state.sel && state.sel.s === sel && state.sel.n === a ? 'current' : ''}">${toArabicDigits(a)}</button>`;
      }
      list.innerHTML = `
        <select id="ayahSurahSel">
          ${surahs.map((s) => `<option value="${s.number}" ${s.number === sel ? 'selected' : ''}>${s.number}. ${esc(s.name)}</option>`).join('')}
        </select>
        <div class="muted" style="padding:0 10px 6px">${count} آية</div>
        <div class="ayah-grid" id="ayahGrid">${grid}</div>`;
    }
  }

  $('#indexSeg').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-mode]');
    if (!b) return;
    index.mode = b.dataset.mode;
    renderIndex();
  });
  $('#indexSearch').addEventListener('input', renderIndex);
  $('#indexList').addEventListener('click', (e) => {
    const g = e.target.closest('#ayahGrid button');
    if (g) { goToAyah(index.surah, Number(g.dataset.a)); closeSide(); return; }
    const item = e.target.closest('.idx[data-s]');
    if (item) { goToAyah(Number(item.dataset.s), Number(item.dataset.a)); closeSide(); }
  });
  $('#indexList').addEventListener('change', (e) => {
    if (e.target.id === 'ayahSurahSel') { index.surah = Number(e.target.value); renderIndex(); }
  });

  // ---------- تحميل الصفحات ----------
  // الصفحة = آيات من إصدارات متعددة (نص + تلاوة + تفسير + ترجمة اختيارية)
  async function loadPage(p) {
    if (p < 1 || p > TOTAL_PAGES) return null;
    const key = p + '|' + [settings.riwaya, settings.reciter, settings.tafsir, settings.translation, settings.tajweed].join('|');
    if (pageCache.has(key)) return pageCache.get(key);

    const ids = [settings.riwaya, settings.reciter, settings.tafsir];
    if (settings.translation) ids.push(settings.translation);
    const withTajweed = settings.tajweed && settings.riwaya !== 'quran-tajweed';
    if (withTajweed) ids.push('quran-tajweed');

    const res = await Promise.all(ids.map((id) => getJSON(`${API}/page/${p}/${id}`)));
    const byId = {};
    ids.forEach((id, i) => { byId[id] = res[i].data.ayahs; });
    const base = byId[settings.riwaya];
    const markupSrc = settings.riwaya === 'quran-tajweed' ? base : (withTajweed ? byId['quran-tajweed'] : null);

    const ayahs = base.map((a, i) => {
      const markup = markupSrc ? markupSrc[i].text : null;
      return {
        s: a.surah.number,
        n: a.numberInSurah,
        g: a.number,
        page: p,
        juz: a.juz,
        text: clean(a.text),
        html: markup ? renderTajweed(markup) : esc(clean(a.text)),
        audio: byId[settings.reciter]?.[i]?.audio || null,
        tafsir: byId[settings.tafsir]?.[i]?.text || '',
        tr: settings.translation ? (byId[settings.translation]?.[i]?.text || '') : '',
      };
    });
    const obj = { p, ayahs };
    pageCache.set(key, obj);
    return obj;
  }

  // رقم الصفحة لأي آية (من بيانات السورة)
  async function pageOfAyah(s, a) {
    const json = await getJSON(`${API}/surah/${s}/quran-uthmani`);
    return json.data.ayahs[a - 1].page;
  }

  async function findAyah(s, a) {
    const p = await pageOfAyah(s, a);
    const pg = await loadPage(p);
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
    if (opts.save !== false) saveLast();
  }

  function renderPage(dir) {
    const pg = state.pg;
    let html = '';
    let openP = false;
    let lastS = 0;
    pg.ayahs.forEach((a) => {
      if (a.s !== lastS) {
        if (openP) { html += '</p>'; openP = false; }
        if (a.n === 1) {
          html += `<div class="surah-banner">${esc(surahName(a.s))}</div>`;
          if (a.s !== 1 && a.s !== 9) html += `<div class="bism">بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ</div>`;
        }
        html += '<p class="flow">';
        openP = true;
        lastS = a.s;
      }
      html += `<span class="ay" data-g="${a.g}">${a.html} <span class="end" data-act="tafsir" data-g="${a.g}" title="الآية">${toArabicDigits(a.n)}</span></span> `;
    });
    if (openP) html += '</p>';

    const body = $('#pageBody');
    body.innerHTML = html;

    const page = $('#page');
    page.classList.remove('flip-next', 'flip-prev');
    void page.offsetWidth;
    if (dir === 'next') page.classList.add('flip-next');
    if (dir === 'prev') page.classList.add('flip-prev');

    markSelection();
  }

  function markSelection() {
    $$('#pageBody .ay.sel').forEach((el) => el.classList.remove('sel'));
    $$('#pageBody .ay.playing').forEach((el) => el.classList.remove('playing'));
    if (state.sel) {
      const el = $(`#pageBody .ay[data-g="${state.sel.g}"]`);
      if (el) el.classList.add('sel');
    }
    if (play.cur) {
      const el = $(`#pageBody .ay[data-g="${play.cur.g}"]`);
      if (el) el.classList.add('playing');
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
    $('#pageNo').textContent = `صفحة ${toArabicDigits(pg.p)} من ${toArabicDigits(TOTAL_PAGES)}`;
    $('#pPrevS').disabled = pg.p <= 1;
    $('#pNextS').disabled = pg.p >= TOTAL_PAGES;
    $('#topTitle').textContent = `${surahName(state.sel.s)} · الجزء ${toArabicDigits(state.sel.juz || juz)} · ص ${toArabicDigits(pg.p)}`;

    // قائمة اختيار الآية تتبع السورة المحددة
    syncPlayControls();
    const bm = isBookmarked(state.sel.s, state.sel.n);
    $('#btnBm').textContent = bm ? '★ علامة' : '☆ علامة';
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
    btn.style.display = last.p === state.page ? 'none' : 'inline-block';
    btn.textContent = `↩ آخر موضع (ص ${toArabicDigits(last.p)})`;
  }

  // ---------- التقليب ----------
  function nextPage() { if (state.page < TOTAL_PAGES) showPage(state.page + 1, { dir: 'next' }); }
  function prevPage() { if (state.page > 1) showPage(state.page - 1, { dir: 'prev' }); }

  $('#pNextS').addEventListener('click', nextPage);
  $('#pPrevS').addEventListener('click', prevPage);

  // التقليب بالأسهم: → السابقة، ← التالية (نفس اتجاه السحب)
  document.addEventListener('keydown', (e) => {
    if (!$('#view-reader').classList.contains('active')) return;
    if (e.target.matches('input, select, textarea')) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); prevPage(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); nextPage(); }
  });

  // السحب باللمس أو الفأرة: يمين ← السابقة، يسار ← التالية
  let drag = null;
  const stage = $('#stage');
  stage.addEventListener('pointerdown', (e) => {
    if (e.target.closest('button, select')) return;
    drag = { x: e.clientX, y: e.clientY, t: Date.now(), hadSel: !!(window.getSelection && window.getSelection().toString().trim()) };
  });
  stage.addEventListener('pointerup', (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    const held = Date.now() - drag.t;
    const hadSel = drag.hadSel;
    drag = null;
    // لا تقلب الصفحة أثناء تحديد النص (ضغط مطوّل أو تحديد نشط)
    // التحديد الجديد يبدأ بضغط مطوّل؛ التحديد القديم لا يمنع السحب السريع
    const selectingNow = !!(window.getSelection && window.getSelection().toString().trim());
    if (held > 350 || (!hadSel && selectingNow)) return;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.6) {
      window.getSelection()?.removeAllRanges();
      if (dx > 0) nextPage(); else prevPage();
    }
  });
  stage.addEventListener('pointercancel', () => { drag = null; });

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
    // التفسير والترجمة يظهران من زر "التفسير" فقط. الكلمة الملونة تعرض قاعدة التجويد
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
  $('#playReciter').addEventListener('change', (e) => {
    onSettingChange('reciter', e.target.value);
  });

  $('#btnResume').addEventListener('click', () => {
    const last = getLast();
    if (last && last.p) showPage(last.p, { selG: last.g, save: false });
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
      showPage(ayah.page, { selG: ayah.g });
    } catch {
      toast('تعذر الوصول إلى الآية. تحقق من الاتصال.');
    }
  }

  // ---------- التفسير ----------
  function showTafsirPanel(a) {
    const book = TAFSIRS.find((t) => t[0] === settings.tafsir)?.[1] || '';
    $('#tafsirTitle').textContent = `${surahName(a.s)} - الآية ${toArabicDigits(a.n)}`;
    $('#tafsirAyah').textContent = a.text;
    $('#tafsirLabel').textContent = book || 'التفسير';
    $('#tafsirBody').textContent = a.tafsir || 'لا يوجد تفسير لهذه الآية في هذا الكتاب.';
    const hasTr = !!settings.translation;
    $('#transLabel').style.display = hasTr ? 'block' : 'none';
    $('#tafsirTrans').style.display = hasTr ? 'block' : 'none';
    $('#tafsirTrans').textContent = hasTr ? (a.tr || 'لا توجد ترجمة لهذه الآية.') : '';
    $('#tjPanel').classList.remove('show');
    $('#tafsirPanel').classList.add('show');
  }
  $('#tafsirClose').addEventListener('click', () => $('#tafsirPanel').classList.remove('show'));

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
    $('#btnBm').textContent = isBookmarked(state.sel.s, state.sel.n) ? '★ علامة' : '☆ علامة';
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
    $('#tfTafsir').textContent = a.tafsir || 'لا يوجد تفسير لهذه الآية في هذا الكتاب.';
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
  function setPlayerUI() {
    $('#player').classList.toggle('show', play.active);
    if (play.active && play.cur) {
      $('#playerInfo').textContent = `${play.label} · الآية ${play.cur.n}` +
        (play.repeatCount > 1 ? ` · تكرار ${play.repeatCount - play.repeatLeft + 1}/${play.repeatCount}` : '');
    }
    $('#pToggle').textContent = audio.paused ? '▶' : '⏸';
  }

  async function playAyah(a) {
    if (!a) { stopPlayback(); return; }
    play.cur = a;
    const local = await localAudioUrl(settings.reciter, a.s, a.n).catch(() => null);
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
    // تقليب الصفحة تلقائياً مع التلاوة
    if (a.page && a.page !== state.page && play.follow) {
      state.sel = a; state.selSurah = a.s;
      showPage(a.page, { selG: a.g, save: false });
    } else {
      markSelection();
      if (state.pg && state.pg.ayahs.some((x) => x.g === a.g)) {
        state.sel = a; state.selSurah = a.s; markSelection(); updateChrome();
      }
    }
    store.set('last', { p: a.page || state.page, s: a.s, a: a.n, g: a.g });
    renderLast();
    setPlayerUI();
  }

  // بدء تشغيل السورة من آية محددة حتى نهايتها
  async function startSurahPlay(s, n) {
    const first = await findAyah(s, n);
    if (!first) return;
    const label = `سورة ${surahNameShort(s)}`;
    play.label = label;
    play.repeatCount = 1; play.repeatLeft = 1;
    play.follow = true;
    play.nextFn = async (cur) => {
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
    play.active = false;
    play.cur = null;
    setPlayerUI();
    if (state.pg) markSelection();
    $$('.ayah.playing').forEach((el) => el.classList.remove('playing'));
  }

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

  // قياس ارتفاع شريط التشغيل ليترك المحتوى مساحة له (لا يغطي أزرار الصفحات)
  if (window.ResizeObserver) {
    new ResizeObserver(() => {
      document.documentElement.style.setProperty('--player-h', $('#player').offsetHeight + 'px');
    }).observe($('#player'));
  }

  $('#pToggle').addEventListener('click', () => {
    if (!play.active) return;
    audio.paused ? audio.play() : audio.pause();
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

  $('#btnPlaySurah').addEventListener('click', () => {
    const n = Number($('#playFrom').value) || 1;
    const s = Number($('#playSurah').value) || state.selSurah;
    startSurahPlay(s, n).catch(() => toast('تعذر بدء التلاوة'));
  });

  // ---------- الحفظ ----------
  async function fetchSurahForMemo(n) {
    const ids = [settings.riwaya, settings.reciter, settings.tafsir];
    if (settings.translation) ids.push(settings.translation);
    const json = await getJSON(`${API}/surah/${n}/editions/${ids.join(',')}`);
    const byId = {};
    json.data.forEach((ed) => { byId[ed.edition.identifier] = ed; });
    const base = byId[settings.riwaya];
    return base.ayahs.map((a, i) => ({
      s: n, n: a.numberInSurah, g: a.number, page: a.page,
      html: esc(clean(a.text)),
      audio: byId[settings.reciter]?.ayahs[i]?.audio || null,
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
      renderMemo();
    } catch {
      box.innerHTML = '<div class="muted">تعذر التحميل.</div>';
    }
  }

  function renderMemo() {
    $('#memoText').innerHTML = memo.ayahs.map((a) => `
      <div class="ayah ${memo.hidden ? 'hidden-text' : ''}" data-g="${a.g}">
        <span class="txt">${a.html}</span>
        <span class="end">${toArabicDigits(a.n)}</span>
      </div>`).join('') || '<div class="muted">حدد مقطعاً ثم اضغط تحميل.</div>';
  }
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
    if (last && last.p) { showView('reader'); showPage(last.p, { selG: last.g, save: false }); }
  });

  // ---------- الإعدادات ----------
  function fillSettings() {
    $('#setRiwaya').value = settings.riwaya;
    $('#setReciter').innerHTML = RECITERS.map(([id, name]) => `<option value="${id}">${name}</option>`).join('');
    $('#setReciter').value = settings.reciter;
    $('#playReciter').innerHTML = RECITERS.map(([id, name]) => `<option value="${id}">${name}</option>`).join('');
    $('#playReciter').value = settings.reciter;
    $('#setTafsir').innerHTML = TAFSIRS.map(([id, name]) => `<option value="${id}">${name}</option>`).join('');
    $('#setTafsir').value = settings.tafsir;
    $('#setTranslation').value = settings.translation;
    $('#tfBook').innerHTML = $('#setTafsir').innerHTML;
    $('#tfBook').value = settings.tafsir;
    $('#tfTrans').innerHTML = $('#setTranslation').innerHTML;
    $('#tfTrans').value = settings.translation;
    $('#setSize').value = settings.size;
    $('#sizeVal').textContent = settings.size + 'px';
    $('#setTajweed').checked = !!settings.tajweed;
    applySize();
  }
  function applySize() { document.documentElement.style.setProperty('--quran-size', settings.size + 'px'); }

  function onSettingChange(key, value) {
    settings[key] = value;
    saveSettings();
    if (key === 'reciter') { $('#setReciter').value = value; $('#playReciter').value = value; }
    if (key === 'tafsir') { $('#setTafsir').value = value; $('#tfBook').value = value; }
    if (key === 'translation') { $('#setTranslation').value = value; $('#tfTrans').value = value; }
    pageCache.clear();
    if (state.sel) {
      showPage(state.page, { selG: state.sel.g, save: false }).then(() => {
        if ($('#view-tafsir').classList.contains('active')) renderTafsirView();
      });
    }
  }
  $('#setRiwaya').addEventListener('change', (e) => onSettingChange('riwaya', e.target.value));
  $('#setReciter').addEventListener('change', (e) => onSettingChange('reciter', e.target.value));
  $('#setTafsir').addEventListener('change', (e) => onSettingChange('tafsir', e.target.value));
  $('#setTranslation').addEventListener('change', (e) => onSettingChange('translation', e.target.value));
  $('#setTajweed').addEventListener('change', (e) => onSettingChange('tajweed', e.target.checked));
  $('#setSize').addEventListener('input', (e) => {
    settings.size = Number(e.target.value);
    $('#sizeVal').textContent = settings.size + 'px';
    applySize(); saveSettings();
  });

  // ---------- التحميل للاستماع بدون إنترنت ----------
  // ---------- تحديث التطبيق من GitHub (بدون إعادة تحزيم) ----------
  const UPDATE_KEY = 'quran-update';
  const UPDATE_BASE = 'https://raw.githubusercontent.com/mosalah30688-gif/quran/main/update/';
  const storedUpdate = () => { try { return JSON.parse(localStorage.getItem(UPDATE_KEY) || 'null'); } catch (e) { return null; } };
  const currentVersion = () => (storedUpdate() || {}).version || window.APP_BUNDLE_VERSION || '1.0.0';
  function renderUpdateCard() {
    $('#verVal').textContent = currentVersion();
    $('#btnRestore').hidden = !storedUpdate();
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
      if (!manifest.version || !Array.isArray(manifest.files) || !manifest.files.includes('index.html')) throw new Error('bad manifest');
      // نسخة كاملة أحدث على الهاتف؟ تُثبَّت بدل تحديث الواجهة وحدها
      if (manifest.apk && manifest.apk.url && manifest.apk.version && hasNativePlugin('ApkUpdater')) {
        const nv = await nativeCall('ApkUpdater', 'getVersion').then((r) => r.version).catch(() => null);
        if (nv && newerVersion(manifest.apk.version, nv)) {
          await installNewApk(manifest.apk, st);
          btn.disabled = false;
          return;
        }
      }
      if (manifest.version === currentVersion()) {
        st.textContent = 'أنت على أحدث نسخة (' + manifest.version + ')';
        btn.disabled = false;
        return;
      }
      st.textContent = 'جاري تنزيل الإصدار ' + manifest.version + '...';
      const files = {};
      for (const f of manifest.files) {
        const r = await fetch(UPDATE_BASE + f + '?t=' + Date.now(), { cache: 'no-store' });
        if (!r.ok) throw new Error('file ' + f);
        const txt = await r.text();
        if (!txt.trim()) throw new Error('empty ' + f);
        files[f] = txt;
      }
      localStorage.setItem(UPDATE_KEY, JSON.stringify({ version: manifest.version, files: files }));
      st.textContent = 'تم التنزيل، جاري تطبيق التحديث...';
      setTimeout(() => location.reload(), 400);
    } catch (e) {
      st.textContent = 'تعذّر التحديث. تأكد من الاتصال بالإنترنت وحاول مرة أخرى.';
      btn.disabled = false;
    }
  }
  $('#btnUpdate').addEventListener('click', checkForUpdate);
  $('#btnRestore').addEventListener('click', () => {
    localStorage.removeItem(UPDATE_KEY);
    location.reload();
  });
  renderUpdateCard();

  // مصدر الملفات: everyayah.com (يسمح بالتحميل من المتصفح) - لكل آية ملف مستقل
  const OFFLINE_SRC = {
    'ar.alafasy': 'Alafasy_128kbps',
    'ar.abdurrahmaansudais': 'Abdurrahmaan_As-Sudais_192kbps',
    'ar.husary': 'Husary_128kbps',
    'ar.husarymujawwad': 'Husary_128kbps_Mujawwad',
    'ar.hudhaify': 'Hudhaify_128kbps',
    'ar.shaatree': 'Abu_Bakr_Ash-Shaatree_128kbps',
    'ar.hanirifai': 'Hani_Rifai_192kbps',
    'ar.ibrahimakhbar': 'Ibrahim_Akhdar_32kbps',
    'ar.aymanswoaid': 'Ayman_Sowaid_64kbps',
    'ar.abdullahbasfar': 'Abdullah_Basfar_192kbps',
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
    const folder = OFFLINE_SRC[reciter];
    if (!folder) return toast('هذا القارئ غير متاح للتحميل');
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
            const res = await fetch(`https://everyayah.com/data/${folder}/${pad3(r.s)}${pad3(r.n)}.mp3`);
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

  // ---------- التشغيل الأولي ----------
  applyTheme();
  fillSettings();
  renderBookmarks();
  renderLast();

  // الصفحة الرئيسية = الصفحة التي توقف عندها القارئ
  loadSurahs().finally(async () => {
    // التطبيق اشتغل بنجاح: نلغي علامة التحديث المعلّق
    localStorage.removeItem('quran-update-pending');
    const last = getLast();
    if (last && last.p) {
      showPage(last.p, { selG: last.g, save: false });
    } else {
      goToAyah(1, 1);
    }
  });

  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
})();
