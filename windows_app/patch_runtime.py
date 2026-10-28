"""محمل ترقيعات سراج الصغيرة والموقعة.

هذا الملف جزء من المحرك الثابت ولا يُستبدل بترقيع. كل ترقيع مجلد مستخرج يحوي
``patch.json`` موقّعاً بـEd25519 وقائمة SHA-256 لكل ملف. تُفحص الملفات في كل
تشغيل قبل تنفيذ ``main.py`` الخارجي، وأي فشل يعيد التطبيق تلقائياً إلى النسخة
المضمّنة داخل الحزمة الكاملة.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import runpy
import shutil
import stat
import sys
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path, PurePosixPath

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from packaging.version import InvalidVersion, Version

PATCH_SCHEMA = 1
PATCH_KEY_ID = "siraj-update-2026-01"
MAX_PATCH_BYTES = 128 * 1024 * 1024
MAX_PATCH_FILES = 2000
BLOCKED_SUFFIXES = {".exe", ".dll", ".so", ".dylib", ".pyd", ".msi", ".appimage"}


def _canonical_bytes(value: dict) -> bytes:
    unsigned = deepcopy(value)
    unsigned.pop("signature", None)
    return json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _verify_signature(value: dict, public_key_path: Path) -> bool:
    signature = value.get("signature") if isinstance(value, dict) else None
    if not isinstance(signature, dict) or not public_key_path.is_file():
        return False
    if signature.get("algorithm") != "ed25519" or signature.get("key_id") != PATCH_KEY_ID:
        return False
    try:
        public_key = bytes.fromhex(public_key_path.read_text(encoding="ascii").strip())
        raw = base64.b64decode(str(signature.get("value", "")), validate=True)
        VerifyKey(public_key).verify(_canonical_bytes(value), raw)
        return True
    except (OSError, ValueError, BadSignatureError):
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: object) -> Path | None:
    text = str(value or "")
    pure = PurePosixPath(text)
    if not text or text.startswith(("/", "\\")) or pure.is_absolute() or ".." in pure.parts:
        return None
    if any(not part or part in {".", ".."} for part in pure.parts):
        return None
    path = Path(*pure.parts)
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        return None
    return path


def validate_patch_dir(
    root: Path,
    *,
    product: str,
    runtime_api: int,
    bundled_version: str,
    public_key_path: Path,
) -> dict | None:
    """يتحقق من هوية الترقيع وتوقيعه وكل ملفاته ويرجع الـmanifest الصالح."""
    try:
        root = root.resolve(strict=True)
        manifest_path = root / "patch.json"
        if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size > 2_000_000:
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not _verify_signature(manifest, public_key_path):
            return None
        if (
            manifest.get("schema") != PATCH_SCHEMA
            or manifest.get("kind") != "siraj-signed-patch"
            or manifest.get("product") != product
            or int(manifest.get("runtime_api", -1)) != int(runtime_api)
        ):
            return None
        patch_version = Version(str(manifest.get("version", "")))
        if patch_version < Version(str(bundled_version)):
            return None
        files = manifest.get("files")
        if not isinstance(files, list) or not (2 <= len(files) <= MAX_PATCH_FILES):
            return None
        seen: set[str] = set()
        total = 0
        for item in files:
            if not isinstance(item, dict):
                return None
            relative = _safe_relative(item.get("path"))
            digest = str(item.get("sha256", "")).lower()
            size = int(item.get("size", -1))
            if relative is None or not re_full_sha256(digest) or size < 0:
                return None
            key = relative.as_posix()
            if key in seen:
                return None
            seen.add(key)
            total += size
            if total > MAX_PATCH_BYTES:
                return None
            path = (root / relative).resolve(strict=True)
            if root != path and root not in path.parents:
                return None
            if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
                return None
            if sha256_file(path) != digest:
                return None
        if not {"main.py", "version.py"}.issubset(seen):
            return None
        return manifest
    except (OSError, ValueError, TypeError, InvalidVersion, json.JSONDecodeError):
        return None


def re_full_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def default_patch_root() -> Path:
    override = os.environ.get("SIRAJ_UPDATE_ROOT", "").strip()
    if override:
        return Path(override).expanduser() / "patches"
    executable = Path(sys.executable).resolve()
    if sys.platform.startswith("win") and (executable.parent / "portable.flag").exists():
        return executable.parent / "UserData" / "updates" / "patches"
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "SirajQuran"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "siraj"
    return base / "updates" / "patches"


def find_active_patch(
    *,
    product: str,
    runtime_api: int,
    bundled_version: str,
    public_key_path: Path,
    patch_root: Path | None = None,
) -> tuple[Path, dict] | None:
    patch_root = patch_root or default_patch_root()
    if not patch_root.is_dir():
        return None
    candidates = []
    for child in patch_root.iterdir():
        if child.is_symlink() or not child.is_dir():
            continue
        manifest = validate_patch_dir(
            child,
            product=product,
            runtime_api=runtime_api,
            bundled_version=bundled_version,
            public_key_path=public_key_path,
        )
        if manifest:
            try:
                candidates.append((Version(str(manifest["version"])), child, manifest))
            except (KeyError, InvalidVersion):
                continue
    if not candidates:
        return None
    _version, root, manifest = max(candidates, key=lambda item: item[0])
    return root, manifest


def _safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    total = 0
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        if not members or len(members) > MAX_PATCH_FILES + 1:
            raise ValueError("invalid patch file count")
        for member in members:
            relative = _safe_relative(member.filename.rstrip("/"))
            if relative is None:
                raise ValueError(f"unsafe patch path: {member.filename}")
            if member.flag_bits & 0x1:
                raise ValueError("encrypted patch entries are not supported")
            mode = (member.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                raise ValueError("patch symlinks are not allowed")
            total += int(member.file_size)
            if total > MAX_PATCH_BYTES + 2_000_000:
                raise ValueError("patch is too large")
            target = (destination / relative).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"unsafe patch path: {member.filename}")
        zf.extractall(destination)


def install_patch_archive(
    archive: Path,
    *,
    product: str,
    runtime_api: int,
    bundled_version: str,
    public_key_path: Path,
    patch_root: Path | None = None,
) -> dict:
    """يثبت ترقيعاً موقّعاً إلى مجلد المستخدم مع استبدال ذري قدر الإمكان."""
    archive = Path(archive).resolve(strict=True)
    if not archive.is_file() or archive.suffix.lower() not in {".sirajpatch", ".zip"}:
        raise ValueError("invalid patch archive")
    patch_root = patch_root or default_patch_root()
    patch_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="siraj-patch-", dir=str(patch_root.parent)))
    staging = work / "payload"
    staging.mkdir()
    try:
        _safe_extract(archive, staging)
        manifest = validate_patch_dir(
            staging,
            product=product,
            runtime_api=runtime_api,
            bundled_version=bundled_version,
            public_key_path=public_key_path,
        )
        if not manifest:
            raise ValueError("patch signature or file hashes are invalid")
        version = Version(str(manifest["version"]))
        target = patch_root / str(version)
        if target.exists():
            existing = validate_patch_dir(
                target,
                product=product,
                runtime_api=runtime_api,
                bundled_version=bundled_version,
                public_key_path=public_key_path,
            )
            if existing:
                return existing
            shutil.rmtree(target)
        staging.replace(target)
        return manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_application(
    *,
    product: str,
    runtime_api: int,
    bundled_version: str,
    public_key_path: Path,
) -> int:
    """يشغّل أعلى ترقيع سليم، أو يرجع صامتاً إلى main المضمّن."""
    active = find_active_patch(
        product=product,
        runtime_api=runtime_api,
        bundled_version=bundled_version,
        public_key_path=public_key_path,
    )
    if active:
        root, manifest = active
        os.environ["SIRAJ_PATCH_ROOT"] = str(root)
        os.environ["SIRAJ_EFFECTIVE_VERSION"] = str(manifest["version"])
        sys.path.insert(0, str(root))
        # launcher قرأ version المضمّن لتحديد خط الأساس؛ اسمح للترقيع بتحميل نسخته.
        sys.modules.pop("version", None)
        sys.modules.pop("main", None)
        runpy.run_path(str(root / "main.py"), run_name="__main__")
        return 0
    os.environ.pop("SIRAJ_PATCH_ROOT", None)
    os.environ.pop("SIRAJ_EFFECTIVE_VERSION", None)
    runpy.run_module("main", run_name="__main__", alter_sys=True)
    return 0
