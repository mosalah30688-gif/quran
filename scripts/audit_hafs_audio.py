#!/usr/bin/env python3
"""يفحص توافر عينة من كل قارئ حفص في CDN المعتمد ويكتب دليلاً JSON."""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import urllib.error
import urllib.request
from pathlib import Path

SAMPLES = (1, 262, 6236)


def load_catalog(path: Path):
    tree = ast.parse((path / "main.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "HAFS_RECITERS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("HAFS_RECITERS was not found")


def probe(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Range": "bytes=0-31", "User-Agent": "SirajAudioAudit/1.1"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read(32)
            return {
                "ok": response.status in {200, 206} and len(data) > 0,
                "status": response.status,
                "content_type": response.headers.get_content_type(),
                "bytes_read": len(data),
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except (OSError, urllib.error.URLError) as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", default="windows_app", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    catalog = load_catalog(args.app_dir.resolve())
    rows = []
    for identifier, name, bitrate in catalog:
        checks = []
        for number in SAMPLES:
            url = f"https://cdn.islamic.network/quran/audio/{bitrate}/{identifier}/{number}.mp3"
            checks.append({"ayah_global": number, "url": url, **probe(url)})
        rows.append({
            "identifier": identifier,
            "name": name,
            "bitrate": bitrate,
            "ok": all(item["ok"] for item in checks),
            "checks": checks,
        })
    report = {
        "schema": 1,
        "checked_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "https://cdn.islamic.network/quran/audio/",
        "edition_registry": "https://api.alquran.cloud/v1/edition/format/audio",
        "terms": "https://alquran.cloud/terms-and-conditions",
        "samples": list(SAMPLES),
        "reciter_count": len(rows),
        "all_ok": all(row["ok"] for row in rows),
        "reciters": rows,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
