"""In-process dashboard API response cache keyed by warehouse file freshness.

The dashboard server consults this cache before opening DuckDB. Freshness is
the warehouse file's ``(mtime_ns, size)`` fingerprint — any writer (ingest,
backfill, embed, migrate) that changes the file invalidates the cache without
hooks into those writers.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


Fingerprint = tuple[int, int]
RequestKey = tuple[Any, ...]


def warehouse_fingerprint(path: Path) -> Fingerprint | None:
    """Return ``(mtime_ns, size)`` for ``path``, or ``None`` if it cannot be statted."""
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


def canonical_request_key(
    endpoint: str,
    query: Mapping[str, Sequence[str]],
) -> RequestKey:
    """Return a hashable cache key matching dashboard query-parse semantics.

    Harness filters are sorted; scalar query params use last-wins. Sessions
    keys include the effective limit (capped), offset, and order defaults so
    omitted params share entries with their explicit defaults.
    """
    if endpoint == "session":
        harness = _last(query.get("harness"))
        session_id = _last(query.get("session"))
        return (harness, session_id)

    harnesses = query.get("harness")
    harness_key = tuple(sorted(harnesses)) if harnesses else ()
    since = _last(query.get("since"))
    until = _last(query.get("until"))
    if endpoint != "sessions":
        return (harness_key, since, until)

    limit = 50
    offset = 0
    order = "desc"
    if "limit" in query:
        try:
            limit = int(query["limit"][-1])
        except (ValueError, IndexError):
            limit = 50
        else:
            if limit > 0:
                limit = min(limit, 500)
    if "offset" in query:
        try:
            offset = int(query["offset"][-1])
        except (ValueError, IndexError):
            offset = 0
    if "order" in query and query["order"]:
        order = query["order"][-1].lower()
    return (harness_key, since, until, limit, offset, order)


def _last(values: Sequence[str] | None) -> str | None:
    """Return the last query value, or ``None`` when the key is absent/empty."""
    if not values:
        return None
    return values[-1]


class ResponseCache:
    """Thread-safe store of successful 200 JSON payloads for one warehouse epoch."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fingerprint: Fingerprint | None = None
        self._entries: dict[tuple[str, object], Any] = {}

    def get(
        self,
        fingerprint: Fingerprint,
        endpoint: str,
        request_key: object,
    ) -> Any | None:
        """Return a cached payload, or ``None`` on miss / fingerprint drift."""
        with self._lock:
            self._drop_if_stale(fingerprint)
            if self._fingerprint != fingerprint:
                return None
            return self._entries.get((endpoint, request_key))

    def put(
        self,
        fingerprint: Fingerprint,
        endpoint: str,
        request_key: object,
        payload: Any,
    ) -> None:
        """Store ``payload`` under ``(fingerprint, endpoint, request_key)``.

        Entries from a different fingerprint are dropped (clear-all on drift).
        """
        with self._lock:
            self._drop_if_stale(fingerprint)
            if self._fingerprint != fingerprint:
                self._fingerprint = fingerprint
                self._entries = {}
            self._entries[(endpoint, request_key)] = payload

    def invalidate_if_stale(self, fingerprint: Fingerprint) -> None:
        """Drop all entries when ``fingerprint`` differs from the cached epoch."""
        with self._lock:
            self._drop_if_stale(fingerprint)

    def _drop_if_stale(self, fingerprint: Fingerprint) -> None:
        """Clear the store when ``fingerprint`` is not the current epoch.

        Caller must hold ``_lock``.
        """
        if self._fingerprint is not None and self._fingerprint != fingerprint:
            self._fingerprint = None
            self._entries = {}
