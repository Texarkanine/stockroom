"""CLI for durable torch wheel-index recording.

``stockroom torch record --index <url>`` writes the per-machine index under
stockroom home so :func:`stockroom.torch_source.ensure_torch` can reinstall
after a plugin-root move. Judgment (which wheel) stays in ``sr-initialize``;
this module is mechanism only.
"""

from __future__ import annotations

import argparse
import sys

from stockroom.torch_source import write_index


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.torch_cli",
        description=(
            "Record the per-machine torch wheel index for env heal after "
            "plugin updates."
        ),
    )
    parser.add_argument(
        "action",
        choices=("record",),
        help="record: persist --index under stockroom home",
    )
    parser.add_argument(
        "--index",
        required=True,
        help="torch wheel index URL (e.g. https://download.pytorch.org/whl/cpu)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m stockroom.torch_cli record --index URL``."""
    args = _build_parser().parse_args(argv)
    try:
        path = write_index(args.index)
    except ValueError as exc:
        print(f"stockroom torch: {exc}", file=sys.stderr)
        return 2
    print(f"recorded torch index at {path}: {args.index.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
