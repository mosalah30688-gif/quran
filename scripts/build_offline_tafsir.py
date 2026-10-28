#!/usr/bin/env python3
"""Build and verify Siraj's immutable offline tafsir store from locked sources.

The official Quranpedia book dumps are streamed one ayah at a time so even the
largest classical works never need to be expanded fully in memory.  Text is
sanitized to plain Unicode, grouped into small verse chunks, compressed, and
stored in a read-only SQLite database for fast bounded-memory lookup.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
from html.parser import HTMLParser
import html
import json
import os
import re
import sqlite3
import sys
import tempfile
import urllib.request
import zlib
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "mushaf_app" / "data" / "tafsir-catalog.json"
MANIFEST = ROOT / "audit" / "sources" / "quranpedia-tafsir" / "2026-10-28" / "manifest.json"
ALQURAN_LOCK = ROOT / "audit" / "sources" / "alquran-tafsir" / "2026-10-28" / "SOURCE.json"
DEFAULT_QP_SOURCE = Path.home() / ".cache" / "siraj-tafsir" / "quranpedia"
DEFAULT_ALQURAN_SOURCE = Path.home() / ".cache" / "siraj-tafsir" / "alquran"
DEFAULT_OUTPUT = ROOT / "mushaf_app" / "data" / "tafsir-offline.sqlite3"
QP_BASE_URL = "https://quranpedia.net/dumps"
ALQURAN_BASE_URL = "https://api.alquran.cloud/v1/quran"
USER_AGENT = "Siraj-Quran/4.1 offline-tafsir-builder (https://github.com/mosalah30688-gif/quran)"
CHUNK_SIZE = 16
SCHEMA_VERSION = 1
EXPECTED_QP_BOOKS = 73
EXPECTED_ALQURAN_BOOKS = 5
EXPECTED_QURAN_AYAHS = 6236
ALQURAN_EDITIONS = (
    "ar.muyassar",
    "ar.jalalayn",
    "ar.baghawi",
    "ar.qurtubi",
    "ar.miqbas",
)


class _PlainText(HTMLParser):
    BLOCKS = {"address", "blockquote", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in self.BLOCKS:
            self.parts.append("\n")
        if not self.ignored_depth and tag == "li":
            self.parts.append("• ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)

    def result(self) -> str:
        value = "".join(self.parts).replace("\r", "\n").replace("\xa0", " ")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.split("\n")]
        output: list[str] = []
        for line in lines:
            if line:
                output.append(line)
            elif output and output[-1] != "":
                output.append("")
        return "\n".join(output).strip()


def plain_text(value: object) -> str:
    raw = str(value or "")
    parser = _PlainText()
    try:
        parser.feed(raw)
        parser.close()
        return parser.result()
    except (ValueError, AssertionError):
        return html.unescape(re.sub(r"<[^>]+>", " ", raw)).strip()


def sha256_file(path: Path, block: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while data := stream.read(block):
            digest.update(data)
    return digest.hexdigest()


def _array_start(stream, marker: str) -> str:
    buffer = ""
    while marker not in buffer:
        chunk = stream.read(65_536)
        if not chunk:
            raise ValueError(f"JSON envelope has no {marker!r} array")
        buffer += chunk
        if len(buffer) > 2_000_000:
            raise ValueError("JSON envelope header is unexpectedly large")
    return buffer.split(marker, 1)[1]


def iter_json_array(stream, marker: str) -> Iterator[dict]:
    """Stream objects from a named top-level JSON array."""
    decoder = json.JSONDecoder()
    buffer = _array_start(stream, marker)
    eof = False
    while True:
        buffer = buffer.lstrip()
        if buffer.startswith(","):
            buffer = buffer[1:].lstrip()
        if buffer.startswith("]"):
            return
        try:
            value, end = decoder.raw_decode(buffer)
        except json.JSONDecodeError:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                if eof:
                    raise ValueError("truncated JSON array")
                eof = True
            else:
                buffer += chunk
            continue
        if not isinstance(value, dict):
            raise ValueError("JSON array row is not an object")
        yield value
        buffer = buffer[end:]


def download(url: str, output: Path, expected_size: int, expected_sha256: str, timeout: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.is_file() and output.stat().st_size == expected_size and sha256_file(output) == expected_sha256:
        return
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response, temporary.open("wb") as target:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status}: {url}")
        while block := response.read(1024 * 1024):
            target.write(block)
    if temporary.stat().st_size != expected_size or sha256_file(temporary) != expected_sha256:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"source hash/size mismatch: {url}")
    temporary.replace(output)


def quran_ayah_counts() -> dict[int, int]:
    data = json.loads((ROOT / "mushaf_app" / "data" / "surahs.json").read_text(encoding="utf-8"))
    result = {int(item["number"]): int(item["numberOfAyahs"]) for item in data}
    if len(result) != 114 or sum(result.values()) != EXPECTED_QURAN_AYAHS:
        raise ValueError("unexpected bundled Quran verse counts")
    return result


def encode_chunk(values: list[str | None]) -> bytes:
    raw = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return zlib.compress(raw, 9)


def _insert_ordered_book(
    connection: sqlite3.Connection,
    edition: str,
    source: str,
    rows: Iterator[tuple[int, int, str]],
) -> tuple[int, int, int, int]:
    """Compress Quran-ordered plain text while retaining only one chunk in RAM."""
    current_key: tuple[int, int] | None = None
    current_values: list[str | None] = [None] * CHUNK_SIZE
    pending: list[tuple[str, int, int, bytes]] = []
    source_rows = 0
    nonempty = 0
    chunk_count = 0
    text_bytes = 0

    def flush() -> None:
        nonlocal current_values, chunk_count
        if current_key is not None and any(value for value in current_values):
            pending.append((edition, current_key[0], current_key[1], encode_chunk(current_values)))
            chunk_count += 1
            if len(pending) >= 64:
                connection.executemany(
                    "INSERT INTO tafsir_chunks(edition,surah,chunk,payload) VALUES(?,?,?,?)",
                    pending,
                )
                pending.clear()
        current_values = [None] * CHUNK_SIZE

    for surah, ayah, text in rows:
        source_rows += 1
        key = (surah, (ayah - 1) // CHUNK_SIZE)
        if current_key != key:
            flush()
            current_key = key
        normalized = str(text or "").strip()
        if normalized:
            current_values[(ayah - 1) % CHUNK_SIZE] = normalized
            nonempty += 1
            text_bytes += len(normalized.encode("utf-8"))
    flush()
    if pending:
        connection.executemany(
            "INSERT INTO tafsir_chunks(edition,surah,chunk,payload) VALUES(?,?,?,?)",
            pending,
        )
    connection.execute(
        "INSERT INTO editions(edition,source,ayahs,chunks,text_bytes) VALUES(?,?,?,?,?)",
        (edition, source, nonempty, chunk_count, text_bytes),
    )
    return nonempty, chunk_count, text_bytes, source_rows


def insert_book(
    connection: sqlite3.Connection,
    edition: str,
    source: str,
    rows: Iterator[tuple[int, int, str]],
    ayah_counts: dict[int, int],
) -> tuple[int, int, int, int]:
    # Some book dumps follow printed-volume order and revisit earlier surahs.
    # Stage only the current book on disk, then stream it in Quran order. This
    # keeps RAM bounded even for the 933 MB expanded tafsir-book-322 source.
    staging_root = Path.home() / ".cache" / "siraj-tafsir" / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="book-", dir=staging_root) as temporary_dir:
        staging_path = Path(temporary_dir) / "book.sqlite3"
        staging = sqlite3.connect(staging_path)
        staging.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            PRAGMA temp_store=FILE;
            CREATE TABLE ayahs(
                surah INTEGER NOT NULL,
                ayah INTEGER NOT NULL,
                text TEXT NOT NULL,
                PRIMARY KEY(surah,ayah)
            ) WITHOUT ROWID;
            """
        )
        pending: list[tuple[int, int, str]] = []
        try:
            for surah, ayah, text in rows:
                if surah not in ayah_counts or not 1 <= ayah <= ayah_counts[surah]:
                    raise ValueError(f"invalid verse reference for {edition}: {surah}:{ayah}")
                pending.append((surah, ayah, str(text or "").strip()))
                if len(pending) >= 64:
                    staging.executemany("INSERT INTO ayahs(surah,ayah,text) VALUES(?,?,?)", pending)
                    pending.clear()
            if pending:
                staging.executemany("INSERT INTO ayahs(surah,ayah,text) VALUES(?,?,?)", pending)
            staging.commit()
            cursor = staging.execute("SELECT surah,ayah,text FROM ayahs ORDER BY surah,ayah")
            return _insert_ordered_book(connection, edition, source, iter(cursor))
        except sqlite3.IntegrityError as error:
            raise ValueError(f"duplicate verse reference in source for {edition}") from error
        finally:
            staging.close()


def quranpedia_rows(path: Path) -> Iterator[tuple[int, int, str]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for row in iter_json_array(stream, '"ayahs":['):
            segments: list[str] = []
            seen: set[str] = set()
            for item in row.get("content", []):
                text = plain_text(item.get("text", "") if isinstance(item, dict) else "")
                if text and text not in seen:
                    seen.add(text)
                    segments.append(text)
            yield int(row["surah"]), int(row["ayah"]), "\n\n".join(segments)


def alquran_rows(path: Path) -> Iterator[tuple[int, int, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("code") != 200 or not isinstance(payload.get("data", {}).get("surahs"), list):
        raise ValueError(f"invalid AlQuran Cloud tafsir snapshot: {path}")
    for surah in payload["data"]["surahs"]:
        surah_number = int(surah["number"])
        for ayah in surah.get("ayahs", []):
            yield surah_number, int(ayah["numberInSurah"]), plain_text(ayah.get("text", ""))


def selected_quranpedia_sources(catalog_path: Path, manifest_path: Path) -> list[dict]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = {int(item["book_id"]): item for item in catalog["books"]}
    files = {}
    for item in manifest.get("files", []):
        match = re.fullmatch(r"tafsir-book-(\d+)\.json\.gz", str(item.get("name", "")))
        if match and int(match.group(1)) in selected:
            files[int(match.group(1))] = item
    if len(selected) != EXPECTED_QP_BOOKS or set(files) != set(selected):
        raise ValueError("Quranpedia catalog/manifest selected-book mismatch")
    return [
        {
            "edition": f"qp:{book_id}",
            "book_id": book_id,
            **files[book_id],
        }
        for book_id in sorted(selected)
    ]


def prepare_alquran_lock(source_dir: Path, lock_path: Path, timeout: int) -> dict:
    """Refresh the five already-audited edition snapshots and write a reproducible lock."""
    files = {}
    for edition in ALQURAN_EDITIONS:
        path = source_dir / f"{edition}.json"
        request = urllib.request.Request(f"{ALQURAN_BASE_URL}/{edition}", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        payload = json.loads(raw)
        if payload.get("code") != 200 or payload.get("data", {}).get("edition", {}).get("identifier") != edition:
            raise ValueError(f"unexpected AlQuran Cloud edition payload: {edition}")
        files[f"{edition}.json"] = {
            "url": f"{ALQURAN_BASE_URL}/{edition}",
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "edition": payload["data"]["edition"],
        }
    lock = {
        "schema": 1,
        "snapshot": "2026-10-28",
        "source": "https://alquran.cloud",
        "api": "https://api.alquran.cloud/v1",
        "usage_terms": "https://alquran.cloud/terms-and-conditions",
        "files": files,
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lock


def load_alquran_lock(path: Path) -> dict:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock.get("schema") != 1 or lock.get("snapshot") != "2026-10-28":
        raise ValueError("unexpected AlQuran Cloud tafsir lock")
    files = lock.get("files", {})
    if set(files) != {f"{edition}.json" for edition in ALQURAN_EDITIONS}:
        raise ValueError("AlQuran Cloud tafsir lock edition mismatch")
    return lock


def initialize_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA page_size=4096;
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA locking_mode=EXCLUSIVE;
        PRAGMA temp_store=FILE;
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
        CREATE TABLE editions(
            edition TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            ayahs INTEGER NOT NULL,
            chunks INTEGER NOT NULL,
            text_bytes INTEGER NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE tafsir_chunks(
            edition TEXT NOT NULL,
            surah INTEGER NOT NULL,
            chunk INTEGER NOT NULL,
            payload BLOB NOT NULL,
            PRIMARY KEY(edition,surah,chunk)
        ) WITHOUT ROWID;
        """
    )
    return connection


def build(args) -> dict:
    qp_sources = selected_quranpedia_sources(args.catalog, args.manifest)
    alquran_lock = load_alquran_lock(args.alquran_lock)
    ayah_counts = quran_ayah_counts()

    if args.download:
        for item in qp_sources:
            download(
                f"{QP_BASE_URL}/{item['name']}",
                args.quranpedia_source / item["name"],
                int(item["bytes"]),
                item["sha256"],
                args.timeout,
            )
        for filename, item in alquran_lock["files"].items():
            download(item["url"], args.alquran_source / filename, int(item["bytes"]), item["sha256"], args.timeout)

    for item in qp_sources:
        path = args.quranpedia_source / item["name"]
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise ValueError(f"missing or invalid locked source: {path}")
    for filename, item in alquran_lock["files"].items():
        path = args.alquran_source / filename
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise ValueError(f"missing or invalid locked source: {path}")

    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    connection = initialize_database(temporary)
    stats = {
        "quranpedia_ayahs": 0,
        "quranpedia_source_ayahs": 0,
        "alquran_ayahs": 0,
        "alquran_source_ayahs": 0,
        "chunks": 0,
        "text_bytes": 0,
    }
    expected_qp_coverage = {
        item["edition"]: int(item["coverage_ayahs"])
        for item in json.loads(args.catalog.read_text(encoding="utf-8"))["books"]
    }
    try:
        for index, item in enumerate(qp_sources, 1):
            path = args.quranpedia_source / item["name"]
            ayahs, chunks, text_bytes, source_ayahs = insert_book(
                connection, item["edition"], "quranpedia", quranpedia_rows(path), ayah_counts
            )
            expected_source_ayahs = expected_qp_coverage[item["edition"]]
            if source_ayahs != expected_source_ayahs:
                raise ValueError(
                    f"Quranpedia source coverage mismatch for {item['edition']}: "
                    f"{source_ayahs} != {expected_source_ayahs}"
                )
            stats["quranpedia_ayahs"] += ayahs
            stats["quranpedia_source_ayahs"] += source_ayahs
            stats["chunks"] += chunks
            stats["text_bytes"] += text_bytes
            connection.commit()
            print(f"[{index:02d}/{len(qp_sources)}] {item['edition']}: {ayahs} ayahs, {chunks} chunks", flush=True)
        for edition in ALQURAN_EDITIONS:
            path = args.alquran_source / f"{edition}.json"
            ayahs, chunks, text_bytes, source_ayahs = insert_book(
                connection, edition, "alquran.cloud", alquran_rows(path), ayah_counts
            )
            if source_ayahs != EXPECTED_QURAN_AYAHS:
                raise ValueError(f"AlQuran tafsir source is incomplete: {edition} ({source_ayahs})")
            stats["alquran_ayahs"] += ayahs
            stats["alquran_source_ayahs"] += source_ayahs
            stats["chunks"] += chunks
            stats["text_bytes"] += text_bytes
            connection.commit()
            print(f"[offline] {edition}: {ayahs} ayahs, {chunks} chunks", flush=True)

        metadata = {
            "schema": str(SCHEMA_VERSION),
            "codec": "zlib-json-list-v1",
            "chunk_size": str(CHUNK_SIZE),
            "quranpedia_source": "https://quranpedia.net",
            "quranpedia_license": "https://quranpedia.net/dumps/LICENSE.md",
            "quranpedia_attribution": (
                "Classical works are shared heritage; digitization, structuring, verification, "
                "and metadata by Quranpedia.net."
            ),
            "quranpedia_dump_version": "2026-08-10",
            "quranpedia_manifest_snapshot": "2026-10-28",
            "alquran_source": "https://alquran.cloud",
            "alquran_terms": "https://alquran.cloud/terms-and-conditions",
            "alquran_snapshot": "2026-10-28",
            "edition_count": str(EXPECTED_QP_BOOKS + EXPECTED_ALQURAN_BOOKS),
            **{key: str(value) for key, value in stats.items()},
        }
        connection.executemany("INSERT INTO metadata(key,value) VALUES(?,?)", sorted(metadata.items()))
        connection.commit()
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        connection.execute("VACUUM")
        connection.commit()
    finally:
        connection.close()

    temporary.replace(args.output)
    stats["database_bytes"] = args.output.stat().st_size
    stats["database_sha256"] = sha256_file(args.output)
    return stats


def verify(path: Path, catalog_path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"offline tafsir database is missing: {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        if quick != "ok":
            raise ValueError(f"SQLite quick_check failed: {quick}")
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        editions = dict(connection.execute("SELECT edition,ayahs FROM editions"))
        expected_qp = {item["edition"]: int(item["coverage_ayahs"]) for item in json.loads(catalog_path.read_text(encoding="utf-8"))["books"]}
        if set(editions) != set(expected_qp) | set(ALQURAN_EDITIONS):
            raise ValueError("offline tafsir edition set mismatch")
        for edition, source_rows in expected_qp.items():
            if not 0 < editions[edition] <= source_rows:
                raise ValueError(
                    f"invalid non-empty coverage for {edition}: {editions[edition]} / {source_rows}"
                )
        for edition in ALQURAN_EDITIONS:
            if not 0 < editions[edition] <= EXPECTED_QURAN_AYAHS:
                raise ValueError(f"AlQuran tafsir has invalid coverage: {edition} ({editions[edition]})")
        if int(metadata.get("quranpedia_source_ayahs", "0")) != sum(expected_qp.values()):
            raise ValueError("Quranpedia source-row total mismatch")
        if int(metadata.get("alquran_source_ayahs", "0")) != EXPECTED_QURAN_AYAHS * len(ALQURAN_EDITIONS):
            raise ValueError("AlQuran source-row total mismatch")
        expected_chunks = int(metadata["chunks"])
        actual_chunks = connection.execute("SELECT COUNT(*) FROM tafsir_chunks").fetchone()[0]
        if actual_chunks != expected_chunks:
            raise ValueError("offline tafsir chunk count mismatch")
        # Decode every compressed record, validating the complete packaged text store.
        nonempty = 0
        for edition, surah, chunk, payload in connection.execute(
            "SELECT edition,surah,chunk,payload FROM tafsir_chunks ORDER BY edition,surah,chunk"
        ):
            values = json.loads(zlib.decompress(payload))
            if not isinstance(values, list) or len(values) != CHUNK_SIZE:
                raise ValueError(f"bad tafsir chunk: {edition} {surah}:{chunk}")
            nonempty += sum(bool(value) for value in values)
        if nonempty != sum(editions.values()):
            raise ValueError(f"offline tafsir ayah count mismatch: {nonempty} != {sum(editions.values())}")
    finally:
        connection.close()
    return {
        "editions": len(editions),
        "ayahs": sum(editions.values()),
        "chunks": actual_chunks,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--alquran-lock", type=Path, default=ALQURAN_LOCK)
    parser.add_argument("--quranpedia-source", type=Path, default=DEFAULT_QP_SOURCE)
    parser.add_argument("--alquran-source", type=Path, default=DEFAULT_ALQURAN_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--refresh-alquran-lock", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    for name in ("catalog", "manifest", "alquran_lock", "quranpedia_source", "alquran_source", "output"):
        setattr(args, name, getattr(args, name).expanduser().resolve())
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.refresh_alquran_lock:
        prepare_alquran_lock(args.alquran_source, args.alquran_lock, args.timeout)
    if args.verify:
        stats = verify(args.output, args.catalog)
    else:
        stats = build(args)
        stats.update(verify(args.output, args.catalog))
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
