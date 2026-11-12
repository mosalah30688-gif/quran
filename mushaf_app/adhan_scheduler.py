"""جدولة الأذان على سطح المكتب عبر مؤقتات systemd الخاصة بالمستخدم.

لا يُشغّل التطبيق خدمة دائمة: كل صلاة لها مؤقت `systemd --user` يعمل في وقتها
ويشغّل التطبيق بالوضع ``--adhan <الصلاة>``، فيظهر إشعار ويُشغَّل صوت المؤذن
المختار. تُحدَّث المؤقتات تلقائيًا مع كل تشغيل ومع تغيير المدينة أو الصوت،
لأن مواقيت الصلاة تتغيّر يوميًا.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

import prayer_times as PT

UNIT_PREFIX = 'siraj-adhan'
PRAYER_KEYS = ('fajr', 'dhuhr', 'asr', 'maghrib', 'isha')
DAYS_AHEAD = 2


def _skips_systemctl() -> bool:
    return os.environ.get('SIRAJ_SKIP_SYSTEMCTL') == '1'


def _run(command: list[str], timeout: int = 15) -> tuple[bool, str]:
    if _skips_systemctl():
        return True, 'skipped'
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    message = (result.stderr or result.stdout or '').strip()
    return result.returncode == 0, message


def unit_dir() -> Path:
    root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'systemd' / 'user'
    return root


def plan_events(
    lat: float,
    lng: float,
    timezone: float,
    method: str = 'mwl',
    madhab: str = 'shafi',
    start: dt.date | None = None,
    days: int = DAYS_AHEAD,
) -> list[dict]:
    """مواقيت الأذان القادمة (اليوم والغد) مرتبة زمنيًا."""
    today = start or dt.date.today()
    now = dt.datetime.now()
    events: list[dict] = []
    for offset in range(max(1, days)):
        day = today + dt.timedelta(days=offset)
        table = PT.times(day, lat, lng, timezone, method=method, madhab=madhab)
        if not table:
            continue
        for key in PRAYER_KEYS:
            hours = table.get(key)
            if hours is None:
                continue
            minutes = (hours % 24) * 60
            moment = dt.datetime.combine(day, dt.time(hour=int(minutes // 60), minute=int(round(minutes % 60))))
            if offset == 0 and moment <= now:
                continue
            events.append({'key': key, 'name': PT.NAMES[key], 'at': moment})
    events.sort(key=lambda item: item['at'])
    return events


def prepare_adhan_units(
    executable: Path,
    lat: float,
    lng: float,
    timezone: float,
    method: str = 'mwl',
    madhab: str = 'shafi',
    enabled: bool = True,
    start: dt.date | None = None,
    pre_minutes: int = 0,
) -> tuple[bool, str]:
    """يكتب مؤقتًا لكل صلاة على أقرب موعدين، ويحذف المؤقتات القديمة."""
    folder = unit_dir()
    folder.mkdir(parents=True, exist_ok=True)
    wanted: set[str] = set()

    if not enabled:
        _remove_units(folder, wanted)
        return True, 'تم إيقاف الأذان'

    if '\n' in str(executable) or '\r' in str(executable):
        return False, 'مسار التطبيق غير صالح للجدولة'

    events = plan_events(lat, lng, timezone, method, madhab, start=start)
    by_prayer: dict[str, list[dict]] = {}
    for event in events:
        by_prayer.setdefault(event['key'], []).append(event)

    quoted = json.dumps(str(executable).replace('%', '%%'), ensure_ascii=False)
    try:
        lead = max(0, min(60, int(pre_minutes)))
    except (TypeError, ValueError):
        lead = 0
    for key, items in by_prayer.items():
        occurrences = items[:DAYS_AHEAD]
        if not occurrences:
            continue
        base = f'{UNIT_PREFIX}-{key}'
        wanted.add(base)
        service = folder / f'{base}.service'
        timer = folder / f'{base}.timer'
        service.write_text(
            '[Unit]\nDescription=Siraj adhan ' + key + '\n\n'
            '[Service]\nType=oneshot\n'
            f'ExecStart={quoted} --adhan {key}\n',
            encoding='utf-8',
        )
        calendar = '\n'.join(
            f'OnCalendar={item["at"].strftime("%Y-%m-%d %H:%M:%S")}' for item in occurrences
        )
        timer.write_text(
            '[Unit]\nDescription=Siraj adhan timer ' + key + '\n\n'
            f'[Timer]\n{calendar}\nPersistent=true\nAccuracySec=1s\n\n'
            '[Install]\nWantedBy=timers.target\n',
            encoding='utf-8',
        )

    if lead:
        # تذكير منطوق قبل الأذان بعدد الدقائق المتبقية
        for key, items in by_prayer.items():
            occurrences = [
                item['at'] - dt.timedelta(minutes=lead) for item in items[:DAYS_AHEAD]
            ]
            if not occurrences:
                continue
            base = f'{UNIT_PREFIX}-remind-{key}'
            wanted.add(base)
            (folder / f'{base}.service').write_text(
                '[Unit]\nDescription=Siraj adhan reminder ' + key + '\n\n'
                '[Service]\nType=oneshot\n'
                f'ExecStart={quoted} --adhan-remind {key} {lead}\n',
                encoding='utf-8',
            )
            calendar = '\n'.join(
                f'OnCalendar={moment.strftime("%Y-%m-%d %H:%M:%S")}' for moment in occurrences
            )
            (folder / f'{base}.timer').write_text(
                '[Unit]\nDescription=Siraj adhan reminder timer ' + key + '\n\n'
                f'[Timer]\n{calendar}\nPersistent=true\nAccuracySec=1s\n\n'
                '[Install]\nWantedBy=timers.target\n',
                encoding='utf-8',
            )

    _remove_units(folder, wanted)
    ok, message = _run(['systemctl', '--user', 'daemon-reload'])
    if ok:
        for base in sorted(wanted):
            _run(['systemctl', '--user', 'enable', f'{base}.timer'])
            _run(['systemctl', '--user', 'restart', f'{base}.timer'])
    if not ok:
        return False, message
    upcoming = events[0]['name'] if events else ''
    return True, f'الأذان مضبوط — الأقرب: {upcoming}'.strip()


def _remove_units(folder: Path, keep: set[str]) -> None:
    for path in sorted(folder.glob(f'{UNIT_PREFIX}-*')):
        if path.stem in keep:
            continue
        path.unlink(missing_ok=True)
        if path.suffix == '.timer':
            _run(['systemctl', '--user', 'disable', '--now', path.name])
    if not keep:
        _run(['systemctl', '--user', 'daemon-reload'])


def clear_adhan() -> tuple[bool, str]:
    folder = unit_dir()
    if folder.is_dir():
        _remove_units(folder, set())
    return True, 'تم إيقاف الأذان'


def next_event(
    lat: float, lng: float, timezone: float, method: str = 'mwl', madhab: str = 'shafi',
) -> dict | None:
    events = plan_events(lat, lng, timezone, method, madhab)
    return events[0] if events else None
