"""Durable per-machine torch freeze and torch heal for plugin-root moves.

The plugin/engine tree is disposable (marketplace hash moves, rsync without
``.venv``). Locked deps can be restored from ``uv.lock``; torch cannot — it is
held out of the lock and chosen per machine. This module freezes the accepted
torch stack (hashed requirements + index sidecar) under stockroom home and
reinstalls from that freeze when torch is missing in an engine venv.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from stockroom.home import home_dir

#: Filename under stockroom home holding one torch wheel-index URL.
INDEX_FILENAME = "torch-index"

#: Filename under stockroom home holding the hashed torch freeze.
REQUIREMENTS_FILENAME = "torch-requirements.txt"

#: Default wait for ``uv pip install`` of the freeze (wheels are large).
_DEFAULT_TORCH_TIMEOUT = 240.0

#: Default wait for ``uv pip compile`` when freezing the torch stack.
_DEFAULT_FREEZE_TIMEOUT = 120.0

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class TorchEnsureReport:
    """Outcome of :func:`ensure_torch`.

    ``action`` is ``noop`` (torch already importable), ``installed`` (pip
    ran successfully), or ``failed`` (soft failure with ``reason``).
    """

    action: str
    reason: str = ""


@dataclass(frozen=True)
class TorchFreezeReport:
    """Outcome of :func:`freeze_torch`.

    ``action`` is ``written`` (freeze + index persisted) or ``failed``
    (soft failure with ``reason``; no freeze file left behind).
    """

    action: str
    reason: str = ""
    requirements_path: Path | None = None


def index_path() -> Path:
    """Return the durable torch-index file path (may not exist yet)."""
    return home_dir() / INDEX_FILENAME


def requirements_path() -> Path:
    """Return the durable hashed torch-requirements path (may not exist yet)."""
    return home_dir() / REQUIREMENTS_FILENAME


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


def read_freeze_path() -> Path | None:
    """Return the freeze path when a usable hashed requirements file exists.

    A freeze is usable when the file exists, is non-empty, and contains both a
    ``torch==`` pin and at least one ``--hash=`` line. Otherwise return
    ``None`` (heal must soft-fail rather than floating-install).
    """
    path = requirements_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if "torch==" not in text or "--hash=" not in text:
        return None
    return path


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


def _default_runner(
    cmd: list[str],
    *,
    timeout: float | None = None,
    **kwargs: object,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — caller-controlled argv
        cmd, capture_output=True, text=True, timeout=timeout, **kwargs
    )


def _venv_python(app_dir: Path) -> Path:
    return app_dir / ".venv" / "bin" / "python"


def _read_torch_version(app_dir: Path, *, runner: Runner, timeout: float) -> str | None:
    """Return ``torch.__version__`` from the engine venv, or ``None``."""
    py = _venv_python(app_dir)
    if not py.is_file():
        return None
    try:
        proc = runner(
            [str(py), "-c", "import torch; print(torch.__version__)"],
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    version = (proc.stdout or "").strip().splitlines()
    return version[0].strip() if version else None


def freeze_torch(
    app_dir: Path | str,
    index_url: str,
    *,
    runner: Runner | None = None,
    timeout: float = _DEFAULT_FREEZE_TIMEOUT,
) -> TorchFreezeReport:
    """Freeze the installed torch stack to a hashed requirements file.

    Requires an importable torch in ``app_dir``'s venv. Compiles
    ``torch==<installed.__version__>`` against ``index_url`` via
    ``uv pip compile --generate-hashes --emit-index-url``, then atomically
    writes ``torch-requirements.txt`` and the ``torch-index`` sidecar under
    stockroom home.

    Soft-fails (no raise) when torch is missing or compile fails/times out.
    Raises ``ValueError`` when ``index_url`` is not ``https://``.
    """
    url = index_url.strip()
    if not url.startswith("https://"):
        raise ValueError(f"torch index must be an https:// URL, got {index_url!r}")

    app_dir = Path(os.path.abspath(Path(app_dir).expanduser()))
    run = runner or _default_runner

    version = _read_torch_version(app_dir, runner=run, timeout=min(timeout, 30.0))
    if version is None:
        return TorchFreezeReport(
            action="failed",
            reason=(
                f"torch is not importable in {app_dir} — install torch first, "
                "then re-run freeze"
            ),
        )

    dest = requirements_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix="torch-requirements.",
        suffix=".txt",
        dir=str(dest.parent),
    )
    os.close(fd)
    tmp_path = Path(tmp_name)

    cmd = [
        "uv",
        "pip",
        "compile",
        "--generate-hashes",
        "--no-config",
        "--emit-index-url",
        "--default-index",
        url,
        "-o",
        str(tmp_path),
        "-",
    ]
    try:
        proc = run(cmd, timeout=timeout, input=f"torch=={version}\n")
    except subprocess.TimeoutExpired as exc:
        tmp_path.unlink(missing_ok=True)
        return TorchFreezeReport(
            action="failed",
            reason=f"uv pip compile timed out after {exc.timeout}s",
        )
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        return TorchFreezeReport(
            action="failed",
            reason=f"uv not runnable: {exc}",
        )

    if proc.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        detail = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return TorchFreezeReport(action="failed", reason=detail)

    try:
        os.replace(tmp_path, dest)
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        return TorchFreezeReport(
            action="failed",
            reason=f"failed to write freeze at {dest}: {exc}",
        )

    write_index(url)
    return TorchFreezeReport(
        action="written",
        reason=version,
        requirements_path=dest,
    )


def _torch_importable(app_dir: Path, *, runner: Runner, timeout: float) -> bool:
    py = _venv_python(app_dir)
    if not py.is_file():
        return False
    try:
        proc = runner([str(py), "-c", "import torch"], timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _pip_install_freeze_cmd(app_dir: Path, freeze: Path) -> list[str]:
    """Build ``uv pip install --require-hashes -r <freeze>`` for ``app_dir``."""
    return [
        "uv",
        "pip",
        "install",
        "--no-config",
        "--directory",
        str(app_dir),
        "--require-hashes",
        "-r",
        str(freeze),
    ]


def ensure_torch(
    app_dir: Path | str,
    *,
    runner: Runner | None = None,
    timeout: float = _DEFAULT_TORCH_TIMEOUT,
) -> TorchEnsureReport:
    """Ensure torch is importable in ``app_dir``'s venv from the hashed freeze.

    If torch already imports, return ``noop``. If missing and a usable
    ``torch-requirements.txt`` freeze exists, run
    ``uv pip install --require-hashes -r <freeze>`` (indexes come from the
    freeze via ``--emit-index-url`` at compile time). If missing with no
    freeze, soft-fail naming ``sr-initialize`` / ``docs/user-guide/troubleshooting/torch.md`` — never
    floating-install from the index sidecar alone.
    """
    app_dir = Path(os.path.abspath(Path(app_dir).expanduser()))
    run = runner or _default_runner

    if _torch_importable(app_dir, runner=run, timeout=min(timeout, 30.0)):
        return TorchEnsureReport(action="noop", reason="torch already importable")

    freeze = read_freeze_path()
    if freeze is None:
        return TorchEnsureReport(
            action="failed",
            reason=(
                "torch missing and no hashed freeze at "
                f"{requirements_path()} — run sr-initialize (install → smoke → "
                "freeze) or see docs/user-guide/troubleshooting/torch.md"
            ),
        )

    cmd = _pip_install_freeze_cmd(app_dir, freeze)
    try:
        proc = run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return TorchEnsureReport(
            action="failed",
            reason=f"uv pip install freeze timed out after {exc.timeout}s",
        )
    except OSError as exc:
        return TorchEnsureReport(
            action="failed",
            reason=f"uv not runnable: {exc}",
        )

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return TorchEnsureReport(action="failed", reason=detail)

    return TorchEnsureReport(action="installed", reason=str(freeze))
