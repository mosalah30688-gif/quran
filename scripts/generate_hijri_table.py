#!/usr/bin/env python3
"""يبني جدول أطوال الأشهر الهجرية (أم القرى) المحزوم مع التطبيق.

الجدول يغطي ١٤٠٠–١٥٠٠ هـ، وهو المدى المنشور رسميًا لتقويم أم القرى. يُكتب في
تطبيقي لينكس وويندوز بنفس البايتات، ويُقرأ عند الطلب بلا شبكة.

البناء يحتاج حزمة ``hijridate`` (رخصة MIT) لأنها تحمل بيانات أم القرى:
    python -m pip install hijridate
    python scripts/generate_hijri_table.py

التحقق لا يحتاج أي حزمة خارجية:
    python scripts/generate_hijri_table.py --verify
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = (
    ROOT / "windows_app" / "data" / "hijri-ummalqura.json",
    ROOT / "mushaf_app" / "data" / "hijri-ummalqura.json",
)
FIRST_YEAR = 1400
LAST_YEAR = 1500


def build() -> bytes:
    from hijridate import Gregorian, Hijri  # noqa: PLC0415 (اعتمادية البناء فقط)

    start = Hijri(FIRST_YEAR, 1, 1).to_gregorian()
    end = Hijri(LAST_YEAR, 12, 29).to_gregorian()
    span = (end - start).days
    months: list[tuple[int, int, int]] = []
    current: list | None = None
    for offset in range(span + 1):
        day = start + dt.timedelta(days=offset)
        hijri = Gregorian.fromdate(day).to_hijri()
        if current is None or (hijri.year, hijri.month) != current[0]:
            if current is not None:
                current[2] = offset - current[3]
                months.append((current[0][0], current[0][1], current[2]))
            current = [(hijri.year, hijri.month), None, 0, offset]
    current[2] = span + 1 - current[3]
    months.append((current[0][0], current[0][1], current[2]))

    table: dict[str, str] = {}
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        code = ""
        for month in range(1, 13):
            length = next(item[2] for item in months if item[0] == year and item[1] == month)
            if length not in (29, 30):
                raise ValueError(f"unexpected month length {length} for {year}-{month}")
            code += "1" if length == 30 else "0"
        table[str(year)] = code

    payload = {
        "version": 1,
        "calendar": "Umm al-Qura",
        "range": [FIRST_YEAR, LAST_YEAR],
        "epoch": start.isoformat(),
        "encoding": "one character per month: 1 = 30 days, 0 = 29 days",
        "source": f"hijridate (MIT) Umm al-Qura month lengths {FIRST_YEAR}-{LAST_YEAR} AH",
        "years": table,
    }
    return (json.dumps(payload, ensure_ascii=False, indent=0) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="قارن النسختين بلا بناء")
    args = parser.parse_args()

    if args.verify:
        missing = [path for path in OUTPUTS if not path.is_file()]
        if missing:
            raise SystemExit("missing hijri table: " + ", ".join(p.relative_to(ROOT).as_posix() for p in missing))
        first, second = (path.read_bytes() for path in OUTPUTS)
        if first != second:
            raise SystemExit("hijri table differs between Windows and Linux")
        payload = json.loads(first)
        if payload.get("range") != [FIRST_YEAR, LAST_YEAR]:
            raise SystemExit("unexpected hijri table range")
        if len(payload.get("years", {})) != LAST_YEAR - FIRST_YEAR + 1:
            raise SystemExit("incomplete hijri table years")
        print(f"Verified Umm al-Qura table {FIRST_YEAR}-{LAST_YEAR} AH for both desktop apps")
        return 0

    raw = build()
    for path in OUTPUTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    print(f"Wrote {len(raw)} bytes to {len(OUTPUTS)} desktop apps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
