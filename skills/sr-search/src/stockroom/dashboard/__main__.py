"""Runnable dashboard launcher with idempotent port probing.

The normal path is hook-friendly: probe loopback, print the stable URL and exit
when any listener already owns the port, otherwise detach a foreground re-exec.
When the listener is an owned stockroom dashboard whose recorded engine identity
is stale (plugin-root move), replace it. Foreign listeners are left alone. The
OS bind is the race mutex; a child that loses with ``EADDRINUSE`` exits
successfully because another launcher won.
"""

from __future__ import annotations

import argparse
import errno
import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

import stockroom
from stockroom.dashboard import identity as dash_identity
from stockroom.dashboard import server as dashboard_server

DEFAULT_PORT = 58008
_WAIT_PORT_FREE_SECONDS = 2.0
_WAIT_PORT_FREE_POLL = 0.05

ReadIdentity = Callable[[int], dash_identity.DashboardIdentity | None]
WriteIdentity = Callable[[dash_identity.DashboardIdentity], Path]
VerifyOwned = Callable[[int], bool]
KillFn = Callable[[int], None]
WaitPortFree = Callable[[int], bool]


def probe(port: int) -> bool:
    """Return whether a TCP listener accepts loopback connections on ``port``."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def spawn(argv: Sequence[str]) -> None:
    """Spawn the foreground dashboard command as a detached silent child."""
    subprocess.Popen(
        list(argv),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def verify_owned(pid: int) -> bool:
    """Return True when ``pid`` looks like a stockroom dashboard process."""
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False
    return b"stockroom.dashboard" in cmdline.replace(b"\x00", b" ")


def kill_pid(pid: int) -> None:
    """Send SIGTERM to ``pid``."""
    os.kill(pid, signal.SIGTERM)


def wait_port_free(
    port: int,
    *,
    timeout: float = _WAIT_PORT_FREE_SECONDS,
    probe_fn: Callable[[int], bool] = probe,
) -> bool:
    """Poll until ``port`` is free or ``timeout`` elapses; return whether free."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not probe_fn(port):
            return True
        time.sleep(_WAIT_PORT_FREE_POLL)
    return not probe_fn(port)


def _is_current(record: dash_identity.DashboardIdentity) -> bool:
    return (
        record.app_dir.resolve() == dash_identity.current_app_dir().resolve()
        and record.version == stockroom.__version__
    )


def _foreground_argv(port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "stockroom.dashboard",
        "--foreground",
        "--port",
        str(port),
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stockroom dashboard",
        description="Launch the read-only local stockroom dashboard.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="serve in this process instead of detaching",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    probe_fn: Callable[[int], bool] = probe,
    spawn_fn: Callable[[Sequence[str]], None] = spawn,
    serve_fn: Callable[..., object] | None = None,
    read_identity_fn: ReadIdentity = dash_identity.read,
    write_identity_fn: WriteIdentity = dash_identity.write,
    verify_owned_fn: VerifyOwned = verify_owned,
    kill_fn: KillFn = kill_pid,
    wait_port_free_fn: WaitPortFree | None = None,
) -> int:
    """Probe or launch the local dashboard and print its stable URL."""
    args = _build_parser().parse_args(argv)
    url = f"http://127.0.0.1:{args.port}/"
    serve_impl = serve_fn or dashboard_server.serve
    wait_free = wait_port_free_fn or (
        lambda port: wait_port_free(port, probe_fn=probe_fn)
    )

    if args.foreground:
        try:
            httpd = serve_impl(args.port)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
            print(url)
            return 0
        try:
            write_identity_fn(
                dash_identity.DashboardIdentity(
                    pid=os.getpid(),
                    app_dir=dash_identity.current_app_dir(),
                    version=stockroom.__version__,
                    port=args.port,
                )
            )
        except OSError:
            pass
        print(url)
        try:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
        finally:
            httpd.server_close()
        return 0

    if probe_fn(args.port):
        record = read_identity_fn(args.port)
        if record is not None and verify_owned_fn(record.pid):
            if _is_current(record):
                print(url)
                return 0
            try:
                kill_fn(record.pid)
            except OSError:
                print(url)
                return 0
            if not wait_free(args.port):
                print(url)
                return 0
            spawn_fn(_foreground_argv(args.port))
            print(url)
            return 0
        print(url)
        return 0

    spawn_fn(_foreground_argv(args.port))
    print(url)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through ``main``
    raise SystemExit(main())
