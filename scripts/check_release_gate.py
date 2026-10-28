#!/usr/bin/env python3
"""Fail closed unless a release tag and commit have explicit audit approval."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
TAG_RE = re.compile(r"^siraj-(windows|linux)-(?:patch-)?v[0-9A-Za-z][0-9A-Za-z.+-]*$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, default=Path("audit/RELEASE_GATE.json"))
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()

    if not TAG_RE.fullmatch(args.tag):
        parser.error(f"invalid release tag: {args.tag!r}")
    commit = args.commit.lower()
    if not COMMIT_RE.fullmatch(commit):
        parser.error("commit must be a full 40-character lowercase SHA-1")

    try:
        gate = json.loads(args.gate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"cannot read release gate: {exc}")

    if gate.get("schema") != 1:
        parser.error("unsupported release gate schema")
    if gate.get("ready") is not True:
        parser.error("release gate is closed")
    blockers = gate.get("blockers")
    if not isinstance(blockers, list) or blockers:
        parser.error("release gate must contain an empty blockers list")
    approved_commit = gate.get("approved_commit")
    if not isinstance(approved_commit, str) or approved_commit.lower() != commit:
        parser.error("release commit is not the explicitly approved commit")
    approved_tags = gate.get("approved_tags")
    if not isinstance(approved_tags, list) or args.tag not in approved_tags:
        parser.error("release tag is not explicitly approved")
    if not gate.get("approved_at") or not gate.get("approved_by"):
        parser.error("release approval metadata is incomplete")

    print(f"Release gate approved {args.tag} at {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
