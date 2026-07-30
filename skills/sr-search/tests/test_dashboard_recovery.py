"""Contracts for the in-memory dashboard diagnostic (recovery) HTML page.

MVP: one generic page with shim-first ordered remedies and online manual
links — no classifier. Static/document 404s serve that HTML; API 404s stay JSON.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import duckdb
import pytest

from stockroom.dashboard import recovery, server as dashboard_server


TROUBLESHOOTING_BASE = (
    "https://texarkanine.github.io/stockroom/user-guide/troubleshooting/"
)


@contextmanager
def _running_server(
    *,
    open_warehouse: Callable[..., duckdb.DuckDBPyConnection] | None = None,
    static_root: Path | None = None,
) -> Iterator[tuple[dashboard_server.HTTPServer, str]]:
    httpd = dashboard_server.serve(
        0, open_warehouse=open_warehouse, static_root=static_root
    )
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


def test_diagnostic_html_orders_remedies_shim_first() -> None:
    """Rendered page lists shim/session heal before ensure-env/init before --replace."""
    html = recovery.render_diagnostic_html()
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
    assert "text/html" not in html  # page body, not a Content-Type header string

    shim_idx = html.find("shim rectify")
    if shim_idx < 0:
        shim_idx = html.find("new session")
    ensure_idx = html.find("ensure-env")
    if ensure_idx < 0:
        ensure_idx = html.find("sr-initialize")
    replace_idx = html.find("dashboard --replace")
    if replace_idx < 0:
        replace_idx = html.find("--replace")

    assert shim_idx >= 0, "must mention shim rectify and/or new session"
    assert ensure_idx >= 0, "must mention ensure-env and/or sr-initialize"
    assert replace_idx >= 0, "must mention dashboard --replace (after shim guidance)"
    assert shim_idx < ensure_idx < replace_idx, (
        "remedies must be ordered: shim/session → ensure-env/init → --replace"
    )


def test_diagnostic_html_links_online_troubleshooting_manual() -> None:
    """Page links the published troubleshooting index (and useful anchors)."""
    html = recovery.render_diagnostic_html()
    assert TROUBLESHOOTING_BASE in html
    assert f"{TROUBLESHOOTING_BASE}#dashboard" in html


def test_unknown_static_path_returns_diagnostic_html(
    warehouse_home: Path,
) -> None:
    """Browser-facing unknown paths get the diagnostic HTML page, not bare JSON."""
    with _running_server() as (_httpd, base):
        status, content_type, body = _get(f"{base}/cute-puppies")
        assert status == 404
        assert content_type.startswith("text/html")
        text = body.decode("utf-8")
        assert "shim rectify" in text or "new session" in text
        assert "--replace" in text
        assert TROUBLESHOOTING_BASE in text
        with pytest.raises(json.JSONDecodeError):
            json.loads(body)


def test_missing_index_html_returns_diagnostic_html(
    warehouse_home: Path, tmp_path: Path
) -> None:
    """Broken listener (empty static root / no index) serves the same diagnostic page."""
    empty_static = tmp_path / "empty-static"
    empty_static.mkdir()
    with _running_server(static_root=empty_static) as (_httpd, base):
        status, content_type, body = _get(f"{base}/")
        assert status == 404
        assert content_type.startswith("text/html")
        text = body.decode("utf-8")
        assert TROUBLESHOOTING_BASE in text
        assert "--replace" in text


def test_unknown_api_still_returns_json_404(warehouse_home: Path) -> None:
    """Machine API 404 contract is unchanged by the diagnostic HTML path."""
    with _running_server() as (_httpd, base):
        status, content_type, body = _get(f"{base}/api/nope")
        assert status == 404
        assert content_type.startswith("application/json")
        assert json.loads(body) == {"error": "not found"}


def test_server_imports_recovery_at_module_load() -> None:
    """Recovery must be loaded with the server so it survives plugin-dir deletion."""
    assert hasattr(dashboard_server, "recovery") or "recovery" in dir(dashboard_server)
    # Prefer an explicit module-level binding used by handlers.
    assert dashboard_server.recovery is recovery
