"""UTC timestamp helpers for warehouse storage.

DuckDB ``TIMESTAMP`` columns are timezone-naive. Stockroom's contract is that
every persisted timestamp is **UTC wall clock** (tzinfo stripped after
conversion to UTC). Clients that display times are responsible for rendering
into a timezone.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current time as a naive-UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_from_timestamp(epoch_seconds: float) -> datetime:
    """Convert a POSIX timestamp to a naive-UTC datetime."""
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).replace(tzinfo=None)


def to_utc_naive(value: datetime) -> datetime:
    """Return ``value`` as naive UTC.

    Aware datetimes are converted to UTC before tzinfo is dropped. Naive
    datetimes are treated as already-UTC and returned unchanged.
    """
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value
