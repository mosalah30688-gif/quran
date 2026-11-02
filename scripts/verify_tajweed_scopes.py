#!/usr/bin/env python3
"""Fail-closed checks for independently scoped tajweed curricula.

This verifier intentionally does not infer tajweed. It proves that every selectable
mushaf is represented in the scope registry, that locked assets still match their
SHA-256 fingerprints, that no Hafs fallback is attached to another riwayah, and
that any future curriculum package satisfies the source/review release gate.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "tajweed-scope-registry.json"
SCHEMA_PATH = ROOT / "tajweed-curriculum.schema.json"
CATALOG_PATH = ROOT / "tajweed-learning-catalog.json"
PACKAGES_DIR = ROOT / "tajweed-curricula"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
EXPECTED_SETTINGS = {
    "quran-uthmani",
    "quran-simple",
    "quran-uthmani-min",
    "warsh",
    "qalun",
    "duri",
}
EXPECTED_RIWAYAT = {
    "hafs-an-asim",
    "warsh-an-nafi",
    "qalun-an-nafi",
    "al-duri-an-abi-amr",
}
REQUIRED_BLOCKERS = {
    "tariq",
    "wajh",
    "edition",
    "rule-corpus",
    "annotation-corpus",
    "qualified-review",
}


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing required file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def require_token(value: Any, field: str) -> str:
    require(isinstance(value, str) and TOKEN_RE.fullmatch(value) is not None,
            f"{field} must be a lowercase stable token")
    return value


def require_sha(value: Any, field: str) -> str:
    require(isinstance(value, str) and SHA256_RE.fullmatch(value) is not None,
            f"{field} must be a lowercase SHA-256")
    return value


def validate_scope(scope: Any, field: str) -> tuple[str, str, str, str]:
    require(isinstance(scope, dict), f"{field} must be an object")
    expected = {"riwayah", "tariq", "wajh", "edition"}
    require(set(scope) == expected, f"{field} must contain exactly {sorted(expected)}")
    return tuple(require_token(scope[name], f"{field}.{name}") for name in
                 ("riwayah", "tariq", "wajh", "edition"))  # type: ignore[return-value]


def validate_refs(value: Any, known: set[str], field: str) -> list[str]:
    require(isinstance(value, list) and value, f"{field} must not be empty")
    refs = [require_token(item, field) for item in value]
    require(len(refs) == len(set(refs)), f"{field} must contain unique references")
    require(set(refs) <= known, f"{field} contains unknown references")
    return refs


def record_count(asset: Path, dataset: str) -> int:
    data = load_json(asset)
    if asset.name == "quran-tajweed.json":
        require(dataset == "quran-tajweed" and isinstance(data, list),
                "quran-tajweed text binding has an invalid dataset")
        return len(data)
    if asset.name == "quran-riwayat.json":
        rows = data.get("riwayat", {}).get(dataset) if isinstance(data, dict) else None
        require(isinstance(rows, list), f"missing riwayat dataset {dataset} in {asset.name}")
        return len(rows)
    if asset.name == "quran-hafs.json":
        rows = data.get(dataset) if isinstance(data, dict) else None
        require(isinstance(rows, list), f"missing Hafs dataset {dataset} in {asset.name}")
        return len(rows)
    fail(f"unsupported registry text asset: {asset.name}")


def verse_index(asset: Path, dataset: str, normalization: str = "NONE") -> dict[tuple[int, int], str]:
    data = load_json(asset)
    if asset.name == "quran-tajweed.json" and dataset == "quran-tajweed":
        rows = data
    elif asset.name == "quran-riwayat.json" and isinstance(data, dict):
        rows = data.get("riwayat", {}).get(dataset)
    elif asset.name == "quran-hafs.json" and isinstance(data, dict):
        rows = data.get(dataset)
    else:
        fail(f"cannot resolve dataset {dataset} in {asset.name}")
    require(isinstance(rows, list), f"text dataset {dataset} must be an array")
    index: dict[tuple[int, int], str] = {}
    for position, row in enumerate(rows):
        require(isinstance(row, list) and len(row) >= 4,
                f"invalid text row {position} in {asset.name}/{dataset}")
        key = (int(row[0]), int(row[1]))
        require(key not in index, f"duplicate verse {key} in {asset.name}/{dataset}")
        text = str(row[3])
        index[key] = unicodedata.normalize("NFC", text) if normalization == "NFC" else text
    return index


def verify_schema_gate(schema: Any) -> None:
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
            "tajweed curriculum schema must remain draft 2020-12")
    required = set(schema.get("required", []))
    require({"scope", "display", "textBinding", "sources", "rules", "annotations", "review"} <= required,
            "curriculum schema release fields were weakened")
    display_required = set(schema.get("properties", {}).get("display", {}).get("required", []))
    require({"nameAr", "riwayahAr", "tariqAr", "wajhAr", "editionAr"} == display_required,
            "curriculum display must name riwayah/tariq/wajh/edition in Arabic")
    arabic_label = schema.get("$defs", {}).get("arabicLabel", {})
    require(arabic_label.get("type") == "string" and arabic_label.get("minLength") == 1
            and isinstance(arabic_label.get("pattern"), str)
            and re.search(arabic_label["pattern"], "العربية")
            and not re.search(arabic_label["pattern"], "Latin"),
            "curriculum Arabic display-label pattern was weakened")
    text_required = set(schema.get("properties", {}).get("textBinding", {}).get("required", []))
    require({"asset", "dataset", "sha256", "offsetUnit", "normalization"} <= text_required,
            "text binding must remain asset/dataset/hash/offset locked")
    annotations = schema.get("properties", {}).get("annotations", {})
    require(annotations.get("minItems") == 1,
            "an approved curriculum cannot have an empty annotation layer")
    require(schema.get("additionalProperties") is False,
            "curriculum schema must reject undeclared package fields")
    serialized = json.dumps(schema, sort_keys=True)
    for marker in ("reviewerQualification", "reviewedSha256", "releaseApprover"):
        require(marker in serialized, f"schema is missing approval gate {marker}")
    nonapproved_review = (schema.get("allOf", [{}])[0].get("else", {}).get("properties", {})
                          .get("review", {}).get("properties", {}).get("status", {}).get("enum", []))
    require(set(nonapproved_review) == {"NOT_REVIEWED", "CHANGES_REQUESTED"},
            "unapproved packages must not carry an approved review state")


def verify_registry(registry: Any, catalog: Any) -> tuple[dict[str, dict[str, Any]], int]:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    select_match = re.search(r'<select id="setRiwaya">(.*?)</select>', html, re.DOTALL)
    require(select_match is not None, "index.html is missing the mushaf selector")
    selectable = re.findall(r'<option value="([a-z0-9._-]+)"', select_match.group(1))
    require(len(selectable) == len(set(selectable)), "mushaf selector has duplicate setting values")
    require(set(selectable) == EXPECTED_SETTINGS,
            f"selector/registry expected settings drift: {sorted(set(selectable) ^ EXPECTED_SETTINGS)}")
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    require('value="quran-tajweed"' not in html and 'id="setTajweed"' not in html,
            "the tagged tajweed source must not be exposed as a colored mushaf setting")
    require('id="tjIndependentNote"' in html and 'id="tjPanel"' not in html,
            "tajweed explanations must stay in the independent tajweed tab")
    for forbidden in ("function renderTajweed(", "function renderIndependentTajweed(",
                      "data-tj-rules"):
        require(forbidden not in app, f"reader tajweed renderer returned: {forbidden}")
    active_app = app.replace("delete settings.tajweed;", "")
    require(re.search(r"settings\.tajweed\b", active_app) is None,
            "the removed reader-color preference remains active")

    require(registry.get("schemaVersion") == 1, "unsupported tajweed registry schema")
    require(registry.get("scopeKey") == "riwayah/tariq/wajh/edition",
            "registry scope key must include riwayah/tariq/wajh/edition")
    require(registry.get("fallbackPolicy") == "FORBIDDEN_BETWEEN_SCOPES",
            "cross-scope fallback must remain forbidden")
    policy = registry.get("approvalPolicy", {})
    for key in (
        "requiresDocumentedTextEdition",
        "requiresIndependentRuleAndAnnotationCorpus",
        "requiresLicenseEvidence",
        "requiresSha256Snapshots",
        "requiresQualifiedHumanReviewer",
        "requiresSecondPersonReleaseApproval",
    ):
        require(policy.get(key) is True, f"registry approval policy disabled {key}")
    require(policy.get("machineInferenceMayBePublishedAsApproved") is False,
            "machine inference must never be marked scholarly-approved")

    settings = registry.get("settings")
    require(isinstance(settings, list) and len(settings) == 4,
            "registry must contain exactly the four supported riwayah groups")
    by_setting: dict[str, dict[str, Any]] = {}
    riwayat: set[str] = set()
    blocked = 0

    for entry_index, entry in enumerate(settings):
        prefix = f"registry.settings[{entry_index}]"
        require(isinstance(entry, dict), f"{prefix} must be an object")
        riwayah = require_token(entry.get("riwayah", {}).get("id"), f"{prefix}.riwayah.id")
        require(riwayah not in riwayat, f"duplicate riwayah registry entry: {riwayah}")
        riwayat.add(riwayah)
        ids = entry.get("settingIds")
        require(isinstance(ids, list) and ids, f"{prefix}.settingIds must not be empty")
        for setting_id in ids:
            require_token(setting_id, f"{prefix}.settingIds")
            require(setting_id not in by_setting, f"setting {setting_id} appears twice in registry")
            by_setting[setting_id] = entry

        binding = entry.get("textEdition", {})
        asset_name = binding.get("asset")
        require(isinstance(asset_name, str) and Path(asset_name).name == asset_name,
                f"{prefix}.textEdition.asset must be a root asset filename")
        asset = ROOT / asset_name
        expected_sha = require_sha(binding.get("sha256"), f"{prefix}.textEdition.sha256")
        require(asset.is_file(), f"missing bound text asset: {asset_name}")
        require(digest(asset) == expected_sha, f"text asset hash drift: {asset_name}")
        dataset = require_token(binding.get("dataset"), f"{prefix}.textEdition.dataset")
        actual_count = record_count(asset, dataset)
        require(binding.get("verseRecords") == actual_count,
                f"record count drift for {asset_name}/{dataset}: {actual_count}")

        curricula = entry.get("curricula")
        require(isinstance(curricula, list), f"{prefix}.curricula must be an array")
        if not curricula:
            blocked += 1
            require(entry.get("status") == "BLOCKED_NO_APPROVED_CORPUS",
                    f"{riwayah} without a curriculum must fail closed")
            require(REQUIRED_BLOCKERS <= set(entry.get("unresolvedFields", [])),
                    f"{riwayah} does not name all required scholarly blockers")
            reason = entry.get("blockedReasonAr")
            require(isinstance(reason, str) and "حفص" in reason,
                    f"{riwayah} blocked reason must explicitly reject Hafs fallback")
        else:
            require(riwayah == "hafs-an-asim" and len(curricula) == 1,
                    "only the current isolated Hafs draft may reference a curriculum artifact")
            curriculum = curricula[0]
            require(isinstance(curriculum, dict), f"{prefix}.curricula[0] must be an object")
            artifact_name = curriculum.get("artifact")
            require(artifact_name == CATALOG_PATH.name, "unexpected current curriculum artifact")
            require_sha(curriculum.get("sha256"), f"{prefix}.curricula[0].sha256")
            require(curriculum["sha256"] == digest(CATALOG_PATH),
                    "tajweed learning catalog hash drift in registry")
            require(curriculum.get("status") == "PENDING_SCHOLARLY_REVIEW"
                    and curriculum.get("publishableAsApproved") is False,
                    "the source-unspecified Hafs draft must not be approved")
            validate_scope(curriculum.get("scope"), f"{prefix}.curricula[0].scope")

    require(set(by_setting) == EXPECTED_SETTINGS,
            f"registry setting coverage mismatch: {sorted(set(by_setting) ^ EXPECTED_SETTINGS)}")
    require(riwayat == EXPECTED_RIWAYAT,
            f"registry riwayah coverage mismatch: {sorted(riwayat ^ EXPECTED_RIWAYAT)}")
    require(blocked == 3, "Warsh, Qalun and Duri must remain fail-closed without corpora")

    curricula = catalog.get("curricula")
    require(isinstance(curricula, list) and len(curricula) == 1,
            "current learning catalog must contain only the isolated Hafs draft")
    hafs = curricula[0]
    registry_hafs = by_setting["quran-uthmani"]["curricula"][0]
    require(validate_scope(hafs.get("scope"), "catalog.curricula[0].scope") ==
            validate_scope(registry_hafs.get("scope"), "registry Hafs scope"),
            "catalog and registry Hafs scopes differ")
    require(set(hafs.get("appliesToSettings", [])) ==
            {"quran-uthmani", "quran-simple", "quran-uthmani-min"},
            "Hafs curriculum setting scope changed")
    require(hafs.get("status") == "PENDING_SCHOLARLY_REVIEW"
            and hafs.get("publishableAsApproved") is False,
            "unreviewed Hafs catalog must remain visibly unapproved")
    display = hafs.get("display")
    display_fields = {"nameAr", "riwayahAr", "tariqAr", "wajhAr", "editionAr"}
    require(isinstance(display, dict) and set(display) == display_fields,
            "Hafs draft must expose the complete Arabic scope identity")
    for key in display_fields:
        require(isinstance(display[key], str) and display[key].strip()
                and ARABIC_RE.search(display[key]),
                f"catalog.curricula[0].display.{key} must be Arabic")
    require(display["riwayahAr"] == by_setting["quran-uthmani"]["riwayah"]["labelAr"],
            "Hafs Arabic riwayah label differs from registry")

    unavailable = catalog.get("unavailable")
    require(isinstance(unavailable, list) and len(unavailable) == 3,
            "catalog must fail closed for exactly three non-Hafs settings")
    for item in unavailable:
        setting_id = item.get("settingId")
        require(setting_id in {"warsh", "qalun", "duri"},
                f"unexpected unavailable setting {setting_id}")
        entry = by_setting[setting_id]
        require(item.get("riwayah") == entry["riwayah"]["id"],
                f"catalog/registry riwayah mismatch for {setting_id}")
        require(entry.get("curricula") == [], f"blocked setting {setting_id} acquired a fallback")
    return by_setting, blocked


def canonical_review_payload(package: dict[str, Any]) -> str:
    payload = {key: package[key] for key in
               ("scope", "display", "textBinding", "sources", "rules", "annotations")}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_package(path: Path, package: Any, registry_by_setting: dict[str, dict[str, Any]]) -> str:
    label = str(path.relative_to(ROOT))
    require(isinstance(package, dict), f"{label} must be an object")
    required = {"schemaVersion", "packageId", "status", "publishableAsApproved", "scope", "display",
                "textBinding", "sources", "rules", "annotations", "review"}
    require(set(package) == required,
            f"{label} package fields differ: missing={sorted(required - set(package))}, "
            f"unknown={sorted(set(package) - required)}")
    require(package.get("schemaVersion") == 1, f"{label} has an unsupported schema")
    package_id = require_token(package.get("packageId"), f"{label}.packageId")
    require(isinstance(package.get("publishableAsApproved"), bool),
            f"{label}.publishableAsApproved must be boolean")
    scope = validate_scope(package.get("scope"), f"{label}.scope")
    require(scope[0] in EXPECTED_RIWAYAT, f"{label} has an unknown riwayah")
    display = package.get("display")
    display_fields = {"nameAr", "riwayahAr", "tariqAr", "wajhAr", "editionAr"}
    require(isinstance(display, dict) and set(display) == display_fields,
            f"{label}.display must name the complete scope in Arabic")
    for key in display_fields:
        require(isinstance(display[key], str) and display[key].strip()
                and ARABIC_RE.search(display[key]),
                f"{label}.display.{key} must be Arabic")

    binding = package.get("textBinding")
    require(isinstance(binding, dict), f"{label}.textBinding must be an object")
    binding_fields = {"asset", "dataset", "sha256", "offsetUnit", "normalization"}
    require(set(binding) == binding_fields, f"{label}.textBinding fields differ from schema")
    require(binding.get("offsetUnit") == "unicode-code-point",
            f"{label} annotation offsets must use Unicode code points")
    require(binding.get("normalization") in {"NONE", "NFC"},
            f"{label} has an unsupported normalization")
    asset_name = binding.get("asset")
    require(isinstance(asset_name, str) and Path(asset_name).name == asset_name,
            f"{label} text asset must be a root filename")
    asset = ROOT / asset_name
    require(asset.is_file(), f"{label} bound text asset is missing")
    require(digest(asset) == require_sha(binding.get("sha256"), f"{label}.textBinding.sha256"),
            f"{label} bound text hash drift")
    dataset = require_token(binding.get("dataset"), f"{label}.textBinding.dataset")
    verses = verse_index(asset, dataset, binding["normalization"])

    sources = package.get("sources")
    require(isinstance(sources, list) and sources, f"{label} must cite at least one source")
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        field = f"{label}.sources[{index}]"
        require(isinstance(source, dict), f"{field} must be an object")
        source_fields = {"sourceId", "title", "uri", "snapshotDate", "sha256", "licenseEvidence"}
        require(set(source) == source_fields, f"{field} fields differ from schema")
        require(isinstance(source.get("title"), str) and source["title"].strip(),
                f"{field}.title is required")
        source_id = require_token(source.get("sourceId"), f"{field}.sourceId")
        require(source_id not in source_ids, f"{label} has duplicate source {source_id}")
        source_ids.add(source_id)
        require_sha(source.get("sha256"), f"{field}.sha256")
        require(isinstance(source.get("snapshotDate"), str)
                and DATE_RE.fullmatch(source["snapshotDate"]) is not None,
                f"{field}.snapshotDate must be YYYY-MM-DD")
        require(isinstance(source.get("uri"), str) and "://" in source["uri"],
                f"{field}.uri must be an absolute URI")
        evidence = source.get("licenseEvidence")
        require(isinstance(evidence, str) and evidence.strip(),
                f"{field}.licenseEvidence is required")
        if "://" not in evidence:
            require((ROOT / evidence).is_file(), f"{field} local license evidence is missing")

    rules = package.get("rules")
    require(isinstance(rules, list) and rules, f"{label} must include rules")
    rule_ids: set[str] = set()
    for index, rule in enumerate(rules):
        field = f"{label}.rules[{index}]"
        require(isinstance(rule, dict), f"{field} must be an object")
        rule_fields = {"id", "nameAr", "summaryAr", "detailAr", "color", "sourceRefs"}
        require(set(rule) == rule_fields, f"{field} fields differ from schema")
        rule_id = require_token(rule.get("id"), f"{field}.id")
        require(rule_id not in rule_ids, f"{label} has duplicate rule {rule_id}")
        rule_ids.add(rule_id)
        require(isinstance(rule.get("color"), str)
                and re.fullmatch(r"#[0-9A-Fa-f]{6}", rule["color"]) is not None,
                f"{field}.color must be #RRGGBB")
        validate_refs(rule.get("sourceRefs"), source_ids, f"{field}.sourceRefs")
        for text_field in ("nameAr", "summaryAr", "detailAr"):
            require(isinstance(rule.get(text_field), str) and rule[text_field].strip(),
                    f"{field}.{text_field} is required")

    annotations = package.get("annotations")
    require(isinstance(annotations, list) and annotations,
            f"{label} must include an independent annotation layer")
    seen_annotations: set[tuple[int, int, int, int, str]] = set()
    for index, annotation in enumerate(annotations):
        field = f"{label}.annotations[{index}]"
        require(isinstance(annotation, dict), f"{field} must be an object")
        annotation_required = {"surah", "ayah", "start", "end", "ruleId", "sourceRefs"}
        annotation_allowed = annotation_required | {"noteAr"}
        require(annotation_required <= set(annotation) <= annotation_allowed,
                f"{field} fields differ from schema")
        require("noteAr" not in annotation or isinstance(annotation["noteAr"], str),
                f"{field}.noteAr must be text")
        surah, ayah = annotation.get("surah"), annotation.get("ayah")
        start, end = annotation.get("start"), annotation.get("end")
        require(isinstance(surah, int) and 1 <= surah <= 114 and isinstance(ayah, int) and ayah >= 1,
                f"{field} has an invalid verse reference")
        require((surah, ayah) in verses, f"{field} references a missing verse")
        require(isinstance(start, int) and isinstance(end, int) and 0 <= start < end,
                f"{field} has an invalid half-open span")
        require(end <= len(verses[(surah, ayah)]),
                f"{field} span exceeds the bound Quran text")
        rule_id = annotation.get("ruleId")
        require(rule_id in rule_ids, f"{field} references unknown rule {rule_id}")
        validate_refs(annotation.get("sourceRefs"), source_ids, f"{field}.sourceRefs")
        identity = (surah, ayah, start, end, rule_id)
        require(identity not in seen_annotations, f"{label} has a duplicate annotation {identity}")
        seen_annotations.add(identity)

    status = package.get("status")
    require(status in {"DRAFT", "PENDING_SCHOLARLY_REVIEW", "APPROVED"},
            f"{label} has an invalid status")
    review = package.get("review")
    require(isinstance(review, dict), f"{label}.review must be an object")
    review_allowed = {"status", "reviewerName", "reviewerQualification", "reviewDate",
                      "reviewedSha256", "releaseApprover", "evidence"}
    require("status" in review and set(review) <= review_allowed,
            f"{label}.review fields differ from schema")
    require(review.get("status") in {"NOT_REVIEWED", "CHANGES_REQUESTED", "APPROVED"},
            f"{label}.review.status is invalid")
    if status == "APPROVED":
        require(package.get("publishableAsApproved") is True,
                f"{label} approved package is not release-enabled")
        require(review.get("status") == "APPROVED", f"{label} scholarly review is not approved")
        for key in ("reviewerName", "reviewerQualification", "reviewDate", "reviewedSha256",
                    "releaseApprover", "evidence"):
            require(isinstance(review.get(key), str) and review[key].strip(),
                    f"{label}.review.{key} is required for approval")
        require(DATE_RE.fullmatch(review["reviewDate"]) is not None,
                f"{label}.review.reviewDate must be YYYY-MM-DD")
        require_sha(review["reviewedSha256"], f"{label}.review.reviewedSha256")
        require(review["reviewerName"] != review["releaseApprover"],
                f"{label} requires a second-person release approval")
        require(review["reviewedSha256"] == canonical_review_payload(package),
                f"{label} changed after scholarly review")
    else:
        require(package.get("publishableAsApproved") is False,
                f"{label} unapproved package cannot be publishable as approved")
        require(review.get("status") != "APPROVED",
                f"{label} package/review approval states disagree")

    unique_entries = {id(entry): entry for entry in registry_by_setting.values()}.values()
    matching_entries = [entry for entry in unique_entries if entry["riwayah"]["id"] == scope[0]]
    require(len(matching_entries) == 1, f"{label} must map to exactly one registry riwayah group")
    require(display["riwayahAr"] == matching_entries[0]["riwayah"]["labelAr"],
            f"{label} Arabic riwayah label differs from the registry")
    pointers = matching_entries[0].get("curricula", [])
    relative_artifact = str(path.relative_to(ROOT))
    matching_pointers = [pointer for pointer in pointers
                         if pointer.get("artifact") == relative_artifact
                         and validate_scope(pointer.get("scope"),
                                            f"registry pointer for {package_id}") == scope]
    require(len(matching_pointers) == 1,
            f"{label} must have one exact riwayah/tariq/wajh/edition registry pointer")
    pointer = matching_pointers[0]
    require(pointer.get("sha256") == digest(path), f"{label} registry hash drift")
    require(pointer.get("status") == status
            and pointer.get("publishableAsApproved") is package.get("publishableAsApproved"),
            f"{label} registry release status mismatch")
    return "/".join(scope) + "::" + package_id


def main() -> int:
    try:
        registry = load_json(REGISTRY_PATH)
        schema = load_json(SCHEMA_PATH)
        catalog = load_json(CATALOG_PATH)
        verify_schema_gate(schema)
        by_setting, blocked = verify_registry(registry, catalog)

        package_paths = sorted(PACKAGES_DIR.glob("*.json")) if PACKAGES_DIR.is_dir() else []
        package_keys: set[str] = set()
        for path in package_paths:
            key = validate_package(path, load_json(path), by_setting)
            require(key not in package_keys, f"duplicate curriculum package key: {key}")
            package_keys.add(key)

        print("tajweed scope verification passed:")
        print(f"  settings covered: {len(by_setting)}")
        print(f"  riwayah groups: {len(registry['settings'])}")
        print(f"  fail-closed groups: {blocked}")
        print(f"  schema-validated curriculum packages: {len(package_paths)}")
        print("  cross-scope fallback: forbidden")
        return 0
    except VerificationError as exc:
        print(f"tajweed scope verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
