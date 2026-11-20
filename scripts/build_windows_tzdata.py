#!/usr/bin/env python3
"""يجمّع ملفات TZif اللازمة لمدن سراج داخل مجلد مستقل لحزمة Windows.

ويندوز لا يملك قاعدة مناطق زمنية في النظام، ووحدة ``zoneinfo`` القياسية تحتاج ملفات
IANA على القرص. هذا السكربت ينسخ ملفات المناطق الزمنية المستخدمة فعلًا في
``prayer-cities.json`` (بلا تعديل) إلى ``windows_app/tzdata`` مع ملف إسناد، حتى تعمل
مواقيت الصلاة والتوقيت الصيفي داخل الحزمة المجمّدة وداخل الترقيعات الصغيرة أيضًا.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP = ROOT / "windows_app"
DEFAULT_SYSTEM_TZ = Path("/usr/share/zoneinfo")


def required_zones(cities_path: Path) -> list[str]:
    data = json.loads(cities_path.read_text(encoding="utf-8"))
    zones = {str(city.get("tz") or "") for city in data.get("cities", []) if city.get("tz")}
    if not zones:
        raise SystemExit("prayer-cities.json has no time zones")
    return sorted(zones)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", type=Path, default=DEFAULT_APP)
    parser.add_argument("--system-tz", type=Path, default=DEFAULT_SYSTEM_TZ)
    args = parser.parse_args()
    app_dir = args.app_dir.resolve()
    source = args.system_tz.resolve()
    if not source.is_dir():
        raise SystemExit(f"missing system time zone database: {source}")

    zones = required_zones(app_dir / "data" / "prayer-cities.json")
    target = app_dir / "tzdata"
    if target.exists():
        shutil.rmtree(target)
    copied = []
    for zone in zones:
        origin = source / zone
        if not origin.is_file():
            raise SystemExit(f"missing time zone file for {zone}")
        destination = target / zone
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin, destination)
        copied.append({"zone": zone, "size": destination.stat().st_size})

    attribution = {
        "source": "IANA Time Zone Database (TZif), as shipped by the operating system",
        "version": (source / "tzdata.zi").read_text(encoding="utf-8").splitlines()[0]
        if (source / "tzdata.zi").is_file()
        else "unknown",
        "license": "Public domain (IANA tz database), see https://www.iana.org/time-zones",
        "zones": copied,
    }
    (target / "ATTRIBUTION.json").write_text(
        json.dumps(attribution, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"copied {len(copied)} time zones into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
