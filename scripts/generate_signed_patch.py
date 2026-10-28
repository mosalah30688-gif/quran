#!/usr/bin/env python3
"""يبني حزمة ترقيع صغيرة لسراج ويوقّع فهرس ملفاتها بـEd25519."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import time
import zipfile
from pathlib import Path, PurePosixPath

from update_signing import sign_manifest

IMMUTABLE_RUNTIME_FILES = {
    "__init__.py",
    "launcher.py",
    "patch_runtime.py",
    "portable_updater.py",
}


def default_patch_files(app_dir: Path) -> tuple[str, ...]:
    """Include patchable modules and local JSON content, not a fragile hand list."""
    files = [
        path.name
        for path in sorted(app_dir.glob("*.py"))
        if path.name not in IMMUTABLE_RUNTIME_FILES and path.is_file() and not path.is_symlink()
    ]
    data_dir = app_dir / "data"
    if data_dir.is_dir() and not data_dir.is_symlink():
        files.extend(
            path.relative_to(app_dir).as_posix()
            for path in sorted(data_dir.glob("*.json"))
            if path.is_file() and not path.is_symlink()
        )
    return tuple(files)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(value: str) -> str:
    name = PurePosixPath(value).as_posix()
    pure = PurePosixPath(name)
    if not name or pure.is_absolute() or ".." in pure.parts or name.startswith(("/", "\\")):
        raise ValueError(f"unsafe patch path: {value}")
    return name


def zip_time() -> tuple[int, int, int, int, int, int]:
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0") or 0)
    if not epoch:
        epoch = int(time.time())
    value = dt.datetime.fromtimestamp(max(epoch, 315532800), tz=dt.timezone.utc)
    # ZIP timestamps have a two-second resolution.
    return value.year, value.month, value.day, value.hour, value.minute, value.second - value.second % 2


def add_bytes(zf: zipfile.ZipFile, name: str, data: bytes, timestamp) -> None:
    info = zipfile.ZipInfo(name, timestamp)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    zf.writestr(info, data, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", required=True, choices=("siraj-quran-windows", "siraj-quran-linux"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--runtime-api", type=int, default=1)
    parser.add_argument("--app-dir", required=True, type=Path)
    parser.add_argument("--include", action="append", default=[], help="مسار نسبي إضافي داخل app-dir؛ يمكن تكراره")
    parser.add_argument("--notes", default="تحديث داخلي لسراج.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--signing-seed",
        default=os.environ.get("SIRAJ_UPDATE_SIGNING_SEED") or os.environ.get("WINDOWS_UPDATE_SIGNING_SEED", ""),
        help="Base64 Ed25519 seed (normally a GitHub Actions secret)",
    )
    args = parser.parse_args()
    if not args.signing_seed:
        parser.error("SIRAJ_UPDATE_SIGNING_SEED or WINDOWS_UPDATE_SIGNING_SEED is required")
    app_dir = args.app_dir.resolve()
    names = sorted({
        safe_name(name)
        for name in (*default_patch_files(app_dir), *args.include)
    })
    if not {"main.py", "version.py"}.issubset(names):
        parser.error("app-dir must contain patchable main.py and version.py")
    payload: dict[str, bytes] = {}
    files = []
    for name in names:
        path = (app_dir / Path(*PurePosixPath(name).parts)).resolve()
        if app_dir != path and app_dir not in path.parents:
            parser.error(f"file escapes app directory: {name}")
        if not path.is_file() or path.is_symlink():
            parser.error(f"missing regular file: {path}")
        data = path.read_bytes()
        payload[name] = data
        files.append({"path": name, "size": len(data), "sha256": digest(data)})

    published = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest = sign_manifest({
        "schema": 1,
        "kind": "siraj-signed-patch",
        "product": args.product,
        "version": args.version,
        "runtime_api": args.runtime_api,
        "published_at": published,
        "release_notes": args.notes,
        "files": files,
    }, args.signing_seed)
    manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    timestamp = zip_time()
    with zipfile.ZipFile(args.output, "w") as zf:
        add_bytes(zf, "patch.json", manifest_data, timestamp)
        for name in names:
            add_bytes(zf, name, payload[name], timestamp)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
