"""Torch-safe engine-environment readiness for plugin-root moves.

When a marketplace/local plugin tree appears without a synced ``.venv``, path
rectify alone leaves ``uv run --no-sync`` pointed at an empty or missing env.
This module is the single tested owner of **env** healing: probe with
``uv sync --frozen --inexact --check``, and when incomplete heal with
``uv sync --frozen --inexact`` — never an exact sync (exact sync uninstalls
out-of-lock torch).

Called from ``stockroom.shim.rectify`` / ``shim ensure-env`` so hooks inherit
healing without duplicating shell policy in both harness JSON files.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

#: Bounded wait for probe/heal so a hung ``uv`` cannot stall the session hook.
_DEFAULT_TIMEOUT = 45.0

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class EnsureReport:
    """Outcome of :func:`ensure_engine_env`.

    ``action`` is ``noop`` (already ready / nothing to do), ``synced`` (heal
    ran successfully), or ``failed`` (soft failure with ``reason``).
    """

    action: str
    app_dir: Path
    reason: str = ""


def _absolute(path: Path | str) -> Path:
    """Expand ``~`` and absolutize without resolving symlinks."""
    return Path(os.path.abspath(Path(path).expanduser()))


def _uv_sync_cmd(app_dir: Path, *extra: str) -> list[str]:
    """Build an ``uv sync`` argv for ``app_dir``."""
    return [
        "uv",
        "sync",
        "--frozen",
        "--inexact",
        *extra,
        "--no-config",
        "--directory",
        str(app_dir),
    ]


def _default_runner(
    cmd: list[str], *, timeout: float
) -> subprocess.CompletedProcess[str]:
    """Run ``cmd`` capturing text output (production runner)."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ensure_engine_env(
    app_dir: Path | str,
    *,
    runner: Runner | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> EnsureReport:
    """Ensure locked deps are present in ``app_dir``'s project environment.

    Probe with ``uv sync --frozen --inexact --check``. When the probe says the
    environment is incomplete, heal with ``uv sync --frozen --inexact`` (never
    exact — preserves out-of-lock torch). Soft-fails on errors so session hooks
    can keep ``|| true`` semantics.
    """
    app_dir = _absolute(app_dir)
    if not (app_dir / "pyproject.toml").is_file():
        return EnsureReport(
            action="failed",
            app_dir=app_dir,
            reason=f"no pyproject.toml in {app_dir}",
        )

    run = runner or _default_runner

    def invoke(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return run(cmd, timeout=timeout)

    try:
        probe = invoke(_uv_sync_cmd(app_dir, "--check"))
    except subprocess.TimeoutExpired as exc:
        return EnsureReport(
            action="failed",
            app_dir=app_dir,
            reason=f"uv sync --check timed out after {exc.timeout}s",
        )
    except OSError as exc:
        return EnsureReport(
            action="failed",
            app_dir=app_dir,
            reason=f"uv not runnable: {exc}",
        )

    if probe.returncode == 0:
        return EnsureReport(action="noop", app_dir=app_dir, reason="already current")

    try:
        heal = invoke(_uv_sync_cmd(app_dir))
    except subprocess.TimeoutExpired as exc:
        return EnsureReport(
            action="failed",
            app_dir=app_dir,
            reason=f"uv sync timed out after {exc.timeout}s",
        )
    except OSError as exc:
        return EnsureReport(
            action="failed",
            app_dir=app_dir,
            reason=f"uv not runnable: {exc}",
        )

    if heal.returncode != 0:
        detail = (heal.stderr or heal.stdout or f"exit {heal.returncode}").strip()
        return EnsureReport(action="failed", app_dir=app_dir, reason=detail)

    return EnsureReport(action="synced", app_dir=app_dir)
