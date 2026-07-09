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
from stockroom.dashboard import metrics
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
            status, payload = _json_get(f"{base}/api/{endpoint}")
            assert status == 200
            assert payload is not None
        _, overview = _json_get(f"{base}/api/overview")
        assert overview == {
            "last_sync": None,
            "per_harness": {},
            "distinct_projects": 0,
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
        assert len(trends["daily"]["days"]) == 14
        assert len(trends["weekly"]["weeks"]) == 12

        status, sessions = _json_get(f"{base}/api/sessions?until=2026-02-01")
        assert status == 200
        assert [row["started"] for row in sessions] == [
            "2026-01-31T00:00:00",
            "2025-01-01T00:00:00",
        ]


def test_repeated_harness_limit_cap_and_short_timeout_are_wired(
    warehouse_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP preserves repeated filters, clamps limit, and opens with 2s backoff."""
    captured: dict[str, object] = {}

    class FakeConnection:
        def close(self) -> None:
            captured["closed"] = True

    def _open(**kwargs):
        captured["open_kwargs"] = kwargs
        return FakeConnection()

    def _sessions(_con, harnesses, since, until, *, limit):
        return {
            "harnesses": harnesses,
            "since": since,
            "until": until,
            "limit": limit,
        }

    monkeypatch.setitem(metrics.ENDPOINTS, "sessions", _sessions)
    with _running_server(open_warehouse=_open) as (_httpd, base):
        status, payload = _json_get(
            f"{base}/api/sessions?harness=cursor&harness=claude&limit=501"
        )
    assert status == 200
    assert payload["harnesses"] == ["cursor", "claude"]
    assert payload["limit"] == 500
    assert captured == {
        "open_kwargs": {"read_only": True, "timeout": 2.0},
        "closed": True,
    }


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
    with _running_server() as (_httpd, base):
        status, content_type, body = _get(f"{base}/")
        assert status == 200
        assert content_type.startswith("text/html")
        assert b"stockroom dashboard" in body

        status, payload = _json_get(f"{base}/%2e%2e/%2e%2e/etc/passwd")
        assert status == 404
        assert payload["error"] == "not found"


def test_dashboard_javascript_assets_have_browser_mime_types(
    warehouse_home: Path,
) -> None:
    """Authored modules and vendored Chart.js are served as JavaScript."""
    with _running_server() as (_httpd, base):
        for asset in [
            "dashboard.mjs",
            "dashboard-core.mjs",
            "dashboard-data.mjs",
            "chart-4.5.1.umd.min.js",
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
