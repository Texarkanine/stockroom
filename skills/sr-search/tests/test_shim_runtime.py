"""Runtime tests for the rendered shim script, run as a real subprocess.

The rendered ``~/.local/bin/stockroom`` is POSIX sh with **no policy**: check
uv, check the baked dir, exec — or refuse with exactly one stderr line. These
tests render real shims into tmp, execute them with a controlled ``PATH``
(a stub ``uv`` that prints its argv + ``PYTHONPATH``) and a fixture ``HOME``,
and assert the whole observable exec/refusal contract. No real uv, engine,
or home directory is ever touched.
"""

import subprocess
from pathlib import Path

import pytest

from stockroom import shim


@pytest.fixture
def engine_dir(tmp_path: Path) -> Path:
    """An alive fixture engine dir (has pyproject.toml + duckdb-ready venv)."""
    d = tmp_path / "engine"
    (d / "src").mkdir(parents=True)
    (d / "pyproject.toml").write_text("[project]\nname = 'stockroom'\n")
    _write_venv_python(d, succeed=True)
    return d


def _write_venv_python(engine: Path, *, succeed: bool) -> Path:
    """Install a stub ``.venv/bin/python`` that accepts ``-c import duckdb``.

    When ``succeed`` is True the stub exits 0 (env looks ready). When False it
    exits 1 so the shim's readiness refuse path can be asserted.
    """
    bin_dir = engine / ".venv" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    py = bin_dir / "python"
    if succeed:
        body = "#!/bin/sh\nexit 0\n"
    else:
        body = "#!/bin/sh\necho \"ModuleNotFoundError: No module named 'duckdb'\" >&2\nexit 1\n"
    py.write_text(body, encoding="utf-8")
    py.chmod(0o755)
    return py


@pytest.fixture
def write_shim(tmp_path: Path):
    """Return a factory rendering an executable shim for (app_dir, owner)."""

    def _write(app_dir: Path, owner: str) -> Path:
        dest = tmp_path / "bin" / "stockroom"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(shim.render(app_dir, owner))
        dest.chmod(0o755)
        return dest

    return _write


def _run(
    shim_path: Path, *args: str, path: str, home: Path
) -> subprocess.CompletedProcess:
    env = {"PATH": path, "HOME": str(home)}
    return subprocess.run(
        [str(shim_path), *args], env=env, capture_output=True, text=True
    )


def test_valid_dir_execs_with_torch_safe_contract(
    write_shim, engine_dir: Path, stub_uv: Path, tmp_path: Path
) -> None:
    """A valid baked dir execs into uv with the full torch-safe contract:
    correct --project APP_DIR, PYTHONPATH to $APP_DIR/src, --no-sync,
    --no-config, and the dispatcher module."""
    shim_path = write_shim(engine_dir, "cursor")
    result = _run(shim_path, "query", path=str(stub_uv), home=tmp_path / "home")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    args = [ln.removeprefix("UV_ARG:") for ln in lines if ln.startswith("UV_ARG:")]
    pythonpath = next(
        ln.removeprefix("UV_PYTHONPATH:")
        for ln in lines
        if ln.startswith("UV_PYTHONPATH:")
    )
    assert pythonpath == f"{engine_dir}/src"
    assert args[0] == "run"
    assert "--no-sync" in args
    assert "--no-config" in args
    project_idx = args.index("--project")
    assert args[project_idx + 1] == str(engine_dir)
    assert args[-3:] == ["-m", "stockroom", "query"]


def test_args_forwarded_verbatim_including_spaces(
    write_shim, engine_dir: Path, stub_uv: Path, tmp_path: Path
) -> None:
    """Arguments (including embedded spaces) reach uv verbatim, unsplit."""
    shim_path = write_shim(engine_dir, "cursor")
    result = _run(
        shim_path,
        "query",
        "SELECT 1 AS n",
        path=str(stub_uv),
        home=tmp_path / "home",
    )
    assert result.returncode == 0, result.stderr
    args = [
        ln.removeprefix("UV_ARG:")
        for ln in result.stdout.splitlines()
        if ln.startswith("UV_ARG:")
    ]
    assert args[-2:] == ["query", "SELECT 1 AS n"]


@pytest.mark.parametrize(
    ("owner", "remedy_token"),
    [("cursor", "sr-initialize"), ("claude", "sr-initialize"), ("dev", "make shim")],
)
def test_invalid_dir_one_line_owner_remedy(
    write_shim,
    stub_uv: Path,
    tmp_path: Path,
    owner: str,
    remedy_token: str,
) -> None:
    """A dead baked dir refuses with exactly one stderr line naming the
    owner-appropriate remedy, nonzero exit, nothing on stdout."""
    dead = tmp_path / "gone-engine"
    shim_path = write_shim(dead, owner)
    result = _run(shim_path, "query", path=str(stub_uv), home=tmp_path / "home")
    assert result.returncode != 0
    assert result.stdout == ""
    stderr_lines = result.stderr.splitlines()
    assert len(stderr_lines) == 1
    assert remedy_token in stderr_lines[0]


def test_uv_missing_one_line_127(write_shim, engine_dir: Path, tmp_path: Path) -> None:
    """Without uv on PATH the shim fails with the single documented line
    and exit 127."""
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    shim_path = write_shim(engine_dir, "cursor")
    result = _run(shim_path, "query", path=str(empty_bin), home=tmp_path / "home")
    assert result.returncode == 127
    stderr_lines = result.stderr.splitlines()
    assert len(stderr_lines) == 1
    assert "uv not found" in stderr_lines[0]
    assert "sr-initialize" in stderr_lines[0]


@pytest.mark.parametrize(
    ("owner", "remedy_token"),
    [("cursor", "sr-initialize"), ("claude", "sr-initialize"), ("dev", "make shim")],
)
def test_env_not_ready_one_line_owner_remedy(
    write_shim,
    stub_uv: Path,
    tmp_path: Path,
    owner: str,
    remedy_token: str,
) -> None:
    """Pyproject present but venv cannot import duckdb → refuse with
    remedy before ``uv run --no-sync`` (no silent empty-venv path)."""
    engine = tmp_path / "engine-empty-env"
    (engine / "src").mkdir(parents=True)
    (engine / "pyproject.toml").write_text("[project]\nname = 'stockroom'\n")
    _write_venv_python(engine, succeed=False)
    shim_path = write_shim(engine, owner)
    result = _run(shim_path, "query", path=str(stub_uv), home=tmp_path / "home")
    assert result.returncode != 0
    assert result.stdout == ""
    stderr_lines = result.stderr.splitlines()
    assert len(stderr_lines) == 1
    assert "engine env" in stderr_lines[0] or "not ready" in stderr_lines[0]
    assert remedy_token in stderr_lines[0]
    # Stub uv must not have been exec'd (no UV_ARG lines).
    assert "UV_ARG:" not in result.stdout
