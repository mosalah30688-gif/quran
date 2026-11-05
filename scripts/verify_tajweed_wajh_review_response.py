#!/usr/bin/env python3
"""Generate and verify fillable scholarly responses to the non-Hafs wajh packet.

This verifier checks structure, evidence bindings, completeness, and two-person
separation. It deliberately cannot determine whether a tajweed choice is
scientifically correct and never opens a runtime or publication gate.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit/sources/tajweed-riwayat/2026-11-02"
PACKET_PATH = AUDIT_DIR / "WAJH_REVIEW_PACKET.json"
SCHEMA_PATH = AUDIT_DIR / "WAJH_REVIEW_RESPONSE.schema.json"
TEMPLATE_PATH = AUDIT_DIR / "WAJH_REVIEW_RESPONSE_TEMPLATE.json"
GUIDE_PATH = AUDIT_DIR / "WAJH_REVIEW_GUIDE.ar.md"
SCHOLARLY_REVIEW_PATH = ROOT / "audit/SCHOLARLY_REVIEW.md"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ROOT_KEYS = {
    "schemaVersion", "responseId", "updatedAt", "status", "packetBinding",
    "structuralValidationOnly", "scholarlyAccuracyDeterminedBySoftware",
    "publishableAsApproved", "runtimeActivationRequested", "containsQuranText",
    "containsCopiedRuleProse", "containsTrainingExamples", "containsAnnotationSpans",
    "scopeResponses",
}
SCOPE_KEYS = {
    "settingId", "targetRoute", "candidateEdition", "responseStatus", "reviewer",
    "decisionResponses", "selectedProfile", "secondPersonApproval",
}
REVIEWER_KEYS = {
    "name", "qualification", "qualificationEvidenceLocator", "exactRouteExperience",
    "organization", "reviewStartedAt", "reviewCompletedAt", "evidenceLocator",
    "evidenceSha256", "attestationFullReviewNotSampling", "attestationExactRoute",
    "attestationNoCrossScopeInference",
}
DECISION_KEYS = {
    "decisionId", "topicId", "sourceId", "printedPage", "status",
    "selectedPracticeId", "selectedPracticeLabelAr", "sourceLocator", "reviewerNoteAr",
}
PROFILE_KEYS = {
    "status", "wajhId", "wajhLabelAr", "editionId", "editionSha256",
    "editionEvidenceLocator", "countTraditionId", "totalAyahs",
    "surahCountTableSha256", "compatibilityAttestationAr",
}
APPROVAL_KEYS = {
    "status", "approverName", "approverQualification", "approvalDate",
    "reviewedScopePayloadSha256", "evidenceLocator", "evidenceSha256",
}
FORBIDDEN_PAYLOAD_KEYS = {
    "text", "quranText", "ruleText", "ruleProse", "example", "examples", "ayah",
    "ayahs", "annotations", "spans",
}
SCOPE_STATUSES = {
    "PENDING", "IN_PROGRESS", "SUBMITTED_FOR_SECOND_APPROVAL",
    "SCIENTIFICALLY_APPROVED", "CHANGES_REQUESTED", "REJECTED",
}
DECISION_STATUSES = {"PENDING", "APPROVED", "CHANGES_REQUESTED", "REJECTED"}


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"missing {display_path(path)}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON in {display_path(path)}: {exc}") from exc


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"oneOf": [schema, {"type": "null"}]}


def build_expected_schema(packet: dict[str, Any]) -> dict[str, Any]:
    packet_hash = file_sha256(PACKET_PATH)
    token = {"type": "string", "pattern": "^[a-z0-9][a-z0-9._-]{0,127}$"}
    short_text = {"type": "string", "minLength": 1, "maxLength": 1000}
    note = {"type": "string", "minLength": 1, "maxLength": 2000}
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    day = {"type": "string", "format": "date"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://siraj.app/schemas/tajweed-wajh-review-response-v1.json",
        "title": "Siraj non-Hafs wajh scholarly review response",
        "description": (
            "Structural evidence contract only. Schema validity is not scholarly approval "
            "and never authorizes publication or runtime activation."
        ),
        "type": "object",
        "additionalProperties": False,
        "required": sorted(ROOT_KEYS),
        "properties": {
            "schemaVersion": {"const": 1},
            "responseId": token,
            "updatedAt": nullable(day),
            "status": {"enum": ["DRAFT", "IN_PROGRESS", "SCIENTIFIC_REVIEW_COMPLETE"]},
            "packetBinding": {
                "type": "object",
                "additionalProperties": False,
                "required": ["packetId", "packetSha256"],
                "properties": {
                    "packetId": {"const": packet["packetId"]},
                    "packetSha256": {"const": packet_hash},
                },
            },
            "structuralValidationOnly": {"const": True},
            "scholarlyAccuracyDeterminedBySoftware": {"const": False},
            "publishableAsApproved": {"const": False},
            "runtimeActivationRequested": {"const": False},
            "containsQuranText": {"const": False},
            "containsCopiedRuleProse": {"const": False},
            "containsTrainingExamples": {"const": False},
            "containsAnnotationSpans": {"const": False},
            "scopeResponses": {
                "type": "array", "minItems": 3, "maxItems": 3,
                "items": {"$ref": "#/$defs/scopeResponse"},
            },
        },
        "$defs": {
            "reviewer": {
                "type": "object", "additionalProperties": False,
                "required": sorted(REVIEWER_KEYS),
                "properties": {
                    "name": nullable(short_text),
                    "qualification": nullable(note),
                    "qualificationEvidenceLocator": nullable(short_text),
                    "exactRouteExperience": nullable(note),
                    "organization": nullable(short_text),
                    "reviewStartedAt": nullable(day),
                    "reviewCompletedAt": nullable(day),
                    "evidenceLocator": nullable(short_text),
                    "evidenceSha256": nullable(sha),
                    "attestationFullReviewNotSampling": {"type": "boolean"},
                    "attestationExactRoute": {"type": "boolean"},
                    "attestationNoCrossScopeInference": {"type": "boolean"},
                },
            },
            "decisionResponse": {
                "type": "object", "additionalProperties": False,
                "required": sorted(DECISION_KEYS),
                "properties": {
                    "decisionId": token,
                    "topicId": token,
                    "sourceId": token,
                    "printedPage": {"type": "integer", "minimum": 1},
                    "status": {"enum": sorted(DECISION_STATUSES)},
                    "selectedPracticeId": nullable(token),
                    "selectedPracticeLabelAr": nullable(short_text),
                    "sourceLocator": nullable(short_text),
                    "reviewerNoteAr": nullable(note),
                },
            },
            "selectedProfile": {
                "type": "object", "additionalProperties": False,
                "required": sorted(PROFILE_KEYS),
                "properties": {
                    "status": {"enum": ["PENDING", "APPROVED_BY_REVIEWER"]},
                    "wajhId": nullable(token),
                    "wajhLabelAr": nullable(short_text),
                    "editionId": nullable(token),
                    "editionSha256": nullable(sha),
                    "editionEvidenceLocator": nullable(short_text),
                    "countTraditionId": nullable(token),
                    "totalAyahs": nullable({"type": "integer", "minimum": 1, "maximum": 10000}),
                    "surahCountTableSha256": nullable(sha),
                    "compatibilityAttestationAr": nullable(note),
                },
            },
            "secondPersonApproval": {
                "type": "object", "additionalProperties": False,
                "required": sorted(APPROVAL_KEYS),
                "properties": {
                    "status": {"enum": ["NOT_STARTED", "APPROVED", "CHANGES_REQUESTED", "REJECTED"]},
                    "approverName": nullable(short_text),
                    "approverQualification": nullable(note),
                    "approvalDate": nullable(day),
                    "reviewedScopePayloadSha256": nullable(sha),
                    "evidenceLocator": nullable(short_text),
                    "evidenceSha256": nullable(sha),
                },
            },
            "scopeResponse": {
                "type": "object", "additionalProperties": False,
                "required": sorted(SCOPE_KEYS),
                "properties": {
                    "settingId": {"enum": [scope["settingId"] for scope in packet["scopes"]]},
                    "targetRoute": {
                        "type": "object", "additionalProperties": False,
                        "required": ["riwayah", "tariq"],
                        "properties": {"riwayah": token, "tariq": token},
                    },
                    "candidateEdition": token,
                    "responseStatus": {"enum": sorted(SCOPE_STATUSES)},
                    "reviewer": {"$ref": "#/$defs/reviewer"},
                    "decisionResponses": {
                        "type": "array", "minItems": 1,
                        "items": {"$ref": "#/$defs/decisionResponse"},
                    },
                    "selectedProfile": {"$ref": "#/$defs/selectedProfile"},
                    "secondPersonApproval": {"$ref": "#/$defs/secondPersonApproval"},
                },
            },
        },
    }


def blank_reviewer() -> dict[str, Any]:
    return {
        "name": None,
        "qualification": None,
        "qualificationEvidenceLocator": None,
        "exactRouteExperience": None,
        "organization": None,
        "reviewStartedAt": None,
        "reviewCompletedAt": None,
        "evidenceLocator": None,
        "evidenceSha256": None,
        "attestationFullReviewNotSampling": False,
        "attestationExactRoute": False,
        "attestationNoCrossScopeInference": False,
    }


def blank_profile() -> dict[str, Any]:
    return {
        "status": "PENDING",
        "wajhId": None,
        "wajhLabelAr": None,
        "editionId": None,
        "editionSha256": None,
        "editionEvidenceLocator": None,
        "countTraditionId": None,
        "totalAyahs": None,
        "surahCountTableSha256": None,
        "compatibilityAttestationAr": None,
    }


def blank_approval() -> dict[str, Any]:
    return {
        "status": "NOT_STARTED",
        "approverName": None,
        "approverQualification": None,
        "approvalDate": None,
        "reviewedScopePayloadSha256": None,
        "evidenceLocator": None,
        "evidenceSha256": None,
    }


def build_expected_template(packet: dict[str, Any]) -> dict[str, Any]:
    scopes: list[dict[str, Any]] = []
    for scope in packet["scopes"]:
        target = scope["proposedScope"]
        decisions = [
            {
                "decisionId": decision["decisionId"],
                "topicId": decision["topicId"],
                "sourceId": decision["sourceId"],
                "printedPage": decision["printedPage"],
                "status": "PENDING",
                "selectedPracticeId": None,
                "selectedPracticeLabelAr": None,
                "sourceLocator": None,
                "reviewerNoteAr": None,
            }
            for decision in scope["decisionItems"]
        ]
        scopes.append({
            "settingId": scope["settingId"],
            "targetRoute": {"riwayah": target["riwayah"], "tariq": target["tariq"]},
            "candidateEdition": target["edition"],
            "responseStatus": "PENDING",
            "reviewer": blank_reviewer(),
            "decisionResponses": decisions,
            "selectedProfile": blank_profile(),
            "secondPersonApproval": blank_approval(),
        })
    return {
        "schemaVersion": 1,
        "responseId": "siraj-non-hafs-wajh-response-draft-2026-11-02",
        "updatedAt": None,
        "status": "DRAFT",
        "packetBinding": {
            "packetId": packet["packetId"],
            "packetSha256": file_sha256(PACKET_PATH),
        },
        "structuralValidationOnly": True,
        "scholarlyAccuracyDeterminedBySoftware": False,
        "publishableAsApproved": False,
        "runtimeActivationRequested": False,
        "containsQuranText": False,
        "containsCopiedRuleProse": False,
        "containsTrainingExamples": False,
        "containsAnnotationSpans": False,
        "scopeResponses": scopes,
    }


def exact_keys(value: Any, expected: set[str], path: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{path} must be an object")
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    require(not missing and not extra, f"{path} keys differ; missing={missing}, extra={extra}")
    return value


def optional_text(value: Any, path: str, maximum: int = 2000) -> None:
    require(value is None or (
        isinstance(value, str) and value.strip() == value and 1 <= len(value) <= maximum
    ), f"{path} must be null or trimmed non-empty text up to {maximum} characters")


def required_text(value: Any, path: str, maximum: int = 2000) -> None:
    optional_text(value, path, maximum)
    require(value is not None, f"{path} is required")


def optional_token(value: Any, path: str) -> None:
    require(value is None or (isinstance(value, str) and TOKEN_RE.fullmatch(value) is not None),
            f"{path} must be null or a lowercase stable token")


def required_token(value: Any, path: str) -> None:
    optional_token(value, path)
    require(value is not None, f"{path} is required")


def optional_sha(value: Any, path: str) -> None:
    require(value is None or (isinstance(value, str) and SHA_RE.fullmatch(value) is not None),
            f"{path} must be null or a lowercase SHA-256")


def required_sha(value: Any, path: str) -> None:
    optional_sha(value, path)
    require(value is not None, f"{path} is required")


def optional_date(value: Any, path: str) -> None:
    if value is None:
        return
    require(isinstance(value, str) and DATE_RE.fullmatch(value) is not None,
            f"{path} must be null or YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise VerificationError(f"{path} is not a valid calendar date") from exc


def require_blank_object(value: dict[str, Any], expected: dict[str, Any], path: str) -> None:
    require(value == expected, f"{path} must remain completely blank in PENDING state")


def validate_reviewer(reviewer: Any, path: str, complete: bool = False,
                      minimum_identity: bool = False) -> dict[str, Any]:
    reviewer = exact_keys(reviewer, REVIEWER_KEYS, path)
    for key in (
        "name", "qualification", "qualificationEvidenceLocator", "exactRouteExperience",
        "organization", "evidenceLocator",
    ):
        optional_text(reviewer[key], f"{path}.{key}")
    optional_date(reviewer["reviewStartedAt"], f"{path}.reviewStartedAt")
    optional_date(reviewer["reviewCompletedAt"], f"{path}.reviewCompletedAt")
    optional_sha(reviewer["evidenceSha256"], f"{path}.evidenceSha256")
    for key in (
        "attestationFullReviewNotSampling", "attestationExactRoute",
        "attestationNoCrossScopeInference",
    ):
        require(isinstance(reviewer[key], bool), f"{path}.{key} must be boolean")
    if complete:
        for key in (
            "name", "qualification", "qualificationEvidenceLocator", "exactRouteExperience",
            "reviewStartedAt", "reviewCompletedAt", "evidenceLocator",
        ):
            required_text(reviewer[key], f"{path}.{key}")
        required_sha(reviewer["evidenceSha256"], f"{path}.evidenceSha256")
        require(reviewer["attestationFullReviewNotSampling"] is True,
                f"{path} must attest full review, not sampling")
        require(reviewer["attestationExactRoute"] is True,
                f"{path} must attest exact-route competence")
        require(reviewer["attestationNoCrossScopeInference"] is True,
                f"{path} must reject cross-scope inference")
        require(reviewer["reviewCompletedAt"] >= reviewer["reviewStartedAt"],
                f"{path}.reviewCompletedAt precedes reviewStartedAt")
    elif minimum_identity:
        required_text(reviewer["name"], f"{path}.name")
        required_text(reviewer["qualification"], f"{path}.qualification")
        required_text(reviewer["evidenceLocator"], f"{path}.evidenceLocator")
        required_sha(reviewer["evidenceSha256"], f"{path}.evidenceSha256")
    return reviewer


def validate_decision(value: Any, expected: dict[str, Any], path: str) -> None:
    decision = exact_keys(value, DECISION_KEYS, path)
    for key in ("decisionId", "topicId", "sourceId", "printedPage"):
        require(decision[key] == expected[key], f"{path}.{key} does not match packet")
    status = decision["status"]
    require(status in DECISION_STATUSES, f"{path}.status is invalid")
    optional_token(decision["selectedPracticeId"], f"{path}.selectedPracticeId")
    optional_text(decision["selectedPracticeLabelAr"], f"{path}.selectedPracticeLabelAr")
    optional_text(decision["sourceLocator"], f"{path}.sourceLocator")
    optional_text(decision["reviewerNoteAr"], f"{path}.reviewerNoteAr")
    if status == "PENDING":
        for key in ("selectedPracticeId", "selectedPracticeLabelAr", "sourceLocator", "reviewerNoteAr"):
            require(decision[key] is None, f"{path}.{key} must be null while pending")
    elif status == "APPROVED":
        required_token(decision["selectedPracticeId"], f"{path}.selectedPracticeId")
        required_text(decision["selectedPracticeLabelAr"], f"{path}.selectedPracticeLabelAr")
        required_text(decision["sourceLocator"], f"{path}.sourceLocator")
    else:
        required_text(decision["sourceLocator"], f"{path}.sourceLocator")
        required_text(decision["reviewerNoteAr"], f"{path}.reviewerNoteAr")


def validate_profile(value: Any, setting_id: str, packet_scope: dict[str, Any],
                     path: str) -> dict[str, Any]:
    profile = exact_keys(value, PROFILE_KEYS, path)
    require(profile["status"] in {"PENDING", "APPROVED_BY_REVIEWER"},
            f"{path}.status is invalid")
    for key in ("wajhLabelAr", "editionEvidenceLocator", "compatibilityAttestationAr"):
        optional_text(profile[key], f"{path}.{key}")
    for key in ("wajhId", "editionId", "countTraditionId"):
        optional_token(profile[key], f"{path}.{key}")
    for key in ("editionSha256", "surahCountTableSha256"):
        optional_sha(profile[key], f"{path}.{key}")
    total = profile["totalAyahs"]
    require(total is None or (isinstance(total, int) and not isinstance(total, bool)
                              and 1 <= total <= 10000),
            f"{path}.totalAyahs must be null or an integer from 1 to 10000")
    if profile["status"] == "PENDING":
        require_blank_object(profile, blank_profile(), path)
    else:
        for key in ("wajhId", "editionId", "countTraditionId"):
            required_token(profile[key], f"{path}.{key}")
        for key in ("wajhLabelAr", "editionEvidenceLocator", "compatibilityAttestationAr"):
            required_text(profile[key], f"{path}.{key}")
        for key in ("editionSha256", "surahCountTableSha256"):
            required_sha(profile[key], f"{path}.{key}")
        require(profile["wajhId"] != "pending-qualified-review",
                f"{path}.wajhId cannot retain the pending placeholder")
        require(total is not None, f"{path}.totalAyahs is required")
        if setting_id == "duri":
            observed = packet_scope.get("countAudit", {}).get("observedTotals", [])
            allowed = {item for item in observed if item != 6218}
            require(total in allowed,
                    f"{path}.totalAyahs must resolve to documented 6214 or 6217; 6218 is rejected")
    return profile


def reviewed_scope_payload_sha256(scope_response: dict[str, Any]) -> str:
    payload = copy.deepcopy(scope_response)
    payload["responseStatus"] = "SUBMITTED_FOR_SECOND_APPROVAL"
    payload.pop("secondPersonApproval", None)
    return canonical_sha256(payload)


def validate_approval(value: Any, reviewer: dict[str, Any], scope_response: dict[str, Any],
                      path: str) -> dict[str, Any]:
    approval = exact_keys(value, APPROVAL_KEYS, path)
    status = approval["status"]
    require(status in {"NOT_STARTED", "APPROVED", "CHANGES_REQUESTED", "REJECTED"},
            f"{path}.status is invalid")
    for key in ("approverName", "approverQualification", "evidenceLocator"):
        optional_text(approval[key], f"{path}.{key}")
    optional_date(approval["approvalDate"], f"{path}.approvalDate")
    for key in ("reviewedScopePayloadSha256", "evidenceSha256"):
        optional_sha(approval[key], f"{path}.{key}")
    if status == "NOT_STARTED":
        require_blank_object(approval, blank_approval(), path)
    else:
        for key in ("approverName", "approverQualification", "evidenceLocator"):
            required_text(approval[key], f"{path}.{key}")
        required_text(approval["approvalDate"], f"{path}.approvalDate")
        required_sha(approval["reviewedScopePayloadSha256"],
                     f"{path}.reviewedScopePayloadSha256")
        required_sha(approval["evidenceSha256"], f"{path}.evidenceSha256")
        require(reviewer.get("name") is not None, f"{path} requires a named reviewer")
        require(approval["approverName"].casefold() != reviewer["name"].casefold(),
                f"{path}.approverName must be independent from reviewer.name")
        require(approval["reviewedScopePayloadSha256"] ==
                reviewed_scope_payload_sha256(scope_response),
                f"{path}.reviewedScopePayloadSha256 does not bind the submitted scope")
        if reviewer.get("reviewCompletedAt") is not None:
            require(approval["approvalDate"] >= reviewer["reviewCompletedAt"],
                    f"{path}.approvalDate precedes review completion")
    return approval


def verify_payload_boundary(response: dict[str, Any]) -> None:
    encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
    require(len(encoded) <= 1_000_000, "response exceeds the one-megabyte metadata limit")
    stack: list[Any] = [response]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            found = set(value) & FORBIDDEN_PAYLOAD_KEYS
            require(not found, f"response contains forbidden payload keys: {sorted(found)}")
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)


def expected_overall_status(scope_statuses: list[str]) -> str:
    if all(status == "PENDING" for status in scope_statuses):
        return "DRAFT"
    if all(status == "SCIENTIFICALLY_APPROVED" for status in scope_statuses):
        return "SCIENTIFIC_REVIEW_COMPLETE"
    return "IN_PROGRESS"


def validate_response(response: Any, packet: dict[str, Any]) -> dict[str, Any]:
    response = exact_keys(response, ROOT_KEYS, "response")
    require(response["schemaVersion"] == 1, "response.schemaVersion must be 1")
    required_token(response["responseId"], "response.responseId")
    optional_date(response["updatedAt"], "response.updatedAt")
    binding = exact_keys(response["packetBinding"], {"packetId", "packetSha256"},
                         "response.packetBinding")
    require(binding["packetId"] == packet["packetId"], "packetId does not match packet")
    require(binding["packetSha256"] == file_sha256(PACKET_PATH),
            "packetSha256 does not match the committed packet")
    fixed_flags = {
        "structuralValidationOnly": True,
        "scholarlyAccuracyDeterminedBySoftware": False,
        "publishableAsApproved": False,
        "runtimeActivationRequested": False,
        "containsQuranText": False,
        "containsCopiedRuleProse": False,
        "containsTrainingExamples": False,
        "containsAnnotationSpans": False,
    }
    for key, expected in fixed_flags.items():
        require(response[key] is expected, f"response.{key} must remain {expected!r}")
    verify_payload_boundary(response)

    scopes = response["scopeResponses"]
    require(isinstance(scopes, list) and len(scopes) == len(packet["scopes"]),
            "scopeResponses must cover all packet scopes")
    scope_statuses: list[str] = []
    for index, (scope_response, packet_scope) in enumerate(zip(scopes, packet["scopes"])):
        path = f"response.scopeResponses[{index}]"
        scope_response = exact_keys(scope_response, SCOPE_KEYS, path)
        setting_id = packet_scope["settingId"]
        require(scope_response["settingId"] == setting_id,
                f"{path}.settingId order or value does not match packet")
        target = exact_keys(scope_response["targetRoute"], {"riwayah", "tariq"},
                            f"{path}.targetRoute")
        proposed = packet_scope["proposedScope"]
        require(target == {"riwayah": proposed["riwayah"], "tariq": proposed["tariq"]},
                f"{path}.targetRoute does not match packet")
        require(scope_response["candidateEdition"] == proposed["edition"],
                f"{path}.candidateEdition does not match packet")
        status = scope_response["responseStatus"]
        require(status in SCOPE_STATUSES, f"{path}.responseStatus is invalid")
        scope_statuses.append(status)

        complete_review = status in {"SUBMITTED_FOR_SECOND_APPROVAL", "SCIENTIFICALLY_APPROVED"}
        reviewer = validate_reviewer(
            scope_response["reviewer"], f"{path}.reviewer",
            complete=complete_review,
            minimum_identity=status in {"CHANGES_REQUESTED", "REJECTED"},
        )
        decisions = scope_response["decisionResponses"]
        expected_decisions = packet_scope["decisionItems"]
        require(isinstance(decisions, list) and len(decisions) == len(expected_decisions),
                f"{path}.decisionResponses does not cover every packet decision")
        for decision_index, (decision, expected) in enumerate(zip(decisions, expected_decisions)):
            validate_decision(decision, expected,
                              f"{path}.decisionResponses[{decision_index}]")
        profile = validate_profile(scope_response["selectedProfile"], setting_id,
                                   packet_scope, f"{path}.selectedProfile")
        approval = validate_approval(scope_response["secondPersonApproval"], reviewer,
                                     scope_response, f"{path}.secondPersonApproval")

        if status == "PENDING":
            require_blank_object(reviewer, blank_reviewer(), f"{path}.reviewer")
            require(all(item["status"] == "PENDING" for item in decisions),
                    f"{path} pending scope cannot contain decided topics")
            require(profile["status"] == "PENDING", f"{path} pending scope cannot select a profile")
            require(approval["status"] == "NOT_STARTED",
                    f"{path} pending scope cannot contain second approval")
        elif status == "IN_PROGRESS":
            require(approval["status"] == "NOT_STARTED",
                    f"{path} in-progress scope cannot contain second approval")
        elif status == "SUBMITTED_FOR_SECOND_APPROVAL":
            require(all(item["status"] == "APPROVED" for item in decisions),
                    f"{path} submitted scope requires every decision approved")
            require(profile["status"] == "APPROVED_BY_REVIEWER",
                    f"{path} submitted scope requires an approved profile")
            require(approval["status"] == "NOT_STARTED",
                    f"{path} submitted scope must await an independent approver")
        elif status == "SCIENTIFICALLY_APPROVED":
            require(all(item["status"] == "APPROVED" for item in decisions),
                    f"{path} approved scope requires every decision approved")
            require(profile["status"] == "APPROVED_BY_REVIEWER",
                    f"{path} approved scope requires an approved profile")
            require(approval["status"] == "APPROVED",
                    f"{path} requires independent second-person approval")

    expected_status = expected_overall_status(scope_statuses)
    require(response["status"] == expected_status,
            f"response.status must be {expected_status} for current scope states")
    if response["status"] != "DRAFT":
        require(response["updatedAt"] is not None,
                "response.updatedAt is required once review work starts")
    return response


def first_difference(actual: Any, expected: Any, path: str = "$") -> str | None:
    if type(actual) is not type(expected):
        return f"{path}: type {type(actual).__name__} != {type(expected).__name__}"
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            return f"{path}: keys differ"
        for key in expected:
            found = first_difference(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return f"{path}: list length differs"
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            found = first_difference(actual_item, expected_item, f"{path}[{index}]")
            if found:
                return found
        return None
    if actual != expected:
        return f"{path}: {actual!r} != {expected!r}"
    return None


def verify_guide() -> None:
    try:
        guide = GUIDE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise VerificationError("missing wajh review guide") from exc
    for marker in (
        "WAJH_REVIEW_RESPONSE_TEMPLATE.json",
        "SUBMITTED_FOR_SECOND_APPROVAL",
        "reviewedScopePayloadSha256",
        "التحقق البنيوي لا يثبت صحة الاختيار علميًا",
    ):
        require(marker in guide, f"review guide missing response marker: {marker}")


def verify_not_runtime() -> None:
    for base in (
        ROOT / "www", ROOT / "update", ROOT / "windows_app/data",
        ROOT / "mushaf_app/data", ROOT / "tajweed-curricula",
    ):
        if not base.exists():
            continue
        leaked = [
            path for path in base.rglob("*")
            if path.is_file()
            and any(marker in path.name.lower() for marker in ("wajh-review", "wajh_review"))
        ]
        if leaked:
            raise VerificationError(
                f"wajh review response leaked into runtime: {leaked[0].relative_to(ROOT)}"
            )


def verify_ledger() -> None:
    try:
        ledger = SCHOLARLY_REVIEW_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise VerificationError("missing scholarly review ledger") from exc
    entries = {
        path: digest
        for path, digest in re.findall(r"\| `([^`]+)` \| `([0-9a-f]{64})` \|", ledger)
    }
    for path in (SCHEMA_PATH, TEMPLATE_PATH, GUIDE_PATH):
        relative = str(path.relative_to(ROOT))
        require(entries.get(relative) == file_sha256(path),
                f"scholarly ledger hash drift: {relative}")


def verify_committed_contract(packet: dict[str, Any]) -> None:
    expected_schema = build_expected_schema(packet)
    actual_schema = load_json(SCHEMA_PATH)
    difference = first_difference(actual_schema, expected_schema)
    require(difference is None, f"response schema drift: {difference}")
    expected_template = build_expected_template(packet)
    actual_template = load_json(TEMPLATE_PATH)
    difference = first_difference(actual_template, expected_template)
    require(difference is None, f"response template drift: {difference}")
    validate_response(actual_template, packet)
    verify_guide()
    verify_not_runtime()
    verify_ledger()


def write_contract(packet: dict[str, Any]) -> None:
    for path, payload in (
        (SCHEMA_PATH, build_expected_schema(packet)),
        (TEMPLATE_PATH, build_expected_template(packet)),
    ):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true",
                        help="write the deterministic response schema and blank template")
    action.add_argument("--response", type=Path,
                        help="structurally validate a reviewer-filled response")
    parser.add_argument("--print-review-hashes", action="store_true",
                        help="print canonical scope hashes for independent second approval")
    args = parser.parse_args()
    try:
        packet = load_json(PACKET_PATH)
        if args.write:
            write_contract(packet)
            return 0
        verify_committed_contract(packet)
        response_path = args.response.resolve() if args.response else TEMPLATE_PATH
        response = validate_response(load_json(response_path), packet)
        statuses = {item["settingId"]: item["responseStatus"]
                    for item in response["scopeResponses"]}
        print("Verified tajweed wajh review response structure only:")
        print("  scholarly accuracy determined by software: no")
        print("  publishable as approved: no")
        print("  runtime activation requested: no")
        print("  scope states: " + ", ".join(f"{key}={value}" for key, value in statuses.items()))
        if args.print_review_hashes:
            for scope in response["scopeResponses"]:
                if scope["responseStatus"] in {
                    "SUBMITTED_FOR_SECOND_APPROVAL", "SCIENTIFICALLY_APPROVED"
                }:
                    print(f"  {scope['settingId']}: {reviewed_scope_payload_sha256(scope)}")
        return 0
    except (VerificationError, KeyError, TypeError, ValueError) as exc:
        print(f"tajweed wajh review response verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
