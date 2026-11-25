'use strict';

/*
 * أذان مقامات مشاري راشد العفاسي: تسعة مقامات، كل ملف موجود ومطابق لبصمته،
 * والمصدر مسجَّل، والواجهة تعرض المقام وتفلتره.
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const ROOT = path.join(__dirname, '..');
const DATA = require('../prayer-data.js');
const read = (file) => fs.readFileSync(path.join(ROOT, file), 'utf8');
const exists = (file) => fs.existsSync(path.join(ROOT, file));

const MAQAMAT = DATA.adhans.filter((item) => item.maqam);
const CATALOG = JSON.parse(read('adhan-catalog.json'));
const CATALOG_MAQAMAT = CATALOG.items.filter((item) => item.maqam);

test('المقامات: تسعة مقامات للعفاسي مع تسمية عربية ومدة وأصل', () => {
  assert.equal(MAQAMAT.length, 9);
  const labels = MAQAMAT.map((item) => item.maqamLabel);
  ['مقام الكرد', 'مقام الكرد المنخفض', 'مقام البيات', 'مقام الصبا', 'مقام الحجاز',
    'مقام النهاوند', 'مقام الرست', 'مقام السيكاه', 'مقام العجم'].forEach((label) => {
    assert.ok(labels.includes(label), `مفقود: ${label}`);
  });
  MAQAMAT.forEach((item) => {
    assert.ok(item.name.startsWith('أذان العفاسي'), item.id);
    assert.ok(item.seconds > 90 && item.seconds < 400, item.id);
  });
});

test('المقامات: كل ملف صوتي موجود وحجمه وبصمته مطابقان للكتالوج', () => {
  assert.equal(CATALOG_MAQAMAT.length, MAQAMAT.length);
  MAQAMAT.forEach((item) => {
    const entry = CATALOG_MAQAMAT.find((c) => c.id === item.id);
    assert.ok(entry, `مدخل الكتالوج مفقود: ${item.id}`);
    const file = path.join('audio/adhans-maqamat', entry.file);
    assert.ok(exists(file), `الملف مفقود: ${file}`);
    const bytes = fs.readFileSync(path.join(ROOT, file));
    assert.ok(bytes.length > 200_000, `${item.id}: ملف صغير جدًا`);
    assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), entry.sha256,
      `${item.id}: البصمة لا تطابق الكتالوج`);
    assert.match(entry.url, /^https:\/\/raw\.githubusercontent\.com\/mosalah30688-gif\/quran\/main\/audio\/adhans-maqamat\//);
  });
});

test('المقامات: المضغوط داخل الحزمة يعمل دون إنترنت (أصول + ويب)', () => {
  const bundled = MAQAMAT.filter((item) => item.bundled);
  assert.deepEqual(bundled.map((item) => item.maqam).sort(), ['kurd', 'kurd-low']);
  bundled.forEach((item) => {
    assert.ok(exists(`audio/adhans/${item.id}.mp3`), `نسخة الويب: ${item.id}`);
    assert.ok(exists(`android/app/src/main/assets/adhans/${item.id}.mp3`), `أصول أندرويد: ${item.id}`);
    assert.ok(fs.statSync(path.join(ROOT, `audio/adhans/${item.id}.mp3`)).size > 200_000);
    assert.equal(item.local, `audio/adhans/${item.id}.mp3`);
  });
  // البقية تُنزَّل من القناة عند الطلب ولا تُثقل الحزمة
  MAQAMAT.filter((item) => !item.bundled).forEach((item) => {
    assert.equal(item.local, '', item.id);
  });
});

test('المقامات: المصدر موثّق في ملف الاعتماد', () => {
  const audit = read('audit/ADHAN_MAQAMAT_PROVENANCE.md');
  MAQAMAT.forEach((item) => {
    assert.ok(audit.includes(item.id), `المعرّف غير موثّق: ${item.id}`);
  });
  const sources = CATALOG_MAQAMAT.map((item) => item.source && item.source.video).filter(Boolean);
  assert.equal(sources.length, MAQAMAT.length, 'كل مقام له مصدر مسجَّل');
  assert.equal(new Set(sources).size, sources.length, 'لا تكرار للمصادر');
});

test('المقامات: الواجهة تعرض المقام في السطر وتفلتره بزر سريع', () => {
  const ui = read('prayer-ui.js');
  assert.match(ui, /item\.maqamLabel \? `<b class="pt-maqam">/);
  assert.match(ui, /data-name="\$\{esc\(item\.name\)\} \$\{esc\(item\.region \|\| ''\)\} \$\{esc\(item\.maqamLabel \|\| ''\)\}/);
  assert.match(ui, /data-adhan-chip="maqam"/);
  assert.match(ui, /state\.adhanFilter = chip\.dataset\.adhanChip === 'maqam' \? 'مقام' : '';/);
  assert.match(ui, /ابحث باسم المؤذن أو المقام/);
  const html = read('index.html');
  assert.match(html, /\.pt-chip\.is-on \{/);
  assert.match(html, /\.pt-maqam \{/);
});

test('المقامات: ملف محلي ناقص يتحول إلى البث من الشبكة بدل الفشل الصامت', () => {
  const ui = read('prayer-ui.js');
  assert.match(ui, /let usingLocal = Boolean\(local\);/);
  assert.match(ui, /if \(usingLocal && item\.url\) \{/);
  assert.match(ui, /audio\.src = item\.url; await audio\.play\(\); return;/);
});
