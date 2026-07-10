"""End-to-end tests for the ``stockroom.doctor`` CLI (subprocess convention).

Runs ``python -m stockroom.doctor`` as a real subprocess. CI is torch-free
by construction (it never provisions torch), so ``probe`` must still exit 0
with torch reported as a fact (B13) and ``smoke`` must produce the one-line
ratcheted diagnosis — remedy command included — with exit 1 (B14, the
CI-testable loud failure). B14 is the complement of the
``importorskip("torch")`` real-model smoke: on a torch-provisioned dev box
it skips (the subprocess would genuinely succeed) while the real-model test
runs, and vice versa on CI.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

import stockroom

_SRC_DIR = str(Path(stockroom.__file__).parent.parent)


def _run(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC_DIR, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    return subprocess.run(
        [sys.executable, "-m", "stockroom.doctor", *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_probe_exits_zero_and_prints_fact_keys() -> None:
    """B13: ``doctor probe`` in a torch-free env exits 0 and reports the
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


def test_smoke_torch_free_env_fails_loudly_with_remedy() -> None:
    """B14: ``doctor smoke`` without torch exits 1 with the one-line
    ratcheted diagnosis carrying the literal provisioning command."""
    if importlib.util.find_spec("torch") is not None:
        pytest.skip("torch is provisioned here — the real-model smoke covers this env")
    result = _run("smoke")
    assert result.returncode == 1
    lines = [line for line in result.stderr.splitlines() if line]
    assert len(lines) == 1, f"expected one stderr line, got: {result.stderr!r}"
    assert "Traceback" not in result.stderr
    assert "uv pip install torch --no-config --index" in lines[0]


def test_help_documents_both_actions() -> None:
    """B15: ``doctor --help`` exits 0 and documents probe and smoke."""
    result = _run("--help")
    assert result.returncode == 0, result.stderr
    assert "probe" in result.stdout
    assert "smoke" in result.stdout
