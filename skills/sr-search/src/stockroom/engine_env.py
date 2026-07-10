"""Torch-safe engine-environment readiness for plugin-root moves.

When a marketplace/local plugin tree appears without a synced ``.venv``, path
rectify alone leaves ``uv run --no-sync`` pointed at an empty or missing env.
This module is the single tested owner of **env** healing: probe with
``uv sync --frozen --inexact --check``, heal locked deps with
``uv sync --frozen --inexact``, then restore out-of-lock torch from the durable
index under stockroom home (:mod:`stockroom.torch_source`).

Called from ``stockroom.shim.rectify`` / ``shim ensure-env`` so hooks inherit
healing without duplicating shell policy in both harness JSON files.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from stockroom.torch_source import ensure_torch

#: Bounded wait for locked-deps probe/heal.
_DEFAULT_TIMEOUT = 45.0

#: Bounded wait for torch wheel install (large downloads).
_DEFAULT_TORCH_TIMEOUT = 240.0

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class EnsureReport:
    """Outcome of :func:`ensure_engine_env`.

    ``action`` is ``noop`` (deps + torch already ready), ``synced`` (deps
    and/or torch were healed), or ``failed`` (soft failure with ``reason``).
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
    torch_timeout: float = _DEFAULT_TORCH_TIMEOUT,
) -> EnsureReport:
    """Ensure locked deps and recorded torch are present in ``app_dir``.

    1. Probe/heal locked deps with ``uv sync --frozen --inexact`` (never exact).
    2. Ensure torch via :func:`stockroom.torch_source.ensure_torch` using the
       durable index under stockroom home.

    Soft-fails on errors so session hooks can keep ``|| true`` semantics.
    """
    app_dir = _absolute(app_dir)
    if not (app_dir / "pyproject.toml").is_file():
        return EnsureReport(
            action="failed",
            app_dir=app_dir,
            reason=f"no pyproject.toml in {app_dir}",
        )

    run = runner or _default_runner

    def invoke(
        cmd: list[str], *, cmd_timeout: float = timeout
    ) -> subprocess.CompletedProcess[str]:
        return run(cmd, timeout=cmd_timeout)

    deps_action = "noop"
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

    if probe.returncode != 0:
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
        deps_action = "synced"

    torch_report = ensure_torch(app_dir, runner=run, timeout=torch_timeout)
    if torch_report.action == "failed":
        return EnsureReport(
            action="failed",
            app_dir=app_dir,
            reason=torch_report.reason,
        )
    if torch_report.action == "installed" or deps_action == "synced":
        return EnsureReport(
            action="synced",
            app_dir=app_dir,
            reason=torch_report.reason or "locked deps synced",
        )
    return EnsureReport(action="noop", app_dir=app_dir, reason="already current")
