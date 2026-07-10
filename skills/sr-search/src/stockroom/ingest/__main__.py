"""CLI entrypoint: ``python -m stockroom.ingest [--full] [--harness ...]``.

Runs the trace ingest against the operator's history (or the env-pointed
fixture roots in tests), opening the warehouse read-write through
:func:`stockroom.warehouse.open`, and prints a short per-harness summary. This
is the only user-facing surface milestone 3 ships; ``sr-query`` and the
dashboard adopt the same env conventions later.
"""

import argparse

from stockroom import ingest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m stockroom.ingest",
        description="Ingest Cursor and Claude Code history into the warehouse.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Ignore the watermark and re-ingest everything (idempotent).",
    )
    parser.add_argument(
        "--harness",
        choices=("cursor", "claude"),
        default=None,
        help="Ingest only this harness (default: both).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the ingest, print a summary, and return an exit code."""
    args = _build_parser().parse_args(argv)
    summary = ingest.ingest(harness=args.harness, full=args.full)

    print("ingest complete:")
    for harness, counts in summary.by_harness.items():
        print(
            f"  {harness}: {counts.sessions} sessions, "
            f"{counts.messages} messages, {counts.tool_calls} tool_calls"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
