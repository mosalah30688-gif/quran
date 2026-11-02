#!/usr/bin/env python3
"""Read and validate version-bound, user-facing update features."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType

from product_copy import validate_update_features


def load_version_module(path: Path) -> ModuleType:
    if not path.is_file() or path.name != "version.py":
        raise ValueError("a platform version.py file is required")
    spec = importlib.util.spec_from_file_location("siraj_release_version", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load platform version metadata")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_update_features(path: Path) -> list[str]:
    module = load_version_module(path)
    app_version = getattr(module, "APP_VERSION", None)
    features_version = getattr(module, "UPDATE_FEATURES_VERSION", None)
    if not isinstance(app_version, str) or features_version != app_version:
        raise ValueError("update features must be explicitly refreshed for APP_VERSION")
    features = validate_update_features(getattr(module, "UPDATE_FEATURES", None))
    if not features:
        raise ValueError("at least one user-facing update feature is required")
    return features


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version_file", type=Path)
    args = parser.parse_args()
    try:
        features = read_update_features(args.version_file.resolve())
    except (OSError, ValueError) as error:
        parser.error(str(error))
    for feature in features:
        print(feature)


if __name__ == "__main__":
    main()
