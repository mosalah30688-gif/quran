#!/usr/bin/env python3
"""Verify pinned non-Hafs tajweed references without approving runtime curricula."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "audit/sources/tajweed-riwayat/2026-11-02"
SOURCE_PATH = REFERENCE_DIR / "SOURCE.json"
INVENTORY_PATH = REFERENCE_DIR / "RULE_INVENTORY.json"
DURI_AUDIT_PATH = REFERENCE_DIR / "DURI_COUNT_AUDIT.json"
QURANPEDIA_DIR = ROOT / "audit/sources/quranpedia/2026-11-02"
QURANPEDIA_BASELINE = ROOT / "audit/sources/quranpedia/2026-10-27"
CANDIDATES_PATH = ROOT / "audit/tajweed-source-candidates.json"
SCOPE_REGISTRY_PATH = ROOT / "tajweed-scope-registry.json"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

EXPECTED_SCOPES = {
    "warsh": {
        "riwayah": "warsh-an-nafi",
        "reader": "nafi-al-madani",
        "tariq": "al-azraq-via-al-shatibiyyah",
        "records": 6214,
        "mushaf": "mushafs-4.json.gz",
        "baseline": "mushafs-4.json.gz",
        "canonical": "abd940919c897fa930f0a449e113f4fb8219709a48857d45783c39320f3fdc0d",
        "topics": 17,
    },
    "qalun": {
        "riwayah": "qalun-an-nafi",
        "reader": "nafi-al-madani",
        "tariq": "abu-nashit-via-al-shatibiyyah",
        "records": 6214,
        "mushaf": "mushafs-7.json.gz",
        "baseline": "mushafs-7.json.gz",
        "canonical": "363e16e8067622cb94ecfc86e922319f7aa238fb19e689b329ea1cffcd547d9c",
        "topics": 14,
    },
    "duri": {
        "riwayah": "al-duri-an-abi-amr",
        "reader": "abu-amr-al-basri",
        "tariq": "abu-al-zaraa-via-al-shatibiyyah",
        "records": 6218,
        "mushaf": "mushafs-6.json.gz",
        "baseline": "mushafs-6.json.gz",
        "canonical": "5db0d43d0a369aaa4366b4a1fb9b6b3a7d6c680eb2f3a195557a094cf594a164",
        "topics": 12,
    },
}

EXPECTED_LOCAL_FILES = {
    "LICENSE.md": (4227, "1e015f6bb6e4247cfcc68f2a3974f5a506536ab4bd5697161fc395dbcc438baf"),
    "manifest.json": (104416, "ade928bc6385ed5f1f94771e3e8557cecf28797e7a77488cbedc879c6dd1058f"),
    "mushafs-4.json.gz": (422507, "fb79026f75ad8fef6ab9752ee7fda4b8ff312ae45937016a1f8ecac70ebfd1b6"),
    "mushafs-6.json.gz": (421957, "a147439fe592e038b910e1d36ed536c5b65778313b35bee55320f4c5f9a89703"),
    "mushafs-7.json.gz": (418528, "f51234f98a96e3521b2a7c02d2c457158151867dbc720f1a2fadeaa3436d3809"),
}

MANDATORY_SOURCE_IDS = {
    "quranpedia-dumps-2026-11-02",
    "kfgqpc-dev-page-2026-10-28",
    "kfgqpc-warsh-v3",
    "kfgqpc-qalun-v3",
    "kfgqpc-duri-v2",
    "quranpedia-warsh-intro",
    "quranpedia-qalun-intro",
    "quranpedia-duri-intro",
    "libya-warsh-method-2022",
    "libya-qalun-method-2022",
    "duri-fawh-al-itr-2006",
    "duri-oiu-study-2016",
    "duri-fayyad-shatibiyyah",
    "quranpedia-duri-svg-2026-07-13",
    "faraid-al-hisan-counting",
}


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"missing {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def load_gzip_json(path: Path) -> Any:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid gzip JSON {path.relative_to(ROOT)}: {exc}") from exc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_without_license(payload: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    clean = dict(payload)
    clean.pop("license", None)
    encoded = json.dumps(
        clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return encoded, clean


def flatten_ayahs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    require(isinstance(data, dict), "Quranpedia mushaf data must be an object")
    surahs = data.get("surahs")
    require(isinstance(surahs, list) and len(surahs) == 114,
            "Quranpedia mushaf must contain 114 surahs")
    rows: list[dict[str, Any]] = []
    for expected_surah, surah in enumerate(surahs, 1):
        require(isinstance(surah, dict), "Quranpedia surah must be an object")
        require(surah.get("id") == expected_surah,
                f"Quranpedia surah order drift at {expected_surah}")
        ayahs = surah.get("ayahs")
        require(isinstance(ayahs, list) and ayahs,
                f"Quranpedia surah {expected_surah} has no ayahs")
        require([ayah.get("number") for ayah in ayahs] == list(range(1, len(ayahs) + 1)),
                f"Quranpedia numbering drift in surah {expected_surah}")
        rows.extend(ayahs)
    return rows


def verify_quranpedia_snapshot() -> None:
    source = load_json(QURANPEDIA_DIR / "SOURCE.json")
    require(source.get("schema") == 1, "unsupported Quranpedia source schema")
    require(source.get("purpose") == "AUDIT_REFERENCE_CORPORA_NOT_RUNTIME_INPUT",
            "Quranpedia snapshot purpose drift")
    require(source.get("dump_version") == "2026-11-02",
            "Quranpedia dump version drift")
    require(source.get("content_equivalence", {}).get("result") ==
            "IDENTICAL_FOR_MUSHAFS_4_6_7", "missing Quranpedia equivalence finding")
    require(source.get("content_equivalence", {}).get("runtime_regeneration_required") is False,
            "reference snapshot must not request runtime regeneration")

    for name, (expected_bytes, expected_sha) in EXPECTED_LOCAL_FILES.items():
        path = QURANPEDIA_DIR / name
        require(path.is_file(), f"missing pinned Quranpedia file {name}")
        require(path.stat().st_size == expected_bytes, f"byte drift in {name}")
        require(sha256(path) == expected_sha, f"hash drift in {name}")
        declared = source.get("files", {}).get(name)
        require(isinstance(declared, dict), f"SOURCE.json omits {name}")
        require(declared.get("bytes") == expected_bytes and declared.get("sha256") == expected_sha,
                f"SOURCE.json checksum drift for {name}")

    license_text = (QURANPEDIA_DIR / "LICENSE.md").read_text(encoding="utf-8")
    require("Version / النسخة: 2026-11-02" in license_text,
            "Quranpedia licence version is not pinned")
    require("crediting **Quranpedia.net**" in license_text
            and "بيانُ تاريخ هذه النسخة" in license_text,
            "Quranpedia redistribution attribution terms are missing")

    manifest = load_json(QURANPEDIA_DIR / "manifest.json")
    require(manifest.get("version") == "2026-11-02", "manifest version drift")
    manifest_files = {
        item.get("name"): item for item in manifest.get("files", []) if isinstance(item, dict)
    }

    for setting_id, expected in EXPECTED_SCOPES.items():
        filename = expected["mushaf"]
        declaration = source["files"][filename]
        manifest_entry = manifest_files.get(filename)
        require(isinstance(manifest_entry, dict), f"manifest omits {filename}")
        require(manifest_entry.get("sha256") == declaration.get("sha256")
                and manifest_entry.get("bytes") == declaration.get("bytes"),
                f"manifest/source mismatch for {filename}")

        current_payload = load_gzip_json(QURANPEDIA_DIR / filename)
        baseline_payload = load_gzip_json(QURANPEDIA_BASELINE / expected["baseline"])
        current_bytes, current_clean = canonical_without_license(current_payload)
        baseline_bytes, baseline_clean = canonical_without_license(baseline_payload)
        require(current_clean == baseline_clean,
                f"Quran payload changed since 2026-10-27 for {setting_id}")
        current_hash = hashlib.sha256(current_bytes).hexdigest()
        require(current_hash == expected["canonical"],
                f"canonical payload hash drift for {setting_id}")
        require(declaration.get("canonical_payload_sha256_without_top_level_license") == current_hash,
                f"undeclared canonical hash drift for {setting_id}")

        rows = flatten_ayahs(current_payload)
        require(len(rows) == expected["records"],
                f"record count drift for {setting_id}")
        require(declaration.get("records") == len(rows),
                f"declared record count drift for {setting_id}")

    duri = load_gzip_json(QURANPEDIA_DIR / "mushafs-6.json.gz")
    surah_67 = duri["data"]["surahs"][66]["ayahs"]
    require(len(surah_67) == 31, "known Duri surah 67 regression changed")
    duplicated_hafs_9 = [row for row in surah_67 if row.get("number_in_hafs") == [9]]
    require(len(duplicated_hafs_9) == 2,
            "known Duri 67:9 duplicate mapping is no longer represented as audited")


def verify_source_registry() -> dict[str, dict[str, Any]]:
    registry = load_json(SOURCE_PATH)
    require(registry.get("schemaVersion") == 1, "unsupported reference source schema")
    require(registry.get("snapshotDate") == "2026-11-02", "reference snapshot date drift")
    require(registry.get("purpose") ==
            "SCHOLARLY_REFERENCE_METADATA_ONLY_NOT_RUNTIME_DATA",
            "reference source registry must remain metadata-only")
    policy = registry.get("policy", {})
    for key in (
        "referenceBooksAreNotAnnotationCorpora",
        "noRuleTextOrExamplesMayBeCopiedWithoutRightsReview",
        "quranTextLicenseIsSeparateFromReferenceBookRights",
        "machineExtractionRequiresQualifiedHumanReview",
        "aCompleteWajhMustBeFixedBeforeCurriculumGeneration",
        "secondPersonReleaseApprovalRequired",
    ):
        require(policy.get(key) is True, f"reference policy disabled {key}")
    require(policy.get("runtimeActivationAllowed") is False,
            "reference registry cannot activate runtime content")

    sources = registry.get("sources")
    require(isinstance(sources, list) and sources, "reference sources are missing")
    by_id: dict[str, dict[str, Any]] = {}
    for source in sources:
        require(isinstance(source, dict), "reference source must be an object")
        source_id = source.get("id")
        require(isinstance(source_id, str) and TOKEN_RE.fullmatch(source_id) is not None,
                f"invalid reference source id {source_id}")
        require(source_id not in by_id, f"duplicate reference source id {source_id}")
        by_id[source_id] = source
        for key in ("url", "landingUrl"):
            if key in source:
                require(isinstance(source[key], str) and source[key].startswith("https://"),
                        f"non-HTTPS reference URL in {source_id}/{key}")
        for key, value in source.items():
            if key.lower().endswith("sha256"):
                require(isinstance(value, str) and SHA_RE.fullmatch(value) is not None,
                        f"invalid SHA-256 in {source_id}/{key}")
        if source.get("locallyCommitted") is False:
            require(source.get("bytes", source.get("retrievedBytes", 1)) > 0,
                    f"remote reference lacks byte size {source_id}")

    require(MANDATORY_SOURCE_IDS <= set(by_id), "mandatory reference source missing")
    dev_snapshot = ROOT / by_id["kfgqpc-dev-page-2026-10-28"]["localSnapshot"]
    require(dev_snapshot.is_file(), "official developer page snapshot is missing")
    require(sha256(dev_snapshot) == by_id["kfgqpc-dev-page-2026-10-28"]["snapshotSha256"],
            "official developer page snapshot drift")

    scopes = registry.get("scopes")
    require(isinstance(scopes, list) and len(scopes) == 3,
            "reference registry must contain three riwayah scopes")
    scope_by_id = {scope.get("settingId"): scope for scope in scopes}
    require(set(scope_by_id) == set(EXPECTED_SCOPES), "reference scope coverage drift")
    for setting_id, expected in EXPECTED_SCOPES.items():
        scope = scope_by_id[setting_id]
        require(scope.get("riwayah") == expected["riwayah"],
                f"riwayah drift for {setting_id}")
        require(scope.get("reader") == expected["reader"],
                f"reader drift for {setting_id}")
        require(scope.get("tariq") == expected["tariq"],
                f"tariq drift for {setting_id}")
        require(scope.get("identityEvidenceStatus") == "PASS"
                and scope.get("tariqEvidenceStatus") == "PASS",
                f"identity/tariq evidence incomplete for {setting_id}")
        require(str(scope.get("wajhStatus", "")).startswith("BLOCKED_"),
                f"unreviewed wajh was unblocked for {setting_id}")
        require(scope.get("annotationCorpusStatus") == "MISSING",
                f"unexpected annotation corpus for {setting_id}")
        evidence = scope.get("evidence")
        require(isinstance(evidence, list) and evidence,
                f"scope evidence missing for {setting_id}")
        require(all(item.get("sourceId") in by_id for item in evidence),
                f"unknown evidence source in {setting_id}")

    conclusion = registry.get("releaseConclusion", {})
    require(conclusion.get("status") == "QUARANTINED_NOT_PUBLISHABLE"
            and conclusion.get("runtimeChanges") == 0
            and conclusion.get("approvedCurricula") == 0,
            "reference audit cannot approve a release")
    return by_id


def verify_rule_inventory(source_ids: set[str]) -> None:
    inventory = load_json(INVENTORY_PATH)
    require(inventory.get("schemaVersion") == 1, "unsupported rule inventory schema")
    require(inventory.get("purpose") ==
            "REFERENCE_TOPIC_MAP_ONLY_NOT_A_RULESET_OR_CURRICULUM",
            "topic map was misclassified as a ruleset")
    for key, expected in (
        ("metadataOnly", True),
        ("containsQuranText", False),
        ("containsCopiedRuleProse", False),
        ("containsAnnotationSpans", False),
        ("containsTrainingExamples", False),
    ):
        require(inventory.get(key) is expected, f"rule inventory flag drift: {key}")

    scopes = inventory.get("scopes")
    require(isinstance(scopes, list) and len(scopes) == 3,
            "rule inventory scope coverage drift")
    by_setting = {scope.get("settingId"): scope for scope in scopes}
    require(set(by_setting) == set(EXPECTED_SCOPES), "rule inventory settings drift")
    for setting_id, expected in EXPECTED_SCOPES.items():
        scope = by_setting[setting_id]
        target = scope.get("scope", {})
        require(target.get("riwayah") == expected["riwayah"]
                and target.get("tariq") == expected["tariq"]
                and target.get("wajh") == "not-yet-fixed",
                f"rule inventory scope drift for {setting_id}")
        require(scope.get("topicMapStatus") ==
                "COMPLETE_AGAINST_PRIMARY_REFERENCE_TABLE_OF_CONTENTS",
                f"topic map is incomplete for {setting_id}")
        require(scope.get("ruleExtractionStatus") == "NOT_STARTED"
                and scope.get("completeRuleInventoryGate") == "FAIL",
                f"topic map incorrectly passed the rule gate for {setting_id}")
        require(scope.get("primarySourceId") in source_ids,
                f"unknown primary source for {setting_id}")
        topics = scope.get("topics")
        require(isinstance(topics, list) and len(topics) == expected["topics"],
                f"topic count drift for {setting_id}")
        topic_ids = [topic.get("topicId") for topic in topics]
        require(len(set(topic_ids)) == len(topic_ids)
                and all(isinstance(topic_id, str) and TOKEN_RE.fullmatch(topic_id)
                        for topic_id in topic_ids),
                f"invalid topic IDs for {setting_id}")
        require(all(isinstance(topic.get("titleAr"), str) and topic["titleAr"].strip()
                    and isinstance(topic.get("printedPage"), int)
                    and topic["printedPage"] > 0 for topic in topics),
                f"malformed topic locator for {setting_id}")
        for cross_check in scope.get("secondaryCrossChecks", []):
            require(cross_check.get("sourceId") in source_ids,
                    f"unknown cross-check source for {setting_id}")

    forbidden_keys = {"text", "quranText", "ruleText", "example", "examples",
                      "ayah", "ayahs", "annotations", "spans"}
    stack = [inventory]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            require(not (set(value) & forbidden_keys),
                    "metadata-only inventory contains Quran/rule/example payload")
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    require(inventory.get("releaseStatus") == "QUARANTINED_NOT_PUBLISHABLE",
            "rule inventory must remain quarantined")


def verify_duri_count_audit(source_ids: set[str]) -> None:
    audit = load_json(DURI_AUDIT_PATH)
    require(audit.get("schemaVersion") == 1, "unsupported Duri count audit schema")
    require(audit.get("status") ==
            "QUARANTINED_PUBLISHER_OR_QUALIFIED_SCHOLAR_CLARIFICATION_REQUIRED",
            "Duri count conflict was unblocked")
    require(audit.get("runtimeAction") == "NONE", "Duri audit altered runtime")
    observations = audit.get("observations")
    require(isinstance(observations, list) and len(observations) == 4,
            "Duri count observations drift")
    require(all(item.get("sourceId") in source_ids for item in observations),
            "Duri audit references an unknown source")
    totals = {item.get("observationId"): item.get("totalAyahs") for item in observations}
    require(totals == {
        "official-introduction-count": 6214,
        "official-data-package-count": 6217,
        "rendered-archive-embedded-count": 6217,
        "quranpedia-current-dump-count": 6218,
    }, "Duri 6214/6217/6218 evidence drift")

    regression = audit.get("quranpedia67Regression", {})
    require(regression.get("status") == "CONFIRMED"
            and regression.get("surah") == 67
            and regression.get("affectedHafsReference") == 9
            and regression.get("currentDumpRowsForThatReference") == 2
            and regression.get("officialSpreadsheetAndRenderedArchiveRowsForThatReference") == 1
            and regression.get("officialSurahCount") == 30
            and regression.get("currentDumpSurahCount") == 31
            and regression.get("safeAutomaticRepair") is False,
            "Duri 67:9 regression finding drift")

    comparison = audit.get("comparisonAgainstOfficialWarshAndQalun6214Datasets", {})
    rows = comparison.get("rows")
    require(isinstance(rows, list) and len(rows) == 12,
            "Duri per-surah comparison must retain 12 differences")
    require(sum(row.get("delta", 0) for row in rows) == 3
            and comparison.get("deltaSumCheck") == 3
            and comparison.get("netDelta") == 3,
            "Duri per-surah delta no longer sums to three")
    require({row.get("surah") for row in rows} ==
            {11, 19, 26, 30, 35, 58, 67, 73, 74, 86, 91, 99},
            "Duri differing-surah set drift")
    require(audit.get("countingTraditionContext", {}).get("resolutionStatus") ==
            "NOT_RESOLVED", "Duri official count conflict was silently resolved")

    installed = load_json(ROOT / "quran-riwayat.json")
    duri_rows = installed.get("riwayat", {}).get("duri")
    require(isinstance(duri_rows, list) and len(duri_rows) == 6218,
            "installed quarantined Duri record count drift")
    require(sum(1 for row in duri_rows if row[0] == 67) == 31,
            "installed Duri surah 67 finding drift")


def verify_candidate_links() -> None:
    candidates = load_json(CANDIDATES_PATH)
    require(candidates.get("referenceAudit") == {
        "sourceRegistry": "audit/sources/tajweed-riwayat/2026-11-02/SOURCE.json",
        "ruleInventory": "audit/sources/tajweed-riwayat/2026-11-02/RULE_INVENTORY.json",
        "duriCountAudit": "audit/sources/tajweed-riwayat/2026-11-02/DURI_COUNT_AUDIT.json",
    }, "candidate registry does not pin the reference audit")
    entries = candidates.get("riwayat")
    require(isinstance(entries, list) and len(entries) == 3,
            "candidate registry coverage drift")
    by_setting = {entry.get("settingId"): entry for entry in entries}
    require(set(by_setting) == set(EXPECTED_SCOPES), "candidate settings drift")
    for setting_id, expected in EXPECTED_SCOPES.items():
        entry = by_setting[setting_id]
        target = entry.get("targetScope", {})
        require(target.get("riwayah") == expected["riwayah"]
                and target.get("tariq") == expected["tariq"],
                f"candidate route drift for {setting_id}")
        require(entry.get("gates", {}).get("documentedTariq") == "PASS",
                f"documented tariq was not promoted for {setting_id}")
        require(entry.get("gates", {}).get("documentedWajh") == "FAIL",
                f"unreviewed wajh was promoted for {setting_id}")
        require(entry.get("publishableAsApproved") is False,
                f"candidate became publishable for {setting_id}")
        require("FAIL" in entry.get("gates", {}).values(),
                f"candidate has no release blocker for {setting_id}")

    registry = load_json(SCOPE_REGISTRY_PATH)
    for setting_id in EXPECTED_SCOPES:
        matches = [entry for entry in registry.get("settings", [])
                   if setting_id in entry.get("settingIds", [])]
        require(len(matches) == 1
                and matches[0].get("status") == "BLOCKED_NO_APPROVED_CORPUS"
                and matches[0].get("curricula") == [],
                f"reference audit leaked into runtime for {setting_id}")

    require(not list(REFERENCE_DIR.rglob("*.pdf")),
            "copyrighted reference PDF was copied into the metadata-only audit")


def main() -> int:
    try:
        verify_quranpedia_snapshot()
        sources = verify_source_registry()
        verify_rule_inventory(set(sources))
        verify_duri_count_audit(set(sources))
        verify_candidate_links()
        print("Verified non-Hafs tajweed reference sources:")
        print("  Warsh: al-Azraq via al-Shatibiyyah documented; wajh/corpus/review blocked")
        print("  Qalun: Abu Nashit via al-Shatibiyyah documented; wajh/corpus/review blocked")
        print("  Duri: Abu al-Zaraa via al-Shatibiyyah documented; 6214/6217 conflict blocked")
        print("  Quranpedia Duri 67:9 split regression: quarantined (6218, not approved)")
        print("  runtime curricula activated: 0")
        return 0
    except VerificationError as exc:
        print(f"tajweed reference source verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
