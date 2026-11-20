#!/usr/bin/env python3
"""يبني كتالوج القرّاء (quran-reciters.json) من واجهة MP3Quran الرسمية.

    python3 scripts/build_reciter_catalog.py

- كل مصحف (moshaf) يصبح عنصرًا مستقلًا: قارئ + رواية + سيرفر.
- يُقبل ما يغطي ١٠٠ سورة أو أكثر؛ وإن نقص العدد نُختبر السور الناقصة فعليًا على السيرفر
  (بعض المصاحف الجديدة يُبلِّغ عنها المصدر ناقصة وهي كاملة).
- المعرّف = معرّف المصحف في MP3Quran (فريد)، وإن تعارض أُضيف معرّف القارئ.
- العائلة (family) تُشتق من اسم الرواية ليبقى فلتر الروايات يعمل.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'quran-reciters.json'
API = 'https://mp3quran.net/api/v3/reciters?language=ar'

FAMILIES = ['حفص', 'ورش', 'قالون', 'الدوري', 'السوسي', 'شعبة', 'البزي', 'قنبل']


def file_exists(url: str) -> bool:
    request = urllib.request.Request(url, headers={'User-Agent': 'siraj-catalog/1.0', 'Range': 'bytes=0-512'})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.status in (200, 206)
    except Exception:
        return False


def real_total(server: str, reported: int) -> int:
    """يتحقق من السور التي لم يُبلِّغ عنها المصدر: قد تكون موجودة فعلًا."""
    if reported >= 114:
        return 114
    missing = list(range(reported + 1, 115))
    if all(file_exists(f'{server}{number:03d}.mp3') for number in missing):
        return 114
    return reported


def family_of(rewaya: str) -> str:
    for name in FAMILIES:
        if name in rewaya:
            return name
    return 'أخرى'


def main() -> int:
    request = urllib.request.Request(API, headers={'User-Agent': 'siraj-catalog/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode('utf-8'))

    items: list[dict] = []
    seen_servers: set[str] = set()
    seen_ids: set[int] = set()

    for reciter in payload.get('reciters', []):
        name = (reciter.get('name') or '').strip()
        letter = (reciter.get('letter') or '').strip()
        for moshaf in reciter.get('moshaf') or []:
            server = (moshaf.get('server') or '').strip()
            rewaya = (moshaf.get('name') or '').strip()
            total = int(moshaf.get('surah_total') or 0)
            if not name or not server or not rewaya:
                continue
            if total < 100:
                continue
            if not server.startswith('https://') or not server.endswith('/'):
                continue
            if server in seen_servers:
                continue
            identifier = int(moshaf.get('id') or 0)
            if not identifier or identifier in seen_ids:
                identifier = int(reciter.get('id') or 0) * 1000 + len(items) + 1
            while identifier in seen_ids:
                identifier += 1
            if total < 114:
                total = real_total(server, total)
            seen_servers.add(server)
            seen_ids.add(identifier)
            items.append({
                'id': identifier,
                'name': name,
                'letter': letter,
                'server': server,
                'rewaya': rewaya,
                'surahs': total,
                'family': family_of(rewaya),
            })

    items.sort(key=lambda item: (item['name'], -item['surahs'], item['rewaya']))
    families = {}
    for item in items:
        families[item['family']] = families.get(item['family'], 0) + 1

    document = {
        'version': 2,
        'source': 'MP3Quran API v3 — mp3quran.net/api/v3/reciters',
        'note': 'كل مصحف عنصر مستقل (قارئ + رواية + سيرفر)، ملف واحد لكل سورة.',
        'count': len(items),
        'families': families,
        'items': items,
    }
    OUT.write_text(json.dumps(document, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    print(f'كُتب {OUT.name}: {len(items)} مصحفًا لـ {len({i["name"] for i in items})} قارئًا')
    for family, count in sorted(families.items(), key=lambda pair: -pair[1]):
        print(f'  {family}: {count}')
    missing = [name for name in ('حفص', 'ورش', 'قالون', 'الدوري') if name not in families]
    if missing:
        print('تحذير: عائلات مفقودة: ' + ' · '.join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
