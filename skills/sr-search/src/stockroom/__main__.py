"""CLI dispatcher: ``python -m stockroom <subcommand> …``.

The single entrypoint the on-path ``stockroom`` shim (Phase-3 m2) execs into.
It makes the engine behave like one CLI with subcommands: the first token
selects a module from ``SUBCOMMANDS``, everything after it is forwarded
verbatim to that module's own ``main(argv)`` — so each module's argparse
remains the single source of truth for its flags, and ``stockroom <sub>
--help`` is that module's own help.

Dispatch is deliberately dumb: no argparse subparsers duplicating module
flags, no option parsing beyond the first token. The target module is imported
lazily only after dispatch resolves, so ``--help`` / error paths never pull a
heavy import chain (torch, duckdb).

Design record: ``planning/brainstorm/stockroom-on-path-cli.md`` → "The
dispatcher".
"""

import importlib
import sys

from stockroom import __version__

#: First-token subcommand table: name -> (module holding ``main``, one-line
#: summary for the top-level help). Modules are imported lazily at dispatch.
SUBCOMMANDS: dict[str, tuple[str, str]] = {
    "query": ("stockroom.query", "Run raw read-only SQL against the warehouse."),
    "semantic": ("stockroom.semantic", "Vector (semantic) search over the warehouse."),
    "ingest": (
        "stockroom.ingest.__main__",
        "Ingest harness history into the warehouse.",
    ),
    "embed": ("stockroom.embed", "Embed pending message text into vectors."),
    "migrate": ("stockroom.migrate", "Migrate the warehouse to the schema head."),
    "shim": ("stockroom.shim", "Install or rectify the on-path stockroom shim."),
    "doctor": ("stockroom.doctor", "Report environment facts / smoke-test torch."),
    "schedule": (
        "stockroom.schedule",
        "Manage the nightly ingest+embed scheduler entry.",
    ),
    "dashboard": (
        "stockroom.dashboard.__main__",
        "Launch the read-only local dashboard.",
    ),
}


def _usage() -> str:
    """Return the top-level usage/help text listing every subcommand."""
    lines = [
        "usage: stockroom <subcommand> [options]",
        "",
        "The stockroom engine CLI. Run `stockroom <subcommand> --help` for",
        "each subcommand's own options.",
        "",
        "subcommands:",
    ]
    width = max(len(name) for name in SUBCOMMANDS)
    lines += [
        f"  {name:<{width}}  {summary}" for name, (_, summary) in SUBCOMMANDS.items()
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Dispatch the first token to its module CLI; return its exit code.

    Contract:

    * ``--help`` / ``-h`` → usage on stdout, exit ``0``.
    * ``--version`` → ``stockroom <version>`` on stdout, exit ``0``.
    * no arguments → usage on stderr, exit ``2``.
    * unknown subcommand → one-line error naming the token + usage hint on
      stderr, exit ``2``.
    * known subcommand → lazily import the module, call its ``main`` with the
      remaining arguments verbatim, and return its exit code unchanged.
    """
    args = sys.argv[1:] if argv is None else argv

    if not args:
        print(_usage(), file=sys.stderr)
        return 2

    token = args[0]
    if token in ("--help", "-h"):
        print(_usage())
        return 0
    if token == "--version":
        print(f"stockroom {__version__}")
        return 0
    if token not in SUBCOMMANDS:
        print(
            f"stockroom: unknown subcommand '{token}' "
            "(run `stockroom --help` for the list)",
            file=sys.stderr,
        )
        return 2

    module_name, _ = SUBCOMMANDS[token]
    module = importlib.import_module(module_name)
    return module.main(args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
