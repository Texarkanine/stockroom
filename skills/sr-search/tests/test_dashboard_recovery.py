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


def test_diagnostic_html_harness_first_not_circular_cli() -> None:
    """Page explains harness heal first; does not pretend a dead shim can CLI-heal itself."""
    html = recovery.render_diagnostic_html()
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()

    harness_idx = html.find("new chat")
    if harness_idx < 0:
        harness_idx = html.find("new session")
    if harness_idx < 0:
        harness_idx = html.find("Submit a prompt")
    init_idx = html.find("sr-initialize")

    assert harness_idx >= 0, "must start with harness session / prompt heal"
    assert init_idx >= 0, "must offer sr-initialize when hooks cannot restore PATH"
    assert harness_idx < init_idx, "harness before agent initialize"

    # Circular / wrong surface: dead shim cannot CLI-heal; dashboard does not use torch.
    assert "stockroom shim rectify" not in html
    assert "stockroom dashboard --replace" not in html
    assert "ensure-env" not in html
    assert "torch" not in html.lower()
    assert "Torch" not in html


def test_diagnostic_html_links_dedicated_troubleshooting_section() -> None:
    """Page ends at the dedicated recovery troubleshooting section (not a CLI cookbook)."""
    html = recovery.render_diagnostic_html()
    assert TROUBLESHOOTING_BASE in html
    assert f"{TROUBLESHOOTING_BASE}#dashboard-ui-will-not-load" in html


def test_unknown_static_path_returns_diagnostic_html(
    warehouse_home: Path,
) -> None:
    """Browser-facing unknown paths get the diagnostic HTML page, not bare JSON."""
    with _running_server() as (_httpd, base):
        status, content_type, body = _get(f"{base}/cute-puppies")
        assert status == 404
        assert content_type.startswith("text/html")
        text = body.decode("utf-8")
        assert "sr-initialize" in text
        assert "new chat" in text or "new session" in text or "prompt" in text.lower()
        assert "#dashboard-ui-will-not-load" in text
        assert "stockroom shim rectify" not in text
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
        assert "#dashboard-ui-will-not-load" in text
        assert "stockroom shim rectify" not in text


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
