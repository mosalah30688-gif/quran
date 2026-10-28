#!/usr/bin/env python3
"""Collect license evidence for the exact installed Python dependency closure.

Run this only after installing the pinned requirements. The output is intended to
ship inside Windows Portable and Linux AppImage alongside THIRD_PARTY_NOTICES.md.
It supplements, but does not replace, corresponding-source duties for copyleft
components such as Qt.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import re
import shutil
from collections import deque
from pathlib import Path
from typing import Iterable

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
LICENSE_NAMES = re.compile(
    r"^(license|licence|copying|copyright|notice|authors?)([._-].*)?$", re.I
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def requirements_from_file(path: Path) -> list[Requirement]:
    result = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(("-r", "--requirement")):
            continue
        result.append(Requirement(line))
    return result


def active_dependencies(dist: metadata.Distribution) -> Iterable[Requirement]:
    for raw in dist.requires or ():
        req = Requirement(raw)
        if req.marker is not None and not req.marker.evaluate({"extra": ""}):
            continue
        yield req


def dependency_closure(initial: list[Requirement]) -> dict[str, metadata.Distribution]:
    queue = deque(initial)
    found: dict[str, metadata.Distribution] = {}
    while queue:
        req = queue.popleft()
        key = canonicalize_name(req.name)
        if key in found:
            continue
        try:
            dist = metadata.distribution(req.name)
        except metadata.PackageNotFoundError as exc:
            raise SystemExit(f"Required distribution is not installed: {req.name}") from exc
        if req.specifier and dist.version not in req.specifier:
            raise SystemExit(
                f"Installed {req.name} {dist.version} does not satisfy {req.specifier}"
            )
        found[key] = dist
        queue.extend(active_dependencies(dist))
    return found


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._+-]+", "_", value).strip("._") or "file"


def candidate_license_files(dist: metadata.Distribution) -> list[Path]:
    candidates: list[Path] = []
    declared = dist.metadata.get_all("License-File") or []
    for item in declared:
        located = Path(dist.locate_file(item))
        if located.is_file():
            candidates.append(located)
    for item in dist.files or ():
        path = Path(item)
        if not LICENSE_NAMES.match(path.name):
            continue
        located = Path(dist.locate_file(item))
        if located.is_file():
            candidates.append(located)
    unique: dict[str, Path] = {}
    for path in candidates:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        unique.setdefault(digest(data), path)
    return list(unique.values())


def project_urls(dist: metadata.Distribution) -> list[str]:
    values = []
    for raw in dist.metadata.get_all("Project-URL") or ():
        values.append(raw)
    home = dist.metadata.get("Home-page")
    if home:
        values.append(f"Home-page, {home}")
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--overrides",
        type=Path,
        default=ROOT / "third_party" / "python-license-overrides",
        help="Optional repo-supplied notices, grouped by canonical package name",
    )
    parser.add_argument(
        "--fail-missing",
        action="store_true",
        help="Fail when a distribution and its override directory provide no license text",
    )
    args = parser.parse_args()

    req_path = args.requirements if args.requirements.is_absolute() else ROOT / args.requirements
    out = args.output if args.output.is_absolute() else ROOT / args.output
    overrides = args.overrides if args.overrides.is_absolute() else ROOT / args.overrides
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    direct = requirements_from_file(req_path)
    closure = dependency_closure(direct)
    records = []
    missing = []
    for key, dist in sorted(closure.items()):
        name = dist.metadata.get("Name") or key
        target = out / f"{safe_filename(name)}-{safe_filename(dist.version)}"
        target.mkdir()
        copied = []
        used_names: set[str] = set()
        for source in candidate_license_files(dist):
            base = safe_filename(source.name)
            filename = base
            counter = 2
            while filename.lower() in used_names:
                filename = f"{counter}-{base}"
                counter += 1
            used_names.add(filename.lower())
            data = source.read_bytes()
            (target / filename).write_bytes(data)
            copied.append(
                {"file": filename, "sha256": digest(data), "origin": "installed-distribution"}
            )
        override = overrides / key
        if override.is_dir():
            for source in sorted(override.iterdir()):
                if not source.is_file():
                    continue
                base = safe_filename(source.name)
                filename = f"project-{base}"
                counter = 2
                while filename.lower() in used_names:
                    filename = f"project-{counter}-{base}"
                    counter += 1
                used_names.add(filename.lower())
                data = source.read_bytes()
                (target / filename).write_bytes(data)
                copied.append({"file": filename, "sha256": digest(data), "origin": "repository-override"})
        if not copied:
            missing.append(f"{name}=={dist.version}")
        record = {
            "name": name,
            "canonical_name": key,
            "version": dist.version,
            "license_expression": dist.metadata.get("License-Expression"),
            "license_metadata": dist.metadata.get("License"),
            "project_urls": project_urls(dist),
            "requires": [str(item) for item in active_dependencies(dist)],
            "license_files": copied,
        }
        records.append(record)
        (target / "METADATA.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    inventory = {
        "schema": 1,
        "requirements": req_path.relative_to(ROOT).as_posix()
        if req_path.is_relative_to(ROOT)
        else str(req_path),
        "direct_requirements": [str(item) for item in direct],
        "distributions": records,
        "missing_license_files": missing,
        "note": (
            "Collected from exact installed distributions plus explicit repository overrides. "
            "This does not itself satisfy corresponding-source obligations."
        ),
    }
    (out / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Python dependency licenses",
        "",
        "Generated from the exact installed dependency closure. See `inventory.json` for hashes.",
        "This directory does not replace any required corresponding-source offer.",
        "",
        "| Distribution | Version | Declared license | Included texts |",
        "|---|---:|---|---:|",
    ]
    for record in records:
        declared = record["license_expression"] or record["license_metadata"] or "not declared"
        lines.append(
            f"| {record['name']} | {record['version']} | {str(declared).replace('|', '/')} | "
            f"{len(record['license_files'])} |"
        )
    if missing:
        lines += ["", "## Missing texts", ""] + [f"- {item}" for item in missing]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Collected {len(records)} distributions in {out}")
    if missing:
        print("Missing license texts: " + ", ".join(missing))
        if args.fail_missing:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
