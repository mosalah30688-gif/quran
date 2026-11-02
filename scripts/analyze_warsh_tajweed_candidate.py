#!/usr/bin/env python3
"""Audit a quarantined Warsh/al-Azraq tajweed candidate without publishing it.

The input archive is never copied into the project. The output contains only
counts, hashes, references and gate results; it deliberately excludes Quran
text and annotation payloads. Passing these technical checks is not scholarly
approval and does not make the candidate publishable.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ARCHIVE_SHA256 = "0898c80ad1325a36031a24f45a2ca6c1649c051c94e88de89cc594c70273b4f8"
EXPECTED_ARCHIVE_BYTES = 2_642_177
EXPECTED_VERSION = "warsh-tajweed-v1"
EXPECTED_PAGES = 604
EXPECTED_AYAHS = 6_214
EXPECTED_TARIQ = "al_azraq"
TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_project_warsh() -> tuple[dict[tuple[int, int], tuple[int, str]], str]:
    path = ROOT / "quran-riwayat.json"
    raw = path.read_bytes()
    payload = json.loads(raw)
    rows = payload.get("riwayat", {}).get("warsh")
    require(isinstance(rows, list) and len(rows) == EXPECTED_AYAHS,
            "project Warsh text must contain 6,214 records")
    result: dict[tuple[int, int], tuple[int, str]] = {}
    for index, row in enumerate(rows):
        require(isinstance(row, list) and len(row) >= 4,
                f"invalid project Warsh row {index}")
        key = (int(row[0]), int(row[1]))
        require(key not in result, f"duplicate project Warsh reference {key}")
        result[key] = (int(row[2]), str(row[3]))
    return result, sha256(raw)


def normalized(text: str, *, remove_layout_marks: bool = False) -> str:
    value = unicodedata.normalize("NFC", text)
    if remove_layout_marks:
        value = value.replace("۞", "").replace("ـ", "")
    return " ".join(value.split())


def safe_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    members: dict[str, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        require(not path.is_absolute() and ".." not in path.parts,
                f"unsafe archive member {info.filename}")
        require(info.filename not in members, f"duplicate archive member {info.filename}")
        members[info.filename] = info
    return members


def read_json(archive: zipfile.ZipFile, name: str) -> tuple[Any, bytes]:
    try:
        raw = archive.read(name)
    except KeyError as exc:
        raise AuditError(f"missing archive member {name}") from exc
    try:
        return json.loads(raw), raw
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid JSON in {name}: {exc}") from exc


def analyze(path: Path) -> dict[str, Any]:
    raw_archive = path.read_bytes()
    require(len(raw_archive) == EXPECTED_ARCHIVE_BYTES,
            f"archive size drift: {len(raw_archive)}")
    require(sha256(raw_archive) == EXPECTED_ARCHIVE_SHA256,
            "archive SHA-256 does not match the pinned release manifest")
    project, project_sha = load_project_warsh()

    with zipfile.ZipFile(path) as archive:
        members = safe_members(archive)
        manifest, _ = read_json(archive, "manifest.json")
        require(manifest.get("format") == 1, "unsupported candidate format")
        require(manifest.get("version") == EXPECTED_VERSION, "candidate version drift")
        require(manifest.get("riwayah") == "warsh", "candidate is not Warsh")
        require(manifest.get("tariq") == EXPECTED_TARIQ, "candidate is not al-Azraq")
        require(manifest.get("page_count") == EXPECTED_PAGES, "candidate page count drift")

        file_entries = manifest.get("files")
        require(isinstance(file_entries, list) and len(file_entries) == 605,
                "candidate manifest must lock 604 pages and one font")
        declared_names: set[str] = set()
        locked_files = 0
        for index, entry in enumerate(file_entries):
            require(isinstance(entry, dict), f"invalid manifest file entry {index}")
            name = entry.get("name")
            require(isinstance(name, str) and name in members,
                    f"manifest references missing member {name}")
            require(name not in declared_names, f"duplicate manifest file entry {name}")
            declared_names.add(name)
            content = archive.read(name)
            require(entry.get("size") == len(content), f"size drift in {name}")
            require(entry.get("sha256") == sha256(content), f"hash drift in {name}")
            locked_files += 1

        ayahs: dict[tuple[int, int], dict[str, Any]] = {}
        ayah_pages: dict[tuple[int, int], set[int]] = collections.defaultdict(set)
        duplicate_refs: list[dict[str, Any]] = []
        rule_occurrences: collections.Counter[str] = collections.Counter()
        span_count = 0
        word_span_count = 0
        text_hash_failures = 0
        invalid_spans = 0

        for page_number in range(1, EXPECTED_PAGES + 1):
            name = f"pages/p{page_number}.json"
            page, _ = read_json(archive, name)
            require(page.get("format") == 1 and page.get("page") == page_number,
                    f"page identity drift in {name}")
            page_ayahs = page.get("ayahs")
            require(isinstance(page_ayahs, dict), f"missing ayahs in {name}")
            for reference, record in page_ayahs.items():
                require(isinstance(reference, str) and re.fullmatch(r"\d{1,3}:\d{1,3}", reference),
                        f"invalid ayah reference in {name}")
                key = tuple(map(int, reference.split(":")))
                require(1 <= key[0] <= 114 and key[1] >= 1,
                        f"invalid ayah coordinates {reference}")
                require(isinstance(record, dict), f"invalid ayah record {reference}")
                text = record.get("text")
                require(isinstance(text, str) and text, f"empty ayah text {reference}")
                if record.get("text_sha256") != sha256(text.encode("utf-8")):
                    text_hash_failures += 1
                if key in ayahs:
                    require(ayahs[key] == record,
                            f"non-identical repeated ayah {reference} across pages")
                    duplicate_refs.append({
                        "reference": reference,
                        "pages": sorted(ayah_pages[key] | {page_number}),
                    })
                else:
                    ayahs[key] = record
                ayah_pages[key].add(page_number)

                spans = record.get("spans")
                require(isinstance(spans, list), f"invalid spans for {reference}")
                for span in spans:
                    span_count += 1
                    if not (isinstance(span, list) and len(span) == 3
                            and isinstance(span[0], int) and isinstance(span[1], int)
                            and 0 <= span[0] < span[1] <= len(text)
                            and isinstance(span[2], list) and span[2]):
                        invalid_spans += 1
                        continue
                    for rule_id in span[2]:
                        require(isinstance(rule_id, str) and TOKEN_RE.fullmatch(rule_id) is not None,
                                f"invalid rule identifier {rule_id!r}")
                        rule_occurrences[rule_id] += 1

                words = record.get("words")
                require(isinstance(words, list), f"invalid words for {reference}")
                for word in words:
                    require(isinstance(word, list) and len(word) == 2
                            and isinstance(word[0], str) and isinstance(word[1], list),
                            f"invalid word mapping for {reference}")
                    for word_span in word[1]:
                        word_span_count += 1
                        require(isinstance(word_span, list) and len(word_span) == 2
                                and isinstance(word_span[0], int) and isinstance(word_span[1], int)
                                and 0 <= word_span[0] < word_span[1] <= len(text),
                                f"invalid word span for {reference}")

    require(len(ayahs) == EXPECTED_AYAHS, f"unique candidate ayah count is {len(ayahs)}")
    require(set(ayahs) == set(project), "candidate/project reference sets differ")

    exact = 0
    nfc = 0
    layout_normalized = 0
    page_matches = 0
    for key, (project_page, project_text) in project.items():
        candidate_text = ayahs[key]["text"]
        exact += project_text == candidate_text
        nfc += normalized(project_text) == normalized(candidate_text)
        layout_normalized += normalized(project_text, remove_layout_marks=True) == normalized(
            candidate_text, remove_layout_marks=True)
        page_matches += project_page in ayah_pages[key]

    unresolved_text = EXPECTED_AYAHS - layout_normalized
    report = {
        "schemaVersion": 1,
        "analysisDate": "2026-11-02",
        "candidateId": "warsh-al-azraq-qud-generated-v1",
        "scope": {
            "riwayah": "warsh-an-nafi",
            "tariq": "al-azraq",
            "wajh": "generator-default-unreviewed",
            "edition": "king-fahd-warsh-v2-candidate",
        },
        "artifact": {
            "url": "https://github.com/Farouk-Idhemmou/QuranVersion/releases/download/warsh-tajweed-v1/warsh-tajweed-v1.zip",
            "bytes": len(raw_archive),
            "sha256": sha256(raw_archive),
            "releaseManifest": "https://raw.githubusercontent.com/Farouk-Idhemmou/QuranVersion/aedcede27206fd4d6e3e4ee76dc3ed887e10bf18/manifests/warsh-tajweed-v1.json",
        },
        "generator": {
            "name": "quranic-phonemizer",
            "version": "3.0.5",
            "commit": "375d304f09408cedfecd3e3bb083a6b0716a00c4",
            "codeLicense": "MIT",
            "corpusSourceSha256": "c6017e688cc599d88f6fdb1a19cafc9c51d024b3530955f1a878f17d26b9bcbc",
            "corpusUpstreamUrlRecorded": False,
            "corpusRedistributionLicenseRecorded": False,
        },
        "technicalChecks": {
            "manifestLockedFiles": locked_files,
            "pages": EXPECTED_PAGES,
            "uniqueAyahs": len(ayahs),
            "identicalCrossPageDuplicates": duplicate_refs,
            "textHashFailures": text_hash_failures,
            "invalidAnnotationSpans": invalid_spans,
            "annotationSpans": span_count,
            "ruleAssignments": sum(rule_occurrences.values()),
            "ruleIdentifiers": len(rule_occurrences),
            "wordSpans": word_span_count,
        },
        "ruleOccurrences": dict(sorted(rule_occurrences.items())),
        "projectBinding": {
            "asset": "quran-riwayat.json",
            "dataset": "warsh",
            "sha256": project_sha,
            "records": len(project),
            "exactTextMatches": exact,
            "nfcTextMatches": nfc,
            "layoutMarkNormalizedMatches": layout_normalized,
            "unresolvedTextDifferences": unresolved_text,
            "pageMatches": page_matches,
            "pageDifferences": EXPECTED_AYAHS - page_matches,
            "safeAutomaticOffsetTransfer": False,
        },
        "releaseGate": {
            "technicalIntegrity": "PASS",
            "independentCorpusLicense": "FAIL",
            "exactProjectTextBinding": "FAIL",
            "qualifiedWarshReview": "FAIL",
            "secondPersonReleaseApproval": "FAIL",
            "status": "QUARANTINED_NOT_PUBLISHABLE",
            "publishableAsApproved": False,
        },
        "notesAr": [
            "التحقق تقني فقط ولا يمثل اعتمادًا علميًا.",
            "المولد يحدد ورش من طريق الأزرق، لكن مصدر corpus الأصلي لا يسجل رابطًا أو ترخيص إعادة توزيع.",
            "تبقى فروق نصية تمنع نقل الإزاحات تلقائيًا إلى نص سراج.",
            "يلزم فحص بصري كامل أو منهج عينة موثق من شيخ مؤهل في ورش، ثم اعتماد شخص ثانٍ.",
        ],
    }
    require(text_hash_failures == 0 and invalid_spans == 0,
            "candidate internal integrity checks failed")
    require(unresolved_text > 0, "unexpectedly safe binding; review the gate assumptions")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="downloaded warsh-tajweed-v1.zip")
    parser.add_argument("--output", type=Path, help="write deterministic metadata-only JSON report")
    args = parser.parse_args()
    try:
        report = analyze(args.archive)
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (AuditError, OSError, zipfile.BadZipFile) as exc:
        print(f"Warsh candidate audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
