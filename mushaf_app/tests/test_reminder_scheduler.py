import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import reminder_scheduler as scheduler  # noqa: E402


class FakeSettings:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.synced = False

    def value(self, key, default=None, type=None):  # noqa: A002
        value = self.values.get(key, default)
        if type is bool:
            return bool(value)
        if type is str:
            return str(value)
        return value

    def setValue(self, key, value):  # noqa: N802
        self.values[key] = value

    def sync(self):
        self.synced = True


class ReminderSchedulerTests(unittest.TestCase):
    def test_time_validation_and_settings_round_trip(self):
        self.assertEqual(scheduler.valid_time("00:00"), "00:00")
        self.assertEqual(scheduler.valid_time("23:59"), "23:59")
        for bad in ("24:00", "7:30", "20:60", "x", None):
            self.assertEqual(scheduler.valid_time(bad), scheduler.DEFAULT_TIME)
        settings = FakeSettings({"reminder/enabled": False, "reminder/time": "07:05"})
        self.assertEqual(scheduler.reminder_config(settings), (False, "07:05"))
        scheduler.save_reminder_config(settings, True, "99:99")
        self.assertEqual(settings.values["reminder/enabled"], True)
        self.assertEqual(settings.values["reminder/time"], scheduler.DEFAULT_TIME)
        self.assertTrue(settings.synced)

    def test_windows_schedule_uses_limited_daily_user_task(self):
        executable = Path(r"C:\Siraj Quran\Siraj.exe")
        with mock.patch.object(scheduler, "_run", return_value=(True, "")) as run:
            ok, message = scheduler._windows_schedule(executable, True, "06:45")
        self.assertTrue(ok, message)
        command = run.call_args.args[0]
        self.assertEqual(command[:5], ["schtasks", "/Create", "/TN", scheduler.TASK_NAME, "/TR"])
        self.assertEqual(command[5], f'"{executable}" --remind')
        self.assertIn("DAILY", command)
        self.assertIn("06:45", command)
        self.assertEqual(command[-2:], ["/RL", "LIMITED"])

    def test_windows_disable_is_idempotent_for_missing_task(self):
        with mock.patch.object(scheduler, "_run", return_value=(False, "ERROR: cannot find the task")):
            ok, _message = scheduler._windows_schedule(Path("Siraj.exe"), False, "20:00")
        self.assertTrue(ok)

    def test_systemd_units_are_written_escaped_enabled_and_restarted(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "Siraj 100%.AppImage"
            executable.write_bytes(b"app")
            calls = []

            def fake_run(command, timeout=15):
                calls.append(command)
                return True, ""

            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": folder}), mock.patch.object(
                scheduler, "_run", side_effect=fake_run
            ):
                ok, message = scheduler._systemd_schedule(executable, True, "07:05")
                service, timer = scheduler._systemd_paths()
                service_text = service.read_text(encoding="utf-8")
                timer_text = timer.read_text(encoding="utf-8")
            self.assertTrue(ok, message)
            self.assertIn("ExecStart=", service_text)
            self.assertIn("Siraj 100%%.AppImage", service_text)
            self.assertIn(" --remind", service_text)
            self.assertIn("OnCalendar=*-*-* 07:05:00", timer_text)
            self.assertIn("Persistent=true", timer_text)
            self.assertEqual(calls[0], ["systemctl", "--user", "daemon-reload"])
            self.assertEqual(calls[1], ["systemctl", "--user", "enable", timer.name])
            self.assertEqual(calls[2], ["systemctl", "--user", "restart", timer.name])

    def test_systemd_disable_removes_units_and_reloads(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": folder}):
                service, timer = scheduler._systemd_paths()
                service.parent.mkdir(parents=True)
                service.write_text("service", encoding="utf-8")
                timer.write_text("timer", encoding="utf-8")
                with mock.patch.object(scheduler, "_run", return_value=(True, "")) as run:
                    ok, _message = scheduler._systemd_schedule(Path("/tmp/Siraj.AppImage"), False, "20:00")
            self.assertTrue(ok)
            self.assertFalse(service.exists())
            self.assertFalse(timer.exists())
            self.assertEqual(run.call_args_list[0].args[0], ["systemctl", "--user", "disable", "--now", timer.name])
            self.assertEqual(run.call_args_list[1].args[0], ["systemctl", "--user", "daemon-reload"])

    def test_systemd_rejects_newline_in_executable(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": folder}):
            with mock.patch.object(scheduler, "_run") as run:
                ok, _message = scheduler._systemd_schedule(Path("/tmp/Siraj\nBad.AppImage"), True, "20:00")
        self.assertFalse(ok)
        run.assert_not_called()

    def test_application_executable_prefers_appimage(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "Siraj.AppImage"
            executable.write_bytes(b"app")
            with mock.patch.object(scheduler.sys, "platform", "linux"), mock.patch.dict(
                os.environ, {"APPIMAGE": str(executable)}
            ):
                self.assertEqual(scheduler.application_executable(), executable.resolve())

    def test_configure_does_not_touch_system_in_development(self):
        with mock.patch.object(scheduler, "application_executable", return_value=None), mock.patch.object(
            scheduler, "_run"
        ) as run:
            ok, message = scheduler.configure_system_reminder(True, "20:00")
        self.assertTrue(ok)
        self.assertIn("المجمّعة", message)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
