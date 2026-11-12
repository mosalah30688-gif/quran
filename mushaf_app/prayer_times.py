"""حساب مواقيت الصلاة واتجاه القبلة محليًا بلا شبكة.

نقل مباشر لمعادلات نسخة أندرويد (``prayer-times.js``) إلى بايثون: نفس الطرق
ونفس زوايا الفجر والعشاء ونفس قاعدة ارتفاعات خطوط العرض العالية، حتى تتطابق
النتائج بين المنصّتين بالدقيقة.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

DEG = math.pi / 180.0
KAABA = {"lat": 21.4225, "lng": 39.8262}
PRAYERS = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")
NAMES = {
    "fajr": "الفجر",
    "sunrise": "الشروق",
    "dhuhr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "isha": "العشاء",
}

METHODS = {
    "mwl": {"name": "رابطة العالم الإسلامي", "fajr": 18.0, "isha": 17.0},
    "egypt": {"name": "الهيئة المصرية العامة للمساحة", "fajr": 19.5, "isha": 17.5},
    "isna": {"name": "الجمعية الإسلامية لأمريكا الشمالية", "fajr": 15.0, "isha": 15.0},
    "makkah": {"name": "جامعة أم القرى", "fajr": 18.5, "isha_minutes": 90, "isha_minutes_ramadan": 120},
    "karachi": {"name": "جامعة العلوم الإسلامية بكراتشي", "fajr": 18.0, "isha": 18.0},
    "dubai": {"name": "الإمارات (دبي)", "fajr": 18.2, "isha": 18.2},
    "kuwait": {"name": "الكويت", "fajr": 18.0, "isha": 17.5},
    "qatar": {"name": "قطر", "fajr": 18.0, "isha": 18.0},
    "turkey": {"name": "تركيا (ديانت)", "fajr": 18.0, "isha": 17.0},
    "singapore": {"name": "سنغافورة", "fajr": 20.0, "isha": 18.0},
    "france": {"name": "فرنسا (اتحاد المساجد)", "fajr": 12.0, "isha": 12.0},
    "morocco": {"name": "المغرب (وزارة الأوقاف)", "fajr": 19.0, "isha": 17.0},
    "tunisia": {"name": "تونس", "fajr": 18.0, "isha": 18.0},
    "algeria": {"name": "الجزائر (وزارة الشؤون الدينية)", "fajr": 18.0, "isha": 17.0},
    "jordan": {"name": "الأردن (وزارة الأوقاف)", "fajr": 18.0, "isha": 18.0},
}

HIGH_LATITUDE = {
    "none": "بلا تعديل",
    "middle": "منتصف الليل",
    "seventh": "سُبع الليل",
    "angle": "زاوية مقدرة",
}


def fix_angle(value: float) -> float:
    wrapped = value - 360.0 * math.floor(value / 360.0)
    return wrapped + 360.0 if wrapped < 0 else wrapped


def julian_day(date: dt.date | dt.datetime) -> float:
    if isinstance(date, dt.datetime):
        year, month, day = date.year, date.month, date.day
    else:
        year, month, day = date.year, date.month, date.day
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5


def sun_position(date: dt.date | dt.datetime) -> dict:
    jd = julian_day(date)
    d = jd - 2451545.0
    g = fix_angle(357.529 + 0.98560028 * d)
    q = fix_angle(280.459 + 0.98564736 * d)
    l = fix_angle(q + 1.915 * math.sin(g * DEG) + 0.02 * math.sin(2 * g * DEG))
    e = 23.439 - 0.00000036 * d
    declination = math.asin(max(-1.0, min(1.0, math.sin(e * DEG) * math.sin(l * DEG)))) / DEG
    right_ascension = fix_angle(math.atan2(math.cos(e * DEG) * math.sin(l * DEG), math.cos(l * DEG)) / DEG) / 15.0
    equation = q / 15.0 - right_ascension
    return {
        "declination": declination,
        "equation_time": ((equation + 12) % 24) - 12,
    }


def sun_azimuth(date: dt.date | dt.datetime, lat: float, lng: float, timezone: float) -> dict | None:
    """موضع الشمس الآن (زاوية الارتفاع والسمت) — لتحديد القبلة بالظل بلا بوصلة."""
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None
    if not isinstance(date, dt.datetime):
        date = dt.datetime.combine(date, dt.time(12, 0))
    sun = sun_position(date)
    minutes = date.hour * 60 + date.minute + date.second / 60.0
    true_solar_time = minutes + sun["equation_time"] * 60 + 4 * lng - 60 * timezone
    hour_angle_deg = (true_solar_time / 4) - 180
    declination = sun["declination"] * DEG
    latitude = lat * DEG
    angle = hour_angle_deg * DEG
    altitude = math.asin(max(-1.0, min(1.0, (math.sin(latitude) * math.sin(declination)
                                             + math.cos(latitude) * math.cos(declination) * math.cos(angle))))) / DEG
    azimuth = fix_angle(math.atan2(-math.sin(angle),
                                   math.tan(declination) * math.cos(latitude)
                                   - math.sin(latitude) * math.cos(angle)) / DEG) - 180 + 180
    return {
        "altitude": altitude,
        "azimuth": fix_angle(azimuth),
        "declination": sun["declination"],
        "hour_angle": hour_angle_deg,
    }


def hour_angle(altitude: float, lat: float, declination: float) -> float | None:
    numerator = math.sin(altitude * DEG) - math.sin(lat * DEG) * math.sin(declination * DEG)
    denominator = math.cos(lat * DEG) * math.cos(declination * DEG)
    if denominator == 0:
        return None
    ratio = numerator / denominator
    if not math.isfinite(ratio) or ratio > 1 or ratio < -1:
        return None
    return math.acos(ratio) / DEG / 15.0


def night_portion(rule: str, angle: float, night: float) -> float:
    if rule == "middle":
        return night / 2
    if rule == "seventh":
        return night / 7
    if rule == "angle":
        return (night * angle) / 60
    return night / 2


def times(
    date: dt.date | dt.datetime,
    lat: float,
    lng: float,
    timezone: float,
    method: str = "mwl",
    madhab: str = "shafi",
    high_latitude: str = "none",
    adjustments: dict | None = None,
    is_ramadan: bool = False,
) -> dict | None:
    """يرجع المواقيت بالساعات العشرية (٠–٢٤) أو None لموقع غير صالح."""
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None
    spec = METHODS.get(method, METHODS["mwl"])
    madhab_factor = 2 if madhab == "hanafi" else 1
    rule = high_latitude if high_latitude in HIGH_LATITUDE else "none"
    offsets = adjustments or {}

    sun = sun_position(date)
    dhuhr = 12 + timezone - lng / 15.0 - sun["equation_time"]
    sunrise_hour = hour_angle(-0.833, lat, sun["declination"])
    asr_altitude = math.atan2(1, madhab_factor + math.tan(abs(lat - sun["declination"]) * DEG)) / DEG
    asr_hour = hour_angle(asr_altitude, lat, sun["declination"])
    fajr_hour = hour_angle(-spec["fajr"], lat, sun["declination"])

    isha_hour = None
    if "isha" in spec:
        isha_hour = hour_angle(-spec["isha"], lat, sun["declination"])

    night = None
    if sunrise_hour is not None:
        night = 24 - 2 * sunrise_hour

    fajr = None if fajr_hour is None else dhuhr - fajr_hour
    sunrise = None if sunrise_hour is None else dhuhr - sunrise_hour
    asr = None if asr_hour is None else dhuhr + asr_hour
    maghrib = None if sunrise_hour is None else dhuhr + sunrise_hour
    isha = None if isha_hour is None else dhuhr + isha_hour

    if "isha_minutes" in spec:
        minutes = spec.get("isha_minutes_ramadan") if (is_ramadan and spec.get("isha_minutes_ramadan")) else spec["isha_minutes"]
        isha = None if maghrib is None else maghrib + minutes / 60.0

    if night is not None and rule != "none":
        if fajr is None:
            fajr = dhuhr - sunrise_hour - night_portion(rule, spec["fajr"], night)
        if isha is None:
            angle = spec["isha"] if "isha" in spec else 18.0
            isha = dhuhr + sunrise_hour + night_portion(rule, angle, night)
    if fajr is not None and sunrise is not None and fajr > sunrise:
        fajr = sunrise - (night / 7 if night else 0.5)
    if isha is not None and maghrib is not None and isha < maghrib:
        isha = maghrib + (night / 7 if night else 0.5)

    out = {"fajr": fajr, "sunrise": sunrise, "dhuhr": dhuhr, "asr": asr, "maghrib": maghrib, "isha": isha,
           "method": method}
    for key in PRAYERS:
        if out.get(key) is None:
            continue
        offset = float(offsets.get(key, 0) or 0)
        out[key] = out[key] + offset / 60.0
    return out


def format_minutes(hours: float, use_24: bool = False) -> str:
    """تنسيق ساعة عشرية (٤٫٥ = ٤:٣٠) إلى «HH:MM»، مطابق لدالة أندرويد."""
    if hours is None or not math.isfinite(hours):
        return '—'
    # القيمة قد تأتي فوق ٢٤ (بعد منتصف الليل) أو بالسالب؛ نطبّعها داخل اليوم
    normalized = ((hours % 24) + 24) % 24
    hour = int(normalized)
    minute = round((normalized - hour) * 60)
    if minute == 60:
        hour = (hour + 1) % 24
        minute = 0
    if use_24:
        return f'{hour:02d}:{minute:02d}'
    suffix = 'ص' if hour < 12 else 'م'
    display = 12 if hour % 12 == 0 else hour % 12
    return f'{display}:{minute:02d} {suffix}'


def to_minutes(hours: float | None) -> float | None:
    if hours is None:
        return None
    return (hours % 24) * 60


def next_prayer(table: dict, now_minutes: float) -> dict | None:
    """الموعد القادم اليوم؛ وإن انتهى العشاء يرجع فجر الغد بالساعات المتبقية."""
    if not table:
        return None
    now_hours = now_minutes / 60.0
    for key in ('fajr', 'dhuhr', 'asr', 'maghrib', 'isha'):
        value = table.get(key)
        if value is not None and value > now_hours:
            return {'key': key, 'name': NAMES[key], 'at': value, 'minutes_left': (value - now_hours) * 60}
    return None


def next_prayer_any(table: dict, now_minutes: float, tomorrow: dict | None = None) -> dict | None:
    """الموعد القادم ولو بعد منتصف الليل (يستخدم فجر الغد إن لزم)."""
    upcoming = next_prayer(table, now_minutes)
    if upcoming or not tomorrow:
        return upcoming
    value = tomorrow.get('fajr')
    if value is None:
        return None
    return {'key': 'fajr', 'name': NAMES['fajr'], 'at': value,
            'minutes_left': (value + 24 - now_minutes / 60.0) * 60, 'tomorrow': True}


def current_prayer(table: dict, now_minutes: float) -> str | None:
    """الصلاة الداخلة وقتها الآن (لعنوان شاشة الأذان)، أو None قبل الفجر."""
    if not table:
        return None
    now_hours = now_minutes / 60.0
    entered = None
    for key in ('fajr', 'dhuhr', 'asr', 'maghrib', 'isha'):
        value = table.get(key)
        if value is not None and value <= now_hours:
            entered = key
    return entered


def qibla_bearing(lat: float, lng: float) -> float:
    """اتجاه القبلة بالدرجات من الشمال الحقيقي (٠–٣٦٠)."""
    phi1 = lat * DEG
    phi2 = KAABA["lat"] * DEG
    delta = (KAABA["lng"] - lng) * DEG
    y = math.sin(delta)
    x = math.cos(phi1) * math.tan(phi2) - math.sin(phi1) * math.cos(delta)
    bearing = math.atan2(y, x) / DEG
    return (bearing + 360) % 360


HIJRI_MONTHS = (
    'محرم', 'صفر', 'ربيع الأول', 'ربيع الآخر', 'جمادى الأولى', 'جمادى الآخرة',
    'رجب', 'شعبان', 'رمضان', 'شوال', 'ذو القعدة', 'ذو الحجة',
)


_UMM_ALQURA = []


def _ummalqura():
    """جدول أم القرى (طول كل شهر هجري) المحزوم مع التطبيق — دقة رسمية بلا شبكة."""
    global _UMM_ALQURA
    if _UMM_ALQURA:
        return _UMM_ALQURA
    path = Path(__file__).resolve().parent / 'data' / 'hijri-ummalqura.json'
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        epoch = dt.date.fromisoformat(payload['epoch'])
        years = payload['years']
        first, last = payload['range']
        lengths: list[int] = []
        for year in range(first, last + 1):
            coded = years.get(str(year), '')
            lengths.extend(30 if ch == '1' else 29 for ch in coded)
        _UMM_ALQURA = [epoch, first, lengths]
    except (OSError, ValueError, KeyError, TypeError):
        _UMM_ALQURA = [None, 0, []]
    return _UMM_ALQURA


def hijri_parts(date: dt.date | dt.datetime) -> dict:
    """اليوم الهجري بجدول أم القرى، ومع الخروج عن مداه خوارزمية تقريبية."""
    day_date = date.date() if isinstance(date, dt.datetime) else date
    epoch, first_year, lengths = _ummalqura()
    if epoch is not None and lengths:
        offset = (day_date - epoch).days
        if 0 <= offset < sum(lengths):
            index = 0
            while index < len(lengths) and offset >= lengths[index]:
                offset -= lengths[index]
                index += 1
            year = first_year + index // 12
            month = index % 12 + 1
            day = offset + 1
            month_name = HIJRI_MONTHS[month - 1]
            return {
                'year': year, 'month': month, 'month_name': month_name, 'day': day,
                'calendar': 'Umm al-Qura',
                'formatted': f'{day} {month_name} {year} هـ',
            }
    return _hijri_tabular(day_date)


def _hijri_tabular(date: dt.date | dt.datetime) -> dict:
    """تحويل ميلادي إلى هجري (خوارزمية كويتية مبسّطة) لمن خرج عن مدى الجدول."""
    jd = math.floor(julian_day(date)) + 0.5
    l0 = jd - 1948440 + 10632
    n = math.floor((l0 - 1) / 10631)
    l = l0 - 10631 * n + 354
    j = (math.floor((10985 - l) / 5316) * math.floor((50 * l) / 17719)
         + math.floor(l / 5670) * math.floor((43 * l) / 15238))
    l = (l - math.floor((30 - j) / 15) * math.floor((17719 * j) / 50)
         - math.floor(j / 16) * math.floor((15238 * j) / 43) + 29)
    month = math.floor((24 * l) / 709)
    # الخوارزمية ترجع اليوم مع كسر ٠٫٥ دائمًا؛ نطرحه ثم نقرّب لعدد صحيح
    day = int(round(l - math.floor((709 * month) / 24) - 0.5))
    year = 30 * n + j - 30
    month = int(month)
    if day < 1:
        month -= 1
        day = 30
        if month < 1:
            month = 12
            year -= 1
    month_name = HIJRI_MONTHS[month - 1] if 1 <= month <= 12 else ''
    return {
        'year': int(year),
        'month': month,
        'month_name': month_name,
        'day': int(day),
        'calendar': 'tabular',
        'formatted': f'{int(day)} {month_name} {int(year)} هـ',
    }
