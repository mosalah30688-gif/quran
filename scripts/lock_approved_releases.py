#!/usr/bin/env python3
"""Enable GitHub immutability and lock approved or all published releases.

The token is read only from GITHUB_TOKEN and is never written to disk or output.
Archival locking never grants or changes a content license. Required fine-grained
permissions: Administration (write) and Contents (write).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
DEFAULT_REPOSITORY = "mosalah30688-gif/quran"
APPROVED_TAGS = (
    "siraj-windows-v4.1.1",
    "siraj-windows-patch-v4.1.2",
    "siraj-windows-patch-v4.1.3",
    "siraj-linux-test-v4.1.1",
    "siraj-linux-patch-v4.1.2",
    "siraj-tafsir-data-v2026.10.28",
    "siraj-android-v1.4.0",
    "siraj-android-v1.4.1",
    "siraj-android-v1.4.2",
    "siraj-android-v1.4.3",
)


class GitHub:
    def __init__(self, repository: str, token: str) -> None:
        self.repository = repository
        self.token = token

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict | None]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            API + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "Siraj-release-retention/1.0",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            message = ""
            try:
                payload = json.loads(error.read())
                message = str(payload.get("message", ""))
            except Exception:
                pass
            raise RuntimeError(f"GitHub API {method} {path} failed: HTTP {error.code} {message}".strip()) from None

    def release(self, tag: str) -> dict:
        encoded = urllib.parse.quote(tag, safe="")
        status, payload = self.request("GET", f"/repos/{self.repository}/releases/tags/{encoded}")
        if status != 200 or not isinstance(payload, dict):
            raise RuntimeError(f"Release not found: {tag}")
        return payload

    def published_release_tags(self) -> tuple[str, ...]:
        tags: list[str] = []
        page = 1
        while True:
            status, payload = self.request(
                "GET", f"/repos/{self.repository}/releases?per_page=100&page={page}"
            )
            if status != 200 or not isinstance(payload, list):
                raise RuntimeError("Could not enumerate repository releases")
            tags.extend(str(item["tag_name"]) for item in payload if not item.get("draft"))
            if len(payload) < 100:
                break
            page += 1
        return tuple(tags)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--apply", action="store_true", help="Enable the setting and republish selected releases")
    parser.add_argument(
        "--all-published",
        action="store_true",
        help="Preserve every existing published release as an archive; this does not grant or change licenses",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is required and must not be stored in the repository")
    github = GitHub(args.repository, token)
    tags = github.published_release_tags() if args.all_published else APPROVED_TAGS

    if not args.apply:
        scope = "all published archival releases" if args.all_published else "approved releases"
        print(f"Dry run: checking {scope} for permanent locking:")
        for tag in tags:
            release = github.release(tag)
            print(f"- {tag}: draft={release['draft']} immutable={release.get('immutable', False)}")
        print("Re-run with --apply after confirming the repository administration token.")
        return 0

    status, _ = github.request("PUT", f"/repos/{args.repository}/immutable-releases")
    if status != 204:
        raise RuntimeError(f"Unexpected immutable-releases response: {status}")
    status, setting = github.request("GET", f"/repos/{args.repository}/immutable-releases")
    if status != 200 or not setting or setting.get("enabled") is not True:
        raise RuntimeError("Repository release immutability was not enabled")
    print("Repository Immutable Releases: enabled")

    for tag in tags:
        release = github.release(tag)
        if release.get("draft"):
            raise RuntimeError(f"Selected release is still a draft: {tag}")
        if not release.get("immutable"):
            # GitHub makes a previously published release immutable when it is
            # republished through the Update Release endpoint with an empty body.
            github.request("PATCH", f"/repos/{args.repository}/releases/{release['id']}", {})
            release = github.release(tag)
        if release.get("immutable") is not True:
            raise RuntimeError(f"Release did not become immutable: {tag}")
        print(f"Locked permanently: {tag} (release {release['id']})")

    if args.all_published:
        print(f"All {len(tags)} published releases are immutable archival records; licensing scope is unchanged.")
    else:
        print("All explicitly approved releases are immutable.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
