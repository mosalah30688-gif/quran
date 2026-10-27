"""مساعد تحديث النسخة المحمولة من سراج.

يُبنى كملف EXE منفصل ويُشغّل من نسخة مؤقتة بعد إغلاق التطبيق. يحافظ على
UserData وportable.flag ويعيد النسخة السابقة عند فشل الاستبدال.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path


def wait_for_process(pid: int) -> None:
    if os.name == "nt":
        synchronize = 0x00100000
        infinite = 0xFFFFFFFF
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(synchronize, False, pid)
        if handle:
            kernel32.WaitForSingleObject(handle, infinite)
            kernel32.CloseHandle(handle)
            return
    for _ in range(600):
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.25)


def safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe archive path: {member.filename}")
        zf.extractall(destination)


def payload_root(staging: Path, executable_name: str) -> Path:
    direct = staging / executable_name
    if direct.exists():
        return staging
    matches = list(staging.rglob(executable_name))
    if len(matches) != 1:
        raise RuntimeError("portable archive must contain exactly one Siraj executable")
    return matches[0].parent


def message(text: str, error: bool = False) -> None:
    if os.name == "nt":
        flags = 0x10 if error else 0x40
        ctypes.windll.user32.MessageBoxW(None, text, "تحديث سراج", flags)


def install(archive: Path, target: Path, pid: int, restart: str) -> None:
    archive = archive.resolve()
    target = target.resolve()
    if not archive.is_file() or archive.suffix.lower() != ".zip":
        raise RuntimeError("invalid update archive")
    if not target.is_dir() or not (target / "portable.flag").exists():
        raise RuntimeError("target is not a Siraj portable folder")
    if target == Path(target.anchor) or len(target.parts) < 3:
        raise RuntimeError("unsafe target directory")

    wait_for_process(pid)
    work = Path(tempfile.mkdtemp(prefix="SirajPortableUpdate-"))
    staging = work / "new"
    backup = work / "backup"
    staging.mkdir()
    backup.mkdir()
    preserve = {"UserData", "portable.flag"}
    moved = []
    copied = []
    try:
        safe_extract(archive, staging)
        source = payload_root(staging, restart)
        if not (source / restart).is_file():
            raise RuntimeError("new executable is missing")

        for item in list(target.iterdir()):
            if item.name in preserve:
                continue
            destination = backup / item.name
            shutil.move(str(item), str(destination))
            moved.append(item.name)

        for item in source.iterdir():
            if item.name in preserve:
                continue
            destination = target / item.name
            shutil.move(str(item), str(destination))
            copied.append(item.name)

        executable = target / restart
        if not executable.is_file():
            raise RuntimeError("updated executable was not installed")
        subprocess.Popen([str(executable)], cwd=str(target), close_fds=True)
        archive.unlink(missing_ok=True)
    except Exception:
        for name in copied:
            path = target / name
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        for name in moved:
            old = backup / name
            if old.exists():
                shutil.move(str(old), str(target / name))
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--restart", default="Siraj.exe")
    args = parser.parse_args()
    try:
        install(Path(args.archive), Path(args.target), args.pid, Path(args.restart).name)
        return 0
    except Exception as exc:
        message(f"تعذّر تطبيق التحديث، وتمت استعادة النسخة السابقة.\n\n{exc}", error=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
