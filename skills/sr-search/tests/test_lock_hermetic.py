"""The committed lock is hermetic and torch-free; pyproject encodes the contract.

These assertions are the machine-checkable form of stockroom's central trust
promise (tech-brief -> "The Torch Exception"): everything is pinned and
hash-verified from PyPI, with torch (and its CUDA/nvidia transitives) held
entirely out of the cross-platform lock and the pyproject carrying the exact
override that keeps it out.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parents[1]
LOCK_PATH = ENGINE_DIR / "uv.lock"
PYPROJECT_PATH = ENGINE_DIR / "pyproject.toml"

# Substrings that betray a torch/CUDA/nvidia package leaking into the lock.
_FORBIDDEN_SUBSTRINGS = (
    "nvidia",
    "cuda",
    "cublas",
    "cudnn",
    "cufft",
    "curand",
    "cusolver",
    "cusparse",
    "nccl",
    "nvjitlink",
    "nvtx",
)
_FORBIDDEN_EXACT = {"torch", "triton"}

_PYPI_REGISTRY = "https://pypi.org/simple"


@pytest.fixture(scope="module")
def lock() -> dict:
    """Parsed ``uv.lock``. Fails loudly if the committed lock is absent."""
    assert LOCK_PATH.is_file(), f"committed lock missing: {LOCK_PATH}"
    return tomllib.loads(LOCK_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pyproject() -> dict:
    """Parsed ``pyproject.toml``."""
    assert PYPROJECT_PATH.is_file(), f"pyproject missing: {PYPROJECT_PATH}"
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def _packages(lock: dict) -> list[dict]:
    return lock.get("package", [])


def test_lock_has_no_torch_cuda_nvidia(lock: dict) -> None:
    """No package in the lock is torch, triton, or any CUDA/nvidia component."""
    offenders = []
    for pkg in _packages(lock):
        name = pkg.get("name", "").lower()
        if name in _FORBIDDEN_EXACT or any(s in name for s in _FORBIDDEN_SUBSTRINGS):
            offenders.append(pkg.get("name"))
    assert not offenders, f"torch/CUDA/nvidia leaked into the lock: {offenders}"


def test_lock_packages_are_pypi_with_hashes(lock: dict) -> None:
    """Every locked package resolves from PyPI and carries hashes.

    The local virtual root (``stockroom`` itself, ``package = false``) is the
    sole exception: it has a virtual/editable source and no artifacts.
    """
    for pkg in _packages(lock):
        name = pkg.get("name")
        source = pkg.get("source", {})
        if "virtual" in source or "editable" in source:
            continue
        assert source.get("registry") == _PYPI_REGISTRY, (
            f"{name} resolves from a non-PyPI source: {source}"
        )
        sdist = pkg.get("sdist")
        wheels = pkg.get("wheels", [])
        has_sdist_hash = isinstance(sdist, dict) and "hash" in sdist
        has_wheel_hashes = bool(wheels) and all("hash" in w for w in wheels)
        assert has_sdist_hash or has_wheel_hashes, f"{name} has no hashed artifacts"


def test_lock_manifest_overrides_torch(lock: dict) -> None:
    """The lock's manifest records the impossible-marker torch override."""
    overrides = lock.get("manifest", {}).get("overrides", [])
    torch_overrides = [o for o in overrides if o.get("name") == "torch"]
    assert torch_overrides, "lock manifest does not record a torch override"
    assert torch_overrides[0].get("marker") == "python_full_version < '3'"


def test_pyproject_encodes_torch_contract(pyproject: dict) -> None:
    """pyproject pins python >=3.11, the torch override, and package = false."""
    requires_python = pyproject["project"]["requires-python"]
    assert ">=3.11" in requires_python.replace(" ", "")

    tool_uv = pyproject["tool"]["uv"]
    assert tool_uv["package"] is False
    assert "torch; python_full_version < '3'" in tool_uv["override-dependencies"]
