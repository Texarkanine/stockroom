"""Warehouse schema ERD generator: render, @rel parse/coverage, lockstep, dual-audience.

The generator lives at repo-root ``scripts/gen_warehouse_schema.py`` (stdlib,
not an engine package). Tests load it via importlib so pytest does not need
that path on ``PYTHONPATH``.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_RELATIVE_MD_LINK = re.compile(r"\]\((?!https://)[^)]+\)")

_TOY_SNAPSHOT = {
    "indexes": [],
    "tables": {
        "parents": {
            "columns": [
                {"name": "id", "nullable": False, "type": "VARCHAR"},
                {"name": "vec", "nullable": True, "type": "FLOAT[384]"},
            ],
            "primary_key": ["id"],
        },
        "children": {
            "columns": [
                {"name": "id", "nullable": False, "type": "VARCHAR"},
                {"name": "parent_id", "nullable": False, "type": "VARCHAR"},
                {"name": "tags", "nullable": True, "type": "VARCHAR[]"},
            ],
            "primary_key": ["id"],
        },
        "rollups": {
            "columns": [
                {"name": "id", "nullable": False, "type": "HUGEINT"},
                {"name": "payload", "nullable": True, "type": "JSON"},
            ],
            "primary_key": [],
        },
        "orphans": {
            "columns": [{"name": "id", "nullable": False, "type": "VARCHAR"}],
            "primary_key": ["id"],
        },
    },
}

_SKELETON = """# Warehouse Schema

Prose stays.

```mermaid
erDiagram
```

Footer stays.
"""


_TOY_SQL = """
-- ordinary design comment, not an edge
CREATE TABLE parents (
    id VARCHAR,
    vec FLOAT[384],
    PRIMARY KEY (id)
);

-- @rel children(parent_id) -> parents(id)
CREATE TABLE children (
    id VARCHAR,
    parent_id VARCHAR,
    tags VARCHAR[],
    PRIMARY KEY (id)
);

-- @rel rollups(id) -> parents(id) : rolls up
CREATE VIEW rollups AS SELECT id FROM parents;

-- @rel-none orphans
CREATE TABLE orphans (
    id VARCHAR,
    PRIMARY KEY (id)
);
"""


@pytest.fixture(scope="session")
def gen(repo_root: Path) -> ModuleType:
    """Load ``scripts/gen_warehouse_schema.py`` as a module."""
    path = repo_root / "scripts" / "gen_warehouse_schema.py"
    spec = importlib.util.spec_from_file_location("gen_warehouse_schema", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mini_repo(tmp_path: Path, gen: ModuleType, ssot_text: str | None = None) -> Path:
    """Build a tiny repo_root with one snapshot, one migration, optional SSOT."""
    fixtures = tmp_path / "skills/sr-search/tests/fixtures/schema"
    fixtures.mkdir(parents=True)
    (fixtures / "0001_snapshot.json").write_text(
        json.dumps(_TOY_SNAPSHOT), encoding="utf-8"
    )
    migrations = tmp_path / "skills/sr-search/src/stockroom/migrations"
    migrations.mkdir(parents=True)
    (migrations / "0001_toy.sql").write_text(_TOY_SQL, encoding="utf-8")
    if ssot_text is not None:
        ssot = gen.ssot_path(tmp_path)
        ssot.parent.mkdir(parents=True, exist_ok=True)
        ssot.write_text(ssot_text, encoding="utf-8")
    return tmp_path


def test_toy_render_includes_entities_pk_and_sanitized_types(gen: ModuleType) -> None:
    """A 2-table snapshot renders both names, PK markers, and sanitized types."""
    rels = gen.parse_rels(_TOY_SQL)
    diagram = gen.render_er_diagram(_TOY_SNAPSHOT, rels)
    assert diagram.startswith("erDiagram")
    assert "```" not in diagram
    assert "parents" in diagram
    assert "children" in diagram
    assert "PK" in diagram
    assert "FLOAT[384]" not in diagram
    assert "VARCHAR[]" not in diagram
    assert "FLOAT_384" in diagram
    assert "VARCHAR_ARRAY" in diagram
    assert "HUGEINT" in diagram
    assert "JSON" in diagram


def test_view_heuristic_marks_empty_primary_key_as_view(gen: ModuleType) -> None:
    """Empty-PK entities get a visible Mermaid alias; ``%%`` comments do not count."""
    rels = gen.parse_rels(_TOY_SQL)
    diagram = gen.render_er_diagram(_TOY_SNAPSHOT, rels)
    assert 'rollups["rollups (view)"]' in diagram
    assert "%% view:" not in diagram
    assert 'parents["' not in diagram
    assert 'children["' not in diagram
    assert 'orphans["' not in diagram


def test_parse_rels_reads_rel_and_rel_none_ignores_ordinary_sql(
    gen: ModuleType,
) -> None:
    """Toy SQL with two ``@rel`` lines and one ``@rel-none`` yields those edges/entities."""
    graph = gen.parse_rels(_TOY_SQL)
    assert graph.isolated == frozenset({"orphans"})
    pairs = {(rel.source, rel.target, rel.label) for rel in graph.relationships}
    assert pairs == {
        ("children", "parents", None),
        ("rollups", "parents", "rolls up"),
    }
    children = next(rel for rel in graph.relationships if rel.source == "children")
    assert children.source_columns == ("parent_id",)
    assert children.target_columns == ("id",)
    spaced = gen.parse_rels(
        "-- @rel embeddings(harness, owner_id) -> messages(harness, message_id)"
        " : owner_table=messages\n"
    )
    edge = spaced.relationships[0]
    assert edge.source_columns == ("harness", "owner_id")
    assert edge.target_columns == ("harness", "message_id")
    assert edge.label == "owner_table=messages"


def test_parse_rels_rejects_rel_none_plus_rel_from_same_entity(gen: ModuleType) -> None:
    """A contradictory ``@rel-none`` plus ``@rel`` for the same ``<from>`` is an error."""
    sql = """
-- @rel-none children
-- @rel children(parent_id) -> parents(id)
"""
    with pytest.raises(ValueError, match="children"):
        gen.parse_rels(sql)


def test_assert_coverage_passes_when_every_snapshot_name_is_accounted(
    gen: ModuleType,
) -> None:
    """Every snapshot table name is a from, a to, or rel-none."""
    gen.assert_coverage(_TOY_SNAPSHOT, gen.parse_rels(_TOY_SQL))


def test_assert_coverage_fails_unknown_name_and_unaccounted_snapshot(
    gen: ModuleType,
) -> None:
    """An unknown ``@rel`` name fails; a snapshot name in neither set fails."""
    unknown = gen.parse_rels("-- @rel children(parent_id) -> ghosts(id)\n")
    with pytest.raises(ValueError, match="ghosts"):
        gen.assert_coverage(_TOY_SNAPSHOT, unknown)

    partial = gen.parse_rels(
        "-- @rel children(parent_id) -> parents(id)\n-- @rel-none orphans\n"
    )
    with pytest.raises(ValueError, match="rollups"):
        gen.assert_coverage(_TOY_SNAPSHOT, partial)


def test_assert_coverage_fails_when_rel_column_missing_from_entity(
    gen: ModuleType,
) -> None:
    """A column listed in ``@rel`` that is missing from that entity fails."""
    rels = gen.parse_rels("-- @rel children(missing_col) -> parents(id)\n")
    with pytest.raises(ValueError, match="missing_col"):
        gen.assert_coverage(_TOY_SNAPSHOT, rels)


def test_render_includes_logical_relationship_lines(gen: ModuleType) -> None:
    """``@rel`` edges appear as Mermaid relationship lines; ``@rel-none`` has none."""
    rels = gen.parse_rels(_TOY_SQL)
    diagram = gen.render_er_diagram(_TOY_SNAPSHOT, rels)
    assert "parents ||--o{ children" in diagram
    assert "parents ||--o{ rollups" in diagram
    assert "rolls up" in diagram
    assert "orphans ||--" not in diagram
    assert "||--o{ orphans" not in diagram


def test_rendered_diagram_has_no_relative_links(gen: ModuleType) -> None:
    """Generated Mermaid contains no relative markdown links (https URLs allowed)."""
    diagram = gen.render_er_diagram(_TOY_SNAPSHOT, gen.parse_rels(_TOY_SQL))
    assert _RELATIVE_MD_LINK.search(diagram) is None


def test_splice_mermaid_replaces_only_the_one_fence(gen: ModuleType) -> None:
    """Surrounding markdown is preserved; only the mermaid fence body is replaced."""
    page = "# Title\n\nIntro.\n\n```mermaid\nerDiagram\n    stale\n```\n\nOutro.\n"
    spliced = gen.splice_mermaid(page, "erDiagram\n    fresh")
    assert spliced.startswith("# Title\n\nIntro.\n")
    assert spliced.endswith("Outro.\n")
    assert "stale" not in spliced
    assert "erDiagram\n    fresh\n" in spliced
    assert spliced.count("```") == 2


def test_splice_mermaid_rejects_missing_or_multiple_fences(gen: ModuleType) -> None:
    """Exactly one `` ```mermaid `` fence is required."""
    with pytest.raises(ValueError, match="mermaid"):
        gen.splice_mermaid("# no fence\n", "erDiagram")
    two = "```mermaid\na\n```\n```mermaid\nb\n```\n"
    with pytest.raises(ValueError, match="mermaid"):
        gen.splice_mermaid(two, "erDiagram")


def test_head_snapshot_render_includes_every_table(
    repo_root: Path, gen: ModuleType
) -> None:
    """Rendering the repo head ``NNNN_snapshot.json`` includes every ``tables`` key."""
    snapshot = gen.load_head_snapshot(
        repo_root / "skills/sr-search/tests/fixtures/schema"
    )
    isolated = gen.RelGraph(relationships=(), isolated=frozenset(snapshot["tables"]))
    diagram = gen.render_er_diagram(snapshot, isolated)
    for name in snapshot["tables"]:
        assert name in diagram


def test_load_head_snapshot_picks_highest_numeric_prefix(
    tmp_path: Path, gen: ModuleType
) -> None:
    """Highest numeric ``NNNN_snapshot.json`` wins when several snapshots exist."""
    fixtures = tmp_path / "schema"
    fixtures.mkdir()
    low = {"indexes": [], "tables": {"old": {"columns": [], "primary_key": []}}}
    high = {"indexes": [], "tables": {"new": {"columns": [], "primary_key": []}}}
    (fixtures / "0003_snapshot.json").write_text(json.dumps(low), encoding="utf-8")
    (fixtures / "0012_snapshot.json").write_text(json.dumps(high), encoding="utf-8")
    loaded = gen.load_head_snapshot(fixtures)
    assert "new" in loaded["tables"]
    assert "old" not in loaded["tables"]


def test_check_fails_when_ssot_missing_and_does_not_write(
    tmp_path: Path, gen: ModuleType
) -> None:
    """``check`` is nonzero and does not write when the committed SSOT is missing."""
    repo = _mini_repo(tmp_path, gen)
    ssot = gen.ssot_path(repo)
    assert not ssot.exists()
    assert gen.check(repo) != 0
    assert not ssot.exists()


def test_write_then_check_succeeds(tmp_path: Path, gen: ModuleType) -> None:
    """CLI/write splices the diagram into an existing page so ``check`` passes."""
    repo = _mini_repo(tmp_path, gen, ssot_text=_SKELETON)
    gen.write(repo)
    assert gen.ssot_path(repo).is_file()
    assert gen.check(repo) == 0


def test_write_preserves_surrounding_prose(tmp_path: Path, gen: ModuleType) -> None:
    """``write`` does not regenerate title, intro, or footer around the fence."""
    repo = _mini_repo(tmp_path, gen, ssot_text=_SKELETON)
    gen.write(repo)
    text = gen.ssot_path(repo).read_text(encoding="utf-8")
    assert "Prose stays." in text
    assert "Footer stays." in text
    assert "parents" in text
    assert text.startswith("# Warehouse Schema\n")


def test_write_fails_when_ssot_missing(tmp_path: Path, gen: ModuleType) -> None:
    """``write`` does not invent the markdown page; the fence must already exist."""
    repo = _mini_repo(tmp_path, gen)
    with pytest.raises(FileNotFoundError):
        gen.write(repo)
    assert not gen.ssot_path(repo).exists()


def test_check_fails_when_ssot_differs_and_does_not_rewrite(
    tmp_path: Path, gen: ModuleType
) -> None:
    """``check`` is nonzero on a stale mermaid fence and leaves the page unchanged."""
    stale = _SKELETON.replace("erDiagram\n", "erDiagram\n    stale\n")
    repo = _mini_repo(tmp_path, gen, ssot_text=stale)
    ssot = gen.ssot_path(repo)
    before = ssot.read_text(encoding="utf-8")
    assert gen.check(repo) != 0
    assert ssot.read_text(encoding="utf-8") == before


def test_repo_migrations_rel_coverage(repo_root: Path, gen: ModuleType) -> None:
    """Parsing the real ``migrations/`` tree accounts for every head-snapshot entity."""
    snapshot = gen.load_head_snapshot(
        repo_root / "skills/sr-search/tests/fixtures/schema"
    )
    rels = gen.parse_rels_dir(repo_root / "skills/sr-search/src/stockroom/migrations")
    gen.assert_coverage(snapshot, rels)


def test_committed_ssot_matches_head_snapshot_render(
    repo_root: Path, gen: ModuleType
) -> None:
    """``check(repo_root)`` succeeds when the committed SSOT matches a fresh render."""
    assert gen.check(repo_root) == 0


def test_docs_warehouse_schema_symlinks_to_skill_ssot(
    repo_root: Path, gen: ModuleType
) -> None:
    """Advanced docs expose the ERD via a symlink to the skill SSOT."""
    link = repo_root / "docs/advanced/warehouse-schema.md"
    target = gen.ssot_path(repo_root).resolve()
    assert link.is_symlink(), f"expected symlink: {link}"
    assert link.resolve() == target, (
        f"{link} should resolve to {target}, got {link.resolve()}"
    )


def test_make_schema_docs_check_passes(repo_root: Path) -> None:
    """``make schema-docs-check`` from the repo root exits 0 (existence pin)."""
    result = subprocess.run(
        ["make", "schema-docs-check"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"make schema-docs-check failed:\n{result.stdout}\n{result.stderr}"
    )
