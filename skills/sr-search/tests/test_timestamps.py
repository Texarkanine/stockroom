"""Tests for ``stockroom.timestamps`` — UTC-at-rest helpers."""

from datetime import datetime, timedelta, timezone

import pytest

from stockroom import timestamps


def test_utc_now_returns_naive_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    """``utc_now`` is timezone-naive and matches a frozen UTC instant."""
    frozen = datetime(2026, 7, 10, 3, 22, 0, tzinfo=timezone.utc)

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            assert tz is timezone.utc
            return frozen

    monkeypatch.setattr(timestamps, "datetime", _FrozenDateTime)
    got = timestamps.utc_now()
    assert got.tzinfo is None
    assert got == datetime(2026, 7, 10, 3, 22, 0)


def test_utc_from_timestamp_returns_naive_utc() -> None:
    """POSIX epoch seconds become naive UTC wall clock."""
    # 2026-07-10 03:22:00 UTC
    epoch = datetime(2026, 7, 10, 3, 22, 0, tzinfo=timezone.utc).timestamp()
    got = timestamps.utc_from_timestamp(epoch)
    assert got.tzinfo is None
    assert got == datetime(2026, 7, 10, 3, 22, 0)


def test_to_utc_naive_converts_aware_offset_to_utc() -> None:
    """Aware stamps convert to UTC before tzinfo is dropped."""
    cdt = timezone(timedelta(hours=-5))
    local = datetime(2026, 7, 9, 22, 22, 0, tzinfo=cdt)
    got = timestamps.to_utc_naive(local)
    assert got.tzinfo is None
    assert got == datetime(2026, 7, 10, 3, 22, 0)


def test_to_utc_naive_leaves_naive_unchanged() -> None:
    """Naive values are already treated as UTC and returned as-is."""
    naive = datetime(2026, 7, 10, 3, 22, 0)
    assert timestamps.to_utc_naive(naive) is naive
