#!/usr/bin/env python3
"""Verify desktop/mobile audio catalogs only reference audited providers."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ABDULBASIT = "https://cdn.mp3quran.net/audio/abdulbasit-abdulsamad/r2/"


def assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"missing {name} in {path}")


def main() -> int:
    hafs_report = json.loads(
        (ROOT / "audit/audio-cdn-probe-2026-10-28.json").read_text(encoding="utf-8")
    )
    audited_hafs = {item["identifier"]: item["bitrate"] for item in hafs_report.get("reciters", [])}
    if hafs_report.get("all_ok") is not True or len(audited_hafs) != 17:
        raise SystemExit("Hafs evidence does not contain 17 successful audited reciters")

    report = json.loads(
        (ROOT / "audit/riwayat-audio-mp3quran-2026-10-28.json").read_text(encoding="utf-8")
    )
    audited_servers = {item["server"] for item in report.get("records", [])}
    if len(audited_servers) != 5 or ABDULBASIT not in audited_servers:
        raise SystemExit("MP3Quran evidence does not contain the five configured sources")
    for item in report["records"]:
        if item["surah_total"] != 114 or len(item.get("probes", [])) != 3:
            raise SystemExit(f"incomplete MP3Quran evidence for {item['server']}")
    abdulbasit = next(item for item in report["records"] if item["server"] == ABDULBASIT)
    if abdulbasit["moshaf_id"] != 52 or abdulbasit["rewaya_id"] != 2 or "ورش" not in abdulbasit["name"]:
        raise SystemExit("Abdulbasit r2 is not explicitly evidenced as Warsh moshaf 52")

    for app in ("windows_app", "mushaf_app"):
        path = ROOT / app / "main.py"
        hafs = assignment(path, "HAFS_RECITERS")
        riwayat = assignment(path, "RIW_RECITERS")
        configured_hafs = {item[0]: item[2] for item in hafs}
        if configured_hafs != audited_hafs or len(hafs) != len(configured_hafs):
            raise SystemExit(f"{app} Hafs catalog differs from the 17-reciter audit evidence")
        configured_servers = {
            entry[3]
            for entries in riwayat.values()
            for entry in entries
        }
        if configured_servers != audited_servers:
            raise SystemExit(f"{app} riwayat sources differ from the audited server set")
        entry = next(item for item in riwayat["warsh"] if item[0] == "warsh_abdulbasit")
        if entry[2:] != ("surah", ABDULBASIT):
            raise SystemExit(f"{app} Abdulbasit Warsh must use complete MP3Quran surah files")

    scan_paths = [ROOT / "app.js", ROOT / "update/app.js", ROOT / "www/app.js"]
    for path in scan_paths:
        text = path.read_text(encoding="utf-8")
        if "everyayah.com" in text or ABDULBASIT not in text:
            raise SystemExit(f"unaudited Android/web audio source in {path.relative_to(ROOT)}")
        catalog_match = re.search(r"const RECITERS = \[(.*?)\n  \];", text, re.DOTALL)
        if not catalog_match:
            raise SystemExit(f"missing Android/web Hafs catalog in {path.relative_to(ROOT)}")
        web_ids = re.findall(r"\['(ar\.[a-z0-9]+)'\s*,", catalog_match.group(1))
        if len(web_ids) < 16 or len(web_ids) != len(set(web_ids)) or not set(web_ids).issubset(audited_hafs):
            raise SystemExit(f"Android/web Hafs catalog is incomplete or unaudited in {path.relative_to(ROOT)}")
        web_servers = set(
            re.findall(r"https://cdn\.mp3quran\.net/audio/[A-Za-z0-9._/-]+/", text)
        )
        if web_servers != audited_servers:
            raise SystemExit(f"Android/web riwayat sources differ from audit evidence in {path.relative_to(ROOT)}")
        if "ar.waseet" in text or "id.indonesian" in text:
            raise SystemExit(f"blocked edition remains in {path.relative_to(ROOT)}")

    print("Verified 17 desktop Hafs reciters, audited Android subset, and five MP3Quran riwayat sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
