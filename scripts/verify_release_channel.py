#!/usr/bin/env python3
"""Guard the stable Android channel so a release can never drift again.

يفحص هذا الملف سلامة قناة التحديث قبل كل بناء:
  1) الإصدار واحد في package.json و build.gradle و index.html و update/manifest.json
  2) كل ملف في قناة التحديث موجود ومطابق بالبايت لأصل المشروع (لا انحراف بين root و www و update)
  3) بصمات SHA-256 في manifest.json مطابقة للملفات الحقيقية
  4) رابط نسخة APK في القناة يشير إلى ملف يحمل نفس رقم الإصدار (يمنع إصدارات مُزيفة أو مُعاد تسميتها)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(problems: list[str], message: str) -> None:
    problems.append(message)


def main() -> int:
    problems: list[str] = []

    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    if not SEMVER.match(version):
        fail(problems, f"package.json version is not x.y.z: {version}")

    gradle = (ROOT / "android/app/build.gradle").read_text(encoding="utf-8")
    gradle_version = re.search(r'versionName\s+"([^"]+)"', gradle)
    gradle_code = re.search(r"versionCode\s+(\d+)", gradle)
    if not gradle_version or not gradle_code:
        fail(problems, "android/app/build.gradle is missing versionName/versionCode")
    else:
        if gradle_version.group(1) != version:
            fail(problems, f"gradle versionName {gradle_version.group(1)} != package.json {version}")
        major, minor, patch = (int(part) for part in version.split("."))
        expected_code = major * 100 + minor * 10 + patch
        if str(expected_code) != gradle_code.group(1):
            fail(
                problems,
                f"gradle versionCode {gradle_code.group(1)} does not track {version} "
                f"(expected {expected_code}, scheme major*100+minor*10+patch)",
            )

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    if f"APP_BUNDLE_VERSION = '{version}'" not in html:
        fail(problems, f"index.html APP_BUNDLE_VERSION does not match {version}")
    if f"الإصدار {version}" not in html:
        fail(problems, f"index.html about dialog does not show version {version}")

    manifest_path = ROOT / "update/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != version:
        fail(problems, f"update/manifest.json version {manifest.get('version')} != {version}")

    files = manifest.get("files") or []
    hashes = manifest.get("sha256") or {}
    if not isinstance(files, list) or not files or len(set(files)) != len(files):
        fail(problems, "update/manifest.json files must be a unique non-empty list")

    for name in files:
        published = ROOT / "update" / name
        source = ROOT / name
        if not published.is_file():
            fail(problems, f"missing channel file: update/{name}")
            continue
        if not source.is_file():
            fail(problems, f"missing source file: {name}")
            continue
        published_hash = sha256(published)
        if published_hash != sha256(source):
            fail(problems, f"channel drift: update/{name} != {name} (rerun scripts/publish-update.sh)")
        if hashes.get(name) != published_hash:
            fail(problems, f"manifest hash mismatch for {name}")

    apk = manifest.get("apk") or {}
    apk_version = str(apk.get("version") or "")
    apk_url = str(apk.get("url") or "")
    apk_sha = str(apk.get("sha256") or "")
    if not SEMVER.match(apk_version):
        fail(problems, f"manifest apk.version is not x.y.z: {apk_version!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", apk_sha):
        fail(problems, f"manifest apk.sha256 is not a sha256: {apk_sha!r}")
    if not apk_url.endswith(f"Siraj-Android-{apk_version}.apk"):
        fail(problems, f"manifest apk.url does not point at Siraj-Android-{apk_version}.apk: {apk_url}")
    if apk_version == version and f"/siraj-android-v{version}/" not in apk_url:
        fail(problems, f"manifest apk.url tag must be siraj-android-v{version} for the current release: {apk_url}")
    if apk_version > version:
        fail(problems, f"manifest apk.version {apk_version} points at a release newer than the source {version}")

    baseline = ROOT / "update/app.apk"
    if baseline.is_file() and baseline.read_bytes()[:2] != b"PK":
        fail(problems, "update/app.apk is not a valid APK/ZIP baseline")

    if problems:
        print("release channel verification FAILED:", file=sys.stderr)
        for problem in problems:
            print("  - " + problem, file=sys.stderr)
        return 1
    print(
        f"release channel verified: {version} (code {gradle_code.group(1) if gradle_code else '?'}), "
        f"{len(files)} channel files in sync, APK pointer {apk_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
