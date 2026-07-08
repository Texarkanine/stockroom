"""End-to-end tests for the ``stockroom shim`` CLI (subprocess convention).

Runs ``python -m stockroom.shim`` (and the dispatcher-forwarded form) as a
real subprocess against tmp destinations and fixture engine dirs — never the
real ``~/.local/bin``. Exit-code contract: ``install`` refusals are nonzero
(the caller must notice), ``rectify`` no-ops are zero (the hook's designed
steady state must never look like a failure).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import stockroom

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)


@pytest.fixture
def engine_dir(tmp_path: Path) -> Path:
    """An alive fixture engine dir (has pyproject.toml)."""
    d = tmp_path / "engine"
    (d / "src").mkdir(parents=True)
    (d / "pyproject.toml").write_text("[project]\nname = 'stockroom'\n")
    return d


@pytest.fixture
def other_engine_dir(tmp_path: Path) -> Path:
    """A second alive fixture engine dir."""
    d = tmp_path / "engine-2"
    (d / "src").mkdir(parents=True)
    (d / "pyproject.toml").write_text("[project]\nname = 'stockroom'\n")
    return d


@pytest.fixture
def dest(tmp_path: Path) -> Path:
    return tmp_path / "bin" / "stockroom"


def _run(*args: str, tmp_path: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    # Keep every dest dir off PATH so installs never attempt the verify.
    off_path = tmp_path / "off-path"
    off_path.mkdir(exist_ok=True)
    env["PATH"] = str(off_path)
    return subprocess.run(
        [sys.executable, "-m", "stockroom.shim", *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_help_documents_subactions_and_flags(tmp_path: Path) -> None:
    """``--help`` exits 0 and names install, rectify, and the flags."""
    result = _run("--help", tmp_path=tmp_path)
    assert result.returncode == 0, result.stderr
    for token in ("install", "rectify", "--app-dir", "--dest", "--owner", "--takeover"):
        assert token in result.stdout


def test_install_writes_shim_and_exits_zero(
    tmp_path: Path, dest: Path, engine_dir: Path
) -> None:
    """A clean install via the CLI exits 0 and writes the executable shim."""
    result = _run(
        "install",
        "--dest",
        str(dest),
        "--app-dir",
        str(engine_dir),
        "--owner",
        "cursor",
        tmp_path=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert dest.is_file()
    assert dest.stat().st_mode & 0o777 == 0o755


def test_install_refusal_exits_nonzero(
    tmp_path: Path, dest: Path, engine_dir: Path, other_engine_dir: Path
) -> None:
    """An ownership refusal exits nonzero and names the incumbent owner."""
    first = _run(
        "install",
        "--dest",
        str(dest),
        "--app-dir",
        str(engine_dir),
        "--owner",
        "cursor",
        tmp_path=tmp_path,
    )
    assert first.returncode == 0, first.stderr
    second = _run(
        "install",
        "--dest",
        str(dest),
        "--app-dir",
        str(other_engine_dir),
        "--owner",
        "claude",
        tmp_path=tmp_path,
    )
    assert second.returncode != 0
    assert "cursor" in second.stderr


def test_rectify_noop_exits_zero(tmp_path: Path, dest: Path, engine_dir: Path) -> None:
    """rectify against an absent dest is the hook steady state: exit 0."""
    result = _run(
        "rectify",
        "--dest",
        str(dest),
        "--app-dir",
        str(engine_dir),
        "--owner",
        "cursor",
        tmp_path=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert not dest.exists()


def test_rectify_rebakes_moved_root(
    tmp_path: Path, dest: Path, engine_dir: Path, other_engine_dir: Path
) -> None:
    """Integration chain: install as owner A at root X, rectify to root Y →
    shim bakes Y; a foreign rectify leaves it unchanged."""
    install = _run(
        "install",
        "--dest",
        str(dest),
        "--app-dir",
        str(engine_dir),
        "--owner",
        "cursor",
        tmp_path=tmp_path,
    )
    assert install.returncode == 0, install.stderr

    moved = _run(
        "rectify",
        "--dest",
        str(dest),
        "--app-dir",
        str(other_engine_dir),
        "--owner",
        "cursor",
        tmp_path=tmp_path,
    )
    assert moved.returncode == 0, moved.stderr
    assert f"# STOCKROOM_APP_DIR={other_engine_dir}" in dest.read_text()

    foreign = _run(
        "rectify",
        "--dest",
        str(dest),
        "--app-dir",
        str(engine_dir),
        "--owner",
        "claude",
        tmp_path=tmp_path,
    )
    assert foreign.returncode == 0, foreign.stderr
    assert f"# STOCKROOM_APP_DIR={other_engine_dir}" in dest.read_text()


def test_dispatcher_forwards_shim(tmp_path: Path) -> None:
    """``python -m stockroom shim --help`` forwards to the module's help."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    result = subprocess.run(
        [sys.executable, "-m", "stockroom", "shim", "--help"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "rectify" in result.stdout


def test_full_chain_dispatcher_install_then_exec(
    tmp_path: Path, dest: Path, engine_dir: Path, stub_uv: Path
) -> None:
    """Torch-free full chain: install through the real dispatcher, then run
    the written shim with a stub uv and observe the exec contract."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    off_path = tmp_path / "off-path"
    off_path.mkdir(exist_ok=True)
    env["PATH"] = str(off_path)
    installed = subprocess.run(
        [
            sys.executable,
            "-m",
            "stockroom",
            "shim",
            "install",
            "--dest",
            str(dest),
            "--app-dir",
            str(engine_dir),
            "--owner",
            "dev",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert installed.returncode == 0, installed.stderr

    run = subprocess.run(
        [str(dest), "ingest", "--full"],
        env={"PATH": str(stub_uv), "HOME": str(tmp_path / "home")},
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    args = [
        ln.removeprefix("UV_ARG:")
        for ln in run.stdout.splitlines()
        if ln.startswith("UV_ARG:")
    ]
    assert args[-4:] == ["-m", "stockroom", "ingest", "--full"]
    project_idx = args.index("--project")
    assert args[project_idx + 1] == str(engine_dir)
