#!/usr/bin/env python3
"""Download, verify and bundle corresponding source for shipped LGPL parts.

The resulting ZIP is intentionally stored (not recompressed): upstream archives
are already compressed. Linux may additionally include exact Debian/Ubuntu source
package files downloaded from binary-license-report/debian-source-packages.txt.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    sha256: str
    purpose: str


QT_BASE = "https://download.qt.io/official_releases"
COMMON = (
    Source(
        "pyside-setup-everywhere-src-6.12.0.tar.xz",
        f"{QT_BASE}/QtForPython/pyside6/PySide6-6.12.0-src/"
        "pyside-setup-everywhere-src-6.12.0.tar.xz",
        "099c1a597cf33c1b000e11cf68a0b82d216fb802bf81726efc720394f10c7751",
        "PySide6 and Shiboken6 6.12.0",
    ),
    Source(
        "qtbase-everywhere-src-6.12.0.tar.xz",
        f"{QT_BASE}/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz",
        "a951bd163c7b80fc6b8c88d7668fb56abf91c152373e13c10666763238131307",
        "Qt Core/Gui/Widgets/Network/DBus/OpenGL and platform plugins",
    ),
    Source(
        "qtsvg-everywhere-src-6.12.0.tar.xz",
        f"{QT_BASE}/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz",
        "e4ab39534ec97987b1b9b60ef7f4d3253d5912a69f8c713a01753174a4029331",
        "Qt SVG module and SVG plugins",
    ),
)
LINUX = (
    Source(
        "qtwayland-everywhere-src-6.12.0.tar.xz",
        f"{QT_BASE}/qt/6.12/6.12.0/submodules/qtwayland-everywhere-src-6.12.0.tar.xz",
        "ae14d9bcf1bb3c300a3ab2e6a53f50284e5c6c966a4ac4cc5aedcb1bc74e4d02",
        "Qt Wayland client libraries and plugins",
    ),
    Source(
        "type2-runtime-dd6cebedcbddde9c82f89b011e8e1d40b6e43868.tar.gz",
        "https://github.com/AppImage/type2-runtime/archive/"
        "dd6cebedcbddde9c82f89b011e8e1d40b6e43868.tar.gz",
        "f5fec23be76e50e2445ed2d018bac49b367490fc483c62c4637e99ec705d27ba",
        "AppImage type2 runtime 20251108 source, build scripts and libfuse patch",
    ),
    Source(
        "fuse-3.15.0.tar.xz",
        "https://github.com/libfuse/libfuse/releases/download/fuse-3.15.0/fuse-3.15.0.tar.xz",
        "70589cfd5e1cff7ccd6ac91c86c01be340b227285c5e200baa284e401eea2ca0",
        "libfuse 3.15.0, LGPL-2.1-only, statically linked in AppImage runtime",
    ),
    Source(
        "squashfuse-0.5.2.tar.gz",
        "https://github.com/vasi/squashfuse/archive/0.5.2.tar.gz",
        "db0238c5981dabbd80ee09ae15387f390091668ca060a7bc38047912491443d3",
        "squashfuse 0.5.2",
    ),
    Source(
        "zstd-1.5.6.tar.gz",
        "https://github.com/facebook/zstd/releases/download/v1.5.6/zstd-1.5.6.tar.gz",
        "8c29e06cf42aacc1eafc4077ae2ec6c6fcb96a626157e0593d5e82a34fd403c1",
        "zstd 1.5.6",
    ),
    Source(
        "zlib-1.3.1.tar.gz",
        "https://github.com/madler/zlib/archive/refs/tags/v1.3.1.tar.gz",
        "17e88863f3600672ab49182f217281b6fc4d3c762bde361935e436a95214d05c",
        "zlib 1.3.1",
    ),
    Source(
        "mimalloc-2.1.7.tar.gz",
        "https://github.com/microsoft/mimalloc/archive/refs/tags/v2.1.7.tar.gz",
        "0eed39319f139afde8515010ff59baf24de9e47ea316a315398e8027d198202d",
        "mimalloc 2.1.7",
    ),
    Source(
        "musl-1.2.5.tar.gz",
        "https://musl.libc.org/releases/musl-1.2.5.tar.gz",
        "a9a118bbe84d8764da0ea0d28b3ab3fae8477fc7e4085d90102b8596fc7c75e4",
        "musl libc 1.2.5",
    ),
)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(source: Source, target: Path) -> None:
    if target.is_file() and file_hash(target) == source.sha256:
        return
    target.unlink(missing_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(source.url, headers={"User-Agent": "Siraj-source-bundler/1"})
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
            actual = file_hash(partial)
            if actual != source.sha256:
                raise RuntimeError(f"SHA-256 mismatch for {source.name}: {actual}")
            partial.replace(target)
            return
        except Exception as exc:  # network failures are retried, hash failures remain fatal after retries
            last_error = exc
            partial.unlink(missing_ok=True)
            if attempt < 4:
                time.sleep(2**attempt)
    raise RuntimeError(f"Could not download {source.url}: {last_error}")


def zip_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def zip_file(archive: zipfile.ZipFile, path: Path, name: str) -> None:
    """Store an already-compressed source archive with deterministic metadata."""
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o100644 << 16
    info.file_size = path.stat().st_size
    with path.open("rb") as source, archive.open(info, "w", force_zip64=True) as target:
        shutil.copyfileobj(source, target, length=1024 * 1024)


def readme(platform: str, version: str, sources: tuple[Source, ...], has_debian: bool) -> str:
    rows = "\n".join(f"- `{item.name}` — {item.purpose}\n  - {item.url}" for item in sources)
    extra = (
        "\n- `debian-source/` contains exact Ubuntu source packages corresponding to "
        "system shared libraries copied into the tested AppImage. Versions are locked by "
        "the binary inventory generated during that same build.\n"
        if has_debian
        else ""
    )
    return f"""# Siraj {version} — corresponding source ({platform})

This archive accompanies the binary release to satisfy source and relinking rights
for LGPL components. The files are unmodified upstream source archives, verified
before packaging against the SHA-256 values in `SHA256SUMS.txt`.

{rows}
{extra}
## Replacing/relinking Qt

Windows Portable keeps Qt/PySide shared libraries as separate files in the
portable directory. Linux users can extract the AppImage with
`--appimage-extract`, replace ABI-compatible Qt/PySide shared libraries built
from these sources, and repack it with an AppImage tool. Siraj's own code is MIT
licensed and available from the same tagged repository source.

Build instructions:

- Qt: https://doc.qt.io/qt-6/build-sources.html
- Qt for Python: https://doc.qt.io/qtforpython-6/building_from_source/index.html

## Relinking the AppImage runtime (Linux only)

For Linux, the type2-runtime source contains the exact build scripts and
`patches/libfuse/mount.c.diff`. Its `scripts/common/install-dependencies.sh`
builds libfuse 3.15.0 and squashfuse 0.5.2 before linking the runtime. Replace
or modify libfuse, rebuild the runtime, then pass the resulting runtime to
appimagetool with `--runtime-file`. The other runtime libraries are included for
source and license completeness.

No rights in Siraj's external Quran text, exegesis, translation, recitation,
font, icon or data content are granted by this source archive.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("windows", "linux"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--debian-source-dir", type=Path)
    args = parser.parse_args()

    cache = args.cache.resolve()
    output = args.output.resolve()
    debian_dir = args.debian_source_dir.resolve() if args.debian_source_dir else None
    cache.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    sources = COMMON + (LINUX if args.platform == "linux" else ())
    for source in sources:
        print(f"source: {source.name}", flush=True)
        download(source, cache / source.name)

    checksums = [f"{source.sha256}  upstream/{source.name}" for source in sources]
    debian_files = []
    if debian_dir:
        if not debian_dir.is_dir():
            raise SystemExit(f"Debian source directory does not exist: {debian_dir}")
        debian_files = sorted(path for path in debian_dir.rglob("*") if path.is_file())
        if not debian_files:
            raise SystemExit("Debian source directory is empty")
        checksums.extend(
            f"{file_hash(path)}  debian-source/{path.relative_to(debian_dir).as_posix()}"
            for path in debian_files
        )

    temp = output.with_suffix(output.suffix + ".part")
    temp.unlink(missing_ok=True)
    with zipfile.ZipFile(temp, "w", allowZip64=True) as archive:
        for source in sources:
            zip_file(archive, cache / source.name, f"upstream/{source.name}")
        for path in debian_files:
            relative = path.relative_to(debian_dir).as_posix()
            zip_file(archive, path, f"debian-source/{relative}")
        zip_bytes(archive, "SHA256SUMS.txt", ("\n".join(checksums) + "\n").encode())
        zip_bytes(
            archive,
            "README.md",
            readme(args.platform, args.version, sources, bool(debian_files)).encode(),
        )
    temp.replace(output)
    print(f"wrote {output} ({output.stat().st_size} bytes), sha256={file_hash(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
