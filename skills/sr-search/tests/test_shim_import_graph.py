"""Import-graph pins for session-start heal bootstrap (issue #25).

Heal must be reachable on a bare ``uv python find`` interpreter that has no
project site-packages. That requires ``stockroom.shim`` (and the dispatcher
path into it) not to import DuckDB at module load.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import stockroom

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    return env


def _assert_import_does_not_load_duckdb(module: str) -> None:
    """Run ``import <module>`` in a clean subprocess; duckdb must stay unloaded."""
    probe = (
        "import sys; "
        f"import {module}; "
        "assert 'duckdb' not in sys.modules, "
        f'"duckdb loaded via {module}: " + '
        "str(sorted(k for k in sys.modules if 'duck' in k.lower()))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        env=_subprocess_env(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"import {module} must succeed without loading duckdb\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_importing_stockroom_shim_does_not_load_duckdb() -> None:
    """``import stockroom.shim`` must not pull DuckDB (heal entrypoint)."""
    _assert_import_does_not_load_duckdb("stockroom.shim")


def test_dispatcher_shim_help_does_not_load_duckdb() -> None:
    """``python -m stockroom shim --help`` must not import DuckDB."""
    probe = (
        "import sys; "
        "from stockroom.__main__ import main; "
        "code = main(['shim', '--help']); "
        "assert code == 0, code; "
        "assert 'duckdb' not in sys.modules, "
        '"duckdb loaded via dispatcher shim --help: " + '
        "str(sorted(k for k in sys.modules if 'duck' in k.lower()))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        env=_subprocess_env(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "dispatcher shim --help must succeed without loading duckdb\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_importing_torch_source_does_not_load_duckdb() -> None:
    """``import stockroom.torch_source`` must not pull DuckDB (heal stack)."""
    _assert_import_does_not_load_duckdb("stockroom.torch_source")
