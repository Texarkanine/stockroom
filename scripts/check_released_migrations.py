"""Fail when a released migration's SQL differs from the latest release tag.

Stdlib only: no engine venv, no torch, no on-path ``stockroom``. A migration
that shipped in a release keeps its SQL forever; comments and whitespace may
change. A frozen schema file under ``schemas/`` is held to the same rule once
a release carries it. The gate reads the highest ``vX.Y.Z`` tag, lists every
``*.sql`` it holds under ``migrations/`` and ``schemas/``, and compares each
with the working tree as SQL tokens (comments and whitespace dropped). A file
that is missing or renamed in the working tree fails. Files added after the
tag are not checked.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MIGRATIONS_REL = Path("skills/sr-search/src/stockroom/migrations")
SCHEMAS_REL = Path("skills/sr-search/src/stockroom/schemas")

_RELEASE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_TOKEN = re.compile(
    r"""
    (?P<literal>'(?:[^']|'')*')
    | (?P<ident>"(?:[^"]|"")*")
    | (?P<line_comment>--[^\n]*)
    | (?P<block_comment>/\*.*?\*/)
    | (?P<space>\s+)
    | (?P<word>\w+)
    | (?P<other>.)
    """,
    re.VERBOSE | re.DOTALL,
)
_DROPPED = frozenset({"line_comment", "block_comment", "space"})


def sql_tokens(text: str) -> list[str]:
    """Return the SQL tokens of ``text``, without comments or whitespace.

    String literals (``'...'``, with ``''`` inside) and quoted identifiers
    (``"..."``, with ``""`` inside) stay whole, so a ``--`` or ``/*`` inside
    one is not a comment.
    """
    return [
        match.group()
        for match in _TOKEN.finditer(text)
        if match.lastgroup not in _DROPPED
    ]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def latest_release_tag(repo: Path) -> str | None:
    """Return the highest ``vX.Y.Z`` tag in ``repo``, or ``None`` if none.

    Tags are compared as integer triples, so ``v2.10.0`` is after
    ``v2.9.0``. Tags of any other shape (``v3.0.0-rc.1``, ``release-1``) are
    ignored.
    """
    releases: list[tuple[tuple[int, int, int], str]] = []
    for tag in _git(repo, "tag", "--list", "v*").split():
        match = _RELEASE_TAG.match(tag)
        if match:
            major, minor, patch = (int(part) for part in match.groups())
            releases.append(((major, minor, patch), tag))
    return max(releases)[1] if releases else None


def released_sql_files(repo: Path, tag: str) -> dict[str, str]:
    """Return ``{repo-relative path: SQL text}`` for every released SQL file.

    Covers ``*.sql`` under the migrations and schemas folders as ``tag``
    holds them. A folder the tag does not have contributes nothing.
    """
    listing = _git(
        repo,
        "ls-tree",
        "-r",
        "--name-only",
        tag,
        "--",
        MIGRATIONS_REL.as_posix(),
        SCHEMAS_REL.as_posix(),
    )
    return {
        path: _git(repo, "show", f"{tag}:{path}")
        for path in listing.splitlines()
        if path.endswith(".sql")
    }


def problems(repo: Path) -> list[str]:
    """Return one line per released SQL file that the working tree broke.

    Empty when every released file is present with the same SQL tokens. A
    clone with no release tag is itself a problem: the gate cannot run.
    """
    tag = latest_release_tag(repo)
    if tag is None:
        return [
            f"no release tag (vX.Y.Z) in {repo}; "
            "run `git fetch --tags` and run the check again"
        ]
    found: list[str] = []
    for path, released in sorted(released_sql_files(repo, tag).items()):
        current = repo / path
        if not current.is_file():
            found.append(f"{path}: released in {tag} but missing from the tree")
        elif sql_tokens(current.read_text(encoding="utf-8")) != sql_tokens(released):
            found.append(
                f"{path}: SQL differs from {tag} "
                "(released migrations may change only comments and whitespace)"
            )
    return found


def main(argv: list[str] | None = None) -> int:
    """CLI: print each problem to stderr and return 1, else return 0."""
    parser = argparse.ArgumentParser(
        description="Fail when a released migration's SQL has changed."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: this script's repository)",
    )
    args = parser.parse_args(argv)
    found = problems(args.repo)
    for line in found:
        print(f"released migrations: {line}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
