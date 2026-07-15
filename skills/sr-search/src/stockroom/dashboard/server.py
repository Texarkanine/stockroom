"""Loopback-only HTTP routing for dashboard JSON and static assets.

Each API request opens a fresh read-only connection through
``warehouse.open_current`` with a short backoff budget. The dashboard therefore
never migrates, never writes, and never holds a reader lock between refreshes.
Expected warehouse states become stable ``503 {error, action}`` payloads; all
other exceptions are contained behind a clean JSON 500 response.
"""

import json
import mimetypes
from collections.abc import Callable
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import duckdb

from stockroom import warehouse
from stockroom.dashboard import metrics


class _DashboardServer(ThreadingHTTPServer):
    """Threading server carrying request dependencies for its handlers."""

    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        open_warehouse: Callable[..., duckdb.DuckDBPyConnection],
        static_root: Path,
    ) -> None:
        self.open_warehouse = open_warehouse
        self.static_root = static_root.resolve()
        super().__init__(address, _DashboardHandler)


class _DashboardHandler(BaseHTTPRequestHandler):
    """Route one dashboard request without sharing DB connections across threads."""

    server: _DashboardServer

    def log_message(self, _format: str, *_args: object) -> None:
        """Keep the hook-launched local service silent."""

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        self._send_json(404, {"error": "not found"})

    def _open_readonly(self) -> duckdb.DuckDBPyConnection | None:
        """Open a short-lived read-only warehouse connection, or send a 503."""
        try:
            return self.server.open_warehouse(read_only=True, timeout=2.0)
        except FileNotFoundError:
            self._send_json(
                503,
                {
                    "error": "no warehouse yet",
                    "action": "run `stockroom ingest`",
                },
            )
        except warehouse.WarehouseStaleError:
            self._send_json(
                503,
                {
                    "error": "warehouse schema is behind",
                    "action": "run `stockroom migrate`",
                },
            )
        except warehouse.WarehouseBusyError:
            self._send_json(
                503,
                {
                    "error": "warehouse is busy",
                    "action": "retry shortly",
                },
            )
        return None

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        """Serve an API payload or a guarded packaged static file."""
        try:
            parsed = urlsplit(self.path)
            if parsed.path.startswith("/api/"):
                self._serve_api(parsed.path.removeprefix("/api/"), parsed.query)
            else:
                self._serve_static(parsed.path)
        except Exception:
            self._send_json(500, {"error": "internal server error"})

    def _serve_api(self, endpoint_name: str, query_string: str) -> None:
        endpoint = metrics.ENDPOINTS.get(endpoint_name)
        if endpoint is None:
            self._not_found()
            return

        query = parse_qs(query_string, keep_blank_values=True)
        if endpoint_name == "session":
            self._serve_session(endpoint, query)
            return

        harnesses = query.get("harness")
        raw_since = query.get("since", [None])[-1]
        raw_until = query.get("until", [None])[-1]
        since: datetime | None = None
        until: datetime | None = None
        try:
            since = metrics.parse_timestamp(raw_since, "since")
            until = metrics.parse_timestamp(raw_until, "until")
            if since is not None and until is not None and since >= until:
                raise ValueError("since must be before until")
            limit = 50
            offset = 0
            order = "desc"
            if "limit" in query:
                try:
                    limit = int(query["limit"][-1])
                except ValueError as exc:
                    raise ValueError("invalid limit: expected an integer") from exc
                if limit < 0:
                    raise ValueError("invalid limit: must be non-negative")
                if limit > 0:
                    limit = min(limit, 500)
            if "offset" in query:
                try:
                    offset = int(query["offset"][-1])
                except ValueError as exc:
                    raise ValueError("invalid offset: expected an integer") from exc
                if offset < 0:
                    raise ValueError("invalid offset: must be non-negative")
            if "order" in query:
                order = query["order"][-1].lower()
                if order not in {"asc", "desc"}:
                    raise ValueError("invalid order: expected asc or desc")
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        con = self._open_readonly()
        if con is None:
            return

        try:
            if endpoint_name == "sessions":
                payload = endpoint(
                    con,
                    harnesses,
                    since,
                    until,
                    limit=limit,
                    offset=offset,
                    order=order,
                )
            else:
                payload = endpoint(con, harnesses, since, until)
        finally:
            con.close()
        self._send_json(200, payload)

    def _serve_session(
        self, endpoint: Callable[..., Any], query: dict[str, list[str]]
    ) -> None:
        """Serve ``/api/session`` with required ``harness`` + ``session`` identity."""
        try:
            harness = query.get("harness", [None])[-1]
            session_id = query.get("session", [None])[-1]
            if not harness:
                raise ValueError("missing required parameter: harness")
            if not session_id:
                raise ValueError("missing required parameter: session")
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        con = self._open_readonly()
        if con is None:
            return

        try:
            payload = endpoint(con, harness, session_id)
        finally:
            con.close()
        if payload is None:
            self._not_found()
            return
        self._send_json(200, payload)

    def _serve_static(self, raw_path: str) -> None:
        relative = "index.html" if raw_path == "/" else unquote(raw_path).lstrip("/")
        candidate = (self.server.static_root / relative).resolve()
        if (
            not candidate.is_relative_to(self.server.static_root)
            or not candidate.is_file()
        ):
            self._not_found()
            return
        body = candidate.read_bytes()
        content_type = (
            mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        )
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(
    port: int = 58008,
    *,
    host: str = "127.0.0.1",
    open_warehouse: Callable[..., duckdb.DuckDBPyConnection] | None = None,
    static_root: Path | None = None,
) -> HTTPServer:
    """Bind and return the dashboard HTTP server without starting its loop."""
    opener = open_warehouse or warehouse.open_current
    assets = static_root or Path(__file__).parent / "static"
    return _DashboardServer(
        (host, port),
        open_warehouse=opener,
        static_root=assets,
    )
