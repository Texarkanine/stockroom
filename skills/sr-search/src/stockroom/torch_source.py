"""Durable per-machine torch wheel index and torch heal for plugin-root moves.

The plugin/engine tree is disposable (marketplace hash moves, rsync without
``.venv``). Locked deps can be restored from ``uv.lock``; torch cannot — it is
held out of the lock and chosen per machine. This module persists the chosen
index under stockroom home (alongside the warehouse) and reinstalls torch into
an engine venv when it is missing.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from stockroom.warehouse import home_dir

#: Filename under stockroom home holding one torch wheel-index URL.
INDEX_FILENAME = "torch-index"

#: Default wait for ``uv pip install torch`` (wheels are large).
_DEFAULT_TORCH_TIMEOUT = 240.0

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class TorchEnsureReport:
    """Outcome of :func:`ensure_torch`.

    ``action`` is ``noop`` (torch already importable), ``installed`` (pip
    ran successfully), or ``failed`` (soft failure with ``reason``).
    """

    action: str
    reason: str = ""


def index_path() -> Path:
    """Return the durable torch-index file path (may not exist yet)."""
    return home_dir() / INDEX_FILENAME


def read_index() -> str | None:
    """Return the recorded wheel-index URL, or ``None`` if absent/invalid."""
    path = index_path()
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text or not text.startswith("https://"):
        return None
    # Single-line record; ignore trailing junk.
    return text.splitlines()[0].strip()


def write_index(index_url: str) -> Path:
    """Persist ``index_url`` under stockroom home; return the file path.

    Raises ``ValueError`` when the URL is empty or not ``https://``.
    """
    url = index_url.strip()
    if not url.startswith("https://"):
        raise ValueError(f"torch index must be an https:// URL, got {index_url!r}")
    path = index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(url + "\n", encoding="utf-8")
    return path


def _venv_python(app_dir: Path) -> Path:
    return app_dir / ".venv" / "bin" / "python"


def _torch_importable(app_dir: Path, *, runner: Runner, timeout: float) -> bool:
    py = _venv_python(app_dir)
    if not py.is_file():
        return False
    try:
        proc = runner([str(py), "-c", "import torch"], timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _pip_install_cmd(app_dir: Path, index_url: str) -> list[str]:
    return [
        "uv",
        "pip",
        "install",
        "torch",
        "--no-config",
        "--directory",
        str(app_dir),
        "--index",
        index_url,
    ]


def ensure_torch(
    app_dir: Path | str,
    *,
    runner: Runner | None = None,
    timeout: float = _DEFAULT_TORCH_TIMEOUT,
) -> TorchEnsureReport:
    """Ensure torch is importable in ``app_dir``'s venv using the durable index.

    If torch already imports, return ``noop``. If missing and a recorded
    ``https://`` index exists, run ``uv pip install torch`` into the engine
    directory. If missing with no record, soft-fail naming ``sr-initialize`` /
    ``stockroom torch record`` — never guess a wheel.
    """
    app_dir = Path(os.path.abspath(Path(app_dir).expanduser()))
    run = runner or (
        lambda cmd, timeout: subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    )

    if _torch_importable(app_dir, runner=run, timeout=min(timeout, 30.0)):
        return TorchEnsureReport(action="noop", reason="torch already importable")

    index = read_index()
    if index is None:
        return TorchEnsureReport(
            action="failed",
            reason=(
                "torch missing and no durable index at "
                f"{index_path()} — run sr-initialize or "
                "`stockroom torch record --index <url>`"
            ),
        )

    cmd = _pip_install_cmd(app_dir, index)
    try:
        proc = run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return TorchEnsureReport(
            action="failed",
            reason=f"uv pip install torch timed out after {exc.timeout}s",
        )
    except OSError as exc:
        return TorchEnsureReport(
            action="failed",
            reason=f"uv not runnable: {exc}",
        )

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return TorchEnsureReport(action="failed", reason=detail)

    return TorchEnsureReport(action="installed", reason=index)
