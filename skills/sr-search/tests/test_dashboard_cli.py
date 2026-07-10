"""Unit contracts for dashboard probe/spawn/foreground CLI decisions."""

import errno
import sys
from pathlib import Path

from stockroom.dashboard import __main__ as dashboard_cli


def test_already_serving_prints_url_without_spawn(capsys) -> None:
    """A successful probe is an idempotent no-op apart from printing the URL."""
    spawned = []
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 6767,
        spawn_fn=spawned.append,
    )
    assert result == 0
    assert spawned == []
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"


def test_free_port_spawns_foreground_reexec_and_respects_port(capsys) -> None:
    """A free port detaches the exact foreground module re-exec."""
    spawned = []
    result = dashboard_cli.main(
        ["--port", "7777"],
        probe_fn=lambda _port: False,
        spawn_fn=spawned.append,
    )
    assert result == 0
    assert spawned == [
        [
            sys.executable,
            "-m",
            "stockroom.dashboard",
            "--foreground",
            "--port",
            "7777",
        ]
    ]
    assert capsys.readouterr().out == "http://127.0.0.1:7777/\n"


def test_foreground_serves_in_process_without_probe_or_spawn(capsys) -> None:
    """Foreground mode binds and serves directly through the server seam."""
    events = []

    class FakeServer:
        def serve_forever(self) -> None:
            events.append("served")

        def server_close(self) -> None:
            events.append("closed")

    def _serve(port: int):
        events.append(("bound", port))
        return FakeServer()

    def _forbidden(*_args):
        raise AssertionError("probe/spawn must not run in foreground mode")

    result = dashboard_cli.main(
        ["--foreground", "--port", "8888"],
        probe_fn=_forbidden,
        spawn_fn=_forbidden,
        serve_fn=_serve,
    )
    assert result == 0
    assert events == [("bound", 8888), "served", "closed"]
    assert capsys.readouterr().out == "http://127.0.0.1:8888/\n"


def test_foreground_bind_race_is_success_elsewhere(capsys) -> None:
    """EADDRINUSE means another child won the bind mutex and is success."""

    def _race(_port: int):
        raise OSError(errno.EADDRINUSE, "address already in use")

    result = dashboard_cli.main(["--foreground"], serve_fn=_race)
    assert result == 0
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"


def test_foreground_startup_does_not_require_a_warehouse(
    warehouse_home: Path,
    capsys,
) -> None:
    """Missing warehouse is a per-request 503, never a launcher precondition."""
    assert not warehouse_home.exists()
    events = []

    class FakeServer:
        def serve_forever(self) -> None:
            events.append("served")

        def server_close(self) -> None:
            events.append("closed")

    result = dashboard_cli.main(
        ["--foreground"],
        serve_fn=lambda _port: FakeServer(),
    )
    assert result == 0
    assert events == ["served", "closed"]
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"
