"""Unit tests for ``stockroom.doctor`` — probe facts and the loud-failing smoke.

``probe_facts`` is exercised fully torch-free via the injectable
``nvidia-smi`` runner and torch importer (B1–B7): facts are reported for
every environment shape, and no subprocess or import failure ever raises.
``run_smoke``'s failure shapes are covered via injected fakes (B8–B11) —
each failure must print exactly one stderr line that carries the *next
action* (the errmsg ratchet), not just name the problem. The single real
torch/encoder path (B12) is ``importorskip("torch")``-gated per the
engine-wide convention.
"""

import subprocess
import sys
import types

import pytest

from stockroom import doctor
from stockroom.embed import EMBED_DIM
from stockroom.shim import default_app_dir

# --- injectable stand-ins -------------------------------------------------


def _smi_absent(args: list[str]) -> str:
    """A machine with no nvidia-smi on PATH."""
    raise FileNotFoundError("nvidia-smi")


def _smi_failing(args: list[str]) -> str:
    """nvidia-smi present but erroring (e.g. no driver loaded)."""
    raise subprocess.CalledProcessError(1, ["nvidia-smi", *args])


def _smi_garbage(args: list[str]) -> str:
    """nvidia-smi present but emitting nothing parseable."""
    return "ERR!\n"


def _smi_ok(args: list[str]) -> str:
    """A healthy CUDA box (real output shapes captured from a live machine)."""
    if any(arg.startswith("--query-gpu=") for arg in args):
        return "NVIDIA GeForce GTX 1070, 582.28, 6.1\n"
    return (
        "NVIDIA-SMI version  : 580.126.10\n"
        "NVML version        : 580.126\n"
        "DRIVER version      : 582.28\n"
        "CUDA Version        : 13.0\n"
    )


def _import_absent(name: str) -> object:
    """An importer for an environment where torch is not installed."""
    raise ImportError(f"No module named '{name}'")


def _fake_torch(version: str = "2.11.0", cuda: bool = True) -> object:
    """A minimal stand-in exposing __version__ and cuda.is_available()."""
    module = types.SimpleNamespace()
    module.__version__ = version
    module.cuda = types.SimpleNamespace(is_available=lambda: cuda)
    return module


def _importer_for(module: object):
    """An importer that returns ``module`` for 'torch'."""

    def _import(name: str) -> object:
        assert name == "torch"
        return module

    return _import


class _GoodEncoder:
    """Encodes every string to a correct-width constant vector."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.5] * EMBED_DIM for _ in texts]


class _WrongWidthEncoder:
    """Encodes to a vector of the wrong dimension (a broken setup)."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.5] * (EMBED_DIM - 1) for _ in texts]


class _ExplodingEncoder:
    """Raises from encode — the wrong-wheel kernel-crash surface."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("CUDA error: no kernel image is available")


# --- probe: facts, torch-free, never crashes (B1–B7) ----------------------


def _probe(**kwargs) -> dict[str, str]:
    """Run probe_facts with torch absent by default; return facts as a dict."""
    kwargs.setdefault("torch_importer", _import_absent)
    kwargs.setdefault("smi_runner", _smi_absent)
    facts = doctor.probe_facts(**kwargs)
    keys = [key for key, _ in facts]
    assert len(keys) == len(set(keys)), f"duplicate fact keys: {keys}"
    return dict(facts)


def test_probe_reports_os_and_arch() -> None:
    """B1: os/arch come from the platform module as stable facts."""
    import platform

    facts = _probe()
    assert facts["os"] == platform.system()
    assert facts["arch"] == platform.machine()


def test_probe_reports_gpu_and_driver_when_smi_parseable() -> None:
    """B2: a healthy nvidia-smi yields GPU name, driver, driver CUDA
    ceiling, and the compute capability (the sm_ generation input)."""
    facts = _probe(smi_runner=_smi_ok)
    assert facts["gpu"] == "NVIDIA GeForce GTX 1070"
    assert facts["driver"] == "582.28"
    assert facts["driver-cuda"] == "13.0"
    assert facts["gpu-compute-cap"] == "6.1"


def test_probe_reports_gpu_none_when_smi_absent() -> None:
    """B3: no nvidia-smi on PATH is a fact (gpu: none), never an error."""
    facts = _probe(smi_runner=_smi_absent)
    assert facts["gpu"] == "none"
    assert "driver" not in facts
    assert "driver-cuda" not in facts


@pytest.mark.parametrize("runner", [_smi_failing, _smi_garbage])
def test_probe_degrades_gracefully_on_smi_failure(runner) -> None:
    """B4: an erroring or garbage-emitting nvidia-smi degrades to an
    'unavailable' fact — no traceback, no raise."""
    facts = _probe(smi_runner=runner)
    assert facts["gpu"] == "unavailable"


def test_probe_reports_torch_not_installed() -> None:
    """B5: an unimportable torch is a reported fact."""
    facts = _probe(torch_importer=_import_absent)
    assert facts["torch"] == "not installed"
    assert "torch-cuda" not in facts


def test_probe_reports_torch_version_and_cuda() -> None:
    """B6: an importable torch yields its version and CUDA availability."""
    facts = _probe(torch_importer=_importer_for(_fake_torch("2.11.0", cuda=True)))
    assert facts["torch"] == "2.11.0"
    assert facts["torch-cuda"] == "True"


def test_probe_reports_engine_dir() -> None:
    """The engine dir fact names where the engine environment lives."""
    facts = _probe()
    assert facts["engine-dir"] == str(default_app_dir())


def test_probe_never_imports_torch_eagerly() -> None:
    """B7: importing the module and probing goes through the injected
    importer only — the real torch is never touched."""
    calls: list[str] = []

    def recording_importer(name: str) -> object:
        calls.append(name)
        raise ImportError(name)

    already_loaded = "torch" in sys.modules
    facts = _probe(torch_importer=recording_importer)
    assert calls == ["torch"]
    assert facts["torch"] == "not installed"
    if not already_loaded:
        assert "torch" not in sys.modules


def test_format_facts_renders_key_value_lines() -> None:
    """format_facts emits one aligned ``key: value`` line per fact."""
    text = doctor.format_facts([("os", "Linux"), ("gpu-compute-cap", "6.1")])
    lines = text.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("os:")
    assert lines[0].endswith("Linux")
    assert lines[1].startswith("gpu-compute-cap:")
    assert lines[1].endswith("6.1")


# --- smoke: loud-failing verification (B8–B12) -----------------------------


def _one_stderr_line(capsys) -> str:
    """Assert stderr is exactly one line (no traceback) and return it."""
    err = capsys.readouterr().err
    lines = [line for line in err.splitlines() if line]
    assert len(lines) == 1, f"expected one stderr line, got: {err!r}"
    assert "Traceback" not in err
    return lines[0]


def test_smoke_torch_missing_is_ratcheted_diagnosis(capsys) -> None:
    """B8: missing torch → exit 1, one stderr line that names the engine
    environment and carries the literal provisioning command."""
    code = doctor.run_smoke(torch_importer=_import_absent, encoder_factory=_GoodEncoder)
    assert code == 1
    line = _one_stderr_line(capsys)
    assert str(default_app_dir()) in line
    assert "uv pip install torch --no-config --index" in line
    # --directory, not --project: uv pip only finds the engine venv via the
    # working directory, so a --project remedy would be a dead command.
    assert f"--directory {default_app_dir()}" in line


def test_smoke_encoder_failure_names_error_and_next_action(capsys) -> None:
    """B9: an exploding encode (the wrong-wheel crash shape) → exit 1, one
    stderr line naming the failure plus the re-pick remedy."""
    code = doctor.run_smoke(
        torch_importer=_importer_for(_fake_torch()),
        encoder_factory=_ExplodingEncoder,
    )
    assert code == 1
    line = _one_stderr_line(capsys)
    assert "no kernel image" in line
    assert "sr-initialize" in line
    assert "index" in line


def test_smoke_encoder_construction_failure_is_caught(capsys) -> None:
    """B9 (construction half): an encoder factory that raises is compressed
    to the same one-line actionable failure."""

    def exploding_factory() -> object:
        raise OSError("model download failed")

    code = doctor.run_smoke(
        torch_importer=_importer_for(_fake_torch()),
        encoder_factory=exploding_factory,
    )
    assert code == 1
    line = _one_stderr_line(capsys)
    assert "model download failed" in line
    assert "sr-initialize" in line


def test_smoke_wrong_width_vector_is_a_failure(capsys) -> None:
    """B10: a wrong-width vector is a broken setup, not success — exit 1
    with the actionable re-pick line."""
    code = doctor.run_smoke(
        torch_importer=_importer_for(_fake_torch()),
        encoder_factory=_WrongWidthEncoder,
    )
    assert code == 1
    line = _one_stderr_line(capsys)
    assert str(EMBED_DIM) in line
    assert "sr-initialize" in line


def test_smoke_happy_path_reports_version_cuda_and_ok(capsys) -> None:
    """B11: torch + encoder healthy → exit 0; stdout carries the torch
    version, the CUDA availability, and an ok summary."""
    code = doctor.run_smoke(
        torch_importer=_importer_for(_fake_torch("2.11.0", cuda=False)),
        encoder_factory=_GoodEncoder,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "2.11.0" in out
    assert "False" in out
    assert "ok" in out


def test_smoke_real_model_end_to_end(capsys) -> None:
    """B12: with real torch provisioned, the production BgeEncoder path
    encodes one string and exits 0 (machine-local; skipped on torch-free CI)."""
    pytest.importorskip("torch")
    code = doctor.run_smoke()
    assert code == 0
    out = capsys.readouterr().out
    assert "ok" in out
