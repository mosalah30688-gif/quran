#!/usr/bin/env python3
"""Inventory ELF/binary inputs copied by PyInstaller on Debian/Ubuntu.

The script uses PyInstaller's COLLECT-00.toc, which retains each destination and
original source path. It copies Debian copyright files and emits exact source
package/version locks for a later `apt-get source` corresponding-source bundle.
Wheel-provided binaries are classified separately and are covered by the Python
license collector plus the Qt corresponding-source bundle.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Any, Iterator


def run(*args: str) -> str:
    proc = subprocess.run(args, text=True, capture_output=True, check=False)
    if proc.returncode:
        return ""
    return proc.stdout.strip()


def walk(value: Any) -> Iterator[tuple[str, str, str]]:
    if (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(isinstance(item, str) for item in value)
        and value[2] in {"BINARY", "EXTENSION", "EXECUTABLE"}
    ):
        yield value[0], value[1], value[2]
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from walk(item)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dpkg_owner(path: Path) -> str | None:
    candidates = [path]
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        resolved = path
    if resolved != path:
        candidates.append(resolved)
    # usrmerge may expose /lib paths while dpkg records /usr/lib paths.
    text = path.as_posix()
    if text.startswith("/lib/"):
        candidates.append(Path("/usr") / text.lstrip("/"))
    for candidate in candidates:
        output = run("dpkg-query", "-S", str(candidate))
        for line in output.splitlines():
            try:
                package, owned = line.split(": ", 1)
            except ValueError:
                continue
            # dpkg-query also reports usrmerge diversion pseudo-lines such as
            # "diversion by PACKAGE from:"; they are not package identifiers.
            if package.startswith("diversion by "):
                continue
            if Path(owned) == candidate:
                return package.split(":", 1)[0]
    return None


def package_metadata(package: str) -> dict[str, str] | None:
    separator = "\x1f"
    fmt = separator.join(
        ("${binary:Package}", "${Version}", "${source:Package}", "${source:Version}")
    )
    raw = run("dpkg-query", "-W", f"-f={fmt}", package)
    if not raw:
        return None
    fields = raw.split(separator)
    if len(fields) != 4:
        return None
    binary, version, source, source_version = fields
    return {
        "binary_package": binary.split(":", 1)[0],
        "binary_version": version,
        "source_package": source or binary.split(":", 1)[0],
        "source_version": source_version or version,
    }


def classify(path: Path) -> str:
    text = path.as_posix()
    if "site-packages/" in text or "dist-packages/" in text:
        return "python_distribution"
    prefix = Path(sys.base_prefix)
    try:
        path.relative_to(prefix)
        return "python_runtime"
    except ValueError:
        pass
    if text.startswith(("/usr/lib/", "/lib/", "/usr/lib64/", "/lib64/")):
        return "system_package"
    if text.startswith("/usr/local/"):
        return "local_runtime"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toc", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fail-unmapped-system", action="store_true")
    args = parser.parse_args()
    toc = args.toc.resolve()
    bundle_root = args.bundle_root.resolve() if args.bundle_root else None
    out = args.output.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    tree = ast.literal_eval(toc.read_text(encoding="utf-8"))
    entries = []
    packages: dict[str, dict[str, Any]] = {}
    unmapped = []
    seen = set()
    for destination, source_raw, kind in walk(tree):
        key = (destination, source_raw, kind)
        if key in seen:
            continue
        seen.add(key)
        if bundle_root is not None:
            packaged_candidates = (
                bundle_root / destination,
                bundle_root / "_internal" / destination,
            )
            if not any(candidate.exists() for candidate in packaged_candidates):
                continue
        source = Path(source_raw)
        category = classify(source)
        item: dict[str, Any] = {
            "destination": destination,
            "source": source_raw,
            "kind": kind,
            "category": category,
        }
        if source.is_file():
            item["bytes"] = source.stat().st_size
            item["sha256"] = sha256(source)
        if category == "system_package":
            owner = dpkg_owner(source)
            metadata = package_metadata(owner) if owner else None
            if not metadata:
                unmapped.append(source_raw)
            else:
                item.update(metadata)
                binary = metadata["binary_package"]
                package = packages.setdefault(binary, dict(metadata))
                package.setdefault("files", []).append(destination)
        entries.append(item)

    license_root = out / "debian-copyright"
    for binary, package in sorted(packages.items()):
        copyright_path = Path("/usr/share/doc") / binary / "copyright"
        if not copyright_path.is_file():
            package["copyright_file"] = None
            unmapped.append(f"missing copyright: {binary}")
            continue
        target_dir = license_root / binary
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "copyright"
        target.write_bytes(copyright_path.read_bytes())
        package["copyright_file"] = target.relative_to(out).as_posix()
        package["copyright_sha256"] = sha256(target)

    python_license_candidates = [
        Path(sysconfig.get_paths()["stdlib"]) / "LICENSE.txt",
        Path(sys.base_prefix) / "LICENSE.txt",
        Path(sys.base_prefix) / "LICENSE",
    ]
    python_license = next((path for path in python_license_candidates if path.is_file()), None)
    if python_license:
        target = out / "python-runtime-LICENSE.txt"
        target.write_bytes(python_license.read_bytes())
        python_license_record = {
            "version": sys.version,
            "source": str(python_license),
            "file": target.name,
            "sha256": sha256(target),
        }
    else:
        python_license_record = None
        unmapped.append("missing Python runtime license")

    source_locks = sorted(
        {
            (package["source_package"], package["source_version"])
            for package in packages.values()
        }
    )
    (out / "debian-source-packages.txt").write_text(
        "".join(f"{name}={version}\n" for name, version in source_locks), encoding="utf-8"
    )
    report = {
        "schema": 1,
        "toc": str(toc),
        "python_runtime": python_license_record,
        "system_packages": [packages[key] for key in sorted(packages)],
        "binary_inputs": entries,
        "unmapped": sorted(set(unmapped)),
        "note": (
            "System package copyright texts are included here. The exact Debian/Ubuntu "
            "source package locks must be downloaded and shipped separately where required."
        ),
    }
    (out / "inventory.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Inventoried {len(entries)} binary inputs, {len(packages)} system packages; "
        f"{len(set(unmapped))} unmapped"
    )
    if unmapped:
        print("Unmapped:\n" + "\n".join(sorted(set(unmapped))))
    return 2 if args.fail_unmapped_system and unmapped else 0


if __name__ == "__main__":
    raise SystemExit(main())
