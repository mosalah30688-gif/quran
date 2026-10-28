#!/usr/bin/env python3
"""Lock and validate the rights/attribution ledger for live AlQuran Cloud editions."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "audit" / "sources" / "alquran-editions" / "2026-10-28"
URLS = {
    "editions.json.gz": "https://api.alquran.cloud/v1/edition",
    "alquran-terms.html.gz": "https://alquran.cloud/terms-and-conditions",
    "quran-complex-developers.html.gz": "https://qurancomplex.gov.sa/quran-dev/",
}
TAFSIRS = {
    "ar.muyassar": {
        "display": "التفسير الميسر (مجمع الملك فهد)",
        "author_or_owner": "نخبة من العلماء — مجمع الملك فهد لطباعة المصحف الشريف",
        "rights_basis": "The official Quran Complex developer platform offers this content to developers, researchers, and publishers for use in applications and research.",
        "evidence": "https://qurancomplex.gov.sa/quran-dev/",
    },
    "ar.jalalayn": {
        "display": "تفسير الجلالين",
        "author_or_owner": "جلال الدين المحلي (ت 864هـ) وجلال الدين السيوطي (ت 911هـ)",
        "rights_basis": "Public-domain classical underlying work; displayed on demand from the provider and not bundled.",
    },
    "ar.baghawi": {
        "display": "تفسير البغوي",
        "author_or_owner": "الحسين بن مسعود البغوي (ت 516هـ)",
        "rights_basis": "Public-domain classical underlying work; displayed on demand from the provider and not bundled.",
    },
    "ar.qurtubi": {
        "display": "تفسير القرطبي",
        "author_or_owner": "محمد بن أحمد القرطبي (ت 671هـ)",
        "rights_basis": "Public-domain classical underlying work; displayed on demand from the provider and not bundled.",
    },
    "ar.miqbas": {
        "display": "تنوير المقباس",
        "author_or_owner": "منسوب لابن عباس، جمعه الفيروزآبادي (ت 817هـ)",
        "rights_basis": "Public-domain classical underlying work; displayed on demand from the provider and not bundled. Attribution is not a scholarly endorsement.",
    },
}
TRANSLATIONS = {
    "en.sahih": "Saheeh International",
    "fr.hamidullah": "Muhammad Hamidullah",
    "ur.jalandhry": "Fateh Muhammad Jalandhry",
    "tr.diyanet": "Diyanet Isleri",
}
BLOCKED = {
    "ar.waseet": "modern tafsir; no edition-specific permission was established",
    "id.indonesian": "provider metadata identifies the translator as Unknown, so required attribution cannot be completed",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Siraj-Quran-source-audit/1.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status}: {url}")
        return response.read()


def literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"{name} not found in {path}")


def validate_code() -> None:
    expected_tafsirs = [(key, item["display"]) for key, item in TAFSIRS.items()]
    for app in ("windows_app", "mushaf_app"):
        actual = literal_assignment(ROOT / app / "main.py", "TAFSIR_EDITIONS")
        if actual != expected_tafsirs:
            raise ValueError(f"{app} tafsir list does not match approved ledger")
    expected_translations = [("", "بدون ترجمة")] + [
        (key, {
            "en.sahih": "English — Sahih International",
            "fr.hamidullah": "Français — Hamidullah",
            "ur.jalandhry": "اردو — جالندھری",
            "tr.diyanet": "Türkçe — Diyanet",
        }[key])
        for key in TRANSLATIONS
    ]
    actual_translations = literal_assignment(ROOT / "windows_app" / "main.py", "TRANSLATION_EDITIONS")
    if actual_translations != expected_translations:
        raise ValueError("Windows translation list does not match approved ledger")

    scan_paths = [
        ROOT / "windows_app" / "main.py",
        ROOT / "mushaf_app" / "main.py",
        ROOT / "app.js",
        ROOT / "update" / "app.js",
        ROOT / "www" / "app.js",
        ROOT / "index.html",
        ROOT / "update" / "index.html",
        ROOT / "www" / "index.html",
    ]
    for path in scan_paths:
        text = path.read_text(encoding="utf-8")
        for edition in BLOCKED:
            if edition in text:
                raise ValueError(f"blocked edition {edition} remains in {path.relative_to(ROOT)}")


def build_ledger() -> dict:
    edition_raw = gzip.decompress((SOURCE_DIR / "editions.json.gz").read_bytes())
    terms_raw = gzip.decompress((SOURCE_DIR / "alquran-terms.html.gz").read_bytes())
    complex_raw = gzip.decompress((SOURCE_DIR / "quran-complex-developers.html.gz").read_bytes())
    envelope = json.loads(edition_raw)
    if envelope.get("code") != 200 or envelope.get("status") != "OK":
        raise ValueError("invalid AlQuran Cloud edition snapshot")
    by_id = {item["identifier"]: item for item in envelope.get("data", [])}
    required = set(TAFSIRS) | set(TRANSLATIONS) | set(BLOCKED)
    if not required.issubset(by_id):
        raise ValueError("edition snapshot lacks a reviewed identifier")
    terms_text = terms_raw.decode("utf-8", "replace")
    if "Translations are contributed by their rights-holders or sourced from public-domain editions" not in terms_text:
        raise ValueError("translation rights clause is absent from locked terms")
    if "Last updated: 14 June 2026" not in terms_text:
        raise ValueError("unexpected AlQuran Cloud terms version")
    complex_text = complex_raw.decode("utf-8", "replace")
    for phrase in ("التفسير الميسر للقرآن الكريم", "للمطورين والباحثين ودور النشر", "محتوى تطبيقاتهم"):
        if phrase not in complex_text:
            raise ValueError("Quran Complex developer-use evidence is absent")

    ledger = {
        "schema": 1,
        "reviewed_at": "2026-10-28",
        "delivery": "Live API display; these tafsir and translation corpora are not bundled in Siraj releases.",
        "provider": "AlQuran Cloud / Islamic Network",
        "provider_terms": {
            "url": URLS["alquran-terms.html.gz"],
            "last_updated": "2026-06-14",
            "basis": "Translations are contributed by rights-holders or sourced from public-domain editions; translator attribution is required when republishing.",
        },
        "tafsirs": [],
        "translations": [],
        "blocked": [],
        "snapshots": {},
    }
    for identifier, review in TAFSIRS.items():
        metadata = by_id[identifier]
        if metadata.get("type") != "tafsir" or metadata.get("format") != "text":
            raise ValueError(f"wrong provider metadata for {identifier}")
        ledger["tafsirs"].append({"identifier": identifier, "provider_metadata": metadata, **review})
    for identifier, translator in TRANSLATIONS.items():
        metadata = by_id[identifier]
        if metadata.get("type") != "translation" or metadata.get("format") != "text":
            raise ValueError(f"wrong provider metadata for {identifier}")
        if metadata.get("englishName") != translator:
            raise ValueError(f"translator attribution changed for {identifier}")
        ledger["translations"].append(
            {
                "identifier": identifier,
                "translator_or_publisher": translator,
                "provider_metadata": metadata,
                "rights_basis": "AlQuran Cloud terms section IV: contributed by the rights-holder or sourced from a public-domain edition; displayed with the edition identifier and translator attribution.",
            }
        )
    for identifier, reason in BLOCKED.items():
        ledger["blocked"].append({"identifier": identifier, "provider_metadata": by_id[identifier], "reason": reason})
    for name, url in URLS.items():
        compressed = (SOURCE_DIR / name).read_bytes()
        raw = gzip.decompress(compressed)
        ledger["snapshots"][name] = {
            "url": url,
            "response_bytes": len(raw),
            "response_sha256": sha256(raw),
            "snapshot_bytes": len(compressed),
            "snapshot_sha256": sha256(compressed),
        }
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    if args.refresh:
        for name, url in URLS.items():
            raw = fetch(url, args.timeout)
            # Validate the API JSON before replacing the locked snapshot.
            if name == "editions.json.gz":
                json.loads(raw)
            (SOURCE_DIR / name).write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))

    validate_code()
    ledger = build_ledger()
    output = ROOT / "audit" / "alquran-edition-rights-2026-10-28.json"
    encoded = (json.dumps(ledger, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.verify:
        if not output.is_file() or output.read_bytes() != encoded:
            raise SystemExit("AlQuran edition rights ledger is stale")
    else:
        output.write_bytes(encoded)
    print(f"Approved {len(TAFSIRS)} tafsirs and {len(TRANSLATIONS)} translations; blocked {len(BLOCKED)} ambiguous editions")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
