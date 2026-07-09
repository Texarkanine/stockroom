"""Runnable dashboard launcher with idempotent port probing.

The normal path is hook-friendly: probe loopback, print the stable URL and exit
when any listener already owns the port, otherwise detach a foreground re-exec.
The foreground child owns the HTTP loop. The OS bind is the race mutex; a child
that loses with ``EADDRINUSE`` exits successfully because another launcher won.
"""

import argparse
import errno
import socket
import subprocess
import sys
from collections.abc import Callable, Sequence

from stockroom.dashboard import server as dashboard_server

DEFAULT_PORT = 6767


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
) -> int:
    """Probe or launch the local dashboard and print its stable URL."""
    args = _build_parser().parse_args(argv)
    url = f"http://127.0.0.1:{args.port}/"
    serve_impl = serve_fn or dashboard_server.serve

    if args.foreground:
        try:
            httpd = serve_impl(args.port)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
            print(url)
            return 0
        print(url)
        try:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
        finally:
            httpd.server_close()
        return 0

    if not probe_fn(args.port):
        spawn_fn(
            [
                sys.executable,
                "-m",
                "stockroom.dashboard",
                "--foreground",
                "--port",
                str(args.port),
            ]
        )
    print(url)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through ``main``
    raise SystemExit(main())
