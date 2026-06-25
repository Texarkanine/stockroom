"""Migration discovery: enumerate packaged ``NNNN_*.sql`` in version order.

Discovery is the DB-free half of the migration subsystem: it parses the
``migrations/`` package directory into an ascending list of
``(version, path)`` pairs. These tests pin that contract — the ``0001``
schema is discovered in place, non-conforming filenames are ignored, and
ordering is numeric (not lexical), so ``0010`` never sorts before ``0002``.
"""

from pathlib import Path

from stockroom.migrations import Migration, discover, migrations_dir


def test_migrations_dir_holds_packaged_0001(schema_sql_path: Path) -> None:
    """``migrations_dir()`` is the package dir that ships ``0001``."""
    assert migrations_dir() == schema_sql_path.parent
    assert (migrations_dir() / "0001_initial_schema.sql").is_file()


def test_discover_returns_0001_ascending(schema_sql_path: Path) -> None:
    """Default discovery over the package dir yields exactly migration 1."""
    assert discover() == [Migration(1, schema_sql_path)]


def test_discover_ignores_non_conforming_filenames(tmp_path: Path) -> None:
    """Only ``NNNN_<slug>.sql`` names are migrations; everything else is ignored."""
    (tmp_path / "0001_alpha.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "0002_beta.sql").write_text("SELECT 1;", encoding="utf-8")
    # Decoys that must NOT be picked up:
    (tmp_path / "README.md").write_text("docs", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    (tmp_path / "0003.sql").write_text("SELECT 1;", encoding="utf-8")  # no slug
    (tmp_path / "draft_x.sql").write_text("SELECT 1;", encoding="utf-8")  # no number
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")

    found = discover(tmp_path)
    assert found == [
        Migration(1, tmp_path / "0001_alpha.sql"),
        Migration(2, tmp_path / "0002_beta.sql"),
    ]


def test_discover_orders_numerically_not_lexically(tmp_path: Path) -> None:
    """Versions sort by integer value: ``0010`` follows ``0002``, not ``0001``."""
    (tmp_path / "0002_b.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "0010_c.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "0001_a.sql").write_text("SELECT 1;", encoding="utf-8")

    assert [m.version for m in discover(tmp_path)] == [1, 2, 10]
