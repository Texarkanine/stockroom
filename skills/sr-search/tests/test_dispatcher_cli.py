"""End-to-end tests for the ``python -m stockroom`` dispatcher.

These run the dispatcher as a real subprocess (the ``test_query_cli.py``
convention). The dispatcher's contract is first-token dispatch with verbatim
forwarding: everything after the subcommand token is handled by the target
module's own argparse, and its exit code is returned unchanged. Torch-heavy
subcommands (``semantic``, ``embed``) are exercised via ``--help`` only —
both modules print help and exit before any encoder is constructed, so the
whole suite runs torch-free.
"""

import os
import subprocess
import sys
from pathlib import Path

import stockroom

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)

SUBCOMMANDS = (
    "query",
    "semantic",
    "ingest",
    "embed",
    "migrate",
    "shim",
    "doctor",
    "schedule",
    "dashboard",
)


def _base_env(home: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    env["STOCKROOM_HOME"] = str(home)
    return env


def _run(
    *args: str, home: Path, env_extra: dict | None = None
) -> subprocess.CompletedProcess:
    env = _base_env(home)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "stockroom", *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_top_level_help_lists_all_subcommands(tmp_path: Path) -> None:
    """``--help`` exits 0 and stdout names all five subcommands."""
    result = _run("--help", home=tmp_path / "home")
    assert result.returncode == 0, result.stderr
    for sub in SUBCOMMANDS:
        assert sub in result.stdout


def test_version_flag_prints_package_version(tmp_path: Path) -> None:
    """``--version`` exits 0 and prints ``stockroom.__version__``."""
    result = _run("--version", home=tmp_path / "home")
    assert result.returncode == 0, result.stderr
    assert stockroom.__version__ in result.stdout


def test_no_args_prints_usage_to_stderr(tmp_path: Path) -> None:
    """No arguments exits 2 with usage on stderr."""
    result = _run(home=tmp_path / "home")
    assert result.returncode == 2
    assert "usage" in result.stderr.lower()


def test_unknown_subcommand_is_clean_error(tmp_path: Path) -> None:
    """An unknown token exits 2, names the token on stderr, no traceback."""
    result = _run("bogus", home=tmp_path / "home")
    assert result.returncode == 2
    assert "bogus" in result.stderr
    assert "Traceback" not in result.stderr


def test_help_forwards_to_each_module(tmp_path: Path) -> None:
    """``<sub> --help`` exits 0 for every subcommand and shows help text that
    is identifiably the target module's own (a module-unique flag or phrase)."""
    # A module-unique fingerprint from each target's existing argparse help.
    fingerprints = {
        "query": "SQL",
        "semantic": "--limit",
        "ingest": "--harness",
        "embed": "Re-embed",
        "migrate": "schema",
        "shim": "rectify",
        "torch": "--index",
        "doctor": "probe",
        "schedule": "--time",
        "dashboard": "--foreground",
    }
    for sub in SUBCOMMANDS:
        result = _run(sub, "--help", home=tmp_path / "home")
        assert result.returncode == 0, f"{sub}: {result.stderr}"
        assert fingerprints[sub] in result.stdout, f"{sub} help missing fingerprint"


def test_dispatch_runs_query_for_real(
    tmp_path: Path, cursor_root: Path, claude_root: Path, ai_tracking_db: Path
) -> None:
    """``stockroom query "SELECT 1 AS n"`` against an ingested warehouse exits
    0 with the same TSV output as ``python -m stockroom.query``."""
    home = tmp_path / "home"
    env_extra = {
        "STOCKROOM_CURSOR_ROOT": str(cursor_root),
        "STOCKROOM_CLAUDE_ROOT": str(claude_root),
        "STOCKROOM_AI_TRACKING_DB": str(ai_tracking_db),
    }
    ingested = _run("ingest", "--full", home=home, env_extra=env_extra)
    assert ingested.returncode == 0, ingested.stderr

    via_dispatcher = _run("query", "SELECT 1 AS n", home=home)
    assert via_dispatcher.returncode == 0, via_dispatcher.stderr

    direct = subprocess.run(
        [sys.executable, "-m", "stockroom.query", "SELECT 1 AS n"],
        env=_base_env(home),
        capture_output=True,
        text=True,
    )
    assert direct.returncode == 0, direct.stderr
    assert via_dispatcher.stdout == direct.stdout


def test_exit_codes_propagate_from_module(tmp_path: Path) -> None:
    """The module's own exit codes pass through unchanged: empty SQL → 2;
    missing warehouse → 1 with the module's 'run ingest first' hint."""
    empty_sql = _run("query", "   ", home=tmp_path / "home")
    assert empty_sql.returncode == 2

    no_warehouse = _run("query", "SELECT 1", home=tmp_path / "empty-home")
    assert no_warehouse.returncode == 1
    assert "ingest" in no_warehouse.stderr.lower()


def test_dispatch_migrate_bootstraps_warehouse(tmp_path: Path) -> None:
    """``stockroom migrate`` on a fresh home exits 0 and creates the
    warehouse file (locks the dispatch wiring end to end)."""
    home = tmp_path / "home"
    result = _run("migrate", home=home)
    assert result.returncode == 0, result.stderr
    assert (home / "warehouse.duckdb").is_file()
