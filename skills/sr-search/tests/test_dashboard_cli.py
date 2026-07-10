"""Unit contracts for dashboard probe/spawn/foreground CLI decisions."""

import errno
import os
import sys
from pathlib import Path

import stockroom
from stockroom.dashboard import __main__ as dashboard_cli
from stockroom.dashboard import identity as dash_identity
from stockroom.dashboard.identity import DashboardIdentity, current_app_dir


def test_already_serving_prints_url_without_spawn(capsys) -> None:
    """A successful probe with no usable identity leaves the listener alone."""
    spawned = []
    killed = []
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 6767,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: None,
        kill_fn=killed.append,
    )
    assert result == 0
    assert spawned == []
    assert killed == []
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"


def test_same_identity_reuses_without_kill_or_spawn(capsys) -> None:
    """Matching owned identity is an idempotent no-op."""
    spawned = []
    killed = []
    current = DashboardIdentity(
        pid=99,
        app_dir=current_app_dir(),
        version=stockroom.__version__,
        port=6767,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 6767,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: current,
        verify_owned_fn=lambda pid: pid == 99,
        kill_fn=killed.append,
    )
    assert result == 0
    assert spawned == []
    assert killed == []
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"


def test_stale_owned_identity_kills_waits_and_spawns(capsys) -> None:
    """Stale owned listener is replaced from the current engine."""
    spawned = []
    killed = []
    waits = []
    stale = DashboardIdentity(
        pid=55,
        app_dir=Path("/old/plugin/skills/sr-search"),
        version="0.0.0",
        port=6767,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 6767,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: stale,
        verify_owned_fn=lambda pid: pid == 55,
        kill_fn=killed.append,
        wait_port_free_fn=lambda port: waits.append(port) or True,
    )
    assert result == 0
    assert killed == [55]
    assert waits == [6767]
    assert spawned == [
        [
            sys.executable,
            "-m",
            "stockroom.dashboard",
            "--foreground",
            "--port",
            "6767",
        ]
    ]
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"


def test_unverified_identity_is_left_alone(capsys) -> None:
    """Identity pid that fails ownership verify is never killed."""
    spawned = []
    killed = []
    stale = DashboardIdentity(
        pid=55,
        app_dir=Path("/old/engine"),
        version="9.9.9",
        port=6767,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 6767,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: stale,
        verify_owned_fn=lambda _pid: False,
        kill_fn=killed.append,
    )
    assert result == 0
    assert killed == []
    assert spawned == []
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"


def test_kill_failure_still_exits_zero(capsys) -> None:
    """Replace path degrades to success when kill raises."""
    spawned = []

    def _boom(pid: int) -> None:
        raise OSError("permission denied")

    stale = DashboardIdentity(
        pid=55,
        app_dir=Path("/old/engine"),
        version="9.9.9",
        port=6767,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 6767,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: stale,
        verify_owned_fn=lambda pid: pid == 55,
        kill_fn=_boom,
    )
    assert result == 0
    assert spawned == []
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"


def test_version_mismatch_same_app_dir_replaces(capsys) -> None:
    """Same app_dir with a different version is treated as stale."""
    spawned = []
    killed = []
    stale = DashboardIdentity(
        pid=55,
        app_dir=current_app_dir(),
        version="0.0.0-old",
        port=6767,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 6767,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: stale,
        verify_owned_fn=lambda pid: pid == 55,
        kill_fn=killed.append,
        wait_port_free_fn=lambda _port: True,
    )
    assert result == 0
    assert killed == [55]
    assert len(spawned) == 1
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

    written: list[object] = []

    result = dashboard_cli.main(
        ["--foreground", "--port", "8888"],
        probe_fn=_forbidden,
        spawn_fn=_forbidden,
        serve_fn=_serve,
        write_identity_fn=lambda identity: written.append(identity) or Path("."),
    )
    assert result == 0
    assert events == [("bound", 8888), "served", "closed"]
    assert len(written) == 1
    assert written[0].port == 8888  # type: ignore[union-attr]
    assert capsys.readouterr().out == "http://127.0.0.1:8888/\n"


def test_foreground_bind_writes_identity(warehouse_home: Path, capsys) -> None:
    """Successful foreground bind persists pid/app_dir/version/port identity."""

    class FakeServer:
        def serve_forever(self) -> None:
            return

        def server_close(self) -> None:
            return

    result = dashboard_cli.main(
        ["--foreground", "--port", "6767"],
        serve_fn=lambda _port: FakeServer(),
    )
    assert result == 0
    record = dash_identity.read(6767)
    assert record is not None
    assert record.pid == os.getpid()
    assert record.app_dir == current_app_dir()
    assert record.version == stockroom.__version__
    assert record.port == 6767
    assert record == dash_identity.read(6767)
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"
    assert warehouse_home.exists()


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
        write_identity_fn=lambda _identity: Path("/tmp/unused"),
    )
    assert result == 0
    assert events == ["served", "closed"]
    assert capsys.readouterr().out == "http://127.0.0.1:6767/\n"
