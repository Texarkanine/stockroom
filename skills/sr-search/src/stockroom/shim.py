"""Generation, installation, and rectification of the on-path ``stockroom`` shim.

The shim (``~/.local/bin/stockroom``) is a generated POSIX-sh launcher with a
**baked** engine directory (``APP_DIR``) and **succeed-or-refuse** semantics:
it never scans, ranks, or guesses — it either execs the baked engine through
the torch-safe contract or refuses with a one-line remedy. All policy lives
here, in tested Python; the rendered script is environment plumbing only.

Three writers drive this module (all through the same code):

* ``sr-initialize`` (Phase-3 m3) — ``stockroom shim install --owner <harness>``
* the plugin sessionStart / workspaceOpen hooks — ``stockroom shim rectify
  --owner <harness> --app-dir ${*_PLUGIN_ROOT}/skills/sr-search`` (path + env
  staleness healing)
* ``make shim`` — ``stockroom shim install --owner dev`` (dev-checkout parity)

Ownership is explicit (a ``# STOCKROOM_OWNER=`` header marker): only the
owner may rewrite an existing shim; a foreign shim is replaced only when its
baked engine dir is dead *and* ``--takeover`` is passed. ``rectify`` is the
hook-safe subset: ensures the engine env, then owner-match + content-diff
rebake only, never creates.

Design records: ``memory-bank/active/creative/creative-shim-staleness-resolution.md``
and ``creative-shim-generation-surface.md`` (both revised 2026-07-08).
"""

import argparse
import contextlib
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from stockroom import __version__
from stockroom.engine_env import EnsureReport, ensure_engine_env

#: Default shim destination: the conventional user-local bin dir.
DEFAULT_DEST = Path("~/.local/bin/stockroom")

#: The in-package POSIX-sh template the shim is rendered from.
TEMPLATE_PATH = Path(__file__).parent / "shim_template.sh"

#: Header-marker pattern: machine-readable single-line ``# STOCKROOM_KEY=value``.
_HEADER_RE = re.compile(r"^# STOCKROOM_(OWNER|APP_DIR)=(.*)$", re.MULTILINE)

#: Owner label → the one-line staleness remedy baked into that owner's shim.
#: Unknown (future-harness) owners get the harness remedy. Keep these free of
#: shell-active characters (backticks, $, ") — they land inside a double-quoted
#: echo in the rendered script.
_DEV_REMEDY = "run 'make shim' from your stockroom checkout"
_HARNESS_REMEDY = "run sr-initialize (or start a new session to let it heal)"


@dataclass
class ShimReport:
    """Outcome of an :func:`install` or :func:`rectify` call.

    ``action`` is one of ``installed`` / ``refused`` (install) or
    ``rectified`` / ``noop`` (rectify). ``reason`` carries the human-readable
    explanation for refusals and no-ops. The ``path_ok`` / ``verify_*`` fields
    are install-only: PATH membership of the dest dir, and the outcome of the
    conditional install-time ``stockroom --version`` verify (attempted only
    when the dest dir is on ``PATH``).
    """

    action: str
    dest: Path
    reason: str = ""
    path_ok: bool | None = None
    verify_attempted: bool = False
    verify_ok: bool | None = None
    verify_detail: str = ""


def default_app_dir() -> Path:
    """Return the engine directory containing the running ``stockroom`` package.

    The engine is run-in-place (``[tool.uv] package = false``), so the package
    always lives at ``<engine>/src/stockroom/`` — the engine dir is two levels
    above the package directory.
    """
    return Path(__file__).resolve().parent.parent.parent


def _absolute(path: Path | str) -> Path:
    """Expand ``~`` and absolutize without resolving symlinks."""
    return Path(os.path.abspath(Path(path).expanduser()))


def render(app_dir: Path | str, owner: str) -> str:
    """Render the shim script text for ``app_dir`` under ``owner``.

    Substitutes the baked engine dir (absolute), the owner label, the
    generator version stamp, and the owner-appropriate staleness remedy into
    :data:`TEMPLATE_PATH`. Pure: no filesystem writes.
    """
    app_dir = _absolute(app_dir)
    remedy = _DEV_REMEDY if owner == "dev" else _HARNESS_REMEDY
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        text.replace("{{OWNER}}", owner)
        .replace("{{APP_DIR_SH}}", shlex.quote(str(app_dir)))
        .replace("{{APP_DIR}}", str(app_dir))
        .replace("{{VERSION}}", __version__)
        .replace("{{REMEDY}}", remedy)
    )


def _read_header(dest: Path) -> dict[str, str] | None:
    """Parse the ``STOCKROOM_*`` header markers from an existing shim.

    Returns ``{"owner": …, "app_dir": …}`` when both markers are present, or
    ``None`` for a corrupt/unreadable/foreign file — never raises.
    """
    try:
        text = dest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    found = {key.lower(): value for key, value in _HEADER_RE.findall(text)}
    if "owner" not in found or "app_dir" not in found:
        return None
    return found


def _alive(app_dir: str) -> bool:
    """A baked engine dir is alive iff it still holds a ``pyproject.toml``."""
    return (Path(app_dir) / "pyproject.toml").is_file()


def _write_atomic(dest: Path, content: str) -> None:
    """Write ``content`` to ``dest`` (mode ``0o755``) via temp-file + replace."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(tmp_name, 0o755)
        os.replace(tmp_name, dest)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _dest_on_path(dest: Path) -> bool:
    """True iff ``dest``'s directory is an entry of the current ``PATH``."""
    entries = os.environ.get("PATH", "").split(os.pathsep)
    return any(entry and Path(entry) == dest.parent for entry in entries)


def _verify_via_path() -> tuple[bool, str]:
    """Run ``stockroom --version`` through ``PATH``; return (ok, detail)."""
    try:
        proc = subprocess.run(
            ["stockroom", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, proc.stderr.strip()
    return True, proc.stdout.strip()


def install(
    dest: Path | str, app_dir: Path | str, owner: str, *, takeover: bool = False
) -> ShimReport:
    """Write the shim to ``dest``, guarded by the ownership policy.

    Policy (see the staleness-resolution creative doc):

    * dest absent → write (mode ``0o755``, atomic temp-file + ``os.replace``).
    * dest present, same owner → rewrite (idempotent).
    * dest present, different owner, incumbent's baked dir **alive** → refuse.
    * dest present, different owner, incumbent's baked dir **dead** → refuse
      unless ``takeover`` is set.
    * corrupt/unreadable header → treated as foreign with a dead baked dir.

    On a successful write the report also carries PATH membership of the dest
    dir and — only when that dir is on ``PATH`` — the outcome of a
    ``stockroom --version`` verify through ``PATH``.
    """
    dest = _absolute(dest)

    if dest.exists():
        header = _read_header(dest)
        incumbent_owner = header["owner"] if header else "unknown (corrupt header)"
        if header is None or header["owner"] != owner:
            incumbent_alive = header is not None and _alive(header["app_dir"])
            if incumbent_alive:
                return ShimReport(
                    action="refused",
                    dest=dest,
                    reason=(
                        f"{dest} is owned by '{incumbent_owner}' and its engine "
                        "is alive — refusing to replace a working foreign shim"
                    ),
                )
            if not takeover:
                return ShimReport(
                    action="refused",
                    dest=dest,
                    reason=(
                        f"{dest} is owned by '{incumbent_owner}' (engine dead) — "
                        "pass --takeover to replace it"
                    ),
                )

    _write_atomic(dest, render(app_dir, owner))

    report = ShimReport(action="installed", dest=dest)
    report.path_ok = _dest_on_path(dest)
    if report.path_ok:
        report.verify_attempted = True
        report.verify_ok, report.verify_detail = _verify_via_path()
    else:
        report.verify_detail = (
            f"{dest.parent} is not on PATH — skipped the --version verify"
        )
    return report


def rectify(dest: Path | str, app_dir: Path | str, owner: str) -> ShimReport:
    """Re-bake ``dest`` iff it exists, ``owner`` owns it, and content differs.

    The hook-safe healing path: always ensures the engine env for ``app_dir``
    first (torch-safe inexact sync when locked deps are missing), then never
    creates a missing shim, never touches a foreign one, and is a silent no-op
    when the rendered content already matches (steady state).
    """
    ensure_report = ensure_engine_env(app_dir)
    if ensure_report.action == "failed":
        print(
            f"stockroom shim: ensure-env failed — {ensure_report.reason}",
            file=sys.stderr,
        )
    dest = _absolute(dest)

    if not dest.exists():
        return ShimReport(action="noop", dest=dest, reason="dest absent")

    header = _read_header(dest)
    if header is None or header["owner"] != owner:
        return ShimReport(action="noop", dest=dest, reason="not the owner")

    content = render(app_dir, owner)
    if dest.read_text(encoding="utf-8") == content:
        return ShimReport(action="noop", dest=dest, reason="already current")

    _write_atomic(dest, content)
    return ShimReport(action="rectified", dest=dest)


def _build_parser() -> argparse.ArgumentParser:
    """Build the ``python -m stockroom.shim`` parser.

    A flat parser (positional action + shared flags) rather than argparse
    subparsers, so the top-level ``--help`` documents every flag in one page.
    """
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.shim",
        description=(
            "Install, rectify, or ensure-env for the on-path stockroom shim. "
            "install writes (ownership-guarded); rectify re-bakes an owned, "
            "drifted shim and never creates one; ensure-env heals the engine "
            "uv environment (torch-safe inexact sync)."
        ),
    )
    parser.add_argument(
        "action",
        choices=("install", "rectify", "ensure-env"),
        help=(
            "install: write the shim (guarded); rectify: heal an owned shim; "
            "ensure-env: sync locked deps into the engine env"
        ),
    )
    parser.add_argument(
        "--owner",
        default=None,
        help="owner label written into the shim header (cursor / claude / dev)",
    )
    parser.add_argument(
        "--app-dir",
        default=None,
        help="engine directory to bake (default: the running engine)",
    )
    parser.add_argument(
        "--dest",
        default=str(DEFAULT_DEST),
        help=f"shim destination (default: {DEFAULT_DEST})",
    )
    parser.add_argument(
        "--takeover",
        action="store_true",
        help="install only: replace a foreign shim whose baked engine is dead",
    )
    return parser


def _print_ensure(report: EnsureReport) -> None:
    """Emit a one-line ensure-env status for operators / skill logs."""
    if report.action == "synced":
        print(f"ensured env at {report.app_dir}")
    elif report.action == "failed":
        print(f"stockroom shim: ensure-env failed — {report.reason}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m stockroom.shim {install|rectify|ensure-env} […]``.

    ``install`` exits ``0`` on a successful write (PATH problems are warnings,
    not failures) and ``1`` on an ownership refusal. ``rectify`` and
    ``ensure-env`` always exit ``0`` — soft failures are messages, not hook
    breakers.
    """
    args = _build_parser().parse_args(argv)
    app_dir = Path(args.app_dir) if args.app_dir else default_app_dir()

    if args.action == "ensure-env":
        _print_ensure(ensure_engine_env(app_dir))
        return 0

    if not args.owner:
        print(
            "stockroom shim: --owner is required for install and rectify",
            file=sys.stderr,
        )
        return 2

    if args.action == "install":
        report = install(args.dest, app_dir, args.owner, takeover=args.takeover)
        if report.action == "refused":
            print(f"stockroom shim: {report.reason}", file=sys.stderr)
            return 1
        print(f"installed {report.dest} (owner={args.owner}, app-dir={app_dir})")
        if not report.path_ok:
            print(f"warning: {report.verify_detail}", file=sys.stderr)
        elif report.verify_ok:
            print(f"verified via PATH: {report.verify_detail}")
        else:
            print(
                f"warning: --version verify failed: {report.verify_detail}",
                file=sys.stderr,
            )
        return 0

    report = rectify(args.dest, app_dir, args.owner)
    if report.action == "rectified":
        print(f"rectified {report.dest} (owner={args.owner}, app-dir={app_dir})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
