"""تطابق حساب المواقيت والقبلة في لينكس مع نسخة أندرويد المرجعية.

القيم المرجعية أدناه أُخرجت من تنفيذ ``prayer-times.js`` نفسه (المستخدم في
أندرويد) لنفس المدخلات، فالتطابق يعني أن المنصّتين تعطيان نفس الدقيقة.
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import prayer_times as P  # noqa: E402

REFERENCE = [
    # (date, lat, lng, tz, method, {prayer: hours})
    ('2026-11-05', 29.308, 30.842, 2, 'egypt',
     {'fajr': 4.741802, 'sunrise': 6.204742, 'dhuhr': 11.670041,
      'asr': 14.761640, 'maghrib': 17.135340, 'isha': 18.443904}),
    ('2026-11-05', 21.4225, 39.8262, 3, 'makkah',
     {'fajr': 5.128443, 'sunrise': 6.428390, 'dhuhr': 12.071094,
      'asr': 15.307934, 'maghrib': 17.713798, 'isha': 19.213798}),
    ('2026-03-20', 51.507, -0.128, 0, 'mwl',
     {'fajr': 4.174188, 'sunrise': 6.066427, 'dhuhr': 12.135393,
      'asr': 15.415553, 'maghrib': 18.204359, 'isha': 19.980305}),
    ('2026-11-05', 25.204, 55.27, 4, 'dubai',
     {'fajr': 5.167107, 'sunrise': 6.481027, 'dhuhr': 12.041507,
      'asr': 15.215973, 'maghrib': 17.601988, 'isha': 18.915908}),
    ('2026-12-31', 40.71, -74.0, -5, 'isna',
     {'fajr': 5.963486, 'sunrise': 7.329810, 'dhuhr': 11.978970,
      'asr': 14.332129, 'maghrib': 16.628130, 'isha': 17.994454}),
]

QIBLA_REFERENCE = [
    (29.308, 30.842, 132.153866),   # الفيوم
    (21.4225, 39.8262, 0.0),        # مكة
    (51.507, -0.128, 118.986625),   # لندن
    (40.71, -74.0, 58.485838),      # نيويورك
]


class PrayerTimesParityTest(unittest.TestCase):
    def test_matches_android_reference_within_a_minute(self):
        for date_text, lat, lng, tz, method, expected in REFERENCE:
            table = P.times(dt.date.fromisoformat(date_text), lat, lng, tz, method=method)
            self.assertIsNotNone(table)
            for prayer, hours in expected.items():
                diff_minutes = abs(table[prayer] - hours) * 60
                self.assertLess(
                    diff_minutes, 1.0,
                    f'{method}/{prayer} على {date_text} فرق {diff_minutes:.2f} دقيقة',
                )

    def test_high_latitude_returns_none_instead_of_fake_values(self):
        table = P.times(dt.date(2026, 6, 21), 59.33, 18.06, 1, method='mwl')
        self.assertIsNone(table['fajr'])
        self.assertIsNone(table['isha'])
        self.assertIsNotNone(table['dhuhr'])

    def test_makkah_isha_uses_minutes_after_maghrib(self):
        table = P.times(dt.date(2026, 11, 5), 21.4225, 39.8262, 3, method='makkah')
        self.assertAlmostEqual((table['isha'] - table['maghrib']) * 60, 90, delta=0.5)

    def test_hanafi_asr_is_later_than_shafi(self):
        shafi = P.times(dt.date(2026, 11, 5), 29.308, 30.842, 2, method='egypt', madhab='shafi')
        hanafi = P.times(dt.date(2026, 11, 5), 29.308, 30.842, 2, method='egypt', madhab='hanafi')
        self.assertGreater(hanafi['asr'], shafi['asr'])

    def test_qibla_bearing_matches_reference(self):
        for lat, lng, expected in QIBLA_REFERENCE:
            self.assertAlmostEqual(P.qibla_bearing(lat, lng), expected, delta=0.01)

    def test_next_and_current_prayer(self):
        table = P.times(dt.date(2026, 11, 5), 29.308, 30.842, 2, method='egypt')
        # ١٢:٣٠ ظهرًا: القادم هو العصر، والداخل وقته الظهر
        self.assertEqual(P.next_prayer(table, 12 * 60 + 30)['key'], 'asr')
        self.assertEqual(P.current_prayer(table, 12 * 60 + 30), 'dhuhr')
        self.assertIsNone(P.current_prayer(table, 3 * 60))

    def test_format_minutes(self):
        self.assertEqual(P.format_minutes(17 + 5 / 60), '5:05 م')
        self.assertEqual(P.format_minutes(5 + 9 / 60), '5:09 ص')
        self.assertEqual(P.format_minutes(17 + 5 / 60, use_24=True), '17:05')
        self.assertEqual(P.format_minutes(23.999), '12:00 ص')

    def test_hijri_uses_ummalqura_inside_its_range(self):
        known = {
            '2025-03-01': (1446, 9, 1),    # أول رمضان
            '2025-06-05': (1446, 12, 9),   # يوم عرفة
            '2026-03-20': (1447, 10, 1),   # عيد الفطر
            '2024-04-10': (1445, 10, 1),
        }
        for text, expected in known.items():
            parts = P.hijri_parts(dt.date.fromisoformat(text))
            self.assertEqual((parts['year'], parts['month'], parts['day']), expected, text)
            self.assertEqual(parts['calendar'], 'Umm al-Qura')

    def test_hijri_falls_back_outside_the_table(self):
        parts = P.hijri_parts(dt.date(1950, 1, 1))
        self.assertEqual(parts['calendar'], 'tabular')
        self.assertGreater(parts['year'], 1300)

    def test_hijri_month_name_matches_number(self):
        parts = P.hijri_parts(dt.date(2026, 11, 5))
        self.assertEqual(parts['month_name'], P.HIJRI_MONTHS[parts['month'] - 1])
        self.assertIn('هـ', parts['formatted'])

    def test_invalid_location_is_rejected(self):
        self.assertIsNone(P.times(dt.date(2026, 11, 5), 120, 30, 2))


if __name__ == '__main__':
    unittest.main()
