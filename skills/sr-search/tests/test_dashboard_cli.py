"""Unit contracts for dashboard probe/spawn/foreground CLI decisions."""

import errno
import os
import sys
from pathlib import Path

import stockroom
from stockroom.dashboard import __main__ as dashboard_cli
from stockroom.dashboard import identity as dash_identity
from stockroom.dashboard.identity import DashboardIdentity, current_app_dir


def test_default_port_is_58008() -> None:
    """Default dashboard listener port is 58008."""
    assert dashboard_cli.DEFAULT_PORT == 58008


def test_already_serving_prints_url_without_spawn(capsys) -> None:
    """A successful probe with no usable identity leaves the listener alone."""
    spawned = []
    killed = []
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 58008,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: None,
        kill_fn=killed.append,
    )
    assert result == 0
    assert spawned == []
    assert killed == []
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"


def test_same_identity_reuses_without_kill_or_spawn(capsys) -> None:
    """Matching owned identity is an idempotent no-op."""
    spawned = []
    killed = []
    current = DashboardIdentity(
        pid=99,
        app_dir=current_app_dir(),
        version=stockroom.__version__,
        port=58008,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 58008,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: current,
        verify_owned_fn=lambda pid: pid == 99,
        kill_fn=killed.append,
    )
    assert result == 0
    assert spawned == []
    assert killed == []
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"


def test_replace_forces_kill_even_when_identity_current(capsys) -> None:
    """``--replace`` replaces an owned current listener instead of no-op."""
    spawned = []
    killed = []
    waits = []
    current = DashboardIdentity(
        pid=99,
        app_dir=current_app_dir(),
        version=stockroom.__version__,
        port=58008,
    )
    result = dashboard_cli.main(
        ["--replace"],
        probe_fn=lambda port: port == 58008,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: current,
        verify_owned_fn=lambda pid: pid == 99,
        kill_fn=killed.append,
        wait_port_free_fn=lambda port: waits.append(port) or True,
    )
    assert result == 0
    assert killed == [99]
    assert waits == [58008]
    assert spawned == [
        [
            sys.executable,
            "-m",
            "stockroom.dashboard",
            "--foreground",
            "--port",
            "58008",
        ]
    ]
    captured = capsys.readouterr()
    assert captured.out == "http://127.0.0.1:58008/\n"
    assert "replaced" in captured.err


def test_replace_still_leaves_foreign_listener_alone(capsys) -> None:
    """``--replace`` never kills a listener that fails ownership verify."""
    spawned = []
    killed = []
    record = DashboardIdentity(
        pid=55,
        app_dir=current_app_dir(),
        version=stockroom.__version__,
        port=58008,
    )
    result = dashboard_cli.main(
        ["--replace"],
        probe_fn=lambda port: port == 58008,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: record,
        verify_owned_fn=lambda _pid: False,
        kill_fn=killed.append,
    )
    assert result == 0
    assert killed == []
    assert spawned == []
    captured = capsys.readouterr()
    assert captured.out == "http://127.0.0.1:58008/\n"
    assert "replaced" not in captured.err


def test_stale_owned_identity_kills_waits_and_spawns(capsys) -> None:
    """Stale owned listener is replaced from the current engine."""
    spawned = []
    killed = []
    waits = []
    stale = DashboardIdentity(
        pid=55,
        app_dir=Path("/old/plugin/skills/sr-search"),
        version="0.0.0",
        port=58008,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 58008,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: stale,
        verify_owned_fn=lambda pid: pid == 55,
        kill_fn=killed.append,
        wait_port_free_fn=lambda port: waits.append(port) or True,
    )
    assert result == 0
    assert killed == [55]
    assert waits == [58008]
    assert spawned == [
        [
            sys.executable,
            "-m",
            "stockroom.dashboard",
            "--foreground",
            "--port",
            "58008",
        ]
    ]
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"


def test_unverified_identity_is_left_alone(capsys) -> None:
    """Identity pid that fails ownership verify is never killed."""
    spawned = []
    killed = []
    stale = DashboardIdentity(
        pid=55,
        app_dir=Path("/old/engine"),
        version="9.9.9",
        port=58008,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 58008,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: stale,
        verify_owned_fn=lambda _pid: False,
        kill_fn=killed.append,
    )
    assert result == 0
    assert killed == []
    assert spawned == []
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"


def test_kill_failure_still_exits_zero(capsys) -> None:
    """Replace path degrades to success when kill raises."""
    spawned = []

    def _boom(pid: int) -> None:
        raise OSError("permission denied")

    stale = DashboardIdentity(
        pid=55,
        app_dir=Path("/old/engine"),
        version="9.9.9",
        port=58008,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 58008,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: stale,
        verify_owned_fn=lambda pid: pid == 55,
        kill_fn=_boom,
    )
    assert result == 0
    assert spawned == []
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"


def test_version_mismatch_same_app_dir_replaces(capsys) -> None:
    """Same app_dir with a different version is treated as stale."""
    spawned = []
    killed = []
    stale = DashboardIdentity(
        pid=55,
        app_dir=current_app_dir(),
        version="0.0.0-old",
        port=58008,
    )
    result = dashboard_cli.main(
        [],
        probe_fn=lambda port: port == 58008,
        spawn_fn=spawned.append,
        read_identity_fn=lambda _port: stale,
        verify_owned_fn=lambda pid: pid == 55,
        kill_fn=killed.append,
        wait_port_free_fn=lambda _port: True,
    )
    assert result == 0
    assert killed == [55]
    assert len(spawned) == 1
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"


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

    written: list[DashboardIdentity] = []

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
    assert written[0].port == 8888
    assert capsys.readouterr().out == "http://127.0.0.1:8888/\n"


def test_foreground_bind_writes_identity(warehouse_home: Path, capsys) -> None:
    """Successful foreground bind persists pid/app_dir/version/port identity."""

    class FakeServer:
        def serve_forever(self) -> None:
            return

        def server_close(self) -> None:
            return

    result = dashboard_cli.main(
        ["--foreground", "--port", "58008"],
        serve_fn=lambda _port: FakeServer(),
    )
    assert result == 0
    record = dash_identity.read(58008)
    assert record is not None
    assert record.pid == os.getpid()
    assert record.app_dir == current_app_dir()
    assert record.version == stockroom.__version__
    assert record.port == 58008
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"
    assert warehouse_home.exists()


def test_foreground_bind_race_is_success_elsewhere(capsys) -> None:
    """EADDRINUSE means another child won the bind mutex and is success."""

    def _race(_port: int):
        raise OSError(errno.EADDRINUSE, "address already in use")

    result = dashboard_cli.main(["--foreground"], serve_fn=_race)
    assert result == 0
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"


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
    assert capsys.readouterr().out == "http://127.0.0.1:58008/\n"


def test_verify_owned_true_when_proc_cmdline_matches(monkeypatch) -> None:
    """``/proc`` cmdline containing ``stockroom.dashboard`` is owned."""
    monkeypatch.setattr(
        dashboard_cli,
        "_read_proc_cmdline",
        lambda _pid: b"python\x00-m\x00stockroom.dashboard\x00--foreground",
    )
    monkeypatch.setattr(
        dashboard_cli,
        "_read_ps_cmdline",
        lambda _pid: (_ for _ in ()).throw(
            AssertionError("ps unused when /proc works")
        ),
    )
    assert dashboard_cli.verify_owned(4242) is True


def test_verify_owned_false_when_proc_cmdline_lacks_marker(monkeypatch) -> None:
    """``/proc`` cmdline without ``stockroom.dashboard`` is not owned."""
    monkeypatch.setattr(
        dashboard_cli,
        "_read_proc_cmdline",
        lambda _pid: b"nginx\x00-g\x00daemon off;",
    )
    monkeypatch.setattr(
        dashboard_cli,
        "_read_ps_cmdline",
        lambda _pid: (_ for _ in ()).throw(
            AssertionError("ps unused when /proc works")
        ),
    )
    assert dashboard_cli.verify_owned(4242) is False


def test_verify_owned_falls_back_to_ps_when_proc_unavailable(
    monkeypatch,
) -> None:
    """
    Missing ``/proc`` must not silently mean never-owned.

    On Darwin (and any host without ``/proc/{pid}/cmdline``), ownership is
    decided from a portable ``ps`` cmdline that still contains
    ``stockroom.dashboard``.
    """
    monkeypatch.setattr(dashboard_cli, "_read_proc_cmdline", lambda _pid: None)
    monkeypatch.setattr(
        dashboard_cli,
        "_read_ps_cmdline",
        lambda _pid: b"/path/B/python -m stockroom.dashboard --foreground --port 58008",
    )
    assert dashboard_cli.verify_owned(4242) is True


def test_verify_owned_false_when_proc_and_ps_unavailable(monkeypatch) -> None:
    """No cmdline source means the pid is not treated as owned."""
    monkeypatch.setattr(dashboard_cli, "_read_proc_cmdline", lambda _pid: None)
    monkeypatch.setattr(dashboard_cli, "_read_ps_cmdline", lambda _pid: None)
    assert dashboard_cli.verify_owned(4242) is False


def test_verify_owned_false_when_ps_cmdline_lacks_marker(monkeypatch) -> None:
    """``ps`` fallback without ``stockroom.dashboard`` is not owned."""
    monkeypatch.setattr(dashboard_cli, "_read_proc_cmdline", lambda _pid: None)
    monkeypatch.setattr(
        dashboard_cli,
        "_read_ps_cmdline",
        lambda _pid: b"/usr/sbin/nginx -g daemon off;",
    )
    assert dashboard_cli.verify_owned(4242) is False
