/*
 * Siraj Prayer Data v1 — مدن المواقيت وقائمة الأذانات المعتمدة.
 * البيانات ثابتة ومحلية (بلا شبكة)؛ ملفات الأذان تُنزّل بطلب المستخدم وتُحفظ على الجهاز.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SirajPrayerData = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const cities = [
    {
      "n": "القاهرة",
      "c": "مصر",
      "lat": 30.0444,
      "lng": 31.2357,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "الجيزة",
      "c": "مصر",
      "lat": 30.0131,
      "lng": 31.2089,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "الإسكندرية",
      "c": "مصر",
      "lat": 31.2001,
      "lng": 29.9187,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "الفيوم",
      "c": "مصر",
      "lat": 29.3084,
      "lng": 30.8428,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "المنصورة",
      "c": "مصر",
      "lat": 31.0409,
      "lng": 31.3785,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "طنطا",
      "c": "مصر",
      "lat": 30.7865,
      "lng": 31.0004,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "أسيوط",
      "c": "مصر",
      "lat": 27.1809,
      "lng": 31.1837,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "سوهاج",
      "c": "مصر",
      "lat": 26.5591,
      "lng": 31.6957,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "الأقصر",
      "c": "مصر",
      "lat": 25.6872,
      "lng": 32.6396,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "أسوان",
      "c": "مصر",
      "lat": 24.0889,
      "lng": 32.8998,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "بورسعيد",
      "c": "مصر",
      "lat": 31.2653,
      "lng": 32.3019,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "الإسماعيلية",
      "c": "مصر",
      "lat": 30.5965,
      "lng": 32.2715,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "دمياط",
      "c": "مصر",
      "lat": 31.4165,
      "lng": 31.8133,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "الزقازيق",
      "c": "مصر",
      "lat": 30.5877,
      "lng": 31.502,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "بنها",
      "c": "مصر",
      "lat": 30.466,
      "lng": 31.1848,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "مرسى مطروح",
      "c": "مصر",
      "lat": 31.3543,
      "lng": 27.2373,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "الغردقة",
      "c": "مصر",
      "lat": 27.2579,
      "lng": 33.8116,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "شرم الشيخ",
      "c": "مصر",
      "lat": 27.9158,
      "lng": 34.33,
      "tz": "Africa/Cairo",
      "m": "egypt"
    },
    {
      "n": "مكة المكرمة",
      "c": "السعودية",
      "lat": 21.4225,
      "lng": 39.8262,
      "tz": "Asia/Riyadh",
      "m": "makkah"
    },
    {
      "n": "المدينة المنورة",
      "c": "السعودية",
      "lat": 24.5247,
      "lng": 39.5692,
      "tz": "Asia/Riyadh",
      "m": "makkah"
    },
    {
      "n": "الرياض",
      "c": "السعودية",
      "lat": 24.7136,
      "lng": 46.6753,
      "tz": "Asia/Riyadh",
      "m": "makkah"
    },
    {
      "n": "جدة",
      "c": "السعودية",
      "lat": 21.4858,
      "lng": 39.1925,
      "tz": "Asia/Riyadh",
      "m": "makkah"
    },
    {
      "n": "الدمام",
      "c": "السعودية",
      "lat": 26.4207,
      "lng": 50.0888,
      "tz": "Asia/Riyadh",
      "m": "makkah"
    },
    {
      "n": "أبها",
      "c": "السعودية",
      "lat": 18.2164,
      "lng": 42.5053,
      "tz": "Asia/Riyadh",
      "m": "makkah"
    },
    {
      "n": "دبي",
      "c": "الإمارات",
      "lat": 25.2048,
      "lng": 55.2708,
      "tz": "Asia/Dubai",
      "m": "dubai"
    },
    {
      "n": "أبوظبي",
      "c": "الإمارات",
      "lat": 24.4539,
      "lng": 54.3773,
      "tz": "Asia/Dubai",
      "m": "dubai"
    },
    {
      "n": "الشارقة",
      "c": "الإمارات",
      "lat": 25.3463,
      "lng": 55.4209,
      "tz": "Asia/Dubai",
      "m": "dubai"
    },
    {
      "n": "الدوحة",
      "c": "قطر",
      "lat": 25.2854,
      "lng": 51.531,
      "tz": "Asia/Qatar",
      "m": "qatar"
    },
    {
      "n": "الكويت",
      "c": "الكويت",
      "lat": 29.3759,
      "lng": 47.9774,
      "tz": "Asia/Kuwait",
      "m": "kuwait"
    },
    {
      "n": "المنامة",
      "c": "البحرين",
      "lat": 26.2285,
      "lng": 50.586,
      "tz": "Asia/Bahrain",
      "m": "makkah"
    },
    {
      "n": "مسقط",
      "c": "عمان",
      "lat": 23.588,
      "lng": 58.3829,
      "tz": "Asia/Muscat",
      "m": "makkah"
    },
    {
      "n": "صنعاء",
      "c": "اليمن",
      "lat": 15.3694,
      "lng": 44.191,
      "tz": "Asia/Aden",
      "m": "makkah"
    },
    {
      "n": "عدن",
      "c": "اليمن",
      "lat": 12.7855,
      "lng": 45.0187,
      "tz": "Asia/Aden",
      "m": "makkah"
    },
    {
      "n": "بغداد",
      "c": "العراق",
      "lat": 33.3152,
      "lng": 44.3661,
      "tz": "Asia/Baghdad",
      "m": "karachi"
    },
    {
      "n": "أربيل",
      "c": "العراق",
      "lat": 36.1901,
      "lng": 44.0091,
      "tz": "Asia/Baghdad",
      "m": "karachi"
    },
    {
      "n": "عمّان",
      "c": "الأردن",
      "lat": 31.9539,
      "lng": 35.9106,
      "tz": "Asia/Amman",
      "m": "jordan"
    },
    {
      "n": "إربد",
      "c": "الأردن",
      "lat": 32.5556,
      "lng": 35.85,
      "tz": "Asia/Amman",
      "m": "jordan"
    },
    {
      "n": "دمشق",
      "c": "سوريا",
      "lat": 33.5138,
      "lng": 36.2765,
      "tz": "Asia/Damascus",
      "m": "mwl"
    },
    {
      "n": "حلب",
      "c": "سوريا",
      "lat": 36.2021,
      "lng": 37.1343,
      "tz": "Asia/Damascus",
      "m": "mwl"
    },
    {
      "n": "بيروت",
      "c": "لبنان",
      "lat": 33.8938,
      "lng": 35.5018,
      "tz": "Asia/Beirut",
      "m": "mwl"
    },
    {
      "n": "القدس",
      "c": "فلسطين",
      "lat": 31.7683,
      "lng": 35.2137,
      "tz": "Asia/Hebron",
      "m": "jordan"
    },
    {
      "n": "غزة",
      "c": "فلسطين",
      "lat": 31.5017,
      "lng": 34.4668,
      "tz": "Asia/Hebron",
      "m": "jordan"
    },
    {
      "n": "رام الله",
      "c": "فلسطين",
      "lat": 31.9038,
      "lng": 35.2034,
      "tz": "Asia/Hebron",
      "m": "jordan"
    },
    {
      "n": "الخرطوم",
      "c": "السودان",
      "lat": 15.5007,
      "lng": 32.5599,
      "tz": "Africa/Khartoum",
      "m": "egypt"
    },
    {
      "n": "طرابلس",
      "c": "ليبيا",
      "lat": 32.8872,
      "lng": 13.1913,
      "tz": "Africa/Tripoli",
      "m": "mwl"
    },
    {
      "n": "بنغازي",
      "c": "ليبيا",
      "lat": 32.1167,
      "lng": 20.0667,
      "tz": "Africa/Tripoli",
      "m": "mwl"
    },
    {
      "n": "تونس",
      "c": "تونس",
      "lat": 36.8065,
      "lng": 10.1815,
      "tz": "Africa/Tunis",
      "m": "tunisia"
    },
    {
      "n": "الجزائر",
      "c": "الجزائر",
      "lat": 36.7538,
      "lng": 3.0588,
      "tz": "Africa/Algiers",
      "m": "algeria"
    },
    {
      "n": "وهران",
      "c": "الجزائر",
      "lat": 35.6971,
      "lng": -0.6308,
      "tz": "Africa/Algiers",
      "m": "algeria"
    },
    {
      "n": "الدار البيضاء",
      "c": "المغرب",
      "lat": 33.5731,
      "lng": -7.5898,
      "tz": "Africa/Casablanca",
      "m": "morocco"
    },
    {
      "n": "الرباط",
      "c": "المغرب",
      "lat": 34.0209,
      "lng": -6.8416,
      "tz": "Africa/Casablanca",
      "m": "morocco"
    },
    {
      "n": "مراكش",
      "c": "المغرب",
      "lat": 31.6295,
      "lng": -7.9811,
      "tz": "Africa/Casablanca",
      "m": "morocco"
    },
    {
      "n": "نواكشوط",
      "c": "موريتانيا",
      "lat": 18.0735,
      "lng": -15.9582,
      "tz": "Africa/Nouakchott",
      "m": "mwl"
    },
    {
      "n": "مقديشو",
      "c": "الصومال",
      "lat": 2.0469,
      "lng": 45.3182,
      "tz": "Africa/Mogadishu",
      "m": "mwl"
    },
    {
      "n": "دجيبوتي",
      "c": "جيبوتي",
      "lat": 11.5721,
      "lng": 43.1456,
      "tz": "Africa/Djibouti",
      "m": "mwl"
    },
    {
      "n": "بانجول",
      "c": "غامبيا",
      "lat": 13.4549,
      "lng": -16.579,
      "tz": "Africa/Banjul",
      "m": "mwl"
    },
    {
      "n": "لاغوس",
      "c": "نيجيريا",
      "lat": 6.5244,
      "lng": 3.3792,
      "tz": "Africa/Lagos",
      "m": "mwl"
    },
    {
      "n": "نيروبي",
      "c": "كينيا",
      "lat": -1.2921,
      "lng": 36.8219,
      "tz": "Africa/Nairobi",
      "m": "mwl"
    },
    {
      "n": "أديس أبابا",
      "c": "إثيوبيا",
      "lat": 9.032,
      "lng": 38.7469,
      "tz": "Africa/Addis_Ababa",
      "m": "mwl"
    },
    {
      "n": "إستانبول",
      "c": "تركيا",
      "lat": 41.0082,
      "lng": 28.9784,
      "tz": "Europe/Istanbul",
      "m": "turkey"
    },
    {
      "n": "أنقرة",
      "c": "تركيا",
      "lat": 39.9334,
      "lng": 32.8597,
      "tz": "Europe/Istanbul",
      "m": "turkey"
    },
    {
      "n": "طهران",
      "c": "إيران",
      "lat": 35.6892,
      "lng": 51.389,
      "tz": "Asia/Tehran",
      "m": "mwl"
    },
    {
      "n": "كابل",
      "c": "أفغانستان",
      "lat": 34.5553,
      "lng": 69.2075,
      "tz": "Asia/Kabul",
      "m": "karachi"
    },
    {
      "n": "إسلام أباد",
      "c": "باكستان",
      "lat": 33.6844,
      "lng": 73.0479,
      "tz": "Asia/Karachi",
      "m": "karachi"
    },
    {
      "n": "لاهور",
      "c": "باكستان",
      "lat": 31.5204,
      "lng": 74.3587,
      "tz": "Asia/Karachi",
      "m": "karachi"
    },
    {
      "n": "كراتشي",
      "c": "باكستان",
      "lat": 24.8607,
      "lng": 67.0011,
      "tz": "Asia/Karachi",
      "m": "karachi"
    },
    {
      "n": "دلهي",
      "c": "الهند",
      "lat": 28.6139,
      "lng": 77.209,
      "tz": "Asia/Kolkata",
      "m": "karachi"
    },
    {
      "n": "مومباي",
      "c": "الهند",
      "lat": 19.076,
      "lng": 72.8777,
      "tz": "Asia/Kolkata",
      "m": "karachi"
    },
    {
      "n": "حيدر آباد",
      "c": "الهند",
      "lat": 17.385,
      "lng": 78.4867,
      "tz": "Asia/Kolkata",
      "m": "karachi"
    },
    {
      "n": "دكا",
      "c": "بنغلاديش",
      "lat": 23.8103,
      "lng": 90.4125,
      "tz": "Asia/Dhaka",
      "m": "karachi"
    },
    {
      "n": "كولالمبور",
      "c": "ماليزيا",
      "lat": 3.139,
      "lng": 101.6869,
      "tz": "Asia/Kuala_Lumpur",
      "m": "singapore"
    },
    {
      "n": "سنغافورة",
      "c": "سنغافورة",
      "lat": 1.3521,
      "lng": 103.8198,
      "tz": "Asia/Singapore",
      "m": "singapore"
    },
    {
      "n": "جاكرتا",
      "c": "إندونيسيا",
      "lat": -6.2088,
      "lng": 106.8456,
      "tz": "Asia/Jakarta",
      "m": "singapore"
    },
    {
      "n": "سورابايا",
      "c": "إندونيسيا",
      "lat": -7.2575,
      "lng": 112.7521,
      "tz": "Asia/Jakarta",
      "m": "singapore"
    },
    {
      "n": "مانيلا",
      "c": "الفلبين",
      "lat": 14.5995,
      "lng": 120.9842,
      "tz": "Asia/Manila",
      "m": "mwl"
    },
    {
      "n": "طشقند",
      "c": "أوزبكستان",
      "lat": 41.2995,
      "lng": 69.2401,
      "tz": "Asia/Tashkent",
      "m": "mwl"
    },
    {
      "n": "باكو",
      "c": "أذربيجان",
      "lat": 40.4093,
      "lng": 49.8671,
      "tz": "Asia/Baku",
      "m": "mwl"
    },
    {
      "n": "لندن",
      "c": "بريطانيا",
      "lat": 51.5072,
      "lng": -0.1276,
      "tz": "Europe/London",
      "m": "mwl"
    },
    {
      "n": "باريس",
      "c": "فرنسا",
      "lat": 48.8566,
      "lng": 2.3522,
      "tz": "Europe/Paris",
      "m": "france"
    },
    {
      "n": "برلين",
      "c": "ألمانيا",
      "lat": 52.52,
      "lng": 13.405,
      "tz": "Europe/Berlin",
      "m": "mwl"
    },
    {
      "n": "أمستردام",
      "c": "هولندا",
      "lat": 52.3676,
      "lng": 4.9041,
      "tz": "Europe/Amsterdam",
      "m": "mwl"
    },
    {
      "n": "بروكسل",
      "c": "بلجيكا",
      "lat": 50.8503,
      "lng": 4.3517,
      "tz": "Europe/Brussels",
      "m": "mwl"
    },
    {
      "n": "ستوكهولم",
      "c": "السويد",
      "lat": 59.3293,
      "lng": 18.0686,
      "tz": "Europe/Stockholm",
      "m": "mwl"
    },
    {
      "n": "أوسلو",
      "c": "النرويج",
      "lat": 59.9139,
      "lng": 10.7522,
      "tz": "Europe/Oslo",
      "m": "mwl"
    },
    {
      "n": "موسكو",
      "c": "روسيا",
      "lat": 55.7558,
      "lng": 37.6173,
      "tz": "Europe/Moscow",
      "m": "mwl"
    },
    {
      "n": "مدريد",
      "c": "إسبانيا",
      "lat": 40.4168,
      "lng": -3.7038,
      "tz": "Europe/Madrid",
      "m": "mwl"
    },
    {
      "n": "روما",
      "c": "إيطاليا",
      "lat": 41.9028,
      "lng": 12.4964,
      "tz": "Europe/Rome",
      "m": "mwl"
    },
    {
      "n": "فيينا",
      "c": "النمسا",
      "lat": 48.2082,
      "lng": 16.3738,
      "tz": "Europe/Vienna",
      "m": "mwl"
    },
    {
      "n": "نيويورك",
      "c": "أمريكا",
      "lat": 40.7128,
      "lng": -74.006,
      "tz": "America/New_York",
      "m": "isna"
    },
    {
      "n": "شيكاغو",
      "c": "أمريكا",
      "lat": 41.8781,
      "lng": -87.6298,
      "tz": "America/Chicago",
      "m": "isna"
    },
    {
      "n": "لوس أنجلوس",
      "c": "أمريكا",
      "lat": 34.0522,
      "lng": -118.2437,
      "tz": "America/Los_Angeles",
      "m": "isna"
    },
    {
      "n": "هيوستن",
      "c": "أمريكا",
      "lat": 29.7604,
      "lng": -95.3698,
      "tz": "America/Chicago",
      "m": "isna"
    },
    {
      "n": "تورونتو",
      "c": "كندا",
      "lat": 43.6532,
      "lng": -79.3832,
      "tz": "America/Toronto",
      "m": "isna"
    },
    {
      "n": "ساو باولو",
      "c": "البرازيل",
      "lat": -23.5505,
      "lng": -46.6333,
      "tz": "America/Sao_Paulo",
      "m": "mwl"
    },
    {
      "n": "سيدني",
      "c": "أستراليا",
      "lat": -33.8688,
      "lng": 151.2093,
      "tz": "Australia/Sydney",
      "m": "mwl"
    },
    {
      "n": "ملبورن",
      "c": "أستراليا",
      "lat": -37.8136,
      "lng": 144.9631,
      "tz": "Australia/Melbourne",
      "m": "mwl"
    }
  ];
  const adhans = [
    {"id": "haram-makkah", "name": "الحرم المكي", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/019--1.mp3", "seconds": 204, "fajr": false, "local": "audio/adhans/haram-makkah.mp3", "bundled": true},
    {"id": "mulla-makkah", "name": "علي ملا · مكة", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/047--.mp3", "seconds": 175, "fajr": false, "local": "audio/adhans/mulla-makkah.mp3", "bundled": true},
    {"id": "haram-madinah", "name": "الحرم المدني", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/018-.mp3", "seconds": 281, "fajr": false, "local": "audio/adhans/haram-madinah.mp3", "bundled": true},
    {"id": "fajr-makkah", "name": "أذان الفجر · الحرم المكي", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/033--.mp3", "seconds": 222, "fajr": true, "local": "audio/adhans/fajr-makkah.mp3", "bundled": true},
    {"id": "fajr-madinah", "name": "أذان الفجر · الحرم المدني", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/034--.mp3", "seconds": 278, "fajr": true, "local": "audio/adhans/fajr-madinah.mp3", "bundled": true},
    {"id": "abdulbasit", "name": "عبد الباسط عبد الصمد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/049-.mp3", "seconds": 247, "fajr": false, "local": "audio/adhans/abdulbasit.mp3", "bundled": true},
    {"id": "alafasy", "name": "مشاري راشد العفاسي", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/074-1_-.mp3", "seconds": 240, "fajr": false, "local": "audio/adhans/alafasy.mp3", "bundled": true},
    {"id": "alafasy-fajr", "name": "مشاري العفاسي · أذان الفجر", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/038-1.mp3", "seconds": 187, "fajr": true, "local": "audio/adhans/alafasy-fajr.mp3", "bundled": true},
    {"id": "rifat", "name": "محمد رفعت", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/042--.mp3", "seconds": 203, "fajr": false, "local": "audio/adhans/rifat.mp3", "bundled": true},
    {"id": "husary", "name": "محمود خليل الحصري", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/044--.mp3", "seconds": 127, "fajr": false, "local": "audio/adhans/husary.mp3", "bundled": true},
    {"id": "banna", "name": "محمد علي البنا", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/043--.mp3", "seconds": 153, "fajr": false, "local": "audio/adhans/banna.mp3", "bundled": true},
    {"id": "naina", "name": "أحمد نعينع", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/040--.mp3", "seconds": 210, "fajr": false, "local": "audio/adhans/naina.mp3", "bundled": true},
    {"id": "mustafa-ismail", "name": "مصطفى إسماعيل", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/068-.mp3", "seconds": 183, "fajr": false, "local": "audio/adhans/mustafa-ismail.mp3", "bundled": true},
    {"id": "minshawi", "name": "محمد صديق المنشاوي", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/048-.mp3", "seconds": 247, "fajr": false, "local": "audio/adhans/minshawi.mp3", "bundled": true},
    {"id": "shuaisha", "name": "أبو العنين شعيشع", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/071--.mp3", "seconds": 236, "fajr": false, "local": "audio/adhans/shuaisha.mp3", "bundled": true},
    {"id": "aqsa", "name": "المسجد الأقصى · ناجي قزاز", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/045--.mp3", "seconds": 185, "fajr": false, "local": "audio/adhans/aqsa.mp3", "bundled": true},
    {"id": "qatar", "name": "أحمد العمادي · قطر", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/002--.mp3", "seconds": 190, "fajr": false, "local": "audio/adhans/qatar.mp3", "bundled": true},
    {"id": "halabiya", "name": "حمزة الحلبية", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/001-.mp3", "seconds": 241, "fajr": false, "local": "audio/adhans/halabiya.mp3", "bundled": true},
    {"id": "003", "name": "الكــويت", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/003--.mp3", "seconds": 142, "fajr": false, "local": "", "bundled": false},
    {"id": "004-1", "name": "بروني دار السلام 1", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/004----1.mp3", "seconds": 205, "fajr": false, "local": "", "bundled": false},
    {"id": "006", "name": "حسين ايرك", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/006--.mp3", "seconds": 110, "fajr": false, "local": "", "bundled": false},
    {"id": "007", "name": "القـــــدس", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/007--.mp3", "seconds": 182, "fajr": false, "local": "", "bundled": false},
    {"id": "008", "name": "الهنـــد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/008--.mp3", "seconds": 108, "fajr": false, "local": "", "bundled": false},
    {"id": "009", "name": "اندونيسيا", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/009--.mp3", "seconds": 197, "fajr": false, "local": "", "bundled": false},
    {"id": "010", "name": "باكستان", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/010--.mp3", "seconds": 182, "fajr": false, "local": "", "bundled": false},
    {"id": "011-1", "name": "تركيا 1", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/011---1.mp3", "seconds": 178, "fajr": false, "local": "", "bundled": false},
    {"id": "013", "name": "جـــــورجيــــأ", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/013--.mp3", "seconds": 315, "fajr": false, "local": "", "bundled": false},
    {"id": "014", "name": "زهير محمد طارش", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/014-.mp3", "seconds": 184, "fajr": false, "local": "", "bundled": false},
    {"id": "015", "name": "عجمـــــان الأمارات", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/015---.mp3", "seconds": 139, "fajr": false, "local": "", "bundled": false},
    {"id": "016-2", "name": "مكه المكرمة 2", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/016---2.mp3", "seconds": 202, "fajr": false, "local": "", "bundled": false},
    {"id": "017", "name": "الشيخ عبدالباسط عبدالصمـد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/017-_-.mp3", "seconds": 188, "fajr": false, "local": "", "bundled": false},
    {"id": "021", "name": "الحرم المكي محمد رمل", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/021--.mp3", "seconds": 191, "fajr": false, "local": "", "bundled": false},
    {"id": "025-1", "name": "الشيخ البهلول أبوعرقوب1", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/025-1.mp3", "seconds": 208, "fajr": false, "local": "", "bundled": false},
    {"id": "027", "name": "العشاء الشيخ عبدالباسط عبدالصمـد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/027-_-.mp3", "seconds": 187, "fajr": false, "local": "", "bundled": false},
    {"id": "028-1", "name": "الفجــر الكويت 1", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/028---1.mp3", "seconds": 209, "fajr": true, "local": "", "bundled": false},
    {"id": "030", "name": "الفجر بروني دار السلام", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/030---.mp3", "seconds": 208, "fajr": true, "local": "", "bundled": false},
    {"id": "031", "name": "الفجــر جـــزائـر", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/031--.mp3", "seconds": 177, "fajr": true, "local": "", "bundled": false},
    {"id": "032", "name": "الفجر ماليزيا", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/032--.mp3", "seconds": 198, "fajr": true, "local": "", "bundled": false},
    {"id": "035", "name": "الفجر بصوت أحمد نعينع", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/035-.mp3", "seconds": 204, "fajr": true, "local": "", "bundled": false},
    {"id": "036", "name": "الفجر مصــــر", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/036--.mp3", "seconds": 245, "fajr": true, "local": "", "bundled": false},
    {"id": "037", "name": "الفجر، بصوت الأخ أحمد نواف المجلاد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/037-.mp3", "seconds": 221, "fajr": true, "local": "", "bundled": false},
    {"id": "041", "name": "القاهرة عبدالباسط عبدالصمد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/041--.mp3", "seconds": 200, "fajr": false, "local": "", "bundled": false},
    {"id": "046", "name": "المسجد الأقصى ناجي قزا", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/046--.mp3", "seconds": 226, "fajr": false, "local": "", "bundled": false},
    {"id": "050", "name": "بصوت الشيخ المنشاوي", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/050-.mp3", "seconds": 251, "fajr": false, "local": "", "bundled": false},
    {"id": "051", "name": "أأذان بصوت حاج سليمان مختار الجزائر", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/051--.mp3", "seconds": 194, "fajr": false, "local": "", "bundled": false},
    {"id": "052", "name": "أأذان بصوت عبدالباسط عبد الصمد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/052-.mp3", "seconds": 244, "fajr": false, "local": "", "bundled": false},
    {"id": "053", "name": "عبدالكريم جباري", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/053-.mp3", "seconds": 81, "fajr": false, "local": "", "bundled": false},
    {"id": "054", "name": "من فلسطين بصوت صهيب هاني", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/054--.mp3", "seconds": 183, "fajr": false, "local": "", "bundled": false},
    {"id": "055", "name": "من مسجد الملك فهد بنجران بصوت حمـــدان المالكي", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/055-.mp3", "seconds": 266, "fajr": false, "local": "", "bundled": false},
    {"id": "057", "name": "جزر المالديف", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/057--.mp3", "seconds": 185, "fajr": false, "local": "", "bundled": false},
    {"id": "058", "name": "دبــي الأمارات", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/058---.mp3", "seconds": 235, "fajr": false, "local": "", "bundled": false},
    {"id": "059", "name": "ماليزيا", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/059--.mp3", "seconds": 198, "fajr": false, "local": "", "bundled": false},
    {"id": "060", "name": "مسقط عمان", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/060--.mp3", "seconds": 151, "fajr": false, "local": "", "bundled": false},
    {"id": "061", "name": "السيد متولي العال لبنان", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/061---.mp3", "seconds": 169, "fajr": false, "local": "", "bundled": false},
    {"id": "062", "name": "المدينة المنورة", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/062--.mp3", "seconds": 235, "fajr": false, "local": "", "bundled": false},
    {"id": "063", "name": "تونــس", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/063--.mp3", "seconds": 143, "fajr": false, "local": "", "bundled": false},
    {"id": "064", "name": "جــزائــر", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/064--.mp3", "seconds": 162, "fajr": false, "local": "", "bundled": false},
    {"id": "065", "name": "سوريا", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/065--.mp3", "seconds": 221, "fajr": false, "local": "", "bundled": false},
    {"id": "066", "name": "عبدالرزاق صالح لبنان", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/066---.mp3", "seconds": 248, "fajr": false, "local": "", "bundled": false},
    {"id": "067", "name": "مهدي البيشي", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/067--.mp3", "seconds": 221, "fajr": false, "local": "", "bundled": false},
    {"id": "069", "name": "الفجر القــدس", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/069--.mp3", "seconds": 151, "fajr": true, "local": "", "bundled": false},
    {"id": "070", "name": "الفجر أم القــوين", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/070--.mp3", "seconds": 190, "fajr": true, "local": "", "bundled": false},
    {"id": "072", "name": "الأأذان بصوت الأخ أحمد نواف المجلاد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/072-.mp3", "seconds": 196, "fajr": false, "local": "", "bundled": false},
    {"id": "073", "name": "الأذان", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/073-.mp3", "seconds": 120, "fajr": false, "local": "", "bundled": false},
    {"id": "087-2", "name": "الحرم المدني 2", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/087--2.mp3", "seconds": 189, "fajr": false, "local": "", "bundled": false},
    {"id": "088", "name": "تكبير العيد", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/088-.mp3", "seconds": 68, "fajr": false, "local": "", "bundled": false},
    {"id": "090-2", "name": "مؤذن جامع الراجحي بالرياض (2)", "region": "", "url": "https://archive.org/download/AdhaN_M_up-by-muslem/090-2.mp3", "seconds": 149, "fajr": false, "local": "", "bundled": false}
  ];
  return { version: 1, cities, adhans };
});
