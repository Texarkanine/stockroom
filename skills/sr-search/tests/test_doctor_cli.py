"""End-to-end tests for the ``stockroom.doctor`` CLI (subprocess convention).

Runs ``python -m stockroom.doctor`` as a real subprocess. CI is torch-free
by construction (it never provisions torch), so ``probe`` must still exit 0
with torch reported as a fact and ``smoke`` must produce the one-line
ratcheted diagnosis — remedy command included — with exit 1
(CI-testable loud failure). This is the complement of the
``importorskip("torch")`` real-model smoke: on a torch-provisioned dev box
it skips (the subprocess would genuinely succeed) while the real-model test
runs, and vice versa on CI.

Both smoke remediations are exercised here under an isolated
``STOCKROOM_HOME`` (empty → pip; written usable freeze → ensure-env) so
ambient freezes cannot change which remedy string is asserted. Unit tests
in ``test_doctor.py`` still cover the same branches in-process with fakes.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

import stockroom

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)

_USABLE_FREEZE = (
    "--index-url https://download.pytorch.org/whl/cpu\n"
    "torch==2.7.1+cpu \\\n"
    "    --hash=sha256:deadbeef\n"
)


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    run_env = os.environ.copy()
    run_env["PYTHONPATH"] = os.pathsep.join(
        [_SRC_DIR, run_env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    if env:
        run_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "stockroom.doctor", *args],
        env=run_env,
        capture_output=True,
        text=True,
    )


def _skip_if_torch_provisioned() -> None:
    if importlib.util.find_spec("torch") is not None:
        pytest.skip("torch is provisioned here — the real-model smoke covers this env")


def _one_stderr_line(result: subprocess.CompletedProcess) -> str:
    lines = [line for line in result.stderr.splitlines() if line]
    assert len(lines) == 1, f"expected one stderr line, got: {result.stderr!r}"
    assert "Traceback" not in result.stderr
    return lines[0]


def test_probe_exits_zero_and_prints_fact_keys() -> None:
    """``doctor probe`` in a torch-free env exits 0 and reports the
    always-present fact keys."""
    result = _run("probe")
    assert result.returncode == 0, result.stderr
    for key in (
        "os:",
        "arch:",
        "gpu:",
        "torch:",
        "engine-dir:",
        "home:",
        "home-source:",
    ):
        assert key in result.stdout, f"missing fact {key!r} in: {result.stdout}"


def test_smoke_torch_free_env_fails_loudly_with_remedy(tmp_path: Path) -> None:
    """``doctor smoke`` without torch exits 1 with the one-line
    ratcheted no-freeze provisioning remedy (home isolated from ambient)."""
    _skip_if_torch_provisioned()
    home = tmp_path / "stockroom-home"
    home.mkdir()
    result = _run("smoke", env={"STOCKROOM_HOME": str(home)})
    assert result.returncode == 1
    line = _one_stderr_line(result)
    assert "uv pip install torch --no-config --index" in line
    assert "ensure-env" not in line


def test_smoke_torch_free_env_with_freeze_names_ensure_env(tmp_path: Path) -> None:
    """``doctor smoke`` without torch + usable freeze → ensure-env remedy
    (subprocess must honor STOCKROOM_HOME, not the operator's real home)."""
    _skip_if_torch_provisioned()
    home = tmp_path / "stockroom-home"
    home.mkdir()
    (home / "torch-requirements.txt").write_text(_USABLE_FREEZE, encoding="utf-8")
    result = _run("smoke", env={"STOCKROOM_HOME": str(home)})
    assert result.returncode == 1
    line = _one_stderr_line(result)
    assert "stockroom shim ensure-env" in line
    assert "uv pip install torch" not in line


def test_help_documents_both_actions() -> None:
    """``doctor --help`` exits 0 and documents probe and smoke."""
    result = _run("--help")
    assert result.returncode == 0, result.stderr
    assert "probe" in result.stdout
    assert "smoke" in result.stdout
