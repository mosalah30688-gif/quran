"""جدولة تذكير الختمة اليومي للمستخدم من دون خدمة دائمة.

Windows يستخدم مهمة مجدولة بصلاحيات المستخدم، وLinux يستخدم systemd --user.
كلاهما يشغّل نفس التطبيق مع ``--remind``؛ التطبيق يفحص سجل اليوم قبل أن يعرض
أي إشعار، لذلك لا يظهر التنبيه إذا كانت هناك قراءة مسجلة.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

TASK_NAME = "SirajQuranKhatmaReminder"
UNIT_BASE = "siraj-quran-reminder"
DEFAULT_TIME = "20:00"


def valid_time(value: object) -> str:
    text = str(value or DEFAULT_TIME).strip()
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
        return DEFAULT_TIME
    return text


def reminder_config(settings) -> tuple[bool, str]:
    enabled = settings.value("reminder/enabled", True, type=bool)
    when = valid_time(settings.value("reminder/time", DEFAULT_TIME, type=str))
    return bool(enabled), when


def save_reminder_config(settings, enabled: bool, when: str) -> None:
    settings.setValue("reminder/enabled", bool(enabled))
    settings.setValue("reminder/time", valid_time(when))
    settings.sync()


def application_executable() -> Path | None:
    if sys.platform.startswith("linux"):
        appimage = os.environ.get("APPIMAGE", "").strip()
        if appimage:
            path = Path(appimage).expanduser().resolve()
            return path if path.is_file() else None
    if getattr(sys, "frozen", False):
        path = Path(sys.executable).resolve()
        return path if path.is_file() else None
    return None


def _run(command: list[str], timeout: int = 15) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    message = (result.stderr or result.stdout or "").strip()
    return result.returncode == 0, message


def _windows_schedule(executable: Path, enabled: bool, when: str) -> tuple[bool, str]:
    if not enabled:
        ok, message = _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        # عدم وجود المهمة يعادل نجاح التعطيل.
        return (True, "تم تعطيل إشعار النظام") if ok or "cannot find" in message.lower() else (False, message)
    action = f'"{executable}" --remind'
    ok, message = _run([
        "schtasks", "/Create", "/TN", TASK_NAME, "/TR", action,
        "/SC", "DAILY", "/ST", when, "/F", "/RL", "LIMITED",
    ])
    return (True, f"إشعار النظام مضبوط يومياً عند {when}") if ok else (False, message)


def _systemd_paths() -> tuple[Path, Path]:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd" / "user"
    return root / f"{UNIT_BASE}.service", root / f"{UNIT_BASE}.timer"


def _systemd_schedule(executable: Path, enabled: bool, when: str) -> tuple[bool, str]:
    service, timer = _systemd_paths()
    if not enabled:
        _run(["systemctl", "--user", "disable", "--now", timer.name])
        service.unlink(missing_ok=True)
        timer.unlink(missing_ok=True)
        _run(["systemctl", "--user", "daemon-reload"])
        return True, "تم تعطيل إشعار النظام"

    if "\n" in str(executable) or "\r" in str(executable):
        return False, "مسار التطبيق غير صالح للجدولة"
    service.parent.mkdir(parents=True, exist_ok=True)
    # اقتباس JSON متوافق مع اقتباس systemd، مع تعطيل مفسّر % الخاص بالوحدات.
    quoted = json.dumps(str(executable).replace("%", "%%"), ensure_ascii=False)
    hour, minute = when.split(":", 1)
    service_text = (
        "[Unit]\nDescription=Siraj Quran khatma reminder\n\n"
        "[Service]\nType=oneshot\n"
        f"ExecStart={quoted} --remind\n"
    )
    timer_text = (
        "[Unit]\nDescription=Daily Siraj Quran khatma reminder\n\n"
        "[Timer]\n"
        f"OnCalendar=*-*-* {hour}:{minute}:00\n"
        "Persistent=true\nAccuracySec=1min\n\n"
        "[Install]\nWantedBy=timers.target\n"
    )
    service.write_text(service_text, encoding="utf-8")
    timer.write_text(timer_text, encoding="utf-8")
    ok, message = _run(["systemctl", "--user", "daemon-reload"])
    if ok:
        ok, message = _run(["systemctl", "--user", "enable", timer.name])
    if ok:
        # restart مهم عند تغيير الوقت بينما المؤقت مفعّل مسبقاً؛ enable --now وحده لا يعيد جدولة مؤقت نشط.
        ok, message = _run(["systemctl", "--user", "restart", timer.name])
    return (True, f"إشعار النظام مضبوط يومياً عند {when}") if ok else (False, message)


def configure_system_reminder(enabled: bool, when: str) -> tuple[bool, str]:
    """يضبط الجدولة؛ في وضع التطوير لا ينشئ مهاماً على جهاز المطور."""
    when = valid_time(when)
    executable = application_executable()
    if executable is None:
        return True, "ستُفعّل جدولة النظام داخل النسخة المجمّعة"
    if sys.platform.startswith("win"):
        return _windows_schedule(executable, enabled, when)
    if sys.platform.startswith("linux"):
        return _systemd_schedule(executable, enabled, when)
    return False, "جدولة إشعار النظام غير مدعومة على هذا النظام"
