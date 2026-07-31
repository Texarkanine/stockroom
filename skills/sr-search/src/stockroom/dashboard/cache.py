"""In-process dashboard API response cache keyed by warehouse file freshness.

The dashboard server consults this cache before opening DuckDB. Freshness is
the warehouse file's ``(mtime_ns, size)`` fingerprint — any writer (ingest,
backfill, embed, migrate) that changes the file invalidates the cache without
hooks into those writers.

Within one fingerprint epoch, entries are kept under a hard max-entry LRU so
a long-lived process cannot grow the cache without bound while the user
explores.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


Fingerprint = tuple[int, int]
RequestKey = tuple[Any, ...]

#: Default cap on cached JSON responses per warehouse fingerprint epoch.
DEFAULT_MAX_ENTRIES = 64


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
    """Thread-safe LRU store of successful 200 JSON payloads for one warehouse epoch."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        """Create an empty cache capped at ``max_entries`` responses."""
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._fingerprint: Fingerprint | None = None
        self._entries: OrderedDict[tuple[str, RequestKey], Any] = OrderedDict()

    def get(
        self,
        fingerprint: Fingerprint,
        endpoint: str,
        request_key: RequestKey,
    ) -> Any | None:
        """Return a cached payload, or ``None`` on miss / fingerprint drift.

        A hit moves the entry to most-recently-used.
        """
        with self._lock:
            self._drop_if_stale(fingerprint)
            if self._fingerprint != fingerprint:
                return None
            key = (endpoint, request_key)
            if key not in self._entries:
                return None
            self._entries.move_to_end(key)
            return self._entries[key]

    def put(
        self,
        fingerprint: Fingerprint,
        endpoint: str,
        request_key: RequestKey,
        payload: Any,
    ) -> None:
        """Store ``payload`` under ``(fingerprint, endpoint, request_key)``.

        Entries from a different fingerprint are dropped (clear-all on drift).
        When over ``max_entries``, the least-recently-used entry is evicted.
        """
        with self._lock:
            self._drop_if_stale(fingerprint)
            if self._fingerprint != fingerprint:
                self._fingerprint = fingerprint
                self._entries = OrderedDict()
            key = (endpoint, request_key)
            self._entries[key] = payload
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

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
            self._entries = OrderedDict()
