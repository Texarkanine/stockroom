"""HTTP contracts for the loopback-only stockroom dashboard server."""

import json
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import duckdb
import pytest

from stockroom import ingest, migrate, warehouse
from stockroom.dashboard import metrics, recovery
from stockroom.dashboard import server as dashboard_server
from stockroom.migrations import discover


@contextmanager
def _running_server(
    *,
    open_warehouse: Callable[..., duckdb.DuckDBPyConnection] | None = None,
) -> Iterator[tuple[dashboard_server.HTTPServer, str]]:
    httpd = dashboard_server.serve(0, open_warehouse=open_warehouse)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address
        yield httpd, f"http://{host}:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _get(url: str) -> tuple[int, str, bytes]:
    try:
        with urlopen(url, timeout=5) as response:
            return (
                response.status,
                response.headers.get("Content-Type", ""),
                response.read(),
            )
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read()


def _json_get(url: str) -> tuple[int, dict | list]:
    status, content_type, body = _get(url)
    assert content_type.startswith("application/json")
    return status, json.loads(body)


def test_every_api_route_returns_json_from_current_warehouse(
    warehouse_home: Path,
) -> None:
    """The endpoint registry is fully routable over a current warehouse."""
    warehouse.open(read_only=False).close()
    with _running_server() as (httpd, base):
        assert httpd.server_address[0] == "127.0.0.1"
        for endpoint in metrics.ENDPOINTS:
            if endpoint == "session":
                status, payload = _json_get(
                    f"{base}/api/session?harness=cursor&session=missing"
                )
                assert status == 404
                assert payload["error"] == "not found"
                continue
            status, payload = _json_get(f"{base}/api/{endpoint}")
            assert status == 200
            assert payload is not None
        _, overview = _json_get(f"{base}/api/overview")
        assert overview == {
            "last_sync": None,
            "per_harness": {},
            "distinct_projects": 0,
            "prev_distinct_projects": 0,
        }


def test_unknown_api_and_bad_parameters_return_clean_client_errors(
    warehouse_home: Path,
) -> None:
    """Unknown routes are 404; malformed windows and limits are 400 JSON."""
    warehouse.open(read_only=False).close()
    with _running_server() as (_httpd, base):
        status, payload = _json_get(f"{base}/api/not-real")
        assert status == 404
        assert payload["error"] == "not found"

        for path, parameter in [
            ("/api/overview?since=nope", "since"),
            ("/api/overview?until=nope", "until"),
            ("/api/sessions?limit=nope", "limit"),
            ("/api/sessions?limit=-1", "limit"),
        ]:
            status, payload = _json_get(base + path)
            assert status == 400
            assert parameter in payload["error"]


def test_partial_bounds_preserve_endpoint_specific_defaults(
    warehouse_home: Path,
) -> None:
    """Until-only trends keep 14d/12w; sessions remain open-ended recent-N."""
    con = warehouse.open(read_only=False)
    try:
        for session_id, activity in [
            ("old", datetime(2025, 1, 1)),
            ("recent", datetime(2026, 1, 31)),
        ]:
            con.execute(
                "INSERT INTO sessions "
                "(harness, session_id, project_id, source_path, is_subagent, "
                "source_mtime) VALUES ('cursor', ?, 'p', ?, false, ?)",
                [session_id, f"/tmp/{session_id}.jsonl", activity],
            )
            con.execute(
                "INSERT INTO messages "
                "(harness, session_id, message_id, ordinal, role, text) "
                "VALUES ('cursor', ?, ?, 0, 'user', 'hello')",
                [session_id, f"{session_id}#0"],
            )
    finally:
        con.close()

    with _running_server() as (_httpd, base):
        status, trends = _json_get(f"{base}/api/trends?until=2026-02-01")
        assert status == 200
        assert len(trends["daily"]["labels"]) == 14
        assert len(trends["weekly"]["labels"]) == 12

        status, sessions = _json_get(f"{base}/api/sessions?until=2026-02-01")
        assert status == 200
        assert sessions["total"] == 2
        assert [row["started"] for row in sessions["sessions"]] == [
            "2026-01-31T00:00:00Z",
            "2025-01-01T00:00:00Z",
        ]


def test_repeated_harness_limit_cap_and_short_timeout_are_wired(
    warehouse_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP preserves repeated filters, clamps positive limit, and opens with 2s backoff."""
    captured: dict[str, object] = {}

    class FakeConnection:
        def close(self) -> None:
            captured["closed"] = True

    def _open(**kwargs):
        captured["open_kwargs"] = kwargs
        return FakeConnection()

    def _sessions(_con, harnesses, since, until, *, limit, offset=0, order="desc"):
        return {
            "harnesses": harnesses,
            "since": since,
            "until": until,
            "limit": limit,
            "offset": offset,
            "order": order,
        }

    monkeypatch.setitem(metrics.ENDPOINTS, "sessions", _sessions)
    with _running_server(open_warehouse=_open) as (_httpd, base):
        status, payload = _json_get(
            f"{base}/api/sessions?harness=cursor&harness=claude&limit=501"
        )
    assert status == 200
    assert payload["harnesses"] == ["cursor", "claude"]
    assert payload["limit"] == 500
    assert payload["offset"] == 0
    assert payload["order"] == "desc"
    assert captured == {
        "open_kwargs": {"read_only": True, "timeout": 2.0},
        "closed": True,
    }


def test_sessions_accepts_offset_order_and_show_all_limit(
    warehouse_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sessions API accepts offset/order and limit=0 (show-all, not clamped)."""
    captured: dict[str, object] = {}

    class FakeConnection:
        def close(self) -> None:
            pass

    def _sessions(_con, harnesses, since, until, *, limit, offset=0, order="desc"):
        captured["args"] = {
            "limit": limit,
            "offset": offset,
            "order": order,
        }
        return {"total": 0, "sessions": []}

    monkeypatch.setitem(metrics.ENDPOINTS, "sessions", _sessions)
    with _running_server(open_warehouse=lambda **_: FakeConnection()) as (
        _httpd,
        base,
    ):
        status, payload = _json_get(f"{base}/api/sessions?limit=0&offset=10&order=asc")
        assert status == 200
        assert payload == {"total": 0, "sessions": []}
        assert captured["args"] == {"limit": 0, "offset": 10, "order": "asc"}

        status, err = _json_get(f"{base}/api/sessions?order=sideways")
        assert status == 400
        assert "order" in err["error"]

        status, err = _json_get(f"{base}/api/sessions?offset=-1")
        assert status == 400
        assert "offset" in err["error"]


def test_sessions_ends_endpoint_returns_panel_envelope(
    warehouse_home: Path,
) -> None:
    """GET /api/sessions_ends returns total + newest/oldest for the panel."""
    con = warehouse.open(read_only=False)
    try:
        for i in range(3):
            session_id = f"s{i}"
            activity = datetime(2026, 1, 1 + i)
            con.execute(
                "INSERT INTO sessions "
                "(harness, session_id, project_id, source_path, is_subagent, "
                "source_mtime) VALUES ('cursor', ?, 'p', ?, false, ?)",
                [session_id, f"/tmp/{session_id}.jsonl", activity],
            )
    finally:
        con.close()

    with _running_server() as (_httpd, base):
        status, payload = _json_get(f"{base}/api/sessions_ends")
    assert status == 200
    assert payload["total"] == 3
    assert [row["session_id"] for row in payload["newest"]] == ["s2", "s1", "s0"]
    assert payload["oldest"] == []


def test_missing_stale_and_busy_warehouses_return_actionable_503(
    warehouse_home: Path,
) -> None:
    """Every expected warehouse refusal has stable error/action JSON."""
    with _running_server() as (_httpd, base):
        status, payload = _json_get(f"{base}/api/overview")
        assert status == 503
        assert set(payload) == {"error", "action"}
        assert "stockroom ingest" in payload["action"]

    path = warehouse.warehouse_path()
    con = duckdb.connect(str(path))
    migration = next(item for item in discover() if item.version == 1)
    try:
        con.execute(migration.path.read_text(encoding="utf-8"))
        migrate.ensure_schema_version_table(con)
        con.execute(
            f"INSERT INTO {migrate.SCHEMA_VERSION_TABLE} (version, filename) "
            "VALUES (1, ?)",
            [migration.path.name],
        )
    finally:
        con.close()
    with _running_server() as (_httpd, base):
        status, payload = _json_get(f"{base}/api/overview")
        assert status == 503
        assert set(payload) == {"error", "action"}
        assert "stockroom migrate" in payload["action"]
    con = duckdb.connect(str(path), read_only=True)
    try:
        assert migrate.current_version(con) == 1
    finally:
        con.close()

    def _busy(**_kwargs):
        raise warehouse.WarehouseBusyError("busy")

    with _running_server(open_warehouse=_busy) as (_httpd, base):
        status, payload = _json_get(f"{base}/api/overview")
        assert status == 503
        assert set(payload) == {"error", "action"}
        assert "retry" in payload["action"]


def test_static_root_and_traversal_guard(warehouse_home: Path) -> None:
    """The root serves packaged HTML and encoded traversal cannot escape it."""
    packaged_index = (
        Path(dashboard_server.__file__).resolve().parent / "static" / "index.html"
    ).read_bytes()
    with _running_server() as (_httpd, base):
        status, content_type, body = _get(f"{base}/")
        assert status == 200
        assert content_type.startswith("text/html")
        assert body == packaged_index

        status, content_type, body = _get(f"{base}/%2e%2e/%2e%2e/etc/passwd")
        assert status == 404
        assert content_type.startswith("text/html")
        # Same in-memory diagnostic page as other static misses — not a prose pin.
        assert body == recovery.render_diagnostic_html().encode("utf-8")
        assert b"root:" not in body  # did not escape to /etc/passwd


def test_dashboard_javascript_assets_have_browser_mime_types(
    warehouse_home: Path,
) -> None:
    """Authored modules and vendored Chart.js are served as JavaScript."""
    with _running_server() as (_httpd, base):
        for asset in [
            "dashboard.mjs",
            "dashboard-core.mjs",
            "dashboard-data.mjs",
            "dashboard-session.mjs",
            "chart-4.5.1.umd.min.js",
            "markdown-it-14.1.0.min.js",
        ]:
            status, content_type, body = _get(f"{base}/{asset}")
            assert status == 200, asset
            assert content_type.split(";", 1)[0] in {
                "application/javascript",
                "text/javascript",
            }
            assert body


def test_unexpected_exception_returns_clean_json_500(
    warehouse_home: Path,
) -> None:
    """Unexpected failures never leak tracebacks into the HTTP response."""

    def _explode(**_kwargs):
        raise RuntimeError("private detail")

    with _running_server(open_warehouse=_explode) as (_httpd, base):
        status, payload = _json_get(f"{base}/api/overview")
        assert status == 500
        assert payload == {"error": "internal server error"}
        assert "private detail" not in json.dumps(payload)
        assert "Traceback" not in json.dumps(payload)


def test_session_api_returns_detail_and_client_errors(
    warehouse_home: Path,
) -> None:
    """GET /api/session requires harness+session; maps missing rows to 404."""
    con = warehouse.open(read_only=False)
    try:
        con.execute(
            "INSERT INTO sessions "
            "(harness, session_id, project_id, cwd, source_path, is_subagent, "
            "source_mtime) VALUES "
            "('cursor', 'api-sess', 'p', '/tmp/proj', '/tmp/api-sess.jsonl', "
            "false, ?)",
            [datetime(2026, 3, 1, 10)],
        )
        con.execute(
            "INSERT INTO messages "
            "(harness, session_id, message_id, ordinal, role, text) "
            "VALUES ('cursor', 'api-sess', 'api-sess#0', 0, 'user', 'hello')"
        )
    finally:
        con.close()

    with _running_server() as (_httpd, base):
        status, payload = _json_get(
            f"{base}/api/session?harness=cursor&session=api-sess"
        )
        assert status == 200
        assert payload["session_id"] == "api-sess"
        assert payload["harness"] == "cursor"
        assert payload["messages"][0]["text"] == "hello"

        status, payload = _json_get(f"{base}/api/session?harness=cursor")
        assert status == 400
        assert "error" in payload

        status, payload = _json_get(f"{base}/api/session?session=api-sess")
        assert status == 400
        assert "error" in payload

        status, payload = _json_get(f"{base}/api/session")
        assert status == 400

        status, payload = _json_get(
            f"{base}/api/session?harness=cursor&session=missing"
        )
        assert status == 404
        assert payload["error"] == "not found"


def test_ingest_to_server_integration(
    warehouse_home: Path,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real fixture ingest is visible through the overview endpoint."""
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(cursor_root))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(claude_root))
    con = warehouse.open(read_only=False)
    try:
        ingest.ingest(full=True, con=con, ai_tracking_db=ai_tracking_db)
    finally:
        con.close()

    with _running_server() as (_httpd, base):
        status, payload = _json_get(
            f"{base}/api/overview?since=2000-01-01&until=2100-01-01"
        )
        assert status == 200
        assert payload["per_harness"]["cursor"]["sessions"] > 0
        assert payload["per_harness"]["claude"]["sessions"] > 0


def _counting_opener() -> tuple[
    Callable[..., duckdb.DuckDBPyConnection], dict[str, int]
]:
    """Wrap ``warehouse.open_current`` with an open-call counter."""
    opens = {"n": 0}
    real = warehouse.open_current

    def _open(**kwargs: object) -> duckdb.DuckDBPyConnection:
        opens["n"] += 1
        return real(**kwargs)

    return _open, opens


def test_api_cache_hit_skips_warehouse_open(warehouse_home: Path) -> None:
    """Identical GET after a cold miss returns the same JSON without reopening."""
    warehouse.open(read_only=False).close()
    opener, opens = _counting_opener()
    with _running_server(open_warehouse=opener) as (_httpd, base):
        status1, body1 = _json_get(f"{base}/api/overview")
        assert status1 == 200
        assert opens["n"] == 1
        status2, body2 = _json_get(f"{base}/api/overview")
        assert status2 == 200
        assert body2 == body1
        assert opens["n"] == 1


def test_api_cache_isolates_request_keys(warehouse_home: Path) -> None:
    """Different query strings do not share cache entries (each misses once)."""
    warehouse.open(read_only=False).close()
    opener, opens = _counting_opener()
    with _running_server(open_warehouse=opener) as (_httpd, base):
        status_a, body_a = _json_get(f"{base}/api/overview?harness=cursor")
        status_b, body_b = _json_get(f"{base}/api/overview?harness=claude")
        assert status_a == 200
        assert status_b == 200
        assert opens["n"] == 2
        _json_get(f"{base}/api/overview?harness=cursor")
        _json_get(f"{base}/api/overview?harness=claude")
        assert opens["n"] == 2
        assert body_a == _json_get(f"{base}/api/overview?harness=cursor")[1]
        assert body_b == _json_get(f"{base}/api/overview?harness=claude")[1]


def test_api_cache_invalidates_after_ingest(
    warehouse_home: Path,
    cursor_root: Path,
    claude_root: Path,
    ai_tracking_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Warm cache, ingest new rows, then overview recomputes with fresh data."""
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(cursor_root))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(claude_root))
    warehouse.open(read_only=False).close()
    opener, opens = _counting_opener()
    with _running_server(open_warehouse=opener) as (_httpd, base):
        status, before = _json_get(
            f"{base}/api/overview?since=2000-01-01&until=2100-01-01"
        )
        assert status == 200
        assert before["distinct_projects"] == 0
        assert opens["n"] == 1

        con = warehouse.open(read_only=False)
        try:
            ingest.ingest(full=True, con=con, ai_tracking_db=ai_tracking_db)
        finally:
            con.close()

        status, after = _json_get(
            f"{base}/api/overview?since=2000-01-01&until=2100-01-01"
        )
        assert status == 200
        assert opens["n"] == 2
        assert after["per_harness"]["cursor"]["sessions"] > 0
        assert after != before


def test_api_cache_invalidates_after_write_without_sync_state(
    warehouse_home: Path,
) -> None:
    """A content insert that leaves ``_sync_state`` untouched still busts the cache.

    Models the backfill contract: warehouse rows change without watermark moves.
    """

    def _write_session(session_id: str, project_id: str, when: datetime) -> list:
        """Insert one session and return the current ``_sync_state`` snapshot.

        Uses a nested scope so the writer connection (and its flock) is
        released before the caller opens again — ``close()`` alone is not
        enough while a name still references the connection.
        """
        con = warehouse.open(read_only=False)
        try:
            con.execute(
                "INSERT INTO sessions "
                "(harness, session_id, project_id, source_path, is_subagent, "
                "source_mtime) VALUES "
                "('cursor', ?, ?, ?, false, ?)",
                [session_id, project_id, f"/tmp/{session_id}.jsonl", when],
            )
            return con.execute(
                "SELECT harness, source_root, last_mtime, last_path, updated_at "
                "FROM _sync_state ORDER BY 1, 2"
            ).fetchall()
        finally:
            con.close()

    sync_before = _write_session("pre", "p0", datetime(2026, 1, 1))

    opener, opens = _counting_opener()
    with _running_server(open_warehouse=opener) as (_httpd, base):
        status, before = _json_get(
            f"{base}/api/overview?since=2000-01-01&until=2100-01-01"
        )
        assert status == 200
        assert before["per_harness"]["cursor"]["sessions"] == 1
        assert opens["n"] == 1

        sync_after = _write_session("backfilled", "p1", datetime(2026, 2, 1))
        assert sync_after == sync_before

        status, after = _json_get(
            f"{base}/api/overview?since=2000-01-01&until=2100-01-01"
        )
        assert status == 200
        assert opens["n"] == 2
        assert after["per_harness"]["cursor"]["sessions"] == 2


def test_api_cache_put_keeps_fingerprint_from_get(
    warehouse_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not key a pre-write payload under a post-write fingerprint.

    Models ingest/backfill committing after the query and before a re-stat in
    ``put``. Re-statting would sticky-cache stale JSON under the new epoch.
    """
    warehouse.open(read_only=False).close()
    # miss-get under epoch A, (buggy put would re-stat B), then get under B.
    fps = [(1, 100), (2, 200), (2, 200)]
    calls = {"i": 0}

    def fake_fp(_path: Path) -> tuple[int, int]:
        i = calls["i"]
        calls["i"] += 1
        return fps[min(i, len(fps) - 1)]

    monkeypatch.setattr(
        "stockroom.dashboard.server.dashboard_cache.warehouse_fingerprint",
        fake_fp,
    )
    opener, opens = _counting_opener()
    with _running_server(open_warehouse=opener) as (_httpd, base):
        status1, _body1 = _json_get(f"{base}/api/overview")
        assert status1 == 200
        assert opens["n"] == 1
        status2, _body2 = _json_get(f"{base}/api/overview")
        assert status2 == 200
        # Fixed: epoch-B get misses and reopens. Buggy: sticky hit under B, opens stays 1.
        assert opens["n"] == 2


def test_api_cache_does_not_stick_non_200_responses(warehouse_home: Path) -> None:
    """503 busy and 404 session-miss are not served forever after recovery."""
    warehouse.open(read_only=False).close()
    state = {"busy": True}
    real = warehouse.open_current

    def _maybe_busy(**kwargs: object) -> duckdb.DuckDBPyConnection:
        if state["busy"]:
            raise warehouse.WarehouseBusyError("busy")
        return real(**kwargs)

    with _running_server(open_warehouse=_maybe_busy) as (_httpd, base):
        status, payload = _json_get(f"{base}/api/overview")
        assert status == 503
        assert "retry" in payload["action"]
        state["busy"] = False
        status, payload = _json_get(f"{base}/api/overview")
        assert status == 200
        assert payload["distinct_projects"] == 0

    with _running_server() as (_httpd, base):
        status, payload = _json_get(f"{base}/api/session?harness=cursor&session=later")
        assert status == 404
        con = warehouse.open(read_only=False)
        try:
            con.execute(
                "INSERT INTO sessions "
                "(harness, session_id, project_id, cwd, source_path, is_subagent, "
                "source_mtime) VALUES "
                "('cursor', 'later', 'p', '/tmp/p', '/tmp/later.jsonl', false, ?)",
                [datetime(2026, 3, 1)],
            )
            con.execute(
                "INSERT INTO messages "
                "(harness, session_id, message_id, ordinal, role, text) "
                "VALUES ('cursor', 'later', 'later#0', 0, 'user', 'hi')"
            )
        finally:
            con.close()
        status, payload = _json_get(f"{base}/api/session?harness=cursor&session=later")
        assert status == 200
        assert payload["session_id"] == "later"


def test_api_cache_concurrent_hits_return_identical_json(
    warehouse_home: Path,
) -> None:
    """Concurrent identical GETs after warm-up return the same JSON body."""
    warehouse.open(read_only=False).close()
    opener, opens = _counting_opener()
    with _running_server(open_warehouse=opener) as (_httpd, base):
        url = f"{base}/api/overview"
        status, warm = _json_get(url)
        assert status == 200
        assert opens["n"] == 1

        results: list[tuple[int, dict | list]] = []
        errors: list[BaseException] = []

        def worker() -> None:
            try:
                results.append(_json_get(url))
            except BaseException as exc:  # noqa: BLE001 - collect for main thread
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert not errors
        assert len(results) == 16
        assert all(status == 200 and body == warm for status, body in results)
        assert opens["n"] == 1
