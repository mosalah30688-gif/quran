'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const PT = require('../prayer-times.js');
const DATA = require('../prayer-data.js');

const at = (day) => new Date(day + 'T10:00:00Z');
const hhmm = (value) => PT.formatMinutes(value, true);

test('المواقيت تطابق الحساب المرجعي للقاهرة ومكة', () => {
  const cairo = PT.times({
    date: at('2026-11-06'), lat: 30.0444, lng: 31.2357, timezone: 2, method: 'egypt',
  });
  assert.equal(hhmm(cairo.fajr), '04:44');
  assert.equal(hhmm(cairo.sunrise), '06:13');
  assert.equal(hhmm(cairo.dhuhr), '11:39');
  assert.equal(hhmm(cairo.asr), '14:43');
  assert.equal(hhmm(cairo.isha), '18:24');

  const makkah = PT.times({
    date: at('2026-11-06'), lat: 21.4225, lng: 39.8262, timezone: 3, method: 'makkah',
  });
  assert.equal(hhmm(makkah.fajr), '05:08');
  assert.equal(hhmm(makkah.dhuhr), '12:04');
  assert.equal(hhmm(makkah.maghrib), '17:42');
  // أم القرى: العشاء ٩٠ دقيقة بعد المغرب
  assert.equal(Math.round((makkah.isha - makkah.maghrib) * 60), 90);
});

test('العصر الحنفي متأخر عن الجمهور', () => {
  const base = { date: at('2026-11-06'), lat: 30.0444, lng: 31.2357, timezone: 2, method: 'egypt' };
  const shafi = PT.times({ ...base, madhab: 'shafi' });
  const hanafi = PT.times({ ...base, madhab: 'hanafi' });
  assert.ok(hanafi.asr - shafi.asr > 0.5, 'الحنفي يجب أن يتأخر نحو ٤٥ دقيقة');
});

test('التصحيحات اليدوية تُزحزح الوقت بالدقائق', () => {
  const base = { date: at('2026-11-06'), lat: 30.0444, lng: 31.2357, timezone: 2, method: 'egypt' };
  const plain = PT.times(base);
  const shifted = PT.times({ ...base, adjustments: { fajr: 3, maghrib: -2 } });
  assert.equal(Math.round((shifted.fajr - plain.fajr) * 60), 3);
  assert.equal(Math.round((shifted.maghrib - plain.maghrib) * 60), -2);
});

test('خطوط العرض العالية لا تُنتج أوقاتًا مفقودة', () => {
  const oslo = PT.times({
    date: at('2026-06-21'), lat: 59.9139, lng: 10.7522, timezone: 2,
    method: 'mwl', highLatitude: 'seventh',
  });
  assert.ok(Number.isFinite(oslo.fajr) && Number.isFinite(oslo.isha));
  assert.ok(oslo.fajr < oslo.sunrise && oslo.isha > oslo.maghrib);
});

test('الموعد القادم يتقدّم مع الوقت', () => {
  const options = {
    lat: 30.0444, lng: 31.2357, timezone: 2, method: 'egypt',
  };
  const early = PT.next({ ...options, date: new Date('2026-11-06T02:00:00Z') });
  const late = PT.next({ ...options, date: new Date('2026-11-06T20:00:00Z') });
  assert.equal(early.key, 'fajr');
  assert.equal(late.key, 'fajr');
  assert.equal(late.today, false, 'بعد العشاء يكون الفجر غدًا');
});

test('اتجاه القبلة والمسافة إلى الكعبة', () => {
  const cairo = PT.qibla(30.0444, 31.2357);
  assert.ok(Math.abs(cairo.bearing - 136.1) < 1.5, `قبلة القاهرة ${cairo.bearing}`);
  assert.ok(Math.abs(cairo.distance - 1287) < 40, `مسافة القاهرة ${cairo.distance}`);
  const newYork = PT.qibla(40.7128, -74.006);
  assert.ok(Math.abs(newYork.bearing - 58.5) < 2, `قبلة نيويورك ${newYork.bearing}`);
});

test('موضع الشمس محسوب لطريقة الاتجاه بالشمس', () => {
  const sun = PT.sunAzimuth({
    date: new Date('2026-11-06T10:00:00Z'), lat: 30.0444, lng: 31.2357, timezone: 2,
  });
  assert.ok(sun.azimuth >= 0 && sun.azimuth < 360);
  assert.ok(sun.altitude > 0 && sun.altitude < 90);
});

test('بيانات المدن والأذانات سليمة', () => {
  assert.ok(DATA.cities.length >= 90, 'قائمة المدن موسّعة');
  DATA.cities.forEach((city) => {
    assert.ok(typeof city.n === 'string' && city.n.length);
    assert.ok(Math.abs(city.lat) <= 90 && Math.abs(city.lng) <= 180, city.n);
    assert.ok(PT.METHODS[city.m], `طريقة غير معروفة: ${city.m}`);
  });
  assert.ok(DATA.adhans.length >= 15, 'قائمة المؤذنين موسّعة');
  const ids = new Set();
  DATA.adhans.forEach((item) => {
    assert.ok(!ids.has(item.id), `معرّف مكرر: ${item.id}`);
    ids.add(item.id);
    assert.match(item.url, /^https:\/\/archive\.org\/download\/[^"]+\.mp3$/);
    assert.ok(item.seconds > 30 && item.seconds < 900, item.id);
  });
  assert.ok(DATA.adhans.some((a) => a.fajr), 'يجب توفّر أذان فجر خاص');
});

test('واجهة المواقيت موصولة بالصفحة وبالإقلاع', () => {
  const fs = require('node:fs');
  const root = path.resolve(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  ['ptNextName', 'ptTimes', 'ptAdhanList', 'ptCity', 'ptIqama-fajr', 'ptCompassDial']
    .forEach((id) => assert.match(html, new RegExp(`id="${id}"`)));
  assert.match(html, /<section class="view" id="view-prayer">/);
  const boot = html.slice(html.indexOf("run(null, 'smart-context.js')"));
  assert.ok(boot.indexOf("run(null, 'prayer-times.js')") < boot.indexOf("run(null, 'prayer-ui.js')"));
  assert.ok(boot.indexOf("run(null, 'prayer-ui.js')") < boot.indexOf("run(null, 'app.js')"));
});
