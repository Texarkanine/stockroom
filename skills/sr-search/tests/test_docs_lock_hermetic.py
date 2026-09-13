"""The docs-only root lock is hermetic: PyPI only, no ambient indexes.

The root project is a docs toolchain stub. It does not declare Torch. A
PyTorch wheel index must not participate in resolution — those indexes
also ship common packages, so a contaminated lock is the signature of
ambient user-level uv config leaking into ``uv lock``.
"""

import shutil
import subprocess
from pathlib import Path

import tomllib

_PYPI_REGISTRY = "https://pypi.org/simple"

_USER_UV_CONFIG_MARKERS = (
    "uv.toml",
    ".config/uv",
)


def _packages(lock: dict) -> list[dict]:
    return lock.get("package", [])


def test_docs_lock_packages_are_pypi_with_hashes(repo_root: Path) -> None:
    """Every locked docs package resolves from PyPI and carries hashes.

    The virtual root (``stockroom-docs``) is the sole exception.
    """
    lock_path = repo_root / "uv.lock"
    assert lock_path.is_file(), f"committed root lock missing: {lock_path}"
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))

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


def test_docs_lock_is_not_stale(repo_root: Path) -> None:
    """The committed root lock matches a hermetic re-resolve.

    ``--refresh`` is required: ``uv lock --locked`` without it treats a
    lock that already satisfies the spec as current even when packages
    were resolved from a non-PyPI extra index.
    """
    uv = shutil.which("uv")
    assert uv, "uv not found on PATH"
    proc = subprocess.run(
        [uv, "lock", "--locked", "--refresh", "--no-config"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"committed root lock is stale:\n{proc.stderr}"


def test_engine_source_does_not_write_user_uv_config(repo_root: Path) -> None:
    """Install/torch paths must not write user-level uv config (``uv.toml``)."""
    roots = (
        repo_root / "skills" / "sr-search" / "src",
        repo_root / "scripts",
    )
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            hits = [marker for marker in _USER_UV_CONFIG_MARKERS if marker in text]
            if hits:
                offenders.append(f"{path.relative_to(repo_root)}: {hits}")
        for path in root.rglob("*.sh"):
            text = path.read_text(encoding="utf-8")
            hits = [marker for marker in _USER_UV_CONFIG_MARKERS if marker in text]
            if hits:
                offenders.append(f"{path.relative_to(repo_root)}: {hits}")
    assert not offenders, (
        "install/torch paths must not write or mention user-level uv index "
        "config: " + "; ".join(offenders)
    )
