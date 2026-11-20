"""اختبار جدولة الأذان على ويندوز: مهام Task Scheduler بدل مؤقتات systemd.

الاختبار لا يحتاج ويندوز: يتحقق من خطة المهام والأوامر التي ستُنفّذ، ثم يشغّل مسار
التنفيذ كاملًا مع تعطيل schtasks لضمان أن التطبيق لا يتعطّل على أي منصة.
"""
import datetime as dt
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import adhan_scheduler  # noqa: E402


class WindowsAdhanTaskTests(unittest.TestCase):
    def setUp(self):
        self.events = adhan_scheduler.plan_events(
            30.0444, 31.2357, 2.0, start=dt.date.today(), days=2
        )

    def test_every_prayer_gets_a_task_with_exact_datetime(self):
        tasks = adhan_scheduler.windows_task_names(self.events, lead=0)
        self.assertTrue(tasks)
        self.assertTrue(all(task['name'].startswith('SirajAdhan-') for task in tasks))
        self.assertEqual({task['kind'] for task in tasks}, {'adhan'})
        self.assertTrue(all(task['name'].startswith(f"SirajAdhan-{task['key']}-") for task in tasks))
        self.assertEqual(tasks, sorted(tasks, key=lambda item: item['at']))

    def test_task_commands_use_one_shot_schtasks_entries(self):
        task = adhan_scheduler.windows_task_names(self.events, lead=0)[0]
        commands = adhan_scheduler.windows_task_commands(Path('/opt/siraj/Siraj.exe'), task)
        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertEqual(command[0], 'schtasks')
        self.assertIn('/Create', command)
        self.assertIn('/SC', command)
        self.assertEqual(command[command.index('/SC') + 1], 'ONCE')
        self.assertEqual(command[command.index('/SD') + 1], task['at'].strftime('%m/%d/%Y'))
        self.assertEqual(command[command.index('/ST') + 1], task['at'].strftime('%H:%M'))
        self.assertIn('/RUN' if False else '/TN', command)
        action = command[command.index('/TR') + 1]
        self.assertIn(f'--adhan {task["key"]}', action)
        self.assertIn('Siraj.exe', action)

    def test_reminder_tasks_only_exist_with_lead_minutes(self):
        plain = adhan_scheduler.windows_task_names(self.events, lead=0)
        self.assertFalse([task for task in plain if task['kind'] == 'remind'])
        with_lead = adhan_scheduler.windows_task_names(self.events, lead=10)
        reminders = [task for task in with_lead if task['kind'] == 'remind']
        self.assertEqual(len(reminders), len(plain))
        for task in reminders:
            command = adhan_scheduler.windows_task_commands(Path('Siraj.exe'), task, 10)[0]
            action = command[command.index('/TR') + 1]
            self.assertIn(f'--adhan-remind {task["key"]} 10', action)

    def test_prepare_runs_without_schtasks(self):
        with mock.patch.dict(os.environ, {'SIRAJ_SKIP_SCHTASKS': '1'}):
            ok, message = adhan_scheduler.prepare_adhan_units(
                Path('/opt/siraj/Siraj.exe'), 30.0444, 31.2357, 2.0, enabled=True, pre_minutes=10
            )
        self.assertTrue(ok, message)
        self.assertIn('الأذان مضبوط', message)
        with mock.patch.dict(os.environ, {'SIRAJ_SKIP_SCHTASKS': '1'}):
            ok, message = adhan_scheduler.prepare_adhan_units(
                Path('/opt/siraj/Siraj.exe'), 30.0444, 31.2357, 2.0, enabled=False
            )
        self.assertTrue(ok)

    def test_rejects_broken_executable_path(self):
        ok, _message = adhan_scheduler.prepare_adhan_units(Path('/opt/bad\npath/Siraj.exe'), 30.0, 31.0, 2.0)
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main()
