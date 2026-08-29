"""Generate the warehouse ERD markdown from the head schema golden and @rel comments.

Stdlib only: no engine venv, no torch, no on-path ``stockroom``. Boxes and
columns come from the highest ``NNNN_snapshot.json`` under the schema fixtures
directory. Edges come from ``-- @rel`` / ``-- @rel-none`` comments in
``migrations/*.sql``. Logical relationships are not DuckDB FOREIGN KEYs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

FIXTURES_REL = Path("skills/sr-search/tests/fixtures/schema")
MIGRATIONS_REL = Path("skills/sr-search/src/stockroom/migrations")
SSOT_REL = Path("skills/sr-query/references/warehouse-schema.md")

_SNAPSHOT_NAME = re.compile(r"^(\d{4})_snapshot\.json$")
_REL_NONE = re.compile(r"^-- @rel-none\s+(\w+)\s*$")
_REL = re.compile(
    r"^-- @rel\s+(\w+)\(([^)]+)\)\s*->\s*(\w+)\(([^)]+)\)(?:\s*:\s*(.+))?\s*$"
)


@dataclass(frozen=True)
class Relationship:
    """One logical child→parent (or view→base) edge from a ``-- @rel`` comment.

    ``source`` is ``<from>`` (child / view). ``target`` is ``<to>`` (parent /
    base). Mermaid is drawn ``target ||--o{ source``.
    """

    source: str
    source_columns: tuple[str, ...]
    target: str
    target_columns: tuple[str, ...]
    label: str | None = None


@dataclass(frozen=True)
class RelGraph:
    """Parsed ``@rel`` / ``@rel-none`` comments from migration SQL."""

    relationships: tuple[Relationship, ...]
    isolated: frozenset[str]


def load_head_snapshot(fixtures_dir: Path) -> dict:
    """Return the JSON object from the highest-numbered ``NNNN_snapshot.json``.

    ``fixtures_dir`` is typically ``skills/sr-search/tests/fixtures/schema``.
    Raises ``FileNotFoundError`` if no snapshot is present.
    """
    candidates: list[tuple[int, Path]] = []
    if fixtures_dir.is_dir():
        for path in fixtures_dir.iterdir():
            match = _SNAPSHOT_NAME.match(path.name)
            if match:
                candidates.append((int(match.group(1)), path))
    if not candidates:
        raise FileNotFoundError(f"no NNNN_snapshot.json under {fixtures_dir}")
    candidates.sort()
    return json.loads(candidates[-1][1].read_text(encoding="utf-8"))


def _split_cols(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(",") if part.strip())


def _contradiction(
    isolated: set[str] | frozenset[str], rels: list[Relationship]
) -> None:
    overlap = set(isolated) & {rel.source for rel in rels}
    if overlap:
        names = ", ".join(sorted(overlap))
        raise ValueError(f"@rel-none contradicts @rel from: {names}")


def parse_rels(sql_text: str) -> RelGraph:
    """Parse ``-- @rel`` / ``-- @rel-none`` lines from one SQL document.

    Ordinary ``--`` comments and DDL are ignored. A line that starts with
    ``-- @rel`` but does not match the grammar is an error. An entity that is
    both ``@rel-none`` and a ``<from>`` is an error.
    """
    rels: list[Relationship] = []
    isolated: set[str] = set()
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- @rel-none"):
            match = _REL_NONE.match(stripped)
            if not match:
                raise ValueError(f"malformed @rel-none: {stripped}")
            isolated.add(match.group(1))
            continue
        if stripped.startswith("-- @rel"):
            match = _REL.match(stripped)
            if not match:
                raise ValueError(f"malformed @rel: {stripped}")
            source, source_cols, target, target_cols, label = match.groups()
            caption = label.strip() if label else None
            rels.append(
                Relationship(
                    source=source,
                    source_columns=_split_cols(source_cols),
                    target=target,
                    target_columns=_split_cols(target_cols),
                    label=caption or None,
                )
            )
    _contradiction(isolated, rels)
    return RelGraph(tuple(rels), frozenset(isolated))


def parse_rels_dir(migrations_dir: Path) -> RelGraph:
    """Parse every ``*.sql`` file in ``migrations_dir`` (sorted by name) and merge."""
    rels: list[Relationship] = []
    isolated: set[str] = set()
    for path in sorted(migrations_dir.glob("*.sql")):
        graph = parse_rels(path.read_text(encoding="utf-8"))
        rels.extend(graph.relationships)
        isolated.update(graph.isolated)
    _contradiction(isolated, rels)
    return RelGraph(tuple(rels), frozenset(isolated))


def assert_coverage(snapshot: dict, rels: RelGraph) -> None:
    """Require every snapshot table to be a from, a to, or ``@rel-none``.

    Unknown ``@rel`` / ``@rel-none`` names, missing column names, and an
    entity that is both isolated and a ``<from>`` raise ``ValueError``.
    """
    tables: dict = snapshot["tables"]
    names = set(tables)
    sources = {rel.source for rel in rels.relationships}
    targets = {rel.target for rel in rels.relationships}
    mentioned = sources | targets | set(rels.isolated)
    unknown = mentioned - names
    if unknown:
        raise ValueError(f"unknown @rel names: {', '.join(sorted(unknown))}")
    for rel in rels.relationships:
        source_cols = {col["name"] for col in tables[rel.source]["columns"]}
        target_cols = {col["name"] for col in tables[rel.target]["columns"]}
        for col in rel.source_columns:
            if col not in source_cols:
                raise ValueError(f"missing column {col} on {rel.source}")
        for col in rel.target_columns:
            if col not in target_cols:
                raise ValueError(f"missing column {col} on {rel.target}")
    _contradiction(set(rels.isolated), list(rels.relationships))
    missing = names - mentioned
    if missing:
        raise ValueError(
            f"snapshot entities lack @rel/@rel-none: {', '.join(sorted(missing))}"
        )


def _sanitize_type(duckdb_type: str) -> str:
    if duckdb_type.endswith("[]"):
        return f"{duckdb_type[:-2]}_ARRAY"
    return duckdb_type.replace("[", "_").replace("]", "")


def render_markdown(snapshot: dict, rels: RelGraph) -> str:
    """Return the dual-audience markdown body (Mermaid ``erDiagram``, no relative links)."""
    lines = [
        "# Warehouse schema",
        "",
        "Logical relationships only — DuckDB has no FOREIGN KEY constraints"
        " (deliberate). Boxes and columns come from the head schema golden"
        " snapshot; edges come from `-- @rel` / `-- @rel-none` comments in"
        " the migration SQL.",
        "",
        "```mermaid",
        "erDiagram",
    ]
    tables: dict = snapshot["tables"]
    for name in sorted(tables):
        entity = tables[name]
        pk = set(entity["primary_key"])
        if not entity["primary_key"]:
            lines.append(f"    %% view: {name}")
        lines.append(f"    {name} {{")
        for col in entity["columns"]:
            typ = _sanitize_type(col["type"])
            marker = " PK" if col["name"] in pk else ""
            lines.append(f"        {typ} {col['name']}{marker}")
        lines.append("    }")
    ordered = sorted(
        rels.relationships,
        key=lambda rel: (rel.target, rel.source, rel.label or ""),
    )
    for rel in ordered:
        caption = rel.label or ""
        lines.append(f'    {rel.target} ||--o{{ {rel.source} : "{caption}"')
    lines.extend(
        [
            "```",
            "",
            "Indexes (including the embeddings HNSW index) are omitted; they"
            " are snapshot data, not query-forming structure.",
            "",
        ]
    )
    return "\n".join(lines)


def ssot_path(repo_root: Path) -> Path:
    """Return ``skills/sr-query/references/warehouse-schema.md`` under ``repo_root``."""
    return repo_root / SSOT_REL


def _render_repo(repo_root: Path) -> str:
    snapshot = load_head_snapshot(repo_root / FIXTURES_REL)
    rels = parse_rels_dir(repo_root / MIGRATIONS_REL)
    assert_coverage(snapshot, rels)
    return render_markdown(snapshot, rels)


def check(repo_root: Path) -> int:
    """Return 0 if the committed SSOT matches a fresh render; nonzero otherwise.

    Runs coverage first. Does not write. Missing or differing SSOT is failure.
    """
    try:
        rendered = _render_repo(repo_root)
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"warehouse schema docs: {exc}", file=sys.stderr)
        return 1
    path = ssot_path(repo_root)
    if not path.is_file():
        print(f"warehouse schema docs: missing {path}", file=sys.stderr)
        return 1
    if path.read_text(encoding="utf-8") != rendered:
        print(
            f"warehouse schema docs: {path} is out of date;"
            " run python3 scripts/gen_warehouse_schema.py",
            file=sys.stderr,
        )
        return 1
    return 0


def write(repo_root: Path) -> None:
    """Write a fresh render to the skill SSOT path (after coverage succeeds)."""
    rendered = _render_repo(repo_root)
    path = ssot_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI: default writes the SSOT; ``--check`` compares and returns 0/1."""
    parser = argparse.ArgumentParser(
        description="Generate warehouse schema ERD markdown from the head golden."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 0 if the committed SSOT matches; do not write",
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    if args.check:
        return check(repo_root)
    write(repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
