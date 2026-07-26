"""CLI entrypoint: ``stockroom backfill [--source NAME] [--dry-run] [--force]``.

A deliberate, human-run excavation of a harness's legacy store into the
warehouse. Nothing schedules this: the nightly entry stays ``ingest && embed``.
The corpus is finite and does not grow, so this is a run-once (or rarely)
command — and because it can roughly double the message corpus, the next
``stockroom embed`` will run far longer than usual.

Errors print one line and exit ``1`` rather than surfacing a traceback, which
matters here because the most likely failure is a store that is unreachable or
being written by a running Cursor.
"""

import argparse
import sys
from pathlib import Path

from stockroom import backfill
from stockroom.backfill import cursor_vscdb


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser, with ``--source`` choices from the registry."""
    parser = argparse.ArgumentParser(
        prog="stockroom backfill",
        # Raw formatting so the required-order list keeps its line breaks; the
        # prose is therefore wrapped by hand.
        description=(
            "One-shot backfill of a harness's legacy store into the warehouse.\n"
            "Not scheduled, and safe to re-run: sessions already in the warehouse\n"
            "are skipped, never overwritten."
        ),
        epilog=(
            "REQUIRED ORDER — do all three, in order, every time:\n"
            "  1. quit the harness (not just the window; the whole app)\n"
            "  2. stockroom ingest\n"
            "  3. stockroom backfill\n"
            "\n"
            "Both prerequisites fail silently when skipped. A store still open in\n"
            "the harness can hide its newest conversations from the read without\n"
            "reporting them missing, and skipping ingest makes this reconstruct\n"
            "conversations whose transcripts are already on disk — which you then\n"
            "pay to embed twice."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=sorted(backfill._SOURCES),
        default=None,
        help="Back-fill only this source (default: every registered source).",
    )
    parser.add_argument(
        "--state-vscdb",
        default=None,
        help=(
            "Path to Cursor's globalStorage/state.vscdb for the "
            f"{cursor_vscdb.NAME} source (overrides "
            f"{cursor_vscdb.STATE_VSCDB_ENV_VAR} and "
            f"{cursor_vscdb.STATE_VSCDB_CONFIG_KEY})."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be written without writing anything.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-parse sessions this same source previously authored (matched on "
            "source_path). Sessions ordinary ingest authored stay untouched."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress while backfilling (quiet by default).",
    )
    return parser


def _print_summary(summary: backfill.BackfillSummary) -> None:
    """Print one block per source: what it wrote and what it deliberately did not."""
    print("backfill complete:")
    for name, source in summary.by_source.items():
        if source.note is not None:
            print(f"  {name}: skipped — {source.note}")
            continue
        if source.error is not None:
            print(f"  {name}: failed — {source.error}")
            continue
        print(
            f"  {name}: {source.written} sessions, {source.messages} messages, "
            f"{source.tool_calls} tool_calls "
            f"(of {source.candidates} candidates; "
            f"{source.skipped_existing} already present, "
            f"{source.skipped_empty} empty)"
        )


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the backfill, print a per-source summary, exit."""
    args = _build_parser().parse_args(argv)
    source_paths = (
        {cursor_vscdb.NAME: Path(args.state_vscdb)}
        if args.state_vscdb is not None
        else None
    )
    on_progress = (lambda line: print(line, flush=True)) if args.verbose else None

    try:
        summary = backfill.backfill(
            source=args.source,
            source_paths=source_paths,
            dry_run=args.dry_run,
            force=args.force,
            on_progress=on_progress,
        )
    except backfill.BackfillError as exc:
        print(f"stockroom backfill: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("(dry run — nothing was written)")
    _print_summary(summary)
    if summary.failed:
        for name, source in summary.by_source.items():
            if source.error is not None:
                print(f"stockroom backfill: {name}: {source.error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
