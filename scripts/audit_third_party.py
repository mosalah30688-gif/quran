#!/usr/bin/env python3
"""Create a reproducible inventory of bundled data, fonts, assets and declared deps.

This is an evidence collector, not a legal or scholarly approval. Policy conclusions
live in audit/THIRD_PARTY_REVIEW.md and must be reviewed before a public release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APPS = ("windows_app", "mushaf_app")
TEXT_SUFFIXES = {".py", ".js", ".md", ".sh", ".ps1", ".yml", ".yaml", ".xml", ".txt"}
SOURCE_DOMAINS = (
    "alquran.cloud",
    "islamic.network",
    "mp3quran.net",
    "quranpedia.net",
    "tanzil.net",
)
FONT_LICENSES = {
    "Amiri-Regular.ttf": "OFL-Amiri.txt",
    "AmiriQuran-Regular.ttf": "OFL-AmiriQuran.txt",
    "AmiriQuran-arabic.woff2": "OFL-LICENSE.txt",
    "NotoNaskhArabic-Variable.ttf": "OFL-NotoNaskhArabic.txt",
    "NotoSansArabic-Bold.ttf": "OFL-NotoSansArabic.txt",
    "NotoSansArabic-Regular.ttf": "OFL-NotoSansArabic.txt",
    "ScheherazadeNew-Regular.ttf": "OFL-ScheherazadeNew.txt",
}
REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*==\s*([^\s;]+)")
URL_RE = re.compile(r"https?://[^\s'\"<>`)]+")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return proc.stdout.strip()


def json_inventory(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    item: dict[str, Any] = {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "root_type": type(data).__name__,
    }
    if isinstance(data, (list, dict)):
        item["root_count"] = len(data)
    if isinstance(data, dict):
        item["top_level_keys"] = list(data)[:40]
        metadata: dict[str, Any] = {}
        for key, value in data.items():
            lowered = key.lower()
            if (
                lowered in {"v", "version", "source", "sources", "license", "edition"}
                or "source" in lowered
                or "license" in lowered
            ) and isinstance(value, (str, int, float, bool, type(None))):
                metadata[key] = value
        item["declared_metadata"] = metadata
    return item


def font_inventory(path: Path) -> dict[str, Any]:
    license_name = FONT_LICENSES.get(path.name)
    license_path = path.parent / license_name if license_name else None
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "expected_license_file": license_name,
        "license_present": bool(license_path and license_path.is_file()),
        "license_sha256": sha256(license_path) if license_path and license_path.is_file() else None,
    }


def requirements(path: Path) -> list[dict[str, str]]:
    items = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = REQ_RE.match(raw)
        if match:
            items.append({"name": match.group(1), "version": match.group(2)})
    return items


def source_references() -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {domain: [] for domain in SOURCE_DOMAINS}
    roots = [ROOT / "windows_app", ROOT / "mushaf_app", ROOT / "app.js"]
    paths: list[Path] = []
    for source in roots:
        if source.is_file():
            paths.append(source)
        elif source.is_dir():
            paths.extend(p for p in source.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES)
    for path in sorted(paths):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, 1):
            urls = URL_RE.findall(line)
            for domain in SOURCE_DOMAINS:
                if domain not in line:
                    continue
                found[domain].append(
                    {
                        "path": path.relative_to(ROOT).as_posix(),
                        "line": line_no,
                        "urls": [url.rstrip(".,;") for url in urls if domain in url],
                    }
                )
    return {domain: refs for domain, refs in found.items() if refs}


def parity(entries: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    result = []
    names = sorted({Path(item["path"]).name for values in entries.values() for item in values})
    by_app = {
        app: {Path(item["path"]).name: item for item in entries.get(app, [])}
        for app in APPS
    }
    for name in names:
        left = by_app[APPS[0]].get(name)
        right = by_app[APPS[1]].get(name)
        result.append(
            {
                "name": name,
                APPS[0]: left["sha256"] if left else None,
                APPS[1]: right["sha256"] if right else None,
                "identical": bool(left and right and left["sha256"] == right["sha256"]),
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "audit" / "third-party-inventory-2026-10-28.json",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output

    data: dict[str, list[dict[str, Any]]] = {}
    fonts: dict[str, list[dict[str, Any]]] = {}
    assets: dict[str, list[dict[str, Any]]] = {}
    dependencies: dict[str, list[dict[str, str]]] = {}
    for app in APPS:
        base = ROOT / app
        data[app] = [json_inventory(path) for path in sorted((base / "data").glob("*.json"))]
        fonts[app] = [
            font_inventory(path)
            for path in sorted((base / "fonts").iterdir())
            if path.is_file() and path.suffix.lower() in {".ttf", ".otf", ".woff", ".woff2"}
        ]
        assets[app] = [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for folder in (base / "assets", base)
            if folder.is_dir()
            for path in sorted(folder.iterdir())
            if path.is_file() and path.suffix.lower() in {".png", ".ico", ".svg"}
        ]
        dependencies[app] = requirements(base / "requirements.txt")

    report = {
        "schema": 1,
        "generated_on": "2026-10-28",
        "scope": list(APPS),
        "git_head": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
        "disclaimer": "Evidence inventory only; not a legal or scholarly approval.",
        "data": data,
        "data_parity": parity(data),
        "fonts": fonts,
        "assets": assets,
        "declared_python_dependencies": dependencies,
        "source_references": source_references(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
