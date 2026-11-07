/*
 * Siraj Prayer Times v1
 *
 * حساب فلكي محلي لمواقيت الصلاة واتجاه القبلة، بلا شبكة وبلا أي تبعية خارجية.
 * يعمل في المتصفح وفي Node.js حتى يُختبر منفصلًا عن الواجهة.
 *
 * الطرق المعتمدة في الزوايا (Fajr/Isha) مأخوذة من الطرق المتعارف عليها:
 * رابطة العالم الإسلامي، ISNA، الهيئة المصرية العامة للمساحة، أم القرى، كراتشي،
 * دبي، الكويت، قطر، تركيا، سنغافورة، فرنسا، رابطة أمريكا الشمالية للرصد.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SirajPrayerTimes = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = 1;
  const DEG = Math.PI / 180;
  const KAABA = Object.freeze({ lat: 21.4225, lng: 39.8262 });
  const PRAYERS = Object.freeze(['fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'isha']);
  const NAMES = Object.freeze({
    fajr: 'الفجر', sunrise: 'الشروق', dhuhr: 'الظهر', asr: 'العصر', maghrib: 'المغرب', isha: 'العشاء',
  });

  // الزوايا بالدرجات؛ isha في أم القرى تُحسب بالدقائق بعد المغرب (90، ورمضان 120).
  const METHODS = Object.freeze({
    mwl: { name: 'رابطة العالم الإسلامي', fajr: 18, isha: 17 },
    egypt: { name: 'الهيئة المصرية العامة للمساحة', fajr: 19.5, isha: 17.5 },
    isna: { name: 'الجمعية الإسلامية لأمريكا الشمالية', fajr: 15, isha: 15 },
    makkah: { name: 'جامعة أم القرى', fajr: 18.5, ishaMinutes: 90, ishaMinutesRamadan: 120 },
    karachi: { name: 'جامعة العلوم الإسلامية بكراتشي', fajr: 18, isha: 18 },
    dubai: { name: 'الإمارات (دبي)', fajr: 18.2, isha: 18.2 },
    kuwait: { name: 'الكويت', fajr: 18, isha: 17.5 },
    qatar: { name: 'قطر', fajr: 18, isha: 18 },
    turkey: { name: 'تركيا (ديانت)', fajr: 18, isha: 17 },
    singapore: { name: 'سنغافورة', fajr: 20, isha: 18 },
    france: { name: 'فرنسا (اتحاد المساجد)', fajr: 12, isha: 12 },
    morocco: { name: 'المغرب (وزارة الأوقاف)', fajr: 19, isha: 17 },
    tunisia: { name: 'تونس', fajr: 18, isha: 18 },
    algeria: { name: 'الجزائر (وزارة الشؤون الدينية)', fajr: 18, isha: 17 },
    jordan: { name: 'الأردن (وزارة الأوقاف)', fajr: 18, isha: 18 },
  });

  const HIGH_LATITUDE = Object.freeze({
    none: 'بلا تعديل',
    middle: 'منتصف الليل',
    seventh: 'سُبع الليل',
    angle: 'زاوية مقدرة',
  });

  const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
  const fixAngle = (value) => {
    const wrapped = value - 360 * Math.floor(value / 360);
    return wrapped < 0 ? wrapped + 360 : wrapped;
  };
  const sin = (deg) => Math.sin(deg * DEG);
  const cos = (deg) => Math.cos(deg * DEG);
  const tan = (deg) => Math.tan(deg * DEG);
  const asin = (value) => Math.asin(clamp(value, -1, 1)) / DEG;
  const acos = (value) => Math.acos(clamp(value, -1, 1)) / DEG;
  const atan2 = (y, x) => Math.atan2(y, x) / DEG;

  function julianDay(date) {
    let year = date.getUTCFullYear();
    let month = date.getUTCMonth() + 1;
    const day = date.getUTCDate();
    if (month <= 2) { year -= 1; month += 12; }
    const a = Math.floor(year / 100);
    const b = 2 - a + Math.floor(a / 4);
    return Math.floor(365.25 * (year + 4716)) + Math.floor(30.6001 * (month + 1))
      + day + b - 1524.5;
  }

  // موضع الشمس: الانحراف والميل ومعادلة الزمن ومسير الشمس (بالدرجات/الساعات)
  function sunPosition(date) {
    const jd = julianDay(date);
    const d = jd - 2451545.0;
    const g = fixAngle(357.529 + 0.98560028 * d);
    const q = fixAngle(280.459 + 0.98564736 * d);
    const l = fixAngle(q + 1.915 * sin(g) + 0.02 * sin(2 * g));
    const e = 23.439 - 0.00000036 * d;
    const declination = asin(sin(e) * sin(l));
    const rightAscension = fixAngle(atan2(cos(e) * sin(l), cos(l))) / 15;
    const equation = q / 15 - rightAscension;
    return {
      declination,
      equation,
      // معادلة الزمن بالساعات مع تصحيح التفاف منتصف الليل
      equationTime: ((equation + 12) % 24) - 12,
      apparentLongitude: l,
      meanAnomaly: g,
      obliquity: e,
    };
  }

  // زاوية الساعة (بالساعات) لارتفاع حقيقي للشمس بالدرجات (سالب تحت الأفق)
  function hourAngle(altitude, lat, declination) {
    const numerator = sin(altitude) - sin(lat) * sin(declination);
    const denominator = cos(lat) * cos(declination);
    const ratio = numerator / denominator;
    if (!Number.isFinite(ratio) || ratio > 1 || ratio < -1) return null;
    return acos(ratio) / 15;
  }

  function nightPortion(rule, angle, night, portion) {
    switch (rule) {
      case 'middle': return night / 2;
      case 'seventh': return night / 7;
      case 'angle': return (night * angle) / 60;
      default: return Number.isFinite(portion) ? portion : night / 2;
    }
  }

  function hijriParts(date) {
    // تحويل تقويم ميلادي إلى هجري (خوارزمية كويتية مبسّطة، دقة ±يوم)
    const jd = Math.floor(julianDay(date)) + 0.5;
    const l0 = jd - 1948440 + 10632;
    const n = Math.floor((l0 - 1) / 10631);
    let l = l0 - 10631 * n + 354;
    const j = Math.floor((10985 - l) / 5316) * Math.floor((50 * l) / 17719)
      + Math.floor(l / 5670) * Math.floor((43 * l) / 15238);
    l = l - Math.floor((30 - j) / 15) * Math.floor((17719 * j) / 50)
      - Math.floor(j / 16) * Math.floor((15238 * j) / 43) + 29;
    const month = Math.floor((24 * l) / 709);
    const day = l - Math.floor((709 * month) / 24);
    const year = 30 * n + j - 30;
    return { year, month, day };
  }

  /**
   * حساب المواقيت.
   * @param {object} options
   *   date: Date (يُستخدم يومه المحلي)، lat, lng, timezone (بالساعات)،
   *   method (مفتاح الطرق)، madhab: 'shafi' | 'hanafi'،
   *   highLatitude: 'none' | 'middle' | 'seventh' | 'angle'،
   *   adjustments: { fajr: دقائق، ... }، isRamadan: boolean
   */
  function times(options) {
    const opts = options && typeof options === 'object' ? options : {};
    const date = opts.date instanceof Date ? opts.date : new Date();
    const lat = Number(opts.lat);
    const lng = Number(opts.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
      return null;
    }
    const timezone = Number.isFinite(Number(opts.timezone)) ? Number(opts.timezone)
      : -date.getTimezoneOffset() / 60;
    const method = METHODS[opts.method] || METHODS.mwl;
    const madhab = opts.madhab === 'hanafi' ? 2 : 1;
    const highLatitude = HIGH_LATITUDE[opts.highLatitude] ? opts.highLatitude : 'none';
    const adjustments = opts.adjustments && typeof opts.adjustments === 'object' ? opts.adjustments : {};

    const sun = sunPosition(date);
    const dhuhr = 12 + timezone - lng / 15 - sun.equationTime;
    const sunriseHour = hourAngle(-0.833, lat, sun.declination);
    // ارتفاع العصر: ظل بمقدار (١) للجمهور و(٢) للحنفية
    const asrAltitude = atan2(1, madhab + tan(Math.abs(lat - sun.declination)));
    const asrHour = hourAngle(asrAltitude, lat, sun.declination);
    const fajrHour = hourAngle(-method.fajr, lat, sun.declination);
    let ishaHour = null;
    if (Number.isFinite(method.isha)) ishaHour = hourAngle(-method.isha, lat, sun.declination);

    let night = null;
    if (sunriseHour !== null) night = 24 - 2 * sunriseHour;

    let fajr = fajrHour === null ? null : dhuhr - fajrHour;
    let sunrise = sunriseHour === null ? null : dhuhr - sunriseHour;
    const asr = asrHour === null ? null : dhuhr + asrHour;
    let maghrib = sunriseHour === null ? null : dhuhr + sunriseHour;
    let isha = ishaHour === null ? null : dhuhr + ishaHour;

    if (Number.isFinite(method.ishaMinutes)) {
      const minutes = opts.isRamadan && method.ishaMinutesRamadan
        ? method.ishaMinutesRamadan : method.ishaMinutes;
      isha = maghrib === null ? null : maghrib + minutes / 60;
    }

    // خطوط العرض العالية: نستخدم قاعدة الليل عند تعذّر الزاوية
    if (night !== null && highLatitude !== 'none') {
      if (fajr === null) fajr = dhuhr - sunriseHour - nightPortion(highLatitude, method.fajr, night);
      if (isha === null) {
        isha = dhuhr + sunriseHour + nightPortion(
          highLatitude, Number.isFinite(method.isha) ? method.isha : 18, night,
        );
      }
    }
    if (fajr !== null && sunrise !== null && fajr > sunrise) fajr = sunrise - (night ? night / 7 : 0.5);
    if (isha !== null && maghrib !== null && isha < maghrib) isha = maghrib + (night ? night / 7 : 0.5);

    const out = { fajr, sunrise, dhuhr, asr, maghrib, isha, method: opts.method || 'mwl' };
    PRAYERS.forEach((key) => {
      if (out[key] === null || out[key] === undefined) return;
      const offset = Number(adjustments[key]) || 0;
      out[key] = out[key] + offset / 60;
    });
    return out;
  }

  // دقائق من منتصف الليل ← «HH:MM» بصيغة 12 ساعة عربية
  function formatMinutes(minutes, use24) {
    if (!Number.isFinite(minutes)) return '—';
    const normalized = ((minutes % 1440) + 1440) % 1440;
    const hour = Math.floor(normalized);
    const minute = Math.round((normalized - hour) * 60);
    const h = minute === 60 ? (hour + 1) % 24 : hour;
    const m = minute === 60 ? 0 : minute;
    if (use24) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    const suffix = h < 12 ? 'ص' : 'م';
    const display = h % 12 === 0 ? 12 : h % 12;
    return `${display}:${String(m).padStart(2, '0')} ${suffix}`;
  }

  function minutesNow(date) {
    const d = date instanceof Date ? date : new Date();
    return d.getHours() * 60 + d.getMinutes() + d.getSeconds() / 60;
  }

  // الموعد القادم (مع الانتقال إلى الغد عند انتهاء العشاء)
  function next(options) {
    const date = options && options.date instanceof Date ? options.date : new Date();
    const table = times({ ...options, date });
    if (!table) return null;
    // جدول المواقيت بالساعات العشرية، و«الآن» بالدقائق — نوحّد الوحدة قبل المقارنة
    const nowMinutes = minutesNow(date);
    const nowHours = nowMinutes / 60;
    for (const key of ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']) {
      if (Number.isFinite(table[key]) && table[key] > nowHours) {
        return {
          key, name: NAMES[key], at: table[key],
          minutesLeft: (table[key] - nowHours) * 60, today: true,
        };
      }
    }
    const tomorrow = new Date(date.getTime() + 24 * 3600 * 1000);
    const nextTable = times({ ...options, date: tomorrow });
    if (!nextTable || !Number.isFinite(nextTable.fajr)) return null;
    return {
      key: 'fajr', name: NAMES.fajr, at: nextTable.fajr,
      minutesLeft: (24 - nowHours + nextTable.fajr) * 60, today: false,
    };
  }

  // اتجاه القبلة والمسافة إلى الكعبة
  function qibla(lat, lng) {
    const latitude = Number(lat);
    const longitude = Number(lng);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
    const dLng = KAABA.lng - longitude;
    const bearing = fixAngle(atan2(
      sin(dLng),
      cos(latitude) * tan(KAABA.lat) - sin(latitude) * cos(dLng),
    ));
    const phi1 = latitude * DEG;
    const phi2 = KAABA.lat * DEG;
    const dPhi = phi2 - phi1;
    const dLambda = dLng * DEG;
    const a = Math.sin(dPhi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLambda / 2) ** 2;
    const distance = 2 * 6371 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return { bearing, distance, kaaba: KAABA };
  }

  // موضع الشمس (سمت وارتفاع) لطريقة الاتجاه بالشمس
  function sunAzimuth(options) {
    const opts = options && typeof options === 'object' ? options : {};
    const date = opts.date instanceof Date ? opts.date : new Date();
    const lat = Number(opts.lat);
    const lng = Number(opts.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
    const timezone = Number.isFinite(Number(opts.timezone)) ? Number(opts.timezone)
      : -date.getTimezoneOffset() / 60;
    const sun = sunPosition(date);
    const minutes = minutesNow(date);
    const trueSolarTime = minutes + sun.equationTime * 60 + 4 * lng - 60 * timezone;
    const hourAngleDeg = (trueSolarTime / 4) - 180;
    const declination = sun.declination;
    const altitude = asin(sin(lat) * sin(declination) + cos(lat) * cos(declination) * cos(hourAngleDeg));
    const azimuth = fixAngle(atan2(
      -sin(hourAngleDeg),
      tan(declination) * cos(lat) - sin(lat) * cos(hourAngleDeg),
    ) - 180 + 180);
    return { altitude, azimuth, declination, hourAngle: hourAngleDeg };
  }

  function describe(name) {
    return NAMES[name] || name;
  }

  return {
    VERSION, PRAYERS, NAMES, METHODS, HIGH_LATITUDE, KAABA,
    times, next, qibla, sunAzimuth, formatMinutes, minutesNow,
    hijriParts, sunPosition, hourAngle, describe,
  };
});
