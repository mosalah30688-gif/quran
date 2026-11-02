#!/usr/bin/env python3
"""Verify that tajweed source candidates remain quarantined and fail closed."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "audit/tajweed-source-candidates.json"
REGISTRY_PATH = ROOT / "tajweed-scope-registry.json"
EXPECTED = {
    "warsh": ("warsh-an-nafi", 6214),
    "qalun": ("qalun-an-nafi", 6214),
    "duri": ("al-duri-an-abi-amr", 6218),
}
REQUIRED_GATES = {
    "documentedRiwayah",
    "documentedTariq",
    "documentedWajh",
    "completeRuleInventory",
    "completeAnnotationCorpus",
    "exactSirajTextBinding",
    "redistributionRights",
    "qualifiedHumanReview",
    "secondPersonReleaseApproval",
}
ALLOWED_GATE_VALUES = {
    "PASS",
    "FAIL",
    "PARTIAL",
    "NOT_APPLICABLE",
    "TECHNICAL_PASS_UNREVIEWED",
}
TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"missing {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_local_text_source(source: dict[str, Any], expected_records: int) -> None:
    asset_name = source.get("localAsset")
    require(isinstance(asset_name, str) and Path(asset_name).name == asset_name,
            "candidate localAsset must be a root filename")
    asset = ROOT / asset_name
    require(asset.is_file(), f"missing local source asset {asset_name}")
    expected_sha = source.get("assetSha256")
    require(isinstance(expected_sha, str) and SHA_RE.fullmatch(expected_sha) is not None,
            f"invalid source hash for {asset_name}")
    require(digest(asset) == expected_sha, f"source hash drift for {asset_name}")
    payload = load(asset)
    dataset = source.get("dataset")
    rows = payload.get("riwayat", {}).get(dataset) if isinstance(payload, dict) else None
    require(isinstance(rows, list) and len(rows) == expected_records,
            f"record drift for {asset_name}/{dataset}")
    require(source.get("records") == expected_records,
            f"declared record drift for {asset_name}/{dataset}")


def verify_analysis(relative: str) -> None:
    path = ROOT / relative
    require(path.is_file(), f"missing technical analysis {relative}")
    analysis = load(path)
    require(analysis.get("schemaVersion") == 1, "unsupported Warsh analysis schema")
    require(analysis.get("candidateId") == "warsh-al-azraq-qud-generated-v1",
            "unexpected Warsh candidate analysis")
    scope = analysis.get("scope", {})
    require(scope.get("riwayah") == "warsh-an-nafi" and scope.get("tariq") == "al-azraq",
            "Warsh candidate analysis scope drift")
    artifact = analysis.get("artifact", {})
    require(artifact.get("sha256") ==
            "0898c80ad1325a36031a24f45a2ca6c1649c051c94e88de89cc594c70273b4f8",
            "Warsh candidate archive hash drift")
    require(artifact.get("bytes") == 2_642_177, "Warsh candidate archive size drift")

    checks = analysis.get("technicalChecks", {})
    expected_checks = {
        "manifestLockedFiles": 605,
        "pages": 604,
        "uniqueAyahs": 6214,
        "textHashFailures": 0,
        "invalidAnnotationSpans": 0,
        "annotationSpans": 164141,
        "ruleAssignments": 212214,
        "ruleIdentifiers": 46,
        "wordSpans": 77630,
    }
    for key, value in expected_checks.items():
        require(checks.get(key) == value, f"Warsh analysis drift in {key}")
    duplicates = checks.get("identicalCrossPageDuplicates")
    require(duplicates == [
        {"reference": "4:44", "pages": [85, 86]},
        {"reference": "20:86", "pages": [317, 318]},
        {"reference": "24:36", "pages": [354, 355]},
        {"reference": "24:42", "pages": [355, 356]},
    ], "Warsh cross-page duplicate report drift")

    occurrences = analysis.get("ruleOccurrences")
    require(isinstance(occurrences, dict) and len(occurrences) == 46,
            "Warsh rule occurrence inventory drift")
    require(all(isinstance(key, str) and TOKEN_RE.fullmatch(key) is not None
                and isinstance(value, int) and value > 0
                for key, value in occurrences.items()),
            "Warsh rule occurrence inventory is malformed")
    require(sum(occurrences.values()) == 212_214, "Warsh rule assignment sum drift")
    for required_rule in ("naql", "taqlil", "madd_mim_al_jam", "madd_yaa_zawaid"):
        require(required_rule in occurrences, f"missing Warsh-specific rule {required_rule}")

    binding = analysis.get("projectBinding", {})
    require(binding.get("asset") == "quran-riwayat.json"
            and binding.get("dataset") == "warsh"
            and binding.get("sha256") == digest(ROOT / "quran-riwayat.json"),
            "Warsh candidate project binding drift")
    require(binding.get("records") == 6214
            and binding.get("exactTextMatches") == 5250
            and binding.get("nfcTextMatches") == 5252
            and binding.get("layoutMarkNormalizedMatches") == 5964
            and binding.get("unresolvedTextDifferences") == 250,
            "Warsh candidate text comparison drift")
    require(binding.get("pageMatches") == 6156
            and binding.get("pageDifferences") == 58
            and binding.get("safeAutomaticOffsetTransfer") is False,
            "Warsh candidate must not allow automatic offset transfer")

    generator = analysis.get("generator", {})
    require(generator.get("codeLicense") == "MIT", "generator code license drift")
    require(generator.get("corpusUpstreamUrlRecorded") is False
            and generator.get("corpusRedistributionLicenseRecorded") is False,
            "unresolved corpus provenance must remain explicit")

    gate = analysis.get("releaseGate", {})
    require(gate.get("technicalIntegrity") == "PASS", "technical candidate did not pass integrity")
    for key in ("independentCorpusLicense", "exactProjectTextBinding",
                "qualifiedWarshReview", "secondPersonReleaseApproval"):
        require(gate.get(key) == "FAIL", f"Warsh release blocker {key} was removed")
    require(gate.get("status") == "QUARANTINED_NOT_PUBLISHABLE"
            and gate.get("publishableAsApproved") is False,
            "Warsh candidate must remain quarantined")

    # The report must remain metadata-only: no verse strings or copied annotation arrays.
    forbidden_keys = {"text", "ayahs", "spans", "words", "annotations"}
    stack = [analysis]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            require(not (set(value) & forbidden_keys),
                    "technical analysis contains forbidden Quran/annotation payload")
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)


def main() -> int:
    try:
        payload = load(CANDIDATES_PATH)
        registry = load(REGISTRY_PATH)
        require(payload.get("schemaVersion") == 1, "unsupported candidate registry schema")
        require(payload.get("purpose") == "QUARANTINE_ONLY_NOT_RUNTIME_DATA",
                "candidate data must remain quarantine-only")
        policy = payload.get("policy", {})
        for key in (
            "machineGeneratedAnnotationsRequireQualifiedHumanReview",
            "textOffsetsMustBindExactEditionHash",
            "redistributionRightsMustCoverCorpusAndDerivedAnnotations",
            "secondPersonReleaseApprovalRequired",
            "crossRiwayahFallbackForbidden",
        ):
            require(policy.get(key) is True, f"candidate policy disabled {key}")
        require(policy.get("candidateMayBeShownAsApproved") is False,
                "candidate content cannot be shown as approved")

        entries = payload.get("riwayat")
        require(isinstance(entries, list) and len(entries) == 3,
                "candidate registry must cover Warsh, Qalun and Duri")
        by_setting: dict[str, dict[str, Any]] = {}
        for entry in entries:
            require(isinstance(entry, dict), "candidate riwayah entry must be an object")
            setting_id = entry.get("settingId")
            require(setting_id in EXPECTED and setting_id not in by_setting,
                    f"unexpected or duplicate candidate setting {setting_id}")
            by_setting[setting_id] = entry
            riwayah_id, expected_records = EXPECTED[setting_id]
            require(entry.get("riwayahId") == riwayah_id,
                    f"candidate riwayah identity drift for {setting_id}")
            require(entry.get("publishableAsApproved") is False,
                    f"unreviewed {setting_id} candidate cannot be publishable")
            require(entry.get("candidateStatus") in {
                "QUARANTINED_NOT_PUBLISHABLE", "BLOCKED_NO_ANNOTATION_CORPUS"
            }, f"invalid candidate status for {setting_id}")
            target = entry.get("targetScope", {})
            require(target.get("riwayah") == riwayah_id,
                    f"candidate target scope drift for {setting_id}")
            for field in ("tariq", "wajh", "edition"):
                require(isinstance(target.get(field), str) and target[field],
                        f"missing {setting_id} target scope field {field}")
            gates = entry.get("gates")
            require(isinstance(gates, dict) and set(gates) == REQUIRED_GATES,
                    f"candidate gates drift for {setting_id}")
            require(set(gates.values()) <= ALLOWED_GATE_VALUES,
                    f"invalid gate status for {setting_id}")
            require("FAIL" in gates.values(), f"unapproved {setting_id} candidate has no blocker")
            reasons = entry.get("blockedReasonsAr")
            require(isinstance(reasons, list) and len(reasons) >= 2
                    and all(isinstance(reason, str) and reason.strip() for reason in reasons),
                    f"missing Arabic blocker explanation for {setting_id}")
            sources = entry.get("sources")
            require(isinstance(sources, list) and sources,
                    f"candidate sources missing for {setting_id}")
            source_ids: set[str] = set()
            for source in sources:
                require(isinstance(source, dict), "candidate source must be an object")
                source_id = source.get("id")
                require(isinstance(source_id, str) and TOKEN_RE.fullmatch(source_id) is not None
                        and source_id not in source_ids,
                        f"invalid or duplicate source id {source_id}")
                source_ids.add(source_id)
                if "url" in source:
                    require(isinstance(source["url"], str) and source["url"].startswith("https://"),
                            f"candidate source URL must use HTTPS: {source_id}")
                if "localAsset" in source:
                    verify_local_text_source(source, expected_records)

            analysis_path = entry.get("technicalAnalysis")
            if setting_id == "warsh":
                require(analysis_path ==
                        "audit/tajweed-candidates/warsh-al-azraq-qud-v1.analysis.json",
                        "Warsh technical analysis pointer drift")
                verify_analysis(analysis_path)
            else:
                require(analysis_path is None, f"{setting_id} has an unregistered technical analysis")

        require(set(by_setting) == set(EXPECTED), "candidate setting coverage drift")

        registry_entries = registry.get("settings", [])
        for setting_id, (riwayah_id, _) in EXPECTED.items():
            match = [entry for entry in registry_entries
                     if setting_id in entry.get("settingIds", [])]
            require(len(match) == 1 and match[0].get("riwayah", {}).get("id") == riwayah_id,
                    f"runtime registry mismatch for {setting_id}")
            require(match[0].get("status") == "BLOCKED_NO_APPROVED_CORPUS"
                    and match[0].get("curricula") == [],
                    f"quarantined {setting_id} candidate leaked into runtime")

        forbidden_runtime_files = [
            ROOT / "warsh-tajweed-v1.zip",
            ROOT / "www/warsh-tajweed-v1.zip",
            ROOT / "tajweed-curricula/warsh-al-azraq.json",
            ROOT / "www/tajweed-curricula/warsh-al-azraq.json",
        ]
        require(not any(path.exists() for path in forbidden_runtime_files),
                "quarantined Warsh payload was copied into runtime assets")

        print("Verified tajweed source quarantine:")
        print("  Warsh/al-Azraq: 6,214 ayahs and 46 rule IDs technically audited, still blocked")
        print("  Qalun: no licensed annotation corpus, blocked")
        print("  Duri: no licensed annotation corpus, blocked")
        print("  runtime curricula leaked: 0")
        return 0
    except VerificationError as exc:
        print(f"tajweed source quarantine verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
