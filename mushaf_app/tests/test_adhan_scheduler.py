"""اختبارات جدولة الأذان على لينكس دون لمس systemd الحقيقي."""
import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import adhan_scheduler as A  # noqa: E402

FEYyum = (29.308, 30.842, 2.0)


class AdhanPlanTest(unittest.TestCase):
    def test_plan_only_contains_future_prayers(self):
        start = dt.date(2026, 11, 5)
        events = A.plan_events(*FEYyum, method='egypt', start=start)
        self.assertTrue(events)
        for event in events:
            self.assertIn(event['key'], A.PRAYER_KEYS)
        keys = [event['key'] for event in events]
        # الفجر والظهر والعصر والمغرب والعشاء موجودة على مدى يومين
        for key in A.PRAYER_KEYS:
            self.assertIn(key, keys)
        moments = [event['at'] for event in events]
        self.assertEqual(moments, sorted(moments))

    def test_plan_respects_method_angles(self):
        start = dt.date(2026, 11, 5)
        egypt = A.plan_events(*FEYyum, method='egypt', start=start)
        makkah = A.plan_events(*FEYyum, method='makkah', start=start)
        egypt_fajr = next(e['at'] for e in egypt if e['key'] == 'fajr')
        makkah_fajr = next(e['at'] for e in makkah if e['key'] == 'fajr')
        self.assertNotEqual(egypt_fajr, makkah_fajr)

    def test_invalid_location_gives_no_events(self):
        self.assertEqual(A.plan_events(120, 30, 2), [])


class AdhanUnitsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {
            'XDG_CONFIG_HOME': self.tmp.name,
            'SIRAJ_SKIP_SYSTEMCTL': '1',
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.exe = Path(self.tmp.name) / 'Siraj.AppImage'
        self.exe.write_text('#!/bin/sh\n', encoding='utf-8')

    def unit_files(self):
        folder = Path(self.tmp.name) / 'systemd' / 'user'
        return sorted(p.name for p in folder.glob('siraj-adhan-*'))

    def test_writes_one_service_and_timer_per_prayer(self):
        ok, message = A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5))
        self.assertTrue(ok, message)
        files = self.unit_files()
        for key in A.PRAYER_KEYS:
            self.assertIn(f'siraj-adhan-{key}.service', files)
            self.assertIn(f'siraj-adhan-{key}.timer', files)

    def test_timer_uses_exe_and_prayer_argument(self):
        A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5))
        service = (Path(self.tmp.name) / 'systemd' / 'user' / 'siraj-adhan-fajr.service').read_text(encoding='utf-8')
        self.assertIn('ExecStart=', service)
        self.assertIn('--adhan fajr', service)
        timer = (Path(self.tmp.name) / 'systemd' / 'user' / 'siraj-adhan-fajr.timer').read_text(encoding='utf-8')
        self.assertIn('OnCalendar=2026-11-0', timer)
        self.assertIn('Persistent=true', timer)

    def test_disabling_removes_every_unit(self):
        A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5))
        self.assertTrue(self.unit_files())
        ok, _ = A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', enabled=False)
        self.assertTrue(ok)
        self.assertEqual(self.unit_files(), [])

    def test_reconfiguring_does_not_duplicate_units(self):
        A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5))
        first = self.unit_files()
        A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5))
        self.assertEqual(self.unit_files(), first)

    def test_pre_adhan_reminder_timer_uses_lead_minutes(self):
        ok, message = A.prepare_adhan_units(
            self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5), pre_minutes=15,
        )
        self.assertTrue(ok, message)
        files = self.unit_files()
        self.assertIn('siraj-adhan-remind-fajr.timer', files)
        service = (Path(self.tmp.name) / 'systemd' / 'user' / 'siraj-adhan-remind-fajr.service').read_text(encoding='utf-8')
        self.assertIn('--adhan-remind fajr 15', service)

    def test_zero_lead_creates_no_reminder_units(self):
        A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5), pre_minutes=0)
        self.assertFalse([name for name in self.unit_files() if 'remind' in name])

    def test_reminder_units_are_removed_when_lead_cleared(self):
        A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5), pre_minutes=15)
        self.assertTrue([n for n in self.unit_files() if 'remind' in n])
        A.prepare_adhan_units(self.exe, *FEYyum, method='egypt', start=dt.date(2026, 11, 5), pre_minutes=0)
        self.assertFalse([n for n in self.unit_files() if 'remind' in n])

    def test_path_with_newline_is_rejected(self):
        ok, message = A.prepare_adhan_units(Path('/tmp/bad\npath'), *FEYyum)
        self.assertFalse(ok)
        self.assertIn('مسار', message)


if __name__ == '__main__':
    unittest.main()
