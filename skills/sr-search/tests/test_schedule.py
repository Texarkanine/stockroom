"""Unit tests for ``stockroom.schedule`` (injected-seam convention).

Covers the shared payload renderer and time
validation, the cron half (managed-block idempotency, foreign-line
preservation, the shim-on-PATH refusal, the daemon warning), the launchd
half (plist shape, idempotent re-install, tolerated bootout), and the
platform dispatch refusal. All external effects run through injected
seams (``crontab``/``launchctl`` runners, ``which``, the daemon check),
mirroring ``test_doctor.py``'s ``smi_runner`` precedent — no test here
touches a real crontab, launchd, or PATH.
"""

import plistlib
import subprocess
from pathlib import Path

import pytest

from stockroom import schedule
from stockroom.schedule import (
    MARKER_BEGIN,
    MARKER_END,
    PLIST_LABEL,
    cron_install,
    cron_remove,
    cron_status,
    launchd_install,
    launchd_remove,
    launchd_status,
    parse_time,
    render_payload,
)


class FakeCrontab:
    """An injected ``crontab`` runner backed by an in-memory string.

    ``initial=None`` models a user with no crontab at all: ``-l`` raises
    the "no crontab for user" failure exactly like the real binary. Every
    ``-`` write is recorded so tests can assert both the final content
    and that refusal paths never write.
    """

    def __init__(self, initial: str | None = None) -> None:
        self.content = initial
        self.writes: list[str] = []

    def __call__(self, args: list[str], input: str | None = None) -> str:
        if args == ["-l"]:
            if self.content is None:
                raise subprocess.CalledProcessError(
                    1, ["crontab", "-l"], stderr="no crontab for user"
                )
            return self.content
        if args == ["-"]:
            assert input is not None
            self.content = input
            self.writes.append(input)
            return ""
        raise AssertionError(f"unexpected crontab invocation: {args}")


class FakeLaunchctl:
    """An injected ``launchctl`` runner recording calls.

    ``bootout_fails=True`` models the not-loaded case (the real
    ``launchctl bootout`` exits nonzero when the job isn't loaded).
    """

    def __init__(self, *, bootout_fails: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.bootout_fails = bootout_fails

    def __call__(self, args: list[str]) -> str:
        self.calls.append(list(args))
        if args[0] == "bootout" and self.bootout_fails:
            raise subprocess.CalledProcessError(
                3, ["launchctl", *args], stderr="Boot-out failed: 3: No such process"
            )
        return ""


def fake_which(name: str) -> str | None:
    """Resolve the shim and uv to distinct absolute fake dirs."""
    return {"stockroom": "/fake/bin/stockroom", "uv": "/fake/uv-bin/uv"}.get(name)


def which_without_shim(name: str) -> str | None:
    """A PATH where the stockroom shim is missing but uv resolves."""
    return {"uv": "/fake/uv-bin/uv"}.get(name)


# ---------------------------------------------------------------------------
# shared payload rendering + time validation
# ---------------------------------------------------------------------------


def test_payload_invokes_shim_with_log_redirection(tmp_path: Path) -> None:
    """The payload runs date + ingest + embed through the shim by name,
    appending stdout+stderr of the *whole* command list (not just the last
    ``&&`` operand) to ``<home>/logs/nightly.log``."""
    payload = render_payload(tmp_path)
    assert (
        payload == "(date; stockroom ingest && stockroom embed)"
        f" >> {tmp_path}/logs/nightly.log 2>&1"
    )


def test_payload_is_home_aware(tmp_path: Path) -> None:
    """The log path follows the home the caller passes (STOCKROOM_HOME
    awareness lives in the caller's ``warehouse.home_dir()`` default)."""
    a = render_payload(tmp_path / "home-a")
    b = render_payload(tmp_path / "home-b")
    assert str(tmp_path / "home-a" / "logs" / "nightly.log") in a
    assert str(tmp_path / "home-b" / "logs" / "nightly.log") in b


def test_payload_contains_no_engine_path_and_no_percent(tmp_path: Path) -> None:
    """No raw engine path ever lands in a rendered entry, and the
    payload is ``%``-free (``%`` is newline in crontab syntax) — an explicit
    guard, not incidental."""
    payload = render_payload(tmp_path)
    assert "%" not in payload
    assert "sr-search" not in payload
    assert "python -m" not in payload


def test_parse_time_accepts_strict_hh_mm() -> None:
    """The default and a custom time parse to (hour, minute)."""
    assert parse_time("03:30") == (3, 30)
    assert parse_time("22:15") == (22, 15)
    assert parse_time("00:00") == (0, 0)
    assert parse_time("23:59") == (23, 59)


@pytest.mark.parametrize("bad", ["9:5", "24:00", "12:60", "abc", "1230", "12:3a", ""])
def test_parse_time_rejects_malformed_values(bad: str) -> None:
    """Anything but strict 24-hour HH:MM raises a ValueError naming
    the expected format."""
    with pytest.raises(ValueError, match="HH:MM"):
        parse_time(bad)


def test_cli_rejects_bad_time_with_clean_error(capsys: pytest.CaptureFixture) -> None:
    """At the CLI a malformed ``--time`` exits 2 with a clean error
    naming the HH:MM format (argparse, no traceback)."""
    with pytest.raises(SystemExit) as excinfo:
        schedule.main(["install", "--time", "9:5"], system=lambda: "Linux")
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "HH:MM" in err


# ---------------------------------------------------------------------------
# the cron half
# ---------------------------------------------------------------------------


def test_install_on_empty_crontab_writes_exactly_the_managed_block(
    tmp_path: Path,
) -> None:
    """With no pre-existing crontab ("no crontab for user" treated as
    empty) the written content is exactly the managed block: BEGIN marker,
    one schedule line (cron fields, absolute PATH= prefix from the injected
    which results, /bin/sh -c wrapper), END marker."""
    runner = FakeCrontab(initial=None)
    report = cron_install(
        3,
        30,
        home=tmp_path,
        crontab_runner=runner,
        which=fake_which,
        daemon_check=lambda: True,
    )
    assert report.action == "installed"
    assert len(runner.writes) == 1

    written = runner.writes[0]
    assert written.endswith("\n")
    lines = written.splitlines()
    assert lines[0] == MARKER_BEGIN
    assert lines[-1] == MARKER_END
    assert len(lines) == 3

    entry = lines[1]
    assert entry.startswith("30 3 * * * ")
    assert "PATH=" in entry
    assert "/fake/bin" in entry
    assert "/fake/uv-bin" in entry
    assert "/bin/sh -c " in entry


def test_install_preserves_foreign_lines_byte_for_byte(tmp_path: Path) -> None:
    """Pre-existing foreign crontab lines pass through unmodified, with
    the managed block appended after them."""
    foreign = "MAILTO=me@example.com\n0 5 * * * /usr/bin/foo --bar\n@reboot /opt/baz\n"
    runner = FakeCrontab(initial=foreign)
    report = cron_install(
        3,
        30,
        home=tmp_path,
        crontab_runner=runner,
        which=fake_which,
        daemon_check=lambda: True,
    )
    assert report.action == "installed"
    written = runner.writes[0]
    assert written.startswith(foreign)
    assert MARKER_BEGIN in written
    assert MARKER_END in written


def test_reinstall_replaces_the_managed_block(tmp_path: Path) -> None:
    """Installing over an existing managed block (different time) strips
    the old block and leaves exactly one fresh block — idempotent re-install."""
    foreign = "0 5 * * * /usr/bin/foo\n"
    runner = FakeCrontab(initial=None)
    cron_install(
        3,
        30,
        home=tmp_path,
        crontab_runner=runner,
        which=fake_which,
        daemon_check=lambda: True,
    )
    runner.content = foreign + runner.content  # foreign line above the block
    cron_install(
        22,
        15,
        home=tmp_path,
        crontab_runner=runner,
        which=fake_which,
        daemon_check=lambda: True,
    )

    final = runner.content
    assert final.count(MARKER_BEGIN) == 1
    assert final.count(MARKER_END) == 1
    assert "15 22 * * * " in final
    assert "30 3 * * * " not in final
    assert final.startswith(foreign)


def test_install_refuses_when_shim_not_on_path(tmp_path: Path) -> None:
    """A missing on-path shim refuses (no write) with a reason naming
    the fix — bind the shim first via sr-initialize / make shim."""
    runner = FakeCrontab(initial=None)
    report = cron_install(
        3,
        30,
        home=tmp_path,
        crontab_runner=runner,
        which=which_without_shim,
        daemon_check=lambda: True,
    )
    assert report.action == "refused"
    assert runner.writes == []
    assert "sr-initialize" in report.detail
    assert "make shim" in report.detail


def test_install_with_dead_daemon_still_writes_but_warns(tmp_path: Path) -> None:
    """A not-running cron daemon still installs, but the report carries
    a warning naming the fix; a running daemon produces no warning."""
    dead = FakeCrontab(initial=None)
    report = cron_install(
        3,
        30,
        home=tmp_path,
        crontab_runner=dead,
        which=fake_which,
        daemon_check=lambda: False,
    )
    assert report.action == "installed"
    assert len(dead.writes) == 1
    assert report.warnings
    assert any("sudo service cron start" in w for w in report.warnings)

    alive = FakeCrontab(initial=None)
    report = cron_install(
        3,
        30,
        home=tmp_path,
        crontab_runner=alive,
        which=fake_which,
        daemon_check=lambda: True,
    )
    assert report.action == "installed"
    assert report.warnings == []


def test_default_daemon_check_matches_cron_or_crond() -> None:
    """The default check accepts either daemon name (distro variance)
    and degrades any probe failure to False."""

    def run_only_crond(argv, **kwargs):
        ok = argv == ["pgrep", "-x", "crond"]
        return subprocess.CompletedProcess(argv, 0 if ok else 1)

    def run_nothing(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1)

    def run_missing(argv, **kwargs):
        raise FileNotFoundError("pgrep")

    assert schedule.default_daemon_check(run=run_only_crond) is True
    assert schedule.default_daemon_check(run=run_nothing) is False
    assert schedule.default_daemon_check(run=run_missing) is False


def test_remove_strips_block_and_preserves_foreign_lines(tmp_path: Path) -> None:
    """Remove strips exactly the managed block, leaving foreign lines
    byte-for-byte."""
    foreign = "0 5 * * * /usr/bin/foo\n"
    runner = FakeCrontab(initial=foreign)
    cron_install(
        3,
        30,
        home=tmp_path,
        crontab_runner=runner,
        which=fake_which,
        daemon_check=lambda: True,
    )
    assert MARKER_BEGIN in runner.content

    report = cron_remove(crontab_runner=runner)
    assert report.action == "removed"
    assert runner.content == foreign


def test_remove_is_a_clean_noop_without_a_block(tmp_path: Path) -> None:
    """Remove with no managed block — or no crontab at all — is a clean
    no-op that never writes."""
    no_block = FakeCrontab(initial="0 5 * * * /usr/bin/foo\n")
    report = cron_remove(crontab_runner=no_block)
    assert report.action == "noop"
    assert no_block.writes == []

    no_crontab = FakeCrontab(initial=None)
    report = cron_remove(crontab_runner=no_crontab)
    assert report.action == "noop"
    assert no_crontab.writes == []


def test_status_reports_installed_daemon_and_log_facts(tmp_path: Path) -> None:
    """Status reports the schedule line when the block exists, a daemon
    liveness fact, and the log location fact."""
    runner = FakeCrontab(initial=None)
    cron_install(
        3,
        30,
        home=tmp_path,
        crontab_runner=runner,
        which=fake_which,
        daemon_check=lambda: True,
    )
    lines = cron_status(home=tmp_path, crontab_runner=runner, daemon_check=lambda: True)
    text = "\n".join(lines)
    assert "installed" in text
    assert "30 3 * * * " in text
    assert "daemon: running" in text
    assert f"log: {tmp_path / 'logs' / 'nightly.log'}" in text


def test_status_reports_not_installed_and_dead_daemon(tmp_path: Path) -> None:
    """Without a managed block status says not installed; a dead daemon
    is reported as a fact (not an error); the log fact is always present."""
    runner = FakeCrontab(initial=None)
    lines = cron_status(
        home=tmp_path, crontab_runner=runner, daemon_check=lambda: False
    )
    text = "\n".join(lines)
    assert "not installed" in text
    assert "daemon: not running" in text
    assert f"log: {tmp_path / 'logs' / 'nightly.log'}" in text


def test_cron_install_creates_the_log_directory(tmp_path: Path) -> None:
    """Install creates ``<home>/logs/`` so the entry's redirection
    cannot fail on a missing directory at 03:30."""
    home = tmp_path / "fresh-home"
    assert not (home / "logs").exists()
    cron_install(
        3,
        30,
        home=home,
        crontab_runner=FakeCrontab(initial=None),
        which=fake_which,
        daemon_check=lambda: True,
    )
    assert (home / "logs").is_dir()


# ---------------------------------------------------------------------------
# the launchd half
# ---------------------------------------------------------------------------


def _agents(tmp_path: Path) -> Path:
    agents = tmp_path / "LaunchAgents"
    agents.mkdir(exist_ok=True)
    return agents


def test_launchd_install_writes_a_valid_plist(tmp_path: Path) -> None:
    """Install writes a plistlib-parseable plist with the owned label,
    the /bin/sh -c payload, an absolute PATH, the calendar interval, and
    stdout/stderr routed to the nightly log; launchctl is called
    bootout-then-bootstrap."""
    agents = _agents(tmp_path)
    launchctl = FakeLaunchctl()
    home = tmp_path / "home"
    report = launchd_install(
        3,
        30,
        home=home,
        agents_dir=agents,
        launchctl_runner=launchctl,
        which=fake_which,
    )
    assert report.action == "installed"

    plist_path = agents / f"{PLIST_LABEL}.plist"
    assert plist_path.is_file()
    with plist_path.open("rb") as fh:
        data = plistlib.load(fh)

    assert data["Label"] == PLIST_LABEL
    assert data["ProgramArguments"][:2] == ["/bin/sh", "-c"]
    payload = data["ProgramArguments"][2]
    assert payload == render_payload(home)  # the one shared renderer
    assert data["EnvironmentVariables"]["PATH"].startswith("/")
    assert "/fake/bin" in data["EnvironmentVariables"]["PATH"]
    assert data["StartCalendarInterval"] == {"Hour": 3, "Minute": 30}
    log = str(home / "logs" / "nightly.log")
    assert data["StandardOutPath"] == log
    assert data["StandardErrorPath"] == log
    assert (home / "logs").is_dir()

    assert launchctl.calls[0][0] == "bootout"
    assert launchctl.calls[1][0] == "bootstrap"
    assert str(plist_path) in launchctl.calls[1]


def test_launchd_install_tolerates_bootout_failure(tmp_path: Path) -> None:
    """A failing bootout (job not loaded) is tolerated — bootstrap
    still runs and the install succeeds."""
    agents = _agents(tmp_path)
    launchctl = FakeLaunchctl(bootout_fails=True)
    report = launchd_install(
        3,
        30,
        home=tmp_path / "home",
        agents_dir=agents,
        launchctl_runner=launchctl,
        which=fake_which,
    )
    assert report.action == "installed"
    assert [call[0] for call in launchctl.calls] == ["bootout", "bootstrap"]


def test_launchd_reinstall_rewrites_single_plist(tmp_path: Path) -> None:
    """Re-install rewrites the one owned plist in place (new time,
    still a single file)."""
    agents = _agents(tmp_path)
    home = tmp_path / "home"
    launchd_install(
        3,
        30,
        home=home,
        agents_dir=agents,
        launchctl_runner=FakeLaunchctl(),
        which=fake_which,
    )
    launchd_install(
        22,
        15,
        home=home,
        agents_dir=agents,
        launchctl_runner=FakeLaunchctl(),
        which=fake_which,
    )
    plists = list(agents.glob("*.plist"))
    assert len(plists) == 1
    with plists[0].open("rb") as fh:
        data = plistlib.load(fh)
    assert data["StartCalendarInterval"] == {"Hour": 22, "Minute": 15}


def test_launchd_remove_boots_out_and_deletes(tmp_path: Path) -> None:
    """Remove calls bootout and deletes the plist; removing when
    absent is a clean no-op with no launchctl calls."""
    agents = _agents(tmp_path)
    launchd_install(
        3,
        30,
        home=tmp_path / "home",
        agents_dir=agents,
        launchctl_runner=FakeLaunchctl(),
        which=fake_which,
    )
    launchctl = FakeLaunchctl()
    report = launchd_remove(agents_dir=agents, launchctl_runner=launchctl)
    assert report.action == "removed"
    assert not (agents / f"{PLIST_LABEL}.plist").exists()
    assert [call[0] for call in launchctl.calls] == ["bootout"]

    launchctl = FakeLaunchctl()
    report = launchd_remove(agents_dir=agents, launchctl_runner=launchctl)
    assert report.action == "noop"
    assert launchctl.calls == []


def test_launchd_status_reads_the_plist(tmp_path: Path) -> None:
    """Status reads the interval back from the plist when installed,
    says not installed otherwise, and always carries the log fact."""
    agents = _agents(tmp_path)
    home = tmp_path / "home"
    log_fact = f"log: {home / 'logs' / 'nightly.log'}"

    lines = launchd_status(home=home, agents_dir=agents)
    text = "\n".join(lines)
    assert "not installed" in text
    assert log_fact in text

    launchd_install(
        3,
        30,
        home=home,
        agents_dir=agents,
        launchctl_runner=FakeLaunchctl(),
        which=fake_which,
    )
    lines = launchd_status(home=home, agents_dir=agents)
    text = "\n".join(lines)
    assert "installed" in text
    assert "03:30" in text
    assert log_fact in text


def test_launchd_install_refuses_when_shim_not_on_path(tmp_path: Path) -> None:
    """The shim-on-PATH refusal is a shared guard — it applies on the
    launchd path too, with no plist written and no launchctl calls."""
    agents = _agents(tmp_path)
    launchctl = FakeLaunchctl()
    report = launchd_install(
        3,
        30,
        home=tmp_path / "home",
        agents_dir=agents,
        launchctl_runner=launchctl,
        which=which_without_shim,
    )
    assert report.action == "refused"
    assert "sr-initialize" in report.detail
    assert not (agents / f"{PLIST_LABEL}.plist").exists()
    assert launchctl.calls == []


# ---------------------------------------------------------------------------
# platform dispatch
# ---------------------------------------------------------------------------


def test_unsupported_platform_refuses_naming_wsl(
    capsys: pytest.CaptureFixture,
) -> None:
    """An unsupported platform exits 1 with a stderr line naming WSL
    as the supported Windows path."""
    code = schedule.main(["install"], system=lambda: "Windows")
    assert code == 1
    err = capsys.readouterr().err
    assert "WSL" in err
    assert "Traceback" not in err
