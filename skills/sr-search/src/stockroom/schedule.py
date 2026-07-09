"""Nightly scheduler-entry management (``python -m stockroom.schedule``).

The Phase-3 m4 scheduling surface: installs, reports, and removes the
nightly ``stockroom ingest && stockroom embed`` job on the platform's
native scheduler — cron on Linux (a marker-delimited managed crontab
block; foreign lines pass through byte-for-byte), launchd on macOS (an
owned ``jp.ne.cani.stockroom.nightly.plist``). Idempotent by
construction: install replaces any previous managed entry, remove is a
clean no-op when nothing is installed.

The scheduler's execution environment is hostile (cron runs with
``PATH=/usr/bin:/bin``; launchd inherits no login shell), so every entry
invokes the on-path ``stockroom`` shim **by name** under an install-time
resolved absolute ``PATH=`` prefix inside a ``/bin/sh -c`` wrapper — a
raw engine path never appears in a rendered entry. Output appends to
``<home>/logs/nightly.log`` (``STOCKROOM_HOME``-aware): unredirected
cron output is mailed and discarded on MTA-less boxes, and launchd
defaults to ``/dev/null``.

Judgment (consent to install, time-of-night) lives in the
``sr-initialize`` skill prose; this module is mechanism only. All
external effects run through injectable seams (``crontab`` /
``launchctl`` runners, ``which``, the cron-daemon check, the
LaunchAgents dir), mirroring the engine-wide injection precedent.

Design record: ``memory-bank/active/creative/creative-scheduling-surface.md``.
"""

import argparse
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from stockroom import warehouse

#: Default nightly fire time (24-hour ``HH:MM``).
DEFAULT_TIME = "03:30"

#: Markers delimiting the managed crontab block. Everything between them
#: (inclusive) is owned by this module; no other line is ever touched.
MARKER_BEGIN = (
    "# BEGIN stockroom nightly (managed by 'stockroom schedule' - do not edit)"
)
MARKER_END = "# END stockroom nightly"

#: launchd job label; the owned plist is ``<label>.plist`` in the agents dir.
PLIST_LABEL = "jp.ne.cani.stockroom.nightly"

#: Default LaunchAgents directory (macOS per-user agents).
DEFAULT_AGENTS_DIR = Path("~/Library/LaunchAgents")

#: Strict 24-hour ``HH:MM`` (two digits each, 00:00–23:59).
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

#: The shim-not-on-PATH refusal (the errmsg ratchet: names the fix).
_SHIM_MISSING = (
    "the 'stockroom' command is not on PATH — bind the shim first "
    "(run sr-initialize, or 'make shim' from a dev checkout)"
)

#: The dead-daemon warning (install proceeds; the operator must know).
_DAEMON_WARNING = (
    "cron daemon is not running — the nightly job cannot fire until it is "
    "(WSL: 'sudo service cron start', or enable systemd in /etc/wsl.conf)"
)

#: An injectable ``crontab`` runner: takes the argument list (after the
#: executable) and optional stdin text, returns stdout text, raising
#: :class:`subprocess.CalledProcessError` on failure.
CrontabRunner = Callable[..., str]

#: An injectable ``launchctl`` runner: takes the argument list (after the
#: executable), returns stdout text, raising on failure.
LaunchctlRunner = Callable[[list[str]], str]

#: An injectable ``shutil.which``-shaped resolver.
Which = Callable[[str], str | None]


@dataclass
class ScheduleReport:
    """Outcome of an install/remove call.

    ``action`` is one of ``installed`` / ``removed`` / ``noop`` /
    ``refused``. ``detail`` carries the schedule line (cron) or interval
    (launchd) on success, and the human-readable reason otherwise.
    ``warnings`` are non-fatal report lines (e.g. the cron daemon is not
    running) — the install still happened, but the operator must know.
    """

    action: str
    detail: str = ""
    warnings: list[str] = field(default_factory=list)


def parse_time(value: str) -> tuple[int, int]:
    """Parse a strict 24-hour ``HH:MM`` string into ``(hour, minute)``.

    Raises :class:`ValueError` naming the expected ``HH:MM`` format for
    anything else (``9:5``, ``24:00``, ``abc``, …).
    """
    match = _TIME_RE.match(value)
    if match is None:
        raise ValueError(
            f"invalid time {value!r} — expected 24-hour HH:MM (e.g. 03:30)"
        )
    return int(match.group(1)), int(match.group(2))


def _log_path(home: Path) -> Path:
    """Return the nightly log path under ``home`` (not created here)."""
    return home / "logs" / "nightly.log"


def render_payload(home: Path) -> str:
    """Render the shared nightly shell payload for ``home``.

    The one place the entry content is decided, used verbatim by both
    platforms: ``date; stockroom ingest && stockroom embed`` with
    stdout+stderr appended to ``<home>/logs/nightly.log``. Invokes the
    shim by name (never an engine path) and contains no ``%`` (cron
    newline syntax).
    """
    payload = f"date; stockroom ingest && stockroom embed >> {_log_path(home)} 2>&1"
    assert "%" not in payload, "cron treats % as newline — payload must be %-free"
    return payload


def default_daemon_check(*, run: Callable = subprocess.run) -> bool:
    """Return True iff a cron daemon (``cron`` or ``crond``) is running.

    Probes with ``pgrep -x`` for both names (distro variance: Debian/WSL
    ships ``cron``, RHEL-family ships ``crond``). Any probe failure
    (``pgrep`` absent, nonzero exit) degrades to False — the caller
    reports a warning, never an error.
    """
    for name in ("cron", "crond"):
        try:
            result = run(["pgrep", "-x", name], capture_output=True, timeout=10)
        except Exception:
            return False
        if result.returncode == 0:
            return True
    return False


def _path_prefix(which: Which) -> str | None:
    """Resolve the entry's absolute ``PATH`` from the shim and uv locations.

    Returns ``None`` when the shim does not resolve (the shared refusal).
    The uv dir rides along when present — the shim execs ``uv``, which
    must also resolve under the scheduler's minimal environment.
    """
    shim = which("stockroom")
    if shim is None:
        return None
    dirs = [str(Path(shim).parent)]
    uv = which("uv")
    if uv is not None and str(Path(uv).parent) not in dirs:
        dirs.append(str(Path(uv).parent))
    return ":".join([*dirs, "/usr/bin", "/bin"])


def _sh_wrap(payload: str) -> str:
    """Wrap the payload for a scheduler entry: ``/bin/sh -c '<payload>'``.

    The wrapper is load-bearing on cron: a POSIX ``PATH=`` assignment may
    only prefix a *simple* command, so it cannot sit directly before the
    payload's ``&&`` list. The payload never contains a single quote.
    """
    assert "'" not in payload
    return f"/bin/sh -c '{payload}'"


def _run_crontab(args: list[str], input: str | None = None) -> str:
    """Run ``crontab`` with ``args``; return stdout or raise on failure."""
    return subprocess.run(
        ["crontab", *args],
        input=input,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout


def _read_crontab(runner: CrontabRunner) -> str:
    """Return the current crontab text; a missing crontab is empty."""
    try:
        return runner(["-l"])
    except subprocess.CalledProcessError:
        # "no crontab for <user>" — an empty crontab, not an error.
        return ""


def _strip_managed_block(text: str) -> str:
    """Remove the marker-delimited managed block, preserving all else.

    Foreign lines pass through byte-for-byte; only lines between (and
    including) the BEGIN/END markers are dropped.
    """
    kept: list[str] = []
    inside = False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if stripped == MARKER_BEGIN:
            inside = True
            continue
        if stripped == MARKER_END:
            inside = False
            continue
        if not inside:
            kept.append(line)
    return "".join(kept)


def _managed_block_line(text: str) -> str | None:
    """Return the schedule line inside the managed block, or ``None``."""
    lines = text.splitlines()
    try:
        begin = lines.index(MARKER_BEGIN)
        end = lines.index(MARKER_END)
    except ValueError:
        return None
    body = lines[begin + 1 : end]
    return body[0] if body else None


def cron_install(
    hour: int,
    minute: int,
    *,
    home: Path | None = None,
    crontab_runner: CrontabRunner | None = None,
    which: Which = shutil.which,
    daemon_check: Callable[[], bool] | None = None,
) -> ScheduleReport:
    """Install (or replace) the managed nightly block in the user crontab.

    Reads the current crontab (a missing crontab is an empty one), strips
    any existing managed block, appends a fresh one, and writes back —
    foreign lines pass through byte-for-byte, and re-install is
    idempotent by construction. Refuses (no write) when the ``stockroom``
    shim is not on ``PATH``; a not-running cron daemon still installs but
    the report carries a warning naming the fix. Creates ``<home>/logs/``
    so the entry's redirection cannot fail on a missing directory.
    """
    home = home if home is not None else warehouse.home_dir()
    runner = crontab_runner if crontab_runner is not None else _run_crontab
    check = daemon_check if daemon_check is not None else default_daemon_check

    path_prefix = _path_prefix(which)
    if path_prefix is None:
        return ScheduleReport(action="refused", detail=_SHIM_MISSING)

    _log_path(home).parent.mkdir(parents=True, exist_ok=True)

    entry = f"{minute} {hour} * * * PATH={path_prefix} {_sh_wrap(render_payload(home))}"
    block = f"{MARKER_BEGIN}\n{entry}\n{MARKER_END}\n"

    current = _read_crontab(runner)
    remainder = _strip_managed_block(current)
    if remainder and not remainder.endswith("\n"):
        remainder += "\n"
    runner(["-"], input=remainder + block)

    warnings = [] if check() else [_DAEMON_WARNING]
    return ScheduleReport(action="installed", detail=entry, warnings=warnings)


def cron_remove(*, crontab_runner: CrontabRunner | None = None) -> ScheduleReport:
    """Strip the managed block from the user crontab, preserving all else.

    A clean no-op (``action="noop"``) when no managed block — or no
    crontab at all — exists.
    """
    runner = crontab_runner if crontab_runner is not None else _run_crontab
    current = _read_crontab(runner)
    if MARKER_BEGIN not in current:
        return ScheduleReport(action="noop", detail="not installed")
    runner(["-"], input=_strip_managed_block(current))
    return ScheduleReport(action="removed")


def cron_status(
    *,
    home: Path | None = None,
    crontab_runner: CrontabRunner | None = None,
    daemon_check: Callable[[], bool] | None = None,
) -> list[str]:
    """Report cron scheduling facts as printable lines (never an error).

    ``installed: <schedule line>`` or ``not installed``, plus a
    ``daemon: running|not running`` liveness fact and the
    ``log: <home>/logs/nightly.log`` location fact.
    """
    home = home if home is not None else warehouse.home_dir()
    runner = crontab_runner if crontab_runner is not None else _run_crontab
    check = daemon_check if daemon_check is not None else default_daemon_check

    entry = _managed_block_line(_read_crontab(runner))
    installed = f"installed: {entry}" if entry is not None else "not installed"
    daemon = "running" if check() else "not running"
    return [installed, f"daemon: {daemon}", f"log: {_log_path(home)}"]


def _plist_path(agents_dir: Path) -> Path:
    """Return the owned plist path inside ``agents_dir``."""
    return agents_dir / f"{PLIST_LABEL}.plist"


def _run_launchctl(args: list[str]) -> str:
    """Run ``launchctl`` with ``args``; return stdout or raise on failure."""
    return subprocess.run(
        ["launchctl", *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout


def _bootout(runner: LaunchctlRunner) -> None:
    """Boot the job out, tolerating the not-loaded failure."""
    try:
        runner(["bootout", f"gui/{os.getuid()}/{PLIST_LABEL}"])
    except Exception:
        pass  # not loaded — the expected first-install / already-removed case


def launchd_install(
    hour: int,
    minute: int,
    *,
    home: Path | None = None,
    agents_dir: Path | None = None,
    launchctl_runner: LaunchctlRunner | None = None,
    which: Which = shutil.which,
) -> ScheduleReport:
    """Write the owned nightly plist and (re)load it via ``launchctl``.

    Idempotency is file ownership: the plist is rewritten in place, then
    reloaded with ``bootout`` (not-loaded failures tolerated) followed by
    ``bootstrap gui/<uid>``. Shares the shim-on-PATH refusal and the
    log-dir creation with the cron half.
    """
    home = home if home is not None else warehouse.home_dir()
    agents_dir = (
        agents_dir if agents_dir is not None else DEFAULT_AGENTS_DIR.expanduser()
    )
    runner = launchctl_runner if launchctl_runner is not None else _run_launchctl

    path_prefix = _path_prefix(which)
    if path_prefix is None:
        return ScheduleReport(action="refused", detail=_SHIM_MISSING)

    log = _log_path(home)
    log.parent.mkdir(parents=True, exist_ok=True)

    # The plist routes stdout/stderr itself, so the payload carries no
    # shell redirection here — StandardOutPath/StandardErrorPath own it.
    payload = "date; stockroom ingest && stockroom embed"
    data = {
        "Label": PLIST_LABEL,
        "ProgramArguments": ["/bin/sh", "-c", payload],
        "EnvironmentVariables": {"PATH": path_prefix},
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
    }

    agents_dir.mkdir(parents=True, exist_ok=True)
    plist_path = _plist_path(agents_dir)
    with plist_path.open("wb") as fh:
        plistlib.dump(data, fh)

    _bootout(runner)
    runner(["bootstrap", f"gui/{os.getuid()}", str(plist_path)])
    return ScheduleReport(
        action="installed", detail=f"nightly at {hour:02d}:{minute:02d}"
    )


def launchd_remove(
    *,
    agents_dir: Path | None = None,
    launchctl_runner: LaunchctlRunner | None = None,
) -> ScheduleReport:
    """Bootout and delete the owned plist; a clean no-op when absent."""
    agents_dir = (
        agents_dir if agents_dir is not None else DEFAULT_AGENTS_DIR.expanduser()
    )
    runner = launchctl_runner if launchctl_runner is not None else _run_launchctl

    plist_path = _plist_path(agents_dir)
    if not plist_path.exists():
        return ScheduleReport(action="noop", detail="not installed")
    _bootout(runner)
    plist_path.unlink()
    return ScheduleReport(action="removed")


def launchd_status(
    *,
    home: Path | None = None,
    agents_dir: Path | None = None,
) -> list[str]:
    """Report launchd scheduling facts as printable lines (never an error).

    ``installed: nightly at HH:MM (<label>)`` read back from the plist's
    ``StartCalendarInterval``, or ``not installed``; always the same
    ``log:`` location fact as the cron half.
    """
    home = home if home is not None else warehouse.home_dir()
    agents_dir = (
        agents_dir if agents_dir is not None else DEFAULT_AGENTS_DIR.expanduser()
    )

    plist_path = _plist_path(agents_dir)
    if plist_path.exists():
        with plist_path.open("rb") as fh:
            data = plistlib.load(fh)
        interval = data.get("StartCalendarInterval", {})
        hour, minute = interval.get("Hour", 0), interval.get("Minute", 0)
        installed = f"installed: nightly at {hour:02d}:{minute:02d} ({PLIST_LABEL})"
    else:
        installed = "not installed"
    return [installed, f"log: {_log_path(home)}"]


def _parse_time_arg(value: str) -> tuple[int, int]:
    """argparse adapter: :func:`parse_time` with a clean exit-2 error."""
    try:
        return parse_time(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _build_parser() -> argparse.ArgumentParser:
    """Build the ``python -m stockroom.schedule`` parser (flat, like shim)."""
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.schedule",
        description=(
            "Manage the nightly 'stockroom ingest && stockroom embed' job on "
            "the platform scheduler (cron on Linux/WSL, launchd on macOS). "
            "install: write/replace the managed entry (idempotent); status: "
            "report installed state, daemon liveness, and the log location; "
            "remove: delete the managed entry."
        ),
    )
    parser.add_argument(
        "action",
        choices=("install", "status", "remove"),
        help="install: write the nightly entry; status: report facts; "
        "remove: delete the entry",
    )
    parser.add_argument(
        "--time",
        type=_parse_time_arg,
        default=DEFAULT_TIME,
        metavar="HH:MM",
        help=f"nightly fire time, 24-hour HH:MM (default: {DEFAULT_TIME})",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    system: Callable[[], str] = platform.system,
) -> int:
    """CLI: ``python -m stockroom.schedule {install|status|remove} [--time HH:MM]``.

    Dispatches on ``system()``: ``Linux`` → cron, ``Darwin`` → launchd,
    anything else → exit 1 naming WSL as the supported Windows path.
    ``install`` exits 1 on a shim-missing refusal (warnings are stderr
    lines, not failures); ``status`` and ``remove`` always exit 0.
    """
    args = _build_parser().parse_args(argv)
    hour, minute = args.time if isinstance(args.time, tuple) else parse_time(args.time)

    plat = system()
    if plat not in ("Linux", "Darwin"):
        print(
            f"stockroom schedule: unsupported platform '{plat}' — supported "
            "schedulers are cron (Linux; on Windows use WSL) and launchd (macOS)",
            file=sys.stderr,
        )
        return 1

    if args.action == "status":
        lines = cron_status() if plat == "Linux" else launchd_status()
        print("\n".join(lines))
        return 0

    if args.action == "remove":
        report = cron_remove() if plat == "Linux" else launchd_remove()
        if report.action == "removed":
            print("removed the nightly schedule entry")
        else:
            print("nothing to remove — no nightly schedule entry installed")
        return 0

    report = (
        cron_install(hour, minute) if plat == "Linux" else launchd_install(hour, minute)
    )
    if report.action == "refused":
        print(f"stockroom schedule: {report.detail}", file=sys.stderr)
        return 1
    print(f"installed nightly schedule: {report.detail}")
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
