"""Bounded-memory read-only access to Siraj's bundled tafsir text store."""

from __future__ import annotations

from collections import OrderedDict
import json
from pathlib import Path
import sqlite3
import zlib

EXPECTED_SCHEMA = 1
EXPECTED_CODEC = "zlib-json-list-v1"
EXPECTED_EDITIONS = 78


class OfflineTafsirStore:
    """Lazy immutable SQLite reader with a small decompressed-chunk cache.

    ``lookup`` returns ``(True, text_or_none)`` when an edition is represented
    by the bundled store.  ``None`` then means that the source book itself has
    no text for this verse.  ``(False, None)`` means the data pack is missing or
    invalid, allowing callers to use the optional live-source fallback.
    """

    def __init__(self, path: str | Path, cache_chunks: int = 6) -> None:
        self.path = Path(path)
        self.cache_chunks = max(1, int(cache_chunks))
        self._connection: sqlite3.Connection | None = None
        self._editions: frozenset[str] = frozenset()
        self._chunk_size = 0
        self._cache: OrderedDict[tuple[str, int, int], list[str | None]] = OrderedDict()
        self._failed = False

    def _open(self) -> bool:
        if self._connection is not None:
            return True
        if self._failed or not self.path.is_file():
            return False
        connection: sqlite3.Connection | None = None
        try:
            # as_uri handles spaces and Windows drive letters correctly.
            uri = self.path.resolve().as_uri() + "?mode=ro&immutable=1"
            connection = sqlite3.connect(uri, uri=True, check_same_thread=True)
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if (
                connection.execute("PRAGMA user_version").fetchone()[0] != EXPECTED_SCHEMA
                or metadata.get("schema") != str(EXPECTED_SCHEMA)
                or metadata.get("codec") != EXPECTED_CODEC
                or int(metadata.get("edition_count", "0")) != EXPECTED_EDITIONS
            ):
                raise ValueError("unsupported offline tafsir database")
            chunk_size = int(metadata.get("chunk_size", "0"))
            if not 1 <= chunk_size <= 128:
                raise ValueError("invalid offline tafsir chunk size")
            editions = frozenset(row[0] for row in connection.execute("SELECT edition FROM editions"))
            if len(editions) != EXPECTED_EDITIONS:
                raise ValueError("offline tafsir edition index is incomplete")
            self._connection = connection
            self._editions = editions
            self._chunk_size = chunk_size
            return True
        except (OSError, ValueError, sqlite3.Error):
            if connection is not None:
                connection.close()
            self._failed = True
            return False

    @property
    def available(self) -> bool:
        return self._open()

    @property
    def editions(self) -> frozenset[str]:
        self._open()
        return self._editions

    def lookup(self, edition: str, surah: int, ayah: int) -> tuple[bool, str | None]:
        if not self._open() or edition not in self._editions:
            return False, None
        if not 1 <= int(surah) <= 114 or int(ayah) < 1:
            return True, None
        chunk = (int(ayah) - 1) // self._chunk_size
        slot = (int(ayah) - 1) % self._chunk_size
        key = (str(edition), int(surah), chunk)
        values = self._cache.get(key)
        if values is None:
            try:
                row = self._connection.execute(
                    "SELECT payload FROM tafsir_chunks WHERE edition=? AND surah=? AND chunk=?",
                    key,
                ).fetchone()
                if row is None:
                    return True, None
                decoded = json.loads(zlib.decompress(row[0]))
                if not isinstance(decoded, list) or len(decoded) != self._chunk_size:
                    raise ValueError("invalid offline tafsir payload")
                values = decoded
            except (ValueError, TypeError, zlib.error, sqlite3.Error):
                # Corrupt content must not be confused with an intentionally
                # uncovered verse; disable the pack and allow the live fallback.
                self.close()
                self._failed = True
                return False, None
            self._cache[key] = values
            self._cache.move_to_end(key)
            while len(self._cache) > self.cache_chunks:
                self._cache.popitem(last=False)
        else:
            self._cache.move_to_end(key)
        value = values[slot]
        return True, str(value).strip() if value else None

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._editions = frozenset()
        self._chunk_size = 0
        self._cache.clear()
