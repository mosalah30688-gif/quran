#!/usr/bin/env python3
"""Build or verify the fail-closed non-Hafs wajh review packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit/sources/tajweed-riwayat/2026-11-02"
INVENTORY_PATH = AUDIT_DIR / "RULE_INVENTORY.json"
SOURCE_PATH = AUDIT_DIR / "SOURCE.json"
DURI_COUNT_PATH = AUDIT_DIR / "DURI_COUNT_AUDIT.json"
QURANPEDIA_SOURCE_PATH = ROOT / "audit/sources/quranpedia/2026-11-02/SOURCE.json"
CANDIDATES_PATH = ROOT / "audit/tajweed-source-candidates.json"
SCOPE_REGISTRY_PATH = ROOT / "tajweed-scope-registry.json"
PACKET_PATH = AUDIT_DIR / "WAJH_REVIEW_PACKET.json"
GUIDE_PATH = AUDIT_DIR / "WAJH_REVIEW_GUIDE.ar.md"
SCHOLARLY_REVIEW_PATH = ROOT / "audit/SCHOLARLY_REVIEW.md"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")

SCOPE_CONFIG = {
    "warsh": {
        "expectedTopics": 17,
        "quranpediaFile": "mushafs-4.json.gz",
        "bindingStatus": "CANDIDATE_PENDING_WAJH_AND_QUALIFIED_REVIEW",
        "editionStatus": "PENDING_QUALIFIED_CONFIRMATION",
        "criticalTopics": {
            "madd-wa-qasr",
            "hamzatayn-min-kalima",
            "hamzatayn-min-kalimatayn",
            "fath-wa-imala",
            "raat",
            "lamat",
            "tarkib-al-wujuh-appendix",
        },
        "specialGates": [
            {
                "gateId": "warsh-compatible-face-composition",
                "status": "PENDING_QUALIFIED_REVIEW",
                "blocking": True,
                "sourceIds": ["libya-warsh-method-2022"],
                "locator": "printed page 134",
                "requiredOutcomeAr": "تثبيت تركيب واحد متوافق لجميع الاختيارات، لا جمع أوجه متعارضة ولا اعتماد افتراضي.",
            },
            {
                "gateId": "warsh-rule-and-derived-data-rights",
                "status": "BLOCKED_NO_REDISTRIBUTION_GRANT",
                "blocking": True,
                "sourceIds": ["quranpedia-dumps-2026-11-02", "libya-warsh-method-2022"],
                "locator": "rights conclusion in SOURCE.json",
                "requiredOutcomeAr": "تسجيل إذن صريح يغطي قاعدة الأحكام والبيانات المشتقة، مستقلًا عن ترخيص نص القرآن.",
            },
        ],
    },
    "qalun": {
        "expectedTopics": 14,
        "quranpediaFile": "mushafs-7.json.gz",
        "bindingStatus": "CANDIDATE_PENDING_WAJH_AND_QUALIFIED_REVIEW",
        "editionStatus": "PENDING_QUALIFIED_CONFIRMATION",
        "criticalTopics": {
            "mim-al-jam",
            "madd-wa-qasr",
            "hamzatayn-min-kalima",
            "hamzatayn-min-kalimatayn",
            "hamz-mufrad",
            "fath-wa-imala",
        },
        "specialGates": [
            {
                "gateId": "qalun-compatible-face-composition",
                "status": "PENDING_QUALIFIED_REVIEW",
                "blocking": True,
                "sourceIds": ["libya-qalun-method-2022"],
                "locator": "chapter 3, printed pages 75-124",
                "requiredOutcomeAr": "تثبيت وجه واحد كامل ومتوافق بين أبواب الأصول قبل إنشاء أي منهج.",
            },
            {
                "gateId": "qalun-rule-and-derived-data-rights",
                "status": "BLOCKED_NO_REDISTRIBUTION_GRANT",
                "blocking": True,
                "sourceIds": ["quranpedia-dumps-2026-11-02", "libya-qalun-method-2022"],
                "locator": "rights conclusion in SOURCE.json",
                "requiredOutcomeAr": "تسجيل إذن صريح يغطي قاعدة الأحكام والبيانات المشتقة، مستقلًا عن ترخيص نص القرآن.",
            },
        ],
    },
    "duri": {
        "expectedTopics": 12,
        "quranpediaFile": "mushafs-6.json.gz",
        "bindingStatus": "REJECTED_AS_OFFSET_AUTHORITY_KNOWN_67_9_SPLIT",
        "editionStatus": "BLOCKED_COUNT_SCOPE_AND_DATA_INTEGRITY",
        "criticalTopics": {
            "idgham-saghir",
            "madd-wa-qasr",
            "fath-imala-taqlil",
            "hamz-mufrad",
            "hamzatayn-min-kalima",
            "hamzatayn-min-kalimatayn",
        },
        "specialGates": [
            {
                "gateId": "duri-count-tradition",
                "status": "BLOCKED_EXTERNAL_CLARIFICATION",
                "blocking": True,
                "sourceIds": ["quranpedia-duri-intro", "kfgqpc-duri-v2", "faraid-al-hisan-counting"],
                "locator": "DURI_COUNT_AUDIT.json",
                "requiredOutcomeAr": "حسم موثق للعدد المقصود وجدول السور للطبعة نفسها من الناشر أو مختص مؤهل.",
            },
            {
                "gateId": "duri-quranpedia-67-9-regression",
                "status": "BLOCKED_SOURCE_CORRECTION_OR_REPLACEMENT",
                "blocking": True,
                "sourceIds": ["quranpedia-dumps-2026-11-02", "kfgqpc-duri-v2", "quranpedia-duri-svg-2026-07-13"],
                "locator": "surah 67, Hafs reference 9",
                "requiredOutcomeAr": "استخدام أصل مصحح ومثبت البصمة؛ يمنع الإصلاح الآلي أو حذف سجل اعتباطًا.",
            },
            {
                "gateId": "duri-large-idgham-separation",
                "status": "PENDING_QUALIFIED_REVIEW",
                "blocking": True,
                "sourceIds": ["duri-oiu-study-2016", "duri-fayyad-shatibiyyah"],
                "locator": "Duri and Susi principle sections",
                "requiredOutcomeAr": "تأكيد مستقل يمنع نسبة الإدغام الكبير للدوري من عرض عام يخص قراءة أبي عمرو أو السوسي.",
            },
            {
                "gateId": "duri-rule-and-derived-data-rights",
                "status": "BLOCKED_NO_REDISTRIBUTION_GRANT",
                "blocking": True,
                "sourceIds": ["quranpedia-dumps-2026-11-02", "duri-fawh-al-itr-2006", "duri-oiu-study-2016"],
                "locator": "rights conclusion in SOURCE.json",
                "requiredOutcomeAr": "تسجيل إذن صريح يغطي قاعدة الأحكام والبيانات المشتقة، مستقلًا عن ترخيص نص القرآن.",
            },
        ],
    },
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def by_key(rows: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    require(isinstance(rows, list) and rows, f"{label} must be a non-empty list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        require(isinstance(row, dict), f"{label} item must be an object")
        value = row.get(key)
        require(isinstance(value, str) and value not in result, f"invalid or duplicate {label}/{key}")
        result[value] = row
    return result


def decision_kind(setting_id: str, topic_id: str) -> str:
    if topic_id == "tarkib-al-wujuh-appendix":
        return "FIX_CROSS_TOPIC_COMPATIBILITY"
    if topic_id in SCOPE_CONFIG[setting_id]["criticalTopics"]:
        return "FIX_COMPATIBLE_PRACTICE"
    return "CONFIRM_SCOPE_PRACTICE"


def decision_question(title_ar: str, kind: str) -> str:
    if kind == "FIX_CROSS_TOPIC_COMPATIBILITY":
        return f"ثبّت تركيبًا واحدًا متوافقًا لباب «{title_ar}» مع جميع قرارات الوجه، وسجّل موضع الدليل."
    if kind == "FIX_COMPATIBLE_PRACTICE":
        return f"ثبّت الممارسة المختارة لباب «{title_ar}» ضمن وجه واحد متوافق، وسجّل موضع الدليل."
    return f"أكّد ممارسة باب «{title_ar}» في الوجه المختار، أو صرّح بعدم تعدد الوجه فيه، وسجّل موضع الدليل."


def build_expected_packet() -> dict[str, Any]:
    inventory = load_json(INVENTORY_PATH)
    registry = load_json(SOURCE_PATH)
    duri_count = load_json(DURI_COUNT_PATH)
    quranpedia = load_json(QURANPEDIA_SOURCE_PATH)
    candidates = load_json(CANDIDATES_PATH)
    runtime_registry = load_json(SCOPE_REGISTRY_PATH)

    require(inventory.get("metadataOnly") is True, "topic inventory is not metadata-only")
    require(inventory.get("releaseStatus") == "QUARANTINED_NOT_PUBLISHABLE",
            "topic inventory release status drift")
    require(registry.get("releaseConclusion", {}).get("approvedCurricula") == 0,
            "reference registry unexpectedly approved a curriculum")
    require(duri_count.get("runtimeAction") == "NONE",
            "Duri count audit unexpectedly changed runtime")

    inventory_scopes = by_key(inventory.get("scopes"), "settingId", "inventory scopes")
    source_scopes = by_key(registry.get("scopes"), "settingId", "source scopes")
    source_records = by_key(registry.get("sources"), "id", "reference sources")
    candidate_scopes = by_key(candidates.get("riwayat"), "settingId", "candidate scopes")
    for setting_id, config in SCOPE_CONFIG.items():
        for gate in config["specialGates"]:
            for source_id in gate["sourceIds"]:
                require(source_id in source_records,
                        f"unknown {setting_id} gate source: {source_id}")
    runtime_by_setting: dict[str, dict[str, Any]] = {}
    for setting_id in SCOPE_CONFIG:
        matches = [row for row in runtime_registry.get("settings", [])
                   if setting_id in row.get("settingIds", [])]
        require(len(matches) == 1, f"runtime scope coverage drift for {setting_id}")
        runtime_by_setting[setting_id] = matches[0]

    scopes: list[dict[str, Any]] = []
    for setting_id, config in SCOPE_CONFIG.items():
        inventory_scope = inventory_scopes[setting_id]
        source_scope = source_scopes[setting_id]
        candidate_scope = candidate_scopes[setting_id]
        target = inventory_scope["scope"]
        runtime = runtime_by_setting[setting_id]
        require(source_scope.get("riwayah") == target.get("riwayah")
                and source_scope.get("tariq") == target.get("tariq"),
                f"source/inventory route drift for {setting_id}")
        require(candidate_scope.get("targetScope", {}).get("tariq") == target.get("tariq"),
                f"candidate route drift for {setting_id}")
        require(runtime.get("status") == "BLOCKED_NO_APPROVED_CORPUS"
                and runtime.get("curricula") == [],
                f"runtime scope unexpectedly open for {setting_id}")

        topics = inventory_scope.get("topics")
        require(isinstance(topics, list) and len(topics) == config["expectedTopics"],
                f"topic count drift for {setting_id}")
        decisions: list[dict[str, Any]] = []
        for topic in topics:
            topic_id = topic["topicId"]
            kind = decision_kind(setting_id, topic_id)
            decisions.append({
                "decisionId": f"{setting_id}.{topic_id}",
                "topicId": topic_id,
                "titleAr": topic["titleAr"],
                "sourceId": inventory_scope["primarySourceId"],
                "printedPage": topic["printedPage"],
                "decisionKind": kind,
                "reviewQuestionAr": decision_question(topic["titleAr"], kind),
                "status": "PENDING",
                "selectedPracticeId": None,
                "selectedPracticeLabelAr": None,
                "reviewerSourceLocator": None,
                "reviewerNoteAr": None,
            })

        qp_file = quranpedia["files"][config["quranpediaFile"]]
        runtime_text = runtime["textEdition"]
        text_binding_candidate = {
            "runtimeAsset": runtime_text["asset"],
            "runtimeAssetSha256": runtime_text["sha256"],
            "dataset": runtime_text["dataset"],
            "verseRecords": runtime_text["verseRecords"],
            "quranpediaSnapshot": f"audit/sources/quranpedia/2026-11-02/{config['quranpediaFile']}",
            "quranpediaSnapshotSha256": qp_file["sha256"],
            "canonicalPayloadSha256WithoutTopLevelLicense":
                qp_file["canonical_payload_sha256_without_top_level_license"],
            "status": config["bindingStatus"],
        }

        count_audit = None
        if setting_id == "duri":
            count_audit = {
                "path": "audit/sources/tajweed-riwayat/2026-11-02/DURI_COUNT_AUDIT.json",
                "status": duri_count["status"],
                "observedTotals": [6214, 6217, 6218],
                "automaticRepairAllowed": False,
            }

        scopes.append({
            "settingId": setting_id,
            "proposedScope": {
                "riwayah": target["riwayah"],
                "tariq": target["tariq"],
                "wajh": "pending-qualified-review",
                "edition": target["edition"],
            },
            "routeStatus": "DOCUMENTED",
            "wajhStatus": "NOT_SELECTED",
            "editionStatus": config["editionStatus"],
            "sourceEvidenceIds": [item["sourceId"] for item in source_scope["evidence"]],
            "textBindingCandidate": text_binding_candidate,
            "countAudit": count_audit,
            "decisionItems": decisions,
            "specialGates": config["specialGates"],
            "reviewAssignment": {
                "status": "NOT_ASSIGNED",
                "reviewerName": None,
                "reviewerQualification": None,
                "exactRouteExperience": None,
                "assignedAt": None,
            },
            "finalDecision": {
                "status": "PENDING",
                "selectedWajhId": None,
                "selectedWajhLabelAr": None,
                "selectedEditionId": None,
                "selectedEditionSha256": None,
                "editionEvidenceLocator": None,
                "selectedCountTraditionId": None,
                "selectedTotalAyahs": None,
                "selectedSurahCountTableSha256": None,
                "compatibilityAttestationAr": None,
                "completedDecisionCount": 0,
                "reviewEvidenceSha256": None,
            },
            "secondPersonReleaseApproval": {
                "status": "NOT_STARTED",
                "approverName": None,
                "approverQualification": None,
                "approvalDate": None,
                "approvedArtifactSha256": None,
            },
            "publishableAsApproved": False,
        })

    return {
        "schemaVersion": 1,
        "packetId": "siraj-non-hafs-wajh-review-2026-11-02",
        "updatedAt": "2026-11-02",
        "purpose": "QUALIFIED_HUMAN_WAJH_AND_EDITION_DECISION_PACKET_ONLY",
        "status": "AWAITING_QUALIFIED_REVIEWER",
        "publishableAsApproved": False,
        "containsQuranText": False,
        "containsCopiedRuleProse": False,
        "containsTrainingExamples": False,
        "containsAnnotationSpans": False,
        "inputs": {
            "sourceRegistry": "audit/sources/tajweed-riwayat/2026-11-02/SOURCE.json",
            "topicInventory": "audit/sources/tajweed-riwayat/2026-11-02/RULE_INVENTORY.json",
            "duriCountAudit": "audit/sources/tajweed-riwayat/2026-11-02/DURI_COUNT_AUDIT.json",
            "quranpediaSnapshotRegistry": "audit/sources/quranpedia/2026-11-02/SOURCE.json",
            "candidateRegistry": "audit/tajweed-source-candidates.json",
            "runtimeScopeRegistry": "tajweed-scope-registry.json",
        },
        "reviewContract": {
            "reviewerMustBeQualifiedInExactRiwayahAndTariq": True,
            "fullScopeReviewNotSampling": True,
            "everyDecisionItemMustBeResolved": True,
            "selectedPracticesMustBeMutuallyCompatible": True,
            "sourceLocatorRequiredPerDecision": True,
            "editionAndCountMustBeExplicit": True,
            "reviewEvidenceHashRequired": True,
            "rightsApprovalIsSeparate": True,
            "secondPersonReleaseApprovalRequired": True,
            "machineMaySelectOrApprove": False,
            "runtimeActivationAllowed": False,
        },
        "scopes": scopes,
        "releaseGate": {
            "status": "BLOCKED",
            "runtimeChanges": 0,
            "approvedCurricula": 0,
            "requiredBeforeActivation": [
                "complete-qualified-review-response-for-every-decision",
                "one-compatible-wajh-profile-per-scope",
                "exact-edition-and-count-resolution",
                "licensed-rule-and-derived-data-corpus",
                "exact-text-hash-binding",
                "independent-second-person-release-approval",
            ],
        },
    }


def first_difference(actual: Any, expected: Any, path: str = "$") -> str | None:
    if type(actual) is not type(expected):
        return f"{path}: type {type(actual).__name__} != {type(expected).__name__}"
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            return f"{path}: keys differ; missing={missing}, extra={extra}"
        for key in expected:
            found = first_difference(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return f"{path}: list length {len(actual)} != {len(expected)}"
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            found = first_difference(actual_item, expected_item, f"{path}[{index}]")
            if found:
                return found
        return None
    if actual != expected:
        return f"{path}: {actual!r} != {expected!r}"
    return None


def verify_payload_boundary(packet: dict[str, Any]) -> None:
    forbidden_keys = {
        "text", "quranText", "ruleText", "example", "examples", "ayah", "ayahs",
        "annotations", "spans", "ruleProse",
    }
    stack: list[Any] = [packet]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            require(not (set(value) & forbidden_keys),
                    "wajh packet contains Quran/rule/example/annotation payload")
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)


def verify_guide() -> None:
    try:
        guide = GUIDE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise VerificationError(f"missing {GUIDE_PATH.relative_to(ROOT)}") from exc
    for marker in (
        "مراجعة كاملة لا بالعينة",
        "ورش عن نافع — طريق الأزرق من الشاطبية",
        "قالون عن نافع — طريق أبي نشيط من الشاطبية",
        "الدوري عن أبي عمرو — طريق أبي الزعراء من الشاطبية",
        "اسم المراجع",
        "المؤهل العلمي",
        "معرّف الوجه المختار",
        "بصمة دليل المراجعة",
        "اعتماد شخص ثانٍ مستقل",
        "لا تنسخ نص القرآن أو متن المرجع",
    ):
        require(marker in guide, f"review guide missing marker: {marker}")


def verify_scholarly_ledger() -> None:
    try:
        ledger = SCHOLARLY_REVIEW_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise VerificationError("missing audit/SCHOLARLY_REVIEW.md") from exc
    entries = {
        path: digest
        for path, digest in re.findall(
            r"\| `([^`]+)` \| `([0-9a-f]{64})` \|", ledger
        )
    }
    required_paths = (
        "tajweed-scope-registry.json",
        "audit/tajweed-source-candidates.json",
        "audit/sources/tajweed-riwayat/2026-11-02/SOURCE.json",
        "audit/sources/tajweed-riwayat/2026-11-02/RULE_INVENTORY.json",
        "audit/sources/tajweed-riwayat/2026-11-02/DURI_COUNT_AUDIT.json",
        "audit/sources/tajweed-riwayat/2026-11-02/WAJH_REVIEW_PACKET.json",
    )
    for relative in required_paths:
        declared = entries.get(relative)
        require(isinstance(declared, str) and SHA_RE.fullmatch(declared) is not None,
                f"scholarly ledger omits hash for {relative}")
        path = ROOT / relative
        require(path.is_file(), f"scholarly ledger file missing: {relative}")
        require(sha256(path) == declared, f"scholarly ledger hash drift: {relative}")


def verify_not_runtime() -> None:
    forbidden_roots = (
        ROOT / "www",
        ROOT / "update",
        ROOT / "windows_app/data",
        ROOT / "mushaf_app/data",
        ROOT / "tajweed-curricula",
    )
    for base in forbidden_roots:
        if not base.exists():
            continue
        leaked = [path for path in base.rglob("*")
                  if path.is_file() and "wajh-review" in path.name.lower()]
        if leaked:
            raise VerificationError(
                f"wajh review packet leaked into runtime: {leaked[0].relative_to(ROOT)}"
            )


def verify(packet_path: Path) -> None:
    expected = build_expected_packet()
    actual = load_json(packet_path)
    difference = first_difference(actual, expected)
    require(difference is None, f"review packet drift: {difference}")
    verify_payload_boundary(actual)
    verify_guide()
    verify_not_runtime()
    verify_scholarly_ledger()


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true",
                        help="write the deterministic blank review packet")
    action.add_argument("--verify", action="store_true",
                        help="verify the committed packet (default)")
    parser.add_argument("--packet", type=Path, default=PACKET_PATH,
                        help="packet to compare with the deterministic template")
    args = parser.parse_args()
    try:
        if args.write:
            payload = build_expected_packet()
            PACKET_PATH.parent.mkdir(parents=True, exist_ok=True)
            PACKET_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Wrote {PACKET_PATH.relative_to(ROOT)}")
            return 0
        verify(args.packet.resolve())
        packet = load_json(args.packet.resolve())
        counts = {scope["settingId"]: len(scope["decisionItems"])
                  for scope in packet["scopes"]}
        print("Verified fail-closed tajweed wajh review packet:")
        print(f"  decision coverage: Warsh {counts['warsh']}, Qalun {counts['qalun']}, Duri {counts['duri']}")
        print("  selected wajh profiles: 0")
        print("  qualified reviewers assigned: 0")
        print("  runtime curricula activated: 0")
        return 0
    except (VerificationError, KeyError, TypeError, ValueError) as exc:
        print(f"tajweed wajh review packet verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
