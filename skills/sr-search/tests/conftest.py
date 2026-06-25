"""Shared pytest fixtures for the stockroom engine test suite.

The engine lives inside ``skills/sr-search/`` but several tests
(packaging, licensing) assert against repo-root artifacts. The
``repo_root`` fixture lets those tests reach the root without brittle
relative-path arithmetic.
"""

import os
import subprocess
import sys
import time
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
def spawn_worker() -> Iterator[Callable[..., subprocess.Popen]]:
    """Return a launcher for the warehouse concurrency worker subprocess.

    Each spawned child runs ``tests/_warehouse_worker.py`` under the same
    interpreter, with the engine ``src`` on ``PYTHONPATH`` and the current
    environment inherited (so the test's ``STOCKROOM_HOME`` flows through). All
    children are killed and reaped at teardown so a hung worker can never leak
    past a test.
    """
    src_dir = str(Path(stockroom.__file__).parent.parent)
    worker = Path(__file__).parent / "_warehouse_worker.py"
    children: list[subprocess.Popen] = []

    def _spawn(*args: object) -> subprocess.Popen:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [src_dir, env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        proc = subprocess.Popen(
            [sys.executable, str(worker), *[str(a) for a in args]], env=env
        )
        children.append(proc)
        return proc

    try:
        yield _spawn
    finally:
        for proc in children:
            if proc.poll() is None:
                proc.kill()
            proc.wait()


@pytest.fixture
def wait_for_sentinel() -> Callable[..., None]:
    """Return a helper that blocks until a sentinel file appears.

    Synchronizes a parent with a child that signals readiness by creating a
    file — outcome-based coordination rather than fragile ``sleep`` guesses.
    Raises ``TimeoutError`` if the sentinel never shows within the timeout.
    """

    def _wait(path: Path, timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        while not path.exists():
            if time.monotonic() >= deadline:
                raise TimeoutError(f"sentinel never appeared: {path}")
            time.sleep(0.02)

    return _wait


@pytest.fixture
def warehouse_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``STOCKROOM_HOME`` at a fresh (not-yet-created) tmp directory.

    Returns the intended home path *without* creating it, so tests can assert
    the warehouse helper auto-creates it on first use. Isolates every test
    from the operator's real ``~/.stockroom/`` warehouse.
    """
    home = tmp_path / "stockroom_home"
    monkeypatch.setenv("STOCKROOM_HOME", str(home))
    return home


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
