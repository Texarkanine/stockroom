"""Shared pytest fixtures for the stockroom engine test suite.

The engine lives inside ``skills/sr-search/`` but several tests
(packaging, licensing) assert against repo-root artifacts. The
``repo_root`` fixture lets those tests reach the root without brittle
relative-path arithmetic.
"""

import hashlib
import os
import sqlite3
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import duckdb
import pytest

import stockroom
from stockroom import embed, warehouse
from stockroom.migrate import apply_pending


class FakeEncoder:
    """A deterministic, torch-free :class:`embed.Encoder` for unit tests.

    Maps each input string to a fixed 384-dim vector derived from its SHA-256
    digest, so identical text always encodes to an identical vector (a query
    equal to a stored chunk has cosine distance 0) and distinct text encodes
    distinctly. No model, no torch — the embedding/search logic is exercised in
    full. Shared by ``test_embed`` (the pipeline) and ``test_semantic`` (search).
    """

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()  # 32 bytes
        raw = (digest * (embed.EMBED_DIM // len(digest) + 1))[: embed.EMBED_DIM]
        return [byte / 255.0 for byte in raw]


@pytest.fixture
def stub_uv(tmp_path: Path) -> Path:
    """Write a stub ``uv`` executable and return the bin dir containing it.

    The stub prints its ``PYTHONPATH`` and each argument on its own labelled
    line (``UV_PYTHONPATH:…`` / ``UV_ARG:…``) and exits 0, so the shim runtime
    tests can assert the exact exec contract (baked ``APP_DIR``, torch-safe
    flags, verbatim argument forwarding) without a real uv or engine run.
    """
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir(exist_ok=True)
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/bin/sh\n"
        "printf 'UV_PYTHONPATH:%s\\n' \"$PYTHONPATH\"\n"
        'for arg in "$@"; do\n'
        "    printf 'UV_ARG:%s\\n' \"$arg\"\n"
        "done\n"
        "exit 0\n",
        encoding="utf-8",
    )
    uv.chmod(0o755)
    return bin_dir


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
    from the operator's real XDG warehouse home.
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


@pytest.fixture(scope="session")
def transcripts_dir() -> Path:
    """Return the committed native-format transcript fixtures directory.

    These fixtures are laid out as two faithful *harness roots* (mirroring
    ``~/.cursor/projects`` and ``~/.claude/projects`` on real disk) so the
    ingest discovery/parse/orchestrator tests can scan them exactly as the
    live ingest scans the operator's history.
    """
    path = Path(__file__).parent / "fixtures" / "transcripts"
    assert path.is_dir(), f"transcript fixtures missing: {path}"
    return path


@pytest.fixture(scope="session")
def cursor_root(transcripts_dir: Path) -> Path:
    """Return the Cursor fixture root (stands in for ``~/.cursor/projects``).

    Under it: ``<encoded-project>/agent-transcripts/<conv>/<conv>.jsonl`` with
    subagents at ``<conv>/subagents/<child>.jsonl`` — the real Cursor layout.
    """
    return transcripts_dir / "cursor"


@pytest.fixture(scope="session")
def claude_root(transcripts_dir: Path) -> Path:
    """Return the Claude fixture root (stands in for ``~/.claude/projects``).

    Under it: ``<encoded-cwd>/<sessionId>.jsonl`` with subagents at
    ``<encoded-cwd>/<sessionId>/subagents/agent-*.jsonl`` (+ ``.meta.json``) —
    the real Claude Code layout.
    """
    return transcripts_dir / "claude"


#: Synthetic Cursor ``ai-code-tracking.db`` schema (model-enrichment subset).
#:
#: Matches the current Cursor on-disk shape (``ai_code_hashes`` + optional
#: ``conversation_summaries``). The enrichment happy-path is exercised against
#: this synthetic, clean-room fixture built at test time from documented SQL
#: (reviewable; no opaque binary committed). It is intentionally limited to the
#: model-enrichment grain ingest consumes — attribution tables are out of scope.
_AI_TRACKING_SCHEMA = (
    "CREATE TABLE ai_code_hashes ("
    "  hash           TEXT PRIMARY KEY,"
    "  conversationId TEXT,"
    "  timestamp      INTEGER,"
    "  createdAt      INTEGER NOT NULL,"
    "  model          TEXT"
    ");"
    "CREATE TABLE conversation_summaries ("
    "  conversationId TEXT PRIMARY KEY,"
    "  model          TEXT,"
    "  updatedAt      INTEGER NOT NULL"
    ")"
)

#: Seed rows for ``ai_code_hashes``: (hash, conversationId, timestamp, createdAt, model).
#: Conversation ids overlap the committed Cursor transcript fixtures so the
#: orchestrator can apply enrichment. Timestamps establish first-seen order.
_AI_TRACKING_HASH_SEED = [
    ("h1", "simple-conversation", 100, 100, "gpt-5"),
    ("h2", "simple-conversation", 200, 200, "claude-4.6-sonnet"),
    ("h3", "00000000-0000-4000-8000-000000000001", 150, 150, "gpt-5"),
]


@pytest.fixture
def ai_tracking_db(tmp_path: Path) -> Path:
    """Build a synthetic Cursor ``ai-code-tracking.db`` and return its path.

    Materializes :data:`_AI_TRACKING_SCHEMA` seeded with
    :data:`_AI_TRACKING_HASH_SEED` into a fresh sqlite file under ``tmp_path``.
    Lets the enrichment tests exercise the present-DB read path deterministically
    without committing an opaque binary or depending on the operator's machine.
    """
    db_path = tmp_path / "ai-code-tracking.db"
    con = sqlite3.connect(db_path)
    try:
        con.executescript(_AI_TRACKING_SCHEMA)
        con.executemany(
            "INSERT INTO ai_code_hashes "
            "(hash, conversationId, timestamp, createdAt, model) "
            "VALUES (?, ?, ?, ?, ?)",
            _AI_TRACKING_HASH_SEED,
        )
        con.commit()
    finally:
        con.close()
    return db_path


@pytest.fixture
def schema_con(schema_sql_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a fresh in-memory DuckDB with the ``0001`` schema applied.

    This is deliberately *not* a migration runner (that is milestone 2): the
    fixture simply reads the DDL text and ``execute()``s it against a clean
    in-memory connection, giving each test an isolated database whose shape
    is exactly what ``0001`` declares. Use it for the frozen ``0001`` contract
    tests; ingest tests that write the *current* schema use ``migrated_con``.
    """
    con = duckdb.connect(":memory:")
    con.execute(schema_sql_path.read_text(encoding="utf-8"))
    try:
        yield con
    finally:
        con.close()


@pytest.fixture
def migrated_con() -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield an in-memory DuckDB with the full migration chain applied.

    Unlike ``schema_con`` (which executes only the ``0001`` DDL directly), this
    runs the real packaged migrations (``0001`` + ``0002`` + …) through
    :func:`stockroom.migrate.apply_pending` — i.e. the post-migration schema the
    ingest writer and orchestrator actually target. Each test gets an isolated,
    up-to-date database.

    ``ensure_vss`` is called before applying the chain because ``0003`` creates
    the HNSW index and assumes ``vss`` is already loaded (the precondition the
    ``warehouse.open()`` chokepoint establishes in production).
    """
    con = duckdb.connect(":memory:")
    warehouse.ensure_vss(con)
    apply_pending(con)
    try:
        yield con
    finally:
        con.close()
