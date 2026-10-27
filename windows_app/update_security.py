"""التحقق من توقيع قناة التحديث داخل التطبيق."""
from __future__ import annotations

import base64
import json
from copy import deepcopy
from pathlib import Path

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

UPDATE_KEY_ID = "siraj-update-2026-01"


def canonical_manifest_bytes(manifest: dict) -> bytes:
    value = deepcopy(manifest)
    value.pop("signature", None)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify_update_manifest(manifest: dict, public_key_path: Path) -> bool:
    signature = manifest.get("signature") if isinstance(manifest, dict) else None
    if not isinstance(signature, dict) or not public_key_path.is_file():
        return False
    if signature.get("algorithm") != "ed25519" or signature.get("key_id") != UPDATE_KEY_ID:
        return False
    try:
        public_key = bytes.fromhex(public_key_path.read_text(encoding="ascii").strip())
        raw_signature = base64.b64decode(str(signature.get("value", "")), validate=True)
        VerifyKey(public_key).verify(canonical_manifest_bytes(manifest), raw_signature)
        return True
    except (OSError, ValueError, BadSignatureError):
        return False
