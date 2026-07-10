"""CLI for freezing the accepted per-machine torch stack.

``stockroom torch freeze --index <url> [--app-dir <engine>]`` compiles a
hashed requirements freeze from the torch already installed in the engine
venv and writes it under stockroom home so
:func:`stockroom.torch_source.ensure_torch` can replay the same bits after a
plugin-root move. Judgment (which wheel) stays in ``sr-initialize``; this
module is mechanism only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stockroom.shim import default_app_dir
from stockroom.torch_source import freeze_torch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.torch_cli",
        description=(
            "Freeze the installed torch stack to a hashed requirements file "
            "for env heal after plugin updates."
        ),
    )
    parser.add_argument(
        "action",
        choices=("freeze",),
        help="freeze: compile hashed torch-requirements under stockroom home",
    )
    parser.add_argument(
        "--index",
        required=True,
        help="torch wheel index URL (e.g. https://download.pytorch.org/whl/cpu)",
    )
    parser.add_argument(
        "--app-dir",
        default=None,
        help=(
            "engine directory whose venv holds the accepted torch "
            "(default: running stockroom engine)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m stockroom.torch_cli freeze --index URL [--app-dir DIR]``."""
    args = _build_parser().parse_args(argv)
    app_dir = Path(args.app_dir) if args.app_dir else default_app_dir()
    try:
        report = freeze_torch(app_dir, args.index)
    except ValueError as exc:
        print(f"stockroom torch: {exc}", file=sys.stderr)
        return 2
    if report.action == "failed":
        print(f"stockroom torch freeze failed: {report.reason}", file=sys.stderr)
        return 1
    print(
        f"froze torch {report.reason} at {report.requirements_path} "
        f"(index {args.index.strip()})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
