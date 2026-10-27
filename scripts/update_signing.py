"""Canonical JSON + Ed25519 signing helpers for Siraj update manifests."""
from __future__ import annotations

import base64
import json
from copy import deepcopy

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

KEY_ID = "siraj-update-2026-01"


def unsigned_manifest(manifest: dict) -> dict:
    value = deepcopy(manifest)
    value.pop("signature", None)
    return value


def canonical_bytes(manifest: dict) -> bytes:
    return json.dumps(
        unsigned_manifest(manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sign_manifest(manifest: dict, seed_b64: str) -> dict:
    seed = base64.b64decode(seed_b64.strip(), validate=True)
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be exactly 32 bytes")
    key = SigningKey(seed)
    signature = key.sign(canonical_bytes(manifest)).signature
    result = unsigned_manifest(manifest)
    result["signature"] = {
        "algorithm": "ed25519",
        "key_id": KEY_ID,
        "value": base64.b64encode(signature).decode("ascii"),
    }
    return result


def verify_manifest(manifest: dict, public_key_hex: str) -> bool:
    signature = manifest.get("signature") if isinstance(manifest, dict) else None
    if not isinstance(signature, dict):
        return False
    if signature.get("algorithm") != "ed25519" or signature.get("key_id") != KEY_ID:
        return False
    try:
        raw_signature = base64.b64decode(str(signature.get("value", "")), validate=True)
        key = VerifyKey(bytes.fromhex(public_key_hex.strip()))
        key.verify(canonical_bytes(manifest), raw_signature)
        return True
    except (ValueError, BadSignatureError):
        return False
