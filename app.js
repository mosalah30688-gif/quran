/* القرآن الكريم - تطبيق ويب تقدمي
 * المصادر: api.alquran.cloud (النص والتفسير والتلاوات) + Leaflet (الخريطة)
 */
(() => {
  'use strict';

  const API = 'https://api.alquran.cloud/v1';

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
    translation: '', size: 28, tajweed: false, dark: false,
  };
  const VIEW_TITLES = {
    reader: 'القراءة', memo: 'وضع الحفظ', bookmarks: 'المحفوظات', map: 'مراكز المصاحف', settings: 'الإعدادات',
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // ---------- التخزين المحلي ----------
  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem('quran:' + key); return v === null ? fallback : JSON.parse(v); }
      catch { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem('quran:' + key, JSON.stringify(value)); } catch {}
    },
  };

  const settings = Object.assign({}, DEFAULTS, store.get('settings', {}));
  const saveSettings = () => store.set('settings', settings);

  let surahs = [];
  const cache = new Map();
  const audio = new Audio();
  audio.preload = 'auto';
  const play = { list: [], i: 0, repeatLeft: 1, repeatCount: 1, active: false, label: '' };
  let current = { n: 0, data: null };
  let memo = { ayahs: [], hidden: true, label: '' };
  let index = { mode: 'surah', surah: 1 };
  let suppressTrack = false;

  // ---------- أدوات مساعدة ----------
  const toArabicDigits = (s) => String(s).replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[d]);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clean = (s) => String(s ?? '').replace(/\uFEFF/g, '');

  // رقم الجزء لأي موضع (سورة، آية)
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

  // تحويل ترميز التجويد [code[text] إلى عناصر ملوّنة
  function renderTajweed(raw) {
    let s = esc(clean(raw));
    s = s.replace(/\[([a-z]+)(?::\d+)?\[([^\[\]]*)\]/g, '<span class="tj-$1">$2</span>');
    return s.replace(/\[|\]/g, '');
  }

  // ---------- التنقل ----------
  function showView(name) {
    $$('#tabs button').forEach((b) => b.classList.toggle('active', b.dataset.view === name));
    $$('section.view').forEach((s) => s.classList.toggle('active', s.id === 'view-' + name));
    $('#topTitle').textContent = name === 'reader' && current.data
      ? `${current.data.info.name} · الجزء ${juzOf(current.n, 1)}`
      : (VIEW_TITLES[name] || '');
    if (name === 'map') setTimeout(() => { if (map) map.invalidateSize(); }, 50);
    if (name === 'bookmarks') renderBookmarks();
    if (name !== 'reader') $('#content').scrollTo({ top: 0 });
  }
  function closeSide() { document.body.classList.remove('side-open'); }

  $('#tabs').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-view]');
    if (!b) return;
    showView(b.dataset.view);
    closeSide();
  });
  $('#menuBtn').addEventListener('click', () => document.body.classList.toggle('side-open'));
  $('#backdrop').addEventListener('click', closeSide);

  // ---------- الوضع الليلي ----------
  function applyTheme() {
    document.body.classList.toggle('dark', !!settings.dark);
    $('#themeBtn').textContent = settings.dark ? '☀️' : '🌙';
  }
  $('#themeBtn').addEventListener('click', () => {
    settings.dark = !settings.dark; saveSettings(); applyTheme();
  });

  // ---------- الفهرس الجانبي: سورة / جزء / آية ----------
  async function loadSurahs() {
    try {
      const json = await getJSON(API + '/surah');
      surahs = json.data;
    } catch {
      $('#indexList').innerHTML = '<div class="muted" style="padding:10px">تعذر تحميل الفهرس. تحقق من الاتصال بالإنترنت.</div>';
      return;
    }
    fillMemoSelect();
    renderIndex();
  }

  function fillMemoSelect() {
    $('#memoSurah').innerHTML = surahs.map((s) => `<option value="${s.number}">${s.number}. ${esc(s.name)}</option>`).join('');
  }

  function renderIndex() {
    const seg = index.mode;
    $$('#indexSeg button').forEach((b) => b.classList.toggle('on', b.dataset.mode === seg));
    $('#indexSearchWrap').style.display = seg === 'surah' ? 'block' : 'none';
    const list = $('#indexList');
    if (!surahs.length) return;

    const curN = current.n;
    if (seg === 'surah') {
      const term = $('#indexSearch').value.trim().toLowerCase();
      const items = surahs.filter((s) =>
        !term || String(s.number) === term || s.englishName.toLowerCase().includes(term) ||
        s.englishNameTranslation.toLowerCase().includes(term) || s.name.includes($('#indexSearch').value.trim()));
      list.innerHTML = items.map((s) => `
        <div class="idx ${s.number === curN ? 'current' : ''}" data-s="${s.number}" data-a="1">
          <div class="n">${s.number}</div>
          <div>
            <div class="t">${esc(s.name)}</div>
            <div class="s">${esc(s.englishName)} · ${s.numberOfAyahs} آية · ${s.revelationType === 'Meccan' ? 'مكية' : 'مدنية'}</div>
          </div>
          <div class="badge">جـ ${juzOf(s.number, 1)}</div>
        </div>`).join('') || '<div class="muted" style="padding:10px">لا توجد نتائج.</div>';
    } else if (seg === 'juz') {
      list.innerHTML = JUZ_START.map(([s, a], i) => `
        <div class="idx ${juzOf(curN || 1, 1) === i + 1 && current.data ? 'current' : ''}" data-s="${s}" data-a="${a}">
          <div class="n">${i + 1}</div>
          <div>
            <div class="t">الجزء ${toArabicDigits(i + 1)}</div>
            <div class="s">يبدأ من ${esc(surahs[s - 1]?.name || '')} آية ${a}</div>
          </div>
          <div class="badge"></div>
        </div>`).join('');
    } else {
      // الآية: اختيار السورة ثم شبكة الآيات
      const sel = index.surah;
      const count = surahs[sel - 1]?.numberOfAyahs || 0;
      let grid = '';
      for (let a = 1; a <= count; a++) {
        grid += `<button data-a="${a}" class="${current.n === sel && current.data && curN === sel && a === (store.get('last', {}).a || 0) ? 'current' : ''}">${toArabicDigits(a)}</button>`;
      }
      list.innerHTML = `
        <select id="ayahSurahSel">
          ${surahs.map((s) => `<option value="${s.number}" ${s.number === sel ? 'selected' : ''}>${s.number}. ${esc(s.name)}</option>`).join('')}
        </select>
        <div class="muted" style="padding:0 10px 6px">${surahs[sel - 1] ? esc(surahs[sel - 1].name) + ' · ' + count + ' آية' : ''}</div>
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
    const grid = e.target.closest('#ayahGrid button');
    if (grid) {
      jumpTo(index.surah, Number(grid.dataset.a));
      closeSide();
      return;
    }
    const item = e.target.closest('.idx[data-s]');
    if (item) {
      openSurah(Number(item.dataset.s), Number(item.dataset.a));
      closeSide();
    }
  });
  $('#indexList').addEventListener('change', (e) => {
    if (e.target.id === 'ayahSurahSel') {
      index.surah = Number(e.target.value);
      renderIndex();
    }
  });

  function jumpTo(s, a) {
    if (current.data && current.n === s) {
      scrollToAyah(a, true);
      setLast(s, a);
      showView('reader');
    } else {
      openSurah(s, a);
    }
  }

  // ---------- تحميل السورة بعدة إصدارات ----------
  function editionsFor(includeTajweed) {
    const ids = [settings.riwaya, settings.reciter, settings.tafsir];
    if (settings.translation) ids.push(settings.translation);
    if (includeTajweed && settings.riwaya !== 'quran-tajweed') ids.push('quran-tajweed');
    return ids;
  }

  async function fetchSurah(n) {
    const ids = editionsFor(settings.tajweed);
    const json = await getJSON(`${API}/surah/${n}/editions/${ids.join(',')}`);
    const byId = {};
    json.data.forEach((ed) => { byId[ed.edition.identifier] = ed; });
    const base = byId[settings.riwaya];
    const markupSource = settings.riwaya === 'quran-tajweed' ? base
      : (settings.tajweed && byId['quran-tajweed'] ? byId['quran-tajweed'] : null);
    const ayahs = base.ayahs.map((a, idx) => {
      const markup = markupSource ? markupSource.ayahs[idx].text : null;
      return {
        n: a.numberInSurah,
        text: clean(a.text),
        html: markup ? renderTajweed(markup) : esc(clean(a.text)),
        audio: (byId[settings.reciter]?.ayahs[idx]?.audio) || null,
        tafsir: byId[settings.tafsir]?.ayahs[idx]?.text || '',
        tr: settings.translation ? (byId[settings.translation]?.ayahs[idx]?.text || '') : '',
      };
    });
    const meta = surahs[n - 1] || {};
    return {
      info: {
        number: n, name: meta.name, englishName: meta.englishName,
        translation: meta.englishNameTranslation, ayahs: meta.numberOfAyahs || ayahs.length,
        type: meta.revelationType,
      },
      ayahs,
    };
  }

  // ---------- آخر موضع (الصفحة الرئيسية) ----------
  const getLast = () => store.get('last', { s: 1, a: 1 });
  function setLast(s, a) {
    const prev = getLast();
    if (prev.s === s && prev.a === a) return;
    store.set('last', { s, a });
    renderLast();
    $$('#readerText .ayah.last-read').forEach((el) => el.classList.remove('last-read'));
    const el = document.querySelector(`#readerText .ayah[data-n="${a}"]`);
    if (el && current.n === s) el.classList.add('last-read');
    updateResumeBtn();
  }

  function updateResumeBtn() {
    const last = getLast();
    const btn = $('#btnResume');
    btn.style.display = current.n === last.s ? 'none' : 'inline-block';
    btn.textContent = `↩ الذهاب لآخر موضع (${surahs[last.s - 1]?.name || ''} ${last.a})`;
  }

  function scrollToAyah(a, smooth) {
    const el = document.querySelector(`#readerText .ayah[data-n="${a}"]`);
    if (!el) return;
    suppressTrack = true;
    el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
    setTimeout(() => { suppressTrack = false; }, smooth ? 900 : 150);
  }

  // يحدد الآية الظاهرة أعلى الشاشة ويحفظها تلقائياً
  let trackTimer = null;
  function trackPosition() {
    if (suppressTrack || !current.data || !$('#view-reader').classList.contains('active')) return;
    const els = $$('#readerText .ayah');
    for (const el of els) {
      if (el.getBoundingClientRect().bottom > 120) {
        setLast(current.n, Number(el.dataset.n));
        return;
      }
    }
  }
  $('#content').addEventListener('scroll', () => {
    clearTimeout(trackTimer);
    trackTimer = setTimeout(trackPosition, 120);
  }, { passive: true });

  // ---------- فتح سورة ----------
  async function openSurah(n, startAyah = 1, opts = {}) {
    showView('reader');
    const box = $('#readerText');
    if (!current.data || current.n !== n) {
      box.innerHTML = '<div class="muted">جارٍ تحميل السورة...</div>';
    }
    try {
      const data = await fetchSurah(n);
      current = { n, data };
      renderInfo(data.info);
      renderReader(data);
      setLast(n, startAyah);
      renderLast();
      updateResumeBtn();
      showView('reader');
      renderIndex();
      if (startAyah > 1 || opts.instant) {
        requestAnimationFrame(() => scrollToAyah(startAyah, !opts.instant));
      }
      if (opts.autoPlay) playQueue(data.ayahs, `سورة ${data.info.englishName}`);
    } catch {
      box.innerHTML = '<div class="muted">تعذر تحميل السورة. تحقق من الاتصال بالإنترنت.</div>';
    }
  }

  function renderInfo(info) {
    const juzFrom = juzOf(info.number, 1);
    const juzTo = juzOf(info.number, info.ayahs);
    const juzText = juzFrom === juzTo ? `الجزء ${juzFrom}` : `الأجزاء ${juzFrom} - ${juzTo}`;
    $('#readerInfo').innerHTML = `
      <div class="row" style="justify-content:space-between">
        <div>
          <div style="font-family:Amiri,serif;font-size:26px">${esc(info.name)}</div>
          <div class="muted">${esc(info.englishName)} · ${esc(info.translation || '')} · ${info.ayahs} آية · ${info.type === 'Meccan' ? 'مكية' : 'مدنية'} · ${juzText}</div>
        </div>
        <div class="muted">${RECITERS.find((r) => r[0] === settings.reciter)?.[1] || ''}</div>
      </div>`;
    $('#topTitle').textContent = `${info.name} · الجزء ${juzFrom}`;
  }

  function renderReader(data) {
    const box = $('#readerText');
    const showTafsir = box.dataset.tafsir === '1';
    box.innerHTML = data.ayahs.map((a) => {
      const bm = isBookmarked(data.info.number, a.n);
      return `
      <div class="ayah" id="a-${a.n}" data-n="${a.n}">
        <span class="txt">${a.html}</span>
        <span class="mark" data-act="tafsir" title="التفسير">${toArabicDigits(a.n)}</span>
        <span class="actions">
          <button data-act="play" title="تشغيل">▶</button>
          <button data-act="bm" class="${bm ? 'on' : ''}" title="علامة">${bm ? '★' : '☆'}</button>
        </span>
        ${a.tr ? `<span class="tr">${esc(a.tr)}</span>` : ''}
        <div class="tf-inline muted" style="display:${showTafsir ? 'block' : 'none'};font-size:16px;line-height:1.9;margin-top:6px">${esc(a.tafsir)}</div>
      </div>`;
    }).join('');
    const last = getLast();
    if (last.s === data.info.number) {
      const el = box.querySelector(`.ayah[data-n="${last.a}"]`);
      if (el) el.classList.add('last-read');
    }
  }

  $('#readerText').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn || !current.data) return;
    const ayahEl = btn.closest('.ayah');
    const n = Number(ayahEl.dataset.n);
    const a = current.data.ayahs[n - 1];
    const act = btn.dataset.act;
    if (act === 'play') {
      playQueue(current.data.ayahs.slice(n - 1), `سورة ${current.data.info.englishName}`);
    } else if (act === 'bm') {
      toggleBookmark(current.data.info.number, n, current.data.info.englishName);
      const on = isBookmarked(current.data.info.number, n);
      btn.textContent = on ? '★' : '☆';
      btn.classList.toggle('on', on);
    } else if (act === 'tafsir') {
      showTafsirPanel(current.data.info, a);
    }
    setLast(current.n, n);
  });

  $('#btnTafsirToggle').addEventListener('click', () => {
    const box = $('#readerText');
    box.dataset.tafsir = box.dataset.tafsir === '1' ? '0' : '1';
    $$('.tf-inline', box).forEach((el) => { el.style.display = box.dataset.tafsir === '1' ? 'block' : 'none'; });
  });

  $('#btnResume').addEventListener('click', () => {
    const last = getLast();
    jumpTo(last.s, last.a);
  });

  $('#btnPlaySurah').addEventListener('click', () => {
    if (!current.data) return;
    playQueue(current.data.ayahs, `سورة ${current.data.info.englishName}`);
  });

  // ---------- التفسير (لوحة) ----------
  function showTafsirPanel(info, a) {
    $('#tafsirTitle').textContent = `${info.name} - الآية ${a.n} (${TAFSIRS.find((t) => t[0] === settings.tafsir)?.[1] || ''})`;
    $('#tafsirBody').textContent = a.tafsir || 'لا يوجد تفسير لهذه الآية في هذا الكتاب.';
    $('#tafsirPanel').classList.add('show');
  }
  $('#tafsirClose').addEventListener('click', () => $('#tafsirPanel').classList.remove('show'));

  // ---------- المشغل الصوتي ----------
  function setPlayerUI() {
    const cur = play.list[play.i];
    $('#player').classList.toggle('show', play.active);
    if (play.active && cur) {
      $('#playerInfo').textContent = `${play.label} · الآية ${cur.n}` + (play.repeatCount > 1 ? ` · تكرار ${play.repeatCount - play.repeatLeft + 1}/${play.repeatCount}` : '');
    }
    $('#pToggle').textContent = audio.paused ? '▶' : '⏸';
  }

  function highlight(n) {
    $$('.ayah.playing').forEach((el) => el.classList.remove('playing'));
    const el = document.querySelector(`#readerText .ayah[data-n="${n}"]`) || document.querySelector(`#memoText .ayah[data-n="${n}"]`);
    if (el) {
      el.classList.add('playing');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  function playIndex(i) {
    if (i < 0 || i >= play.list.length) { stopPlayback(); return; }
    play.i = i;
    const a = play.list[i];
    if (!a.audio) { toast('لا يوجد تسجيل لهذه الآية مع القارئ المختار'); playIndex(i + 1); return; }
    audio.src = a.audio;
    audio.play().catch(() => toast('تعذر تشغيل الصوت. اضغط تشغيل مرة أخرى.'));
    play.active = true;
    highlight(a.n);
    if (current.data && $('#readerText .ayah[data-n="' + a.n + '"]')) setLast(current.n, a.n);
    setPlayerUI();
  }

  function playQueue(list, label, repeat = 1) {
    play.list = list;
    play.label = label;
    play.repeatCount = repeat;
    play.repeatLeft = repeat;
    playIndex(0);
  }

  function stopPlayback() {
    audio.pause();
    audio.removeAttribute('src');
    play.active = false;
    $$('.ayah.playing').forEach((el) => el.classList.remove('playing'));
    setPlayerUI();
  }

  audio.addEventListener('ended', () => {
    if (play.repeatLeft > 1) {
      play.repeatLeft--;
      audio.currentTime = 0;
      audio.play();
      setPlayerUI();
      return;
    }
    play.repeatLeft = play.repeatCount;
    playIndex(play.i + 1);
  });
  audio.addEventListener('play', setPlayerUI);
  audio.addEventListener('pause', setPlayerUI);

  $('#pToggle').addEventListener('click', () => {
    if (!play.active) return;
    audio.paused ? audio.play() : audio.pause();
  });
  $('#pNext').addEventListener('click', () => { play.repeatLeft = play.repeatCount; playIndex(play.i + 1); });
  $('#pPrev').addEventListener('click', () => { play.repeatLeft = play.repeatCount; playIndex(Math.max(0, play.i - 1)); });
  $('#pStop').addEventListener('click', stopPlayback);

  // ---------- الحفظ ----------
  async function loadMemo() {
    const n = Number($('#memoSurah').value);
    const from = Math.max(1, parseInt($('#memoFrom').value, 10) || 1);
    const to = parseInt($('#memoTo').value, 10) || from;
    const box = $('#memoText');
    box.innerHTML = '<div class="muted">جارٍ التحميل...</div>';
    try {
      const data = await fetchSurah(n);
      const max = data.ayahs.length;
      const start = Math.min(from, max), end = Math.min(Math.max(to, start), max);
      memo.ayahs = data.ayahs.slice(start - 1, end).map((a) => Object.assign({}, a, { n: a.n }));
      memo.label = `حفظ ${data.info.englishName} ${start}-${end}`;
      renderMemo();
    } catch {
      box.innerHTML = '<div class="muted">تعذر التحميل.</div>';
    }
  }

  function renderMemo() {
    $('#memoText').innerHTML = memo.ayahs.map((a) => `
      <div class="ayah ${memo.hidden ? 'hidden-text' : ''}" data-n="${a.n}">
        <span class="txt">${a.html}</span>
        <span class="mark">${toArabicDigits(a.n)}</span>
      </div>`).join('') || '<div class="muted">حدد مقطعاً ثم اضغط تحميل.</div>';
  }

  $('#btnMemoLoad').addEventListener('click', loadMemo);
  $('#btnMemoHide').addEventListener('click', () => { memo.hidden = !memo.hidden; renderMemo(); });
  $('#btnMemoPlay').addEventListener('click', () => {
    if (!memo.ayahs.length) return toast('حمّل المقطع أولاً');
    playQueue(memo.ayahs, memo.label, Number($('#memoRepeat').value));
  });
  $('#memoText').addEventListener('click', (e) => {
    const ayah = e.target.closest('.ayah');
    if (ayah && memo.hidden) ayah.classList.toggle('hidden-text');
  });

  // ---------- العلامات وآخر قراءة ----------
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
    if (b) { jumpTo(Number(b.dataset.goS), Number(b.dataset.goA)); showView('reader'); }
  });

  function renderLast() {
    const last = getLast();
    const s = surahs[last.s - 1];
    $('#lastRead').innerHTML = `<div class="row" style="justify-content:space-between">
      <span>${s ? esc(s.name) : ''} - الجزء ${juzOf(last.s, last.a)} - الآية ${last.a}</span>
      <button class="btn small" data-go-s="${last.s}" data-go-a="${last.a}">متابعة</button></div>`;
  }
  $('#lastRead').addEventListener('click', (e) => {
    const b = e.target.closest('[data-go-s]');
    if (b) { jumpTo(Number(b.dataset.goS), Number(b.dataset.goA)); showView('reader'); }
  });

  // ---------- الإعدادات ----------
  function fillSettings() {
    $('#setRiwaya').value = settings.riwaya;
    $('#setReciter').innerHTML = RECITERS.map(([id, name]) => `<option value="${id}">${name}</option>`).join('');
    $('#setReciter').value = settings.reciter;
    $('#setTafsir').innerHTML = TAFSIRS.map(([id, name]) => `<option value="${id}">${name}</option>`).join('');
    $('#setTafsir').value = settings.tafsir;
    $('#setTranslation').value = settings.translation;
    $('#setSize').value = settings.size;
    $('#sizeVal').textContent = settings.size + 'px';
    $('#setTajweed').checked = !!settings.tajweed;
    applySize();
  }
  function applySize() {
    document.documentElement.style.setProperty('--quran-size', settings.size + 'px');
  }
  function onSettingChange(key, value, reloadReader) {
    settings[key] = value;
    saveSettings();
    if (reloadReader && current.n) openSurah(current.n, getLast().s === current.n ? getLast().a : 1, { instant: true });
  }
  $('#setRiwaya').addEventListener('change', (e) => onSettingChange('riwaya', e.target.value, true));
  $('#setReciter').addEventListener('change', (e) => onSettingChange('reciter', e.target.value, true));
  $('#setTafsir').addEventListener('change', (e) => onSettingChange('tafsir', e.target.value, false));
  $('#setTranslation').addEventListener('change', (e) => onSettingChange('translation', e.target.value, true));
  $('#setTajweed').addEventListener('change', (e) => onSettingChange('tajweed', e.target.checked, true));
  $('#setSize').addEventListener('input', (e) => {
    settings.size = Number(e.target.value);
    $('#sizeVal').textContent = settings.size + 'px';
    applySize(); saveSettings();
  });
  $('#btnClearCache').addEventListener('click', async () => {
    cache.clear();
    if ('caches' in window) { for (const k of await caches.keys()) await caches.delete(k); }
    toast('تم مسح الذاكرة المؤقتة');
  });

  // ---------- خريطة مراكز المصاحف ----------
  let map = null;
  const markers = {};
  async function initMap() {
    if (typeof L === 'undefined') { $('#map').innerHTML = '<div class="card">تعذر تحميل الخريطة (يلزم اتصال بالإنترنت).</div>'; return; }
    map = L.map('map').setView([25, 30], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, attribution: '&copy; OpenStreetMap',
    }).addTo(map);
    try {
      const res = await fetch('data/centers.json');
      renderCenters(await res.json());
    } catch {
      $('#centerList').innerHTML = '<div class="muted">تعذر تحميل بيانات المراكز.</div>';
    }
  }

  function renderCenters(centers) {
    const colors = { printing: '#0f5b4c', memorization: '#b8860b' };
    centers.forEach((c, idx) => {
      const m = L.circleMarker([c.lat, c.lng], {
        radius: 9, color: '#fff', weight: 2, fillColor: colors[c.type] || '#0f5b4c', fillOpacity: 1,
      }).addTo(map);
      m.bindPopup(`<strong>${esc(c.name)}</strong><br>${esc(c.city)}, ${esc(c.country)}`);
      markers[idx] = m;
    });
    $('#centerList').innerHTML = centers.map((c, idx) => `
      <div class="card center-card" data-idx="${idx}" style="cursor:pointer">
        ${c.image ? `<img src="${esc(c.image)}" alt="${esc(c.name)}" loading="lazy" />` : ''}
        <div style="font-weight:700">${esc(c.name)}</div>
        <div class="muted">${esc(c.city)}، ${esc(c.country)} ${c.founded ? '· تأسس ' + esc(c.founded) : ''}</div>
        <p style="margin:8px 0 0;line-height:1.8">${esc(c.description || '')}</p>
      </div>`).join('');
  }
  $('#centerList').addEventListener('click', (e) => {
    const card = e.target.closest('[data-idx]');
    if (!card || !map) return;
    const m = markers[card.dataset.idx];
    if (m) { map.flyTo(m.getLatLng(), 6); m.openPopup(); }
  });

  // ---------- التشغيل ----------
  applyTheme();
  fillSettings();
  renderBookmarks();
  renderLast();
  initMap();

  // الصفحة الرئيسية = آخر موضع توقف عنده القارئ (بعد تحميل الفهرس)
  loadSurahs().then(() => {
    const last = getLast();
    openSurah(last.s, last.a, { instant: true });
  });

  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
})();
