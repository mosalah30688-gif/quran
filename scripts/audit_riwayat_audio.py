#!/usr/bin/env python3
"""Lock MP3Quran metadata and availability evidence for non-Hafs recitations."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import ssl
import urllib.request
from pathlib import Path

API_URL = "https://www.mp3quran.net/api/v3/reciters?language=ar"
EXPECTED = {
    "https://cdn.mp3quran.net/audio/abdulbasit-abdulsamad/r2/": {
        "reciter_id": 51,
        "reciter": "عبدالباسط عبدالصمد",
        "moshaf_id": 52,
        "name": "ورش عن نافع - مرتل",
        "rewaya_id": 2,
    },
    "https://cdn.mp3quran.net/audio/mahmoud-husary/r3/": {
        "reciter_id": 118,
        "reciter": "محمود خليل الحصري",
        "moshaf_id": 120,
        "name": "ورش عن نافع - مرتل",
        "rewaya_id": 2,
    },
    "https://cdn.mp3quran.net/audio/mahmoud-husary/r5/": {
        "reciter_id": 118,
        "reciter": "محمود خليل الحصري",
        "moshaf_id": 270,
        "name": "قالون عن نافع - مرتل",
        "rewaya_id": 5,
    },
    "https://cdn.mp3quran.net/audio/ali-hudhaifi/r2/": {
        "reciter_id": 74,
        "reciter": "علي بن عبدالرحمن الحذيفي",
        "moshaf_id": 75,
        "name": "قالون عن نافع - مرتل",
        "rewaya_id": 5,
    },
    "https://cdn.mp3quran.net/audio/mahmoud-husary/r4/": {
        "reciter_id": 118,
        "reciter": "محمود خليل الحصري",
        "moshaf_id": 269,
        "name": "الدوري عن أبي عمرو - مرتل",
        "rewaya_id": 13,
    },
}
SAMPLE_SURAHS = (1, 2, 114)


def fetch(request: str | urllib.request.Request, timeout: int) -> tuple[bytes, object]:
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.read(), response.headers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audit/riwayat-audio-mp3quran-2026-10-28.json"),
    )
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    raw, _headers = fetch(API_URL, args.timeout)
    payload = json.loads(raw)
    by_server: dict[str, dict] = {}
    for reciter in payload.get("reciters", []):
        for moshaf in reciter.get("moshaf", []):
            server = moshaf.get("server")
            if server in EXPECTED:
                by_server[server] = {
                    "reciter_id": reciter.get("id"),
                    "reciter": reciter.get("name"),
                    "moshaf_id": moshaf.get("id"),
                    **moshaf,
                }

    records = []
    for server, expected in EXPECTED.items():
        record = by_server.get(server)
        if record is None:
            raise SystemExit(f"MP3Quran API no longer lists {server}")
        for field, value in expected.items():
            if record.get(field) != value:
                raise SystemExit(
                    f"MP3Quran metadata mismatch for {server}: {field}={record.get(field)!r}, expected {value!r}"
                )
        listed = {int(item) for item in str(record.get("surah_list", "")).split(",") if item}
        if record.get("surah_total") != 114 or listed != set(range(1, 115)):
            raise SystemExit(f"MP3Quran source is not a complete 114-surah set: {server}")

        probes = []
        for surah in SAMPLE_SURAHS:
            url = f"{server}{surah:03d}.mp3"
            request = urllib.request.Request(url, headers={"Range": "bytes=0-1023"})
            sample, headers = fetch(request, args.timeout)
            content_type = headers.get_content_type()
            content_range = headers.get("Content-Range", "")
            if content_type not in {"audio/mpeg", "audio/mp3"} or len(sample) != 1024:
                raise SystemExit(f"Invalid audio probe for {url}")
            probes.append(
                {
                    "surah": surah,
                    "url": url,
                    "content_type": content_type,
                    "content_range": content_range,
                    "sample_bytes": len(sample),
                    "sample_sha256": hashlib.sha256(sample).hexdigest(),
                }
            )
        records.append(
            {
                "server": server,
                "reciter_id": record["reciter_id"],
                "reciter": record["reciter"],
                "moshaf_id": record["id"],
                "name": record["name"],
                "rewaya_id": record["rewaya_id"],
                "surah_total": record["surah_total"],
                "surah_list": record["surah_list"],
                "probes": probes,
            }
        )

    report = {
        "schema": 1,
        "fetched_at": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "api_url": API_URL,
        "api_response_sha256": hashlib.sha256(raw).hexdigest(),
        "note": "MP3Quran moshaf id 52, not timing/read id 51, explicitly identifies Abdulbasit r2 as complete Warsh. Playback uses complete surah files and does not depend on ayah timing data.",
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(records)} MP3Quran riwayat sources and {len(records) * len(SAMPLE_SURAHS)} audio samples")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
