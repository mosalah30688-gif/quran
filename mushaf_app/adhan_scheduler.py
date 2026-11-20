"""جدولة الأذان على سطح المكتب بمؤقتات النظام: systemd على Linux ومهام ويندوز على Windows.

لا يُشغّل التطبيق خدمة دائمة: كل صلاة لها مؤقت يعمل في وقتها ويشغّل التطبيق بالوضع
``--adhan <الصلاة>``، فيظهر إشعار ويُشغَّل صوت المؤذن المختار. تُحدَّث المؤقتات
تلقائيًا مع كل تشغيل ومع تغيير المدينة أو الصوت، لأن مواقيت الصلاة تتغيّر يوميًا.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import prayer_times as PT

UNIT_PREFIX = 'siraj-adhan'
WINDOWS_TASK_PREFIX = 'SirajAdhan'
PRAYER_KEYS = ('fajr', 'dhuhr', 'asr', 'maghrib', 'isha')
DAYS_AHEAD = 2


def _skips_systemctl() -> bool:
    return os.environ.get('SIRAJ_SKIP_SYSTEMCTL') == '1'


def _is_windows() -> bool:
    return sys.platform.startswith('win')


def _skips_scheduling() -> bool:
    return _skips_systemctl() or os.environ.get('SIRAJ_SKIP_SCHTASKS') == '1'


def _run(command: list[str], timeout: int = 15) -> tuple[bool, str]:
    if _skips_scheduling():
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
            total = (float(hours) % 24) * 60
            hour = int(total // 60)
            minute = int(round(total - hour * 60))
            if minute >= 60:  # 59.6 دقيقة تُقرَّب إلى الساعة التالية بدل خطأ نطاق
                hour, minute = hour + 1, 0
            if hour >= 24:
                continue
            moment = dt.datetime.combine(day, dt.time(hour=hour, minute=minute))
            if offset == 0 and moment <= now:
                continue
            events.append({'key': key, 'name': PT.NAMES[key], 'at': moment})
    events.sort(key=lambda item: item['at'])
    return events


def windows_task_names(events: list[dict], lead: int = 0) -> list[dict]:
    """يخطّط مهام ويندوز: مهمة لكل صلاة أو تذكير في وقته المحدد بالضبط.

    Task Scheduler يقبل تشغيلًا لمرة واحدة بتاريخ ووقت محددين، لذلك نجدّد المهام مع
    كل تشغيل ومع تغيير المدينة، تمامًا كما تُجدَّد مؤقتات systemd.
    """
    tasks: list[dict] = []
    try:
        minutes = max(0, min(60, int(lead)))
    except (TypeError, ValueError):
        minutes = 0
    for key in PRAYER_KEYS:
        occurrences = [item for item in events if item['key'] == key][:DAYS_AHEAD]
        for item in occurrences:
            tasks.append({
                'name': f'{WINDOWS_TASK_PREFIX}-{key}-{item["at"]:%Y%m%d%H%M}',
                'kind': 'adhan',
                'key': key,
                'at': item['at'],
            })
            if minutes:
                reminder = item['at'] - dt.timedelta(minutes=minutes)
                tasks.append({
                    'name': f'{WINDOWS_TASK_PREFIX}-remind-{key}-{reminder:%Y%m%d%H%M}',
                    'kind': 'remind',
                    'key': key,
                    'at': reminder,
                })
    tasks.sort(key=lambda item: item['at'])
    return tasks


def windows_task_commands(executable: Path, task: dict, lead: int = 0) -> list[list[str]]:
    """أوامر schtasks لإنشاء مهمة صلاة واحدة (منفصلة عن التشغيل لتُختبر بلا ويندوز)."""
    if task['kind'] == 'remind':
        action = f'"{executable}" --adhan-remind {task["key"]} {max(0, min(60, int(lead)))}'
    else:
        action = f'"{executable}" --adhan {task["key"]}'
    at = task['at']
    return [[
        'schtasks', '/Create', '/F', '/TN', task['name'], '/TR', action,
        '/SC', 'ONCE', '/SD', at.strftime('%m/%d/%Y'), '/ST', at.strftime('%H:%M'),
    ]]


def _delete_windows_tasks(keep: set[str]) -> None:
    ok, output = _run(['schtasks', '/Query', '/FO', 'CSV', '/NH'])
    if not ok:
        return
    for line in output.splitlines():
        if not line.startswith(f'"{WINDOWS_TASK_PREFIX}'):
            continue
        name = line.split('","', 1)[0].strip('"')
        if name in keep:
            continue
        _run(['schtasks', '/Delete', '/TN', name, '/F'])


def _prepare_windows_tasks(
    executable: Path, events: list[dict], pre_minutes: int,
) -> tuple[bool, str]:
    try:
        lead = max(0, min(60, int(pre_minutes)))
    except (TypeError, ValueError):
        lead = 0
    tasks = windows_task_names(events, lead)
    keep = {task['name'] for task in tasks}
    _delete_windows_tasks(keep)
    for task in tasks:
        ok = True
        for command in windows_task_commands(executable, task, lead):
            ok, message = _run(command)
            if not ok:
                return False, message
    upcoming = events[0]['name'] if events else ''
    return True, f'الأذان مضبوط — الأقرب: {upcoming}'.strip()


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
    if not enabled:
        if _is_windows():
            _delete_windows_tasks(set())
        else:
            folder = unit_dir()
            folder.mkdir(parents=True, exist_ok=True)
            _remove_units(folder, set())
        return True, 'تم إيقاف الأذان'

    if '\n' in str(executable) or '\r' in str(executable):
        return False, 'مسار التطبيق غير صالح للجدولة'

    events = plan_events(lat, lng, timezone, method, madhab, start=start)
    if _is_windows():
        return _prepare_windows_tasks(executable, events, pre_minutes)

    folder = unit_dir()
    folder.mkdir(parents=True, exist_ok=True)
    wanted: set[str] = set()
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
    if _is_windows():
        _delete_windows_tasks(set())
        return True, 'تم إيقاف الأذان'
    folder = unit_dir()
    if folder.is_dir():
        _remove_units(folder, set())
    return True, 'تم إيقاف الأذان'


def next_event(
    lat: float, lng: float, timezone: float, method: str = 'mwl', madhab: str = 'shafi',
) -> dict | None:
    events = plan_events(lat, lng, timezone, method, madhab)
    return events[0] if events else None
