"""Shared pytest fixtures for the stockroom engine test suite.

The engine lives inside ``skills/sr-search/`` but several tests
(packaging, licensing) assert against repo-root artifacts. The
``repo_root`` fixture lets those tests reach the root without brittle
relative-path arithmetic.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import duckdb
import pytest

import stockroom


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the repository root: the nearest ancestor containing ``.git``.

    Walks up from this file until it finds a directory holding a ``.git``
    entry (directory or file, to support worktrees/submodules). Raises if
    no such ancestor exists, which would mean the tests are running outside
    the repository.
    """
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("Could not locate repository root (no .git ancestor found)")


@pytest.fixture(scope="session")
def schema_sql_path() -> Path:
    """Locate the packaged ``0001`` migration SQL via the installed package.

    Resolving through ``stockroom.__file__`` (rather than a hard-coded repo
    path) pins the migration to its final packaged location
    ``stockroom/migrations/0001_initial_schema.sql`` — the exact path
    milestone 2's framework will consume in place. If the file moves, this
    fixture (and every schema test) fails loudly.
    """
    path = Path(stockroom.__file__).parent / "migrations" / "0001_initial_schema.sql"
    assert path.is_file(), f"migration SQL missing: {path}"
    return path


@pytest.fixture
def tmp_migrations_dir(tmp_path: Path) -> Callable[..., Path]:
    """Return a factory that builds a synthetic migrations directory.

    Given a ``{version: sql}`` mapping, the factory writes one
    ``NNNN_m<version>.sql`` file per entry into a fresh ``migrations/``
    subdirectory of the test's ``tmp_path`` and returns that directory — ready
    to hand to :func:`stockroom.migrations.discover` /
    :func:`stockroom.migrate.apply_pending`. Lets the ordering and atomicity
    tests drive the runner with controlled, non-product migrations.
    """

    def _build(migrations: dict[int, str]) -> Path:
        base = tmp_path / "migrations"
        base.mkdir(exist_ok=True)
        for version, sql in migrations.items():
            (base / f"{version:04d}_m{version}.sql").write_text(sql, encoding="utf-8")
        return base

    return _build


@pytest.fixture
def mem_con() -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a fresh, empty in-memory DuckDB connection.

    Unlike ``schema_con`` (which pre-applies ``0001``), this gives the
    migration-runner tests a blank database so they can exercise the runner's
    own bootstrap path — including "no ``schema_version`` table yet".
    """
    con = duckdb.connect(":memory:")
    try:
        yield con
    finally:
        con.close()


@pytest.fixture
def schema_con(schema_sql_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a fresh in-memory DuckDB with the ``0001`` schema applied.

    This is deliberately *not* a migration runner (that is milestone 2): the
    fixture simply reads the DDL text and ``execute()``s it against a clean
    in-memory connection, giving each test an isolated database whose shape
    is exactly what ``0001`` declares.
    """
    con = duckdb.connect(":memory:")
    con.execute(schema_sql_path.read_text(encoding="utf-8"))
    try:
        yield con
    finally:
        con.close()
