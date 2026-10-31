#!/usr/bin/env python3
"""Shared validation for concise, user-facing Siraj release features."""
from __future__ import annotations

from collections.abc import Iterable

MAX_UPDATE_FEATURES = 5
MAX_UPDATE_FEATURE_LENGTH = 120
TECHNICAL_UPDATE_TERMS = (
    "ed25519",
    "sha-256",
    "sha256",
    "runtime",
    "appimage",
    "portable",
    "ترقيع",
    "توقيع",
    "موقّع",
    "حزمة",
    "محرك",
)


def validate_update_features(values: Iterable[str] | None) -> list[str]:
    """Return a normalized feature list or reject verbose/technical copy."""
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        raise ValueError("update features must be a list, not a string")
    features: list[str] = []
    for raw in values:
        if not isinstance(raw, str):
            raise ValueError("every update feature must be text")
        feature = " ".join(raw.split())
        lowered = feature.casefold()
        if not feature or len(feature) > MAX_UPDATE_FEATURE_LENGTH:
            raise ValueError("update features must be concise non-empty text")
        if any(term in lowered for term in TECHNICAL_UPDATE_TERMS):
            raise ValueError(f"technical implementation detail is forbidden in update feature: {feature!r}")
        features.append(feature)
    if len(features) > MAX_UPDATE_FEATURES:
        raise ValueError(f"at most {MAX_UPDATE_FEATURES} update features are allowed")
    if len(features) != len(set(features)):
        raise ValueError("duplicate update features are not allowed")
    return features
