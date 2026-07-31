"""Unit contracts for dashboard response-cache fingerprinting and storage."""

import threading
from pathlib import Path

from stockroom.dashboard import cache as dashboard_cache


def test_warehouse_fingerprint_returns_mtime_ns_and_size(tmp_path: Path) -> None:
    """Existing warehouse file yields (st_mtime_ns, st_size)."""
    path = tmp_path / "warehouse.duckdb"
    path.write_bytes(b"duckdb-bytes")
    st = path.stat()
    assert dashboard_cache.warehouse_fingerprint(path) == (st.st_mtime_ns, st.st_size)


def test_warehouse_fingerprint_missing_path_returns_none(tmp_path: Path) -> None:
    """Absent path yields None (caller takes the existing 503 path)."""
    assert dashboard_cache.warehouse_fingerprint(tmp_path / "missing.duckdb") is None


def test_response_cache_miss_then_hit_round_trip() -> None:
    """put then get with the same fingerprint/endpoint/key returns the payload."""
    store = dashboard_cache.ResponseCache()
    fingerprint = (1, 100)
    payload = {"ok": True, "n": 3}
    assert store.get(fingerprint, "overview", ("h",)) is None
    store.put(fingerprint, "overview", ("h",), payload)
    assert store.get(fingerprint, "overview", ("h",)) == payload


def test_response_cache_clears_on_fingerprint_drift() -> None:
    """A get/put under a new fingerprint drops entries from the prior fingerprint."""
    store = dashboard_cache.ResponseCache()
    store.put((1, 100), "overview", (), {"v": 1})
    assert store.get((1, 100), "overview", ()) == {"v": 1}

    store.invalidate_if_stale((2, 100))
    assert store.get((1, 100), "overview", ()) is None

    store.put((1, 100), "overview", (), {"v": 1})
    store.put((2, 200), "overview", (), {"v": 2})
    assert store.get((2, 200), "overview", ()) == {"v": 2}
    # Caller always passes the live fingerprint; an older key is a miss.
    assert store.get((1, 100), "overview", ()) is None


def test_response_cache_isolates_request_keys() -> None:
    """Different endpoint or request keys do not share entries."""
    store = dashboard_cache.ResponseCache()
    fp = (1, 50)
    store.put(fp, "overview", ("claude",), {"a": 1})
    store.put(fp, "overview", ("cursor",), {"a": 2})
    store.put(fp, "sessions", ("claude",), {"a": 3})
    assert store.get(fp, "overview", ("claude",)) == {"a": 1}
    assert store.get(fp, "overview", ("cursor",)) == {"a": 2}
    assert store.get(fp, "sessions", ("claude",)) == {"a": 3}
    assert store.get(fp, "overview", ("codex",)) is None


def test_response_cache_is_thread_safe_for_concurrent_puts() -> None:
    """Concurrent put/get under one fingerprint do not corrupt stored payloads."""
    store = dashboard_cache.ResponseCache()
    fingerprint = (9, 999)
    errors: list[BaseException] = []

    def worker(i: int) -> None:
        try:
            key = ("k", i % 8)
            payload = {"i": i}
            store.put(fingerprint, "overview", key, payload)
            got = store.get(fingerprint, "overview", key)
            assert got is not None
            assert got["i"] % 8 == i % 8
        except BaseException as exc:  # noqa: BLE001 - collect for main thread
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(64)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert not errors
