#!/usr/bin/env python3
"""يوقّع Manifest موجودًا؛ يستخدم محليًا للقناة غير المتاحة قبل أول إصدار."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from update_signing import sign_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--signing-seed", default=os.environ.get("WINDOWS_UPDATE_SIGNING_SEED", ""))
    args = parser.parse_args()
    if not args.signing_seed:
        parser.error("WINDOWS_UPDATE_SIGNING_SEED is required")
    value = json.loads(args.manifest.read_text(encoding="utf-8"))
    signed = sign_manifest(value, args.signing_seed)
    args.manifest.write_text(json.dumps(signed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
