"""Shadow-test the DuckDB 2.0 engine against a copy of a real warehouse.

A contributor program, not a stockroom command, and nothing starts it from a
hook. It runs from a clone of the branch under a DuckDB 2.0 overlay of the
engine project, from the repo root::

    uv run --project skills/sr-search --no-config --no-sync --with duckdb==2.0.0 \\
        python scripts/shadow_duckdb_20.py \\
        --source ~/.local/share/stockroom/warehouse.duckdb --home /scratch/shadow

It never opens ``--source`` with DuckDB. Its only operations on that file are
the writer flock beside it, a ``.wal`` check, one byte copy, and a stat. All
other work happens under ``--home``, a new empty directory that becomes the
``STOCKROOM_HOME`` of every stockroom command the script runs. The run needs
twice the source's size plus 1 GiB free there.

Phases, in order (``--stop-after`` ends the run early):

1. Overlay check: this interpreter runs DuckDB 2.0, and with the engine on
   ``PYTHONPATH`` it imports ``stockroom`` and torch. Torch is installed from
   the hashed freeze into this interpreter's environment when it is missing.
2. Synthetic section: one line per DuckDB behaviour the later milestones state,
   then :func:`reproduce` on two small files must return ``loud`` and
   ``folded``. ``--synthetic`` runs only phases 1 and 2.
3. Copy under the writer flock, refusing a source with a ``.wal``.
4. Checkpoint the working copy with DuckDB 2.0 and compare every table with
   the baseline copy in both directions.
5. Ingest, ``embed --verbose``, a checkpoint, semantic search, and the
   unscoped plan, on the working copy, then a DuckDB 1.5.4 writer and a 2.0
   reader.
6. Branch A and branch B: :func:`reproduce` on fresh copies of the baseline
   must return ``loud`` and ``folded``, and the repair must restore both.
7. The same two branches on a newer final 2.0 patch, when PyPI has one.

The script exits 0 only when every phase it ran passed. Stdlib at import:
DuckDB and the engine are imported inside the functions that use them, so the
guards run on any interpreter.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import select
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE = REPO_ROOT / "skills" / "sr-search"
ENGINE_SRC = ENGINE / "src"
INDEX_SQL = ENGINE_SRC / "stockroom" / "migrations" / "0003_embeddings_hnsw_index.sql"

#: Seconds one observation statement, or the kill child's count line, may run
#: before the parent sends SIGKILL.
PROBE_SECONDS = 180.0

#: Free space the copy needs beyond twice the source's size.
MARGIN_BYTES = 1 << 30

WAREHOUSE_NAME = "warehouse.duckdb"
BASELINE_NAME = "baseline.duckdb"
LOCK_NAME = ".warehouse.lock"
INDEX_NAME = "embeddings_vector_hnsw"
OLD_TAG = "v1.0.0+"
OLD_DUCKDB = "1.5.4"
LOCK_ERROR = "Could not set lock"

#: The observation statements, in the order the probe child runs them.
STATEMENTS = ("cosine", "delete", "insert", "checkpoint")

#: ``checkpoint_threshold`` of the synthetic fold, in bytes.
SYNTHETIC_THRESHOLD = 4096

PYPI_SIMPLE = "https://pypi.org/simple/duckdb/"

_ORPHAN_LINE = re.compile(r"embed: removed (\d+) orphaned embedding rows")
_FINAL_PATCH = re.compile(r"2\.0\.(\d+)")

#: Shared head of every DuckDB child program. A child prints each fact as one
#: flushed line, so the parent can read it while the child keeps running.
_CHILD_PRELUDE = r"""
import os
import random
import sys
import time

import duckdb

COSINE_SQL = (
    "SELECT harness, owner_id, array_cosine_distance(vector, ?::FLOAT[384]) "
    "AS distance FROM embeddings WHERE owner_table = 'messages' "
    "ORDER BY distance LIMIT 100"
)
INDEX_COUNT_SQL = (
    "SELECT count FROM pragma_hnsw_index_info() "
    "WHERE index_name = 'embeddings_vector_hnsw'"
)


def say(line):
    print(line, flush=True)


def one_line(exc):
    text = f"{type(exc).__name__}: {exc}".split("Stack Trace:")[0]
    return " ".join(text.split())


def connect(db, read_only=False):
    con = duckdb.connect(db, read_only=read_only)
    try:
        con.execute("LOAD vss")
    except duckdb.Error:
        con.execute("INSTALL vss")
        con.execute("LOAD vss")
    con.execute("SET hnsw_enable_experimental_persistence = true")
    return con


def vector(seed):
    rng = random.Random(seed)
    return [rng.random() for _ in range(384)]


def counts(con):
    index = con.execute(INDEX_COUNT_SQL).fetchone()
    rows = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
    return f"counts {rows} {index[0] if index else 'none'}"
"""

#: Inserts one embedding with the index up, commits, prints the row count, and
#: holds the connection until the parent kills it.
_INSERT_CHILD = (
    _CHILD_PRELUDE
    + r"""
con = connect(sys.argv[1])
con.execute(
    "INSERT INTO embeddings "
    "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
    "VALUES ('shadow', 'messages', 'shadow-kill#0', 0, 'shadow', ?::FLOAT[384])",
    [vector(1)],
)
say(con.execute("SELECT count(*) FROM embeddings").fetchone()[0])
time.sleep(86400)
"""
)

#: Runs the four observation statements, one result line each.
_PROBE_CHILD = (
    _CHILD_PRELUDE
    + r"""
db, tag = sys.argv[1], sys.argv[2]
statements = (
    ("cosine", COSINE_SQL, [vector(2)]),
    (
        "delete",
        "DELETE FROM embeddings "
        "WHERE harness = 'shadow' AND owner_id = 'shadow-kill#0'",
        [],
    ),
    (
        "insert",
        "INSERT INTO embeddings "
        "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
        "VALUES ('shadow', 'messages', ?, 0, 'shadow', ?::FLOAT[384])",
        [f"shadow-{tag}#0", vector(3)],
    ),
    ("checkpoint", "CHECKPOINT", []),
)
try:
    con = connect(db)
except Exception as exc:
    say("open error " + one_line(exc))
    sys.exit(0)
say("open ok")
for name, sql, params in statements:
    try:
        con.execute(sql, params).fetchall()
    except Exception as exc:
        say(f"{name} error {one_line(exc)}")
    else:
        say(f"{name} ok")
try:
    con.close()
except Exception:
    pass
"""
)

#: Commits rows that do not touch ``embeddings`` until the ``.wal`` is gone.
#: It never issues ``CHECKPOINT``: only the automatic checkpoint folds the log.
_FOLD_CHILD = (
    _CHILD_PRELUDE
    + r"""
db, threshold = sys.argv[1], sys.argv[2]
wal = db + ".wal"
con = connect(db)
if threshold != "default":
    con.execute(f"SET checkpoint_threshold = '{int(threshold)}B'")
con.execute("CREATE TABLE IF NOT EXISTS shadow_fold (i BIGINT, pad VARCHAR)")
for commit in range(1, 1001):
    con.execute(
        "INSERT INTO shadow_fold SELECT range, repeat('x', 1000) FROM range(1000)"
    )
    if not os.path.exists(wal):
        say(f"fold ok after {commit} commits")
        break
else:
    say("fold error the .wal remained after 1000 commits")
con.close()
"""
)

#: Reads the index count and the row count read-only.
_COUNT_CHILD = (
    _CHILD_PRELUDE
    + r"""
con = connect(sys.argv[1], read_only=True)
say(counts(con))
con.close()
"""
)

#: Drops and recreates the HNSW index, checkpoints, and prints both counts.
_REPAIR_CHILD = (
    _CHILD_PRELUDE
    + r"""
db, index_sql = sys.argv[1], sys.argv[2]
try:
    con = connect(db)
except Exception as exc:
    say("open error " + one_line(exc))
    sys.exit(1)
for name, sql in (
    ("drop", "DROP INDEX embeddings_vector_hnsw"),
    ("create", index_sql),
    ("checkpoint", "CHECKPOINT"),
):
    try:
        con.execute(sql)
    except Exception as exc:
        say(f"{name} error {one_line(exc)}")
        sys.exit(1)
    say(f"{name} ok")
say(counts(con))
con.close()
"""
)

#: Writes ``shadow_probe``, answers the unscoped cosine query, prints its version.
_WRITER_CHILD = (
    _CHILD_PRELUDE
    + r"""
con = connect(sys.argv[1])
con.execute(
    "CREATE TABLE IF NOT EXISTS shadow_probe (written_at TIMESTAMP, duckdb VARCHAR)"
)
con.execute(
    "INSERT INTO shadow_probe VALUES (current_timestamp, ?)", [duckdb.__version__]
)
rows = con.execute(COSINE_SQL, [vector(2)]).fetchall()
say(f"cosine ok {len(rows)} rows")
say(f"duckdb {duckdb.__version__}")
con.close()
"""
)


class PhaseError(RuntimeError):
    """A shadow phase failed; the message names what was expected and seen."""


@dataclass(frozen=True)
class Probe:
    """One observation statement that was started against a copy.

    ``opened`` is false when the child could not open the database, which is
    not the replay bug. ``hung`` is true when the parent killed the child while
    this statement ran. ``error`` is the exception text when it raised.
    """

    name: str
    opened: bool
    hung: bool
    error: str | None


def classify(
    wal_present: bool,
    probes: list[Probe],
    index_count: int | None,
    row_count: int | None,
) -> str:
    """Label the state of a copy after a killed embeddings insert.

    Returns ``blocked`` when a probe did not open the database or reports a
    lock error, ``loud`` when the ``.wal`` remains and an opened probe hung or
    raised, ``folded`` when the ``.wal`` is gone and the index holds fewer rows
    than ``embeddings``, and ``healthy`` otherwise.
    """
    if any(
        not probe.opened or (probe.error is not None and LOCK_ERROR in probe.error)
        for probe in probes
    ):
        return "blocked"
    if wal_present and any(probe.hung or probe.error is not None for probe in probes):
        return "loud"
    if (
        not wal_present
        and index_count is not None
        and row_count is not None
        and index_count < row_count
    ):
        return "folded"
    return "healthy"


def read_count_line(stream: IO[bytes], deadline: float) -> int:
    """Return the integer a child printed and flushed on ``stream``.

    Waits at most ``deadline`` seconds for one complete line. Raises
    :class:`PhaseError` when the wait ends, when the child closes the stream
    first, or when the line is not an integer.
    """
    line = _LineReader(stream).readline(deadline)
    if line is None:
        raise PhaseError(f"no count line within {deadline:g} seconds")
    if line == "":
        raise PhaseError("the child exited before it printed a count")
    try:
        return int(line.strip())
    except ValueError:
        raise PhaseError(f"the count line is not an integer: {line!r}") from None


def embeddings_held(after_ingest: int, after_embed: int, removed_orphans: int) -> bool:
    """True when embed kept every embedding row except the orphans it reported."""
    return after_embed >= after_ingest - removed_orphans


def newest_final_patch(versions: list[str]) -> str | None:
    """Return the highest final ``2.0.N`` release in ``versions``, or ``None``.

    Pre-releases and dev uploads (``2.0.0.dev1``, ``2.0.1rc1``) are not final
    releases and are ignored. Patch numbers compare as integers.
    """
    patches = [
        int(match.group(1))
        for version in versions
        if (match := _FINAL_PATCH.fullmatch(version))
    ]
    return f"2.0.{max(patches)}" if patches else None


def reproduce(db: Path, *, threshold: int | None, fold: bool) -> str:
    """Kill an embeddings insert on ``db``, label the result, and repair it.

    ``threshold`` is ``None`` for DuckDB's default ``checkpoint_threshold`` or
    a byte count for the fold writer. With ``fold`` false, the copy is
    repaired only when :func:`classify` returns ``loud``. With ``fold`` true,
    a writer that does not touch ``embeddings`` first commits until the
    ``.wal`` is gone, and the copy is repaired only when the label is
    ``folded``. Returns the label. Raises :class:`PhaseError` when the kill
    child prints no count or a repair step fails.

    Every DuckDB step runs in a child of this interpreter, so the parent never
    holds the file while a child writes it. The kill child's count line and
    each observation statement get :data:`PROBE_SECONDS`. The fold writer and
    the repair run until they return.
    """
    db = Path(db)
    wal = _wal_path(db)
    shown = "default" if threshold is None else f"{threshold} bytes"
    _say(f"reproduce {db.name}: checkpoint_threshold {shown}, fold {fold}")
    flushed = _kill_after_insert(db)
    _say(f"  kill: {flushed} embeddings rows flushed; .wal present: {wal.exists()}")
    probes = _observe(db, tag="observe", timeout=PROBE_SECONDS)
    for probe in probes:
        _say(f"  observe: {_describe(probe)}")
    if fold:
        _run_child(
            "fold",
            _FOLD_CHILD,
            str(db),
            "default" if threshold is None else str(threshold),
            timeout=None,
            required="fold ok",
        )
    wal_present = wal.exists()
    index_count = row_count = None
    if not wal_present:
        row_count, index_count = _parse_counts(
            _run_child("counts", _COUNT_CHILD, str(db), timeout=PROBE_SECONDS)
        )
    label = classify(wal_present, probes, index_count, row_count)
    _say(
        f"  classify: {label} (.wal present: {wal_present}, "
        f"index count: {index_count}, rows: {row_count})"
    )
    if label == ("folded" if fold else "loud"):
        _repair(db, flushed)
    return label


def main(argv: list[str] | None = None) -> int:
    """Run the guards and the phases named by ``--stop-after``; return the exit code."""
    args = _build_parser().parse_args(argv)
    if args.reproduce_child is not None:
        return _reproduce_child(args.reproduce_child, fold=args.fold)
    try:
        _run(args)
    except PhaseError as exc:
        print(f"shadow: FAILED: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


def _run(args: argparse.Namespace) -> None:
    """Check the arguments, then run each phase up to ``--stop-after``."""
    if args.home is None:
        raise PhaseError("--home is required")
    home = args.home.expanduser().absolute()
    if args.synthetic:
        _require_empty(home)
        _check_overlay()
        home.mkdir(parents=True, exist_ok=True)
        _synthetic(home / "synthetic")
        _say("shadow: synthetic section passed")
        return
    if args.source is None:
        raise PhaseError("--source is required unless --synthetic is given")
    source = args.source.expanduser().absolute()
    if not source.is_file():
        raise PhaseError(f"--source {source} is not a file")
    if home.resolve() == source.parent.resolve():
        raise PhaseError(f"--home {home} is the directory that holds --source")
    _require_empty(home)
    need = args.min_free_bytes
    if need is None:
        need = 2 * source.stat().st_size + MARGIN_BYTES
    free = shutil.disk_usage(_existing_ancestor(home)).free
    if free < need:
        raise PhaseError(f"--home has {free} bytes free; this run needs {need}")
    if args.stop_after == "all":
        _check_overlay()
        home.mkdir(parents=True, exist_ok=True)
        _synthetic(home / "synthetic")
    baseline, working = _copy(source, home)
    if args.stop_after == "copy":
        return
    _checkpoint_equality(working, baseline)
    if args.stop_after == "checkpoint":
        return
    _live(home, working)
    _branches(baseline, working)
    _patch_repeat(baseline, working)
    _say(f"shadow: every phase passed; {baseline} can be deleted")


# --- guards and the copy ------------------------------------------------------


def _require_empty(home: Path) -> None:
    if home.exists() and (not home.is_dir() or any(home.iterdir())):
        raise PhaseError(f"--home {home} must be a new or empty directory")


def _existing_ancestor(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if candidate.exists():
            return candidate
    return Path("/")


def _wal_path(db: Path) -> Path:
    return db.with_name(db.name + ".wal")


@contextmanager
def _writer_lock(path: Path) -> Iterator[None]:
    """Hold the stockroom writer flock on ``path`` for the context body."""
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            _say(f"copy: waiting for the writer lock at {path}")
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _copy(source: Path, home: Path) -> tuple[Path, Path]:
    """Copy ``source`` to the baseline under the flock, then the baseline to work on."""
    wal = _wal_path(source)
    baseline = home / BASELINE_NAME
    with _writer_lock(source.parent / LOCK_NAME):
        if wal.exists():
            raise PhaseError(
                f"{wal} exists: a writer is running or was killed; "
                "refusing to copy a warehouse with a .wal"
            )
        before = source.stat()
        home.mkdir(parents=True, exist_ok=True)
        _say(f"copy: {source} ({before.st_size} bytes) -> {baseline}")
        shutil.copyfile(source, baseline)
        after = source.stat()
        if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
            raise PhaseError(f"{source} changed while it was copied")
        if wal.exists():
            raise PhaseError(f"{wal} appeared while {source} was copied")
    if baseline.stat().st_size != before.st_size:
        raise PhaseError(f"{baseline} is not the size of {source}")
    working = home / WAREHOUSE_NAME
    _say(f"copy: {baseline} -> {working}")
    shutil.copyfile(baseline, working)
    return baseline, working


def _checkpoint_equality(working: Path, baseline: Path) -> None:
    """Checkpoint ``working`` and compare every table with ``baseline`` both ways."""
    con = _connect(working)
    try:
        con.execute("CHECKPOINT")
        con.execute(f"ATTACH {_literal(baseline)} AS baseline (READ_ONLY)")
        tables = _table_names(con, "current_database()")
        if tables != _table_names(con, "'baseline'"):
            raise PhaseError("the working copy and the baseline list different tables")
        for table in tables:
            mine, theirs = f'main."{table}"', f'baseline.main."{table}"'
            for left, right in ((mine, theirs), (theirs, mine)):
                extra = con.execute(
                    f"SELECT count(*) FROM (SELECT * FROM {left} "
                    f"EXCEPT ALL SELECT * FROM {right})"
                ).fetchone()[0]
                if extra:
                    raise PhaseError(f"{left} has {extra} rows that {right} lacks")
        tag = _storage_tag(con)
    finally:
        con.close()
    _say(
        f"checkpoint: {len(tables)} tables equal the baseline in both directions; "
        f"storage {tag}"
    )


def _table_names(con: Any, database: str) -> list[str]:
    return [
        row[0]
        for row in con.execute(
            "SELECT table_name FROM duckdb_tables() "
            f"WHERE database_name = {database} AND schema_name = 'main' "
            "AND NOT internal ORDER BY table_name"
        ).fetchall()
    ]


# --- the overlay ------------------------------------------------------------------


def _check_overlay() -> None:
    """Require DuckDB 2.0 here, and ``stockroom`` plus torch for the commands."""
    import duckdb

    _say(f"overlay: duckdb {duckdb.__version__} at {sys.executable}")
    if not duckdb.__version__.startswith("2.0"):
        raise PhaseError(
            f"this interpreter runs DuckDB {duckdb.__version__}; run the script "
            "under uv run --with duckdb==2.0.N"
        )
    if _overlay_imports():
        return
    freeze = _torch_freeze()
    if not freeze.is_file():
        raise PhaseError(f"torch is missing and there is no hashed freeze at {freeze}")
    _say(f"overlay: installing torch from {freeze} into {sys.prefix}")
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--no-config",
            "--python",
            sys.executable,
            "--require-hashes",
            "-r",
            str(freeze),
        ],
        check=False,
    )
    if result.returncode != 0 or not _overlay_imports():
        raise PhaseError("torch could not be installed into this interpreter")


def _overlay_imports() -> bool:
    """True when ``duckdb`` 2.0, ``stockroom``, and torch import in a child."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import duckdb, stockroom, torch; print(duckdb.__version__)",
        ],
        env=_engine_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    ok = result.returncode == 0 and result.stdout.startswith("2.0")
    _say(f"overlay: duckdb, stockroom, and torch import: {'yes' if ok else 'no'}")
    return ok


def _torch_freeze() -> Path:
    _engine_on_path()
    from stockroom.home import resolve_home
    from stockroom.torch_source import REQUIREMENTS_FILENAME

    return resolve_home()[0] / REQUIREMENTS_FILENAME


def _engine_on_path() -> None:
    if str(ENGINE_SRC) not in sys.path:
        sys.path.insert(0, str(ENGINE_SRC))


def _engine_env(home: Path | None = None) -> dict[str, str]:
    """This environment with the engine on ``PYTHONPATH`` and, given, a scratch home."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(ENGINE_SRC), env.get("PYTHONPATH", "")) if part
    )
    if home is not None:
        env["STOCKROOM_HOME"] = str(home)
    return env


# --- live phases ------------------------------------------------------------------


def _live(home: Path, working: Path) -> None:
    """Ingest, embed, and search the working copy, then let 1.5.4 write it."""
    import duckdb

    env = _engine_env(home)
    before = _row_counts(working)
    _say(f"live: rows before ingest {before}")
    _stockroom(env, "ingest")
    after_ingest = _row_counts(working)
    _say(f"live: rows after ingest {after_ingest}")
    for table in ("sessions", "messages", "tool_calls"):
        if after_ingest[table] < before[table]:
            raise PhaseError(
                f"ingest: {table} fell from {before[table]} to {after_ingest[table]}"
            )
    output = _stockroom(env, "embed", "--verbose")
    match = _ORPHAN_LINE.search(output)
    removed = int(match.group(1)) if match else 0
    after_embed = _row_counts(working)
    _say(f"live: rows after embed {after_embed}; orphans removed {removed}")
    if not embeddings_held(
        after_ingest["embeddings"], after_embed["embeddings"], removed
    ):
        raise PhaseError(
            f"embed: embeddings fell from {after_ingest['embeddings']} to "
            f"{after_embed['embeddings']} with {removed} orphans reported"
        )
    con = _connect(working)
    try:
        con.execute("CHECKPOINT")
        tag = _storage_tag(con)
    finally:
        con.close()
    if tag != OLD_TAG:
        raise PhaseError(f"the copy's storage tag became {tag}, not {OLD_TAG}")
    _say(f"live: checkpoint done; storage {tag}")
    _stockroom(env, "semantic", "-k", "3", "how does the warehouse lock work")
    _say(f"live: unscoped plan: {_unscoped_plan_line(working)}")
    lines = _run_command(
        f"duckdb {OLD_DUCKDB}",
        [*_uv_python(OLD_DUCKDB), "-c", _WRITER_CHILD, str(working)],
        timeout=PROBE_SECONDS,
        required="cosine ok",
    )
    _require_version(lines, OLD_DUCKDB)
    lines = _run_child(
        "duckdb 2.0",
        _WRITER_CHILD,
        str(working),
        timeout=PROBE_SECONDS,
        required="cosine ok",
    )
    _require_version(lines, duckdb.__version__)
    _say(f"live: {duckdb.__version__} answered after {OLD_DUCKDB} wrote the copy")
    _remove(working)


def _row_counts(db: Path) -> dict[str, int]:
    con = _connect(db, read_only=True)
    try:
        return {
            table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("sessions", "messages", "tool_calls", "embeddings")
        }
    finally:
        con.close()


def _stockroom(env: dict[str, str], *args: str) -> str:
    """Run ``python -m stockroom`` with this interpreter; return its output."""
    lines = _run_command(
        f"stockroom {args[0]}",
        [sys.executable, "-m", "stockroom", *args],
        timeout=None,
        env=env,
        merge_stderr=True,
    )
    return "\n".join(lines)


def _unscoped_plan_line(db: Path) -> str:
    """``EXPLAIN`` the statement unscoped semantic search runs; return its HNSW line."""
    _engine_on_path()
    from stockroom import semantic

    vector = [((index * 7919) % 1000) / 1000.0 for index in range(semantic.EMBED_DIM)]
    con = _connect(db, read_only=True)
    try:
        recorder = _Recorder(con)
        semantic.run_semantic_search(
            "shadow", _FixedEncoder(vector), con=recorder, query_prefix=""
        )
        sql, params = next(
            (sql, params)
            for sql, params in recorder.statements
            if "FROM embeddings" in sql
        )
        plan = "\n".join(
            row[1] for row in con.execute(f"EXPLAIN {sql}", params).fetchall()
        )
    finally:
        con.close()
    lines = [line.strip(" │|") for line in plan.splitlines() if "HNSW" in line]
    if not lines:
        raise PhaseError("the unscoped semantic statement does not plan through HNSW")
    return lines[0]


class _Recorder:
    """Delegates ``execute`` to a connection and records each statement."""

    def __init__(self, con: Any) -> None:
        self._con = con
        self.statements: list[tuple[str, list | None]] = []

    def execute(self, sql: str, params: list | None = None) -> Any:
        self.statements.append((sql, params))
        return self._con.execute(sql, params)


class _FixedEncoder:
    """Encodes every text as one fixed vector."""

    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]


def _branches(baseline: Path, working: Path) -> None:
    """Branch A (leftover ``.wal``) and branch B (folded) on fresh baseline copies."""
    for branch, fold, expected in (("A", False, "loud"), ("B", True, "folded")):
        _say(f"branch {branch}: copy {baseline} -> {working}")
        shutil.copyfile(baseline, working)
        label = reproduce(working, threshold=None, fold=fold)
        if label != expected:
            raise PhaseError(f"branch {branch}: expected {expected}, got {label}")
        _remove(working)


def _patch_repeat(baseline: Path, working: Path) -> None:
    """Repeat both branches on a final 2.0 patch newer than this interpreter's."""
    import duckdb

    current = duckdb.__version__
    newest = newest_final_patch(_pypi_versions())
    if newest is None or _patch(newest) <= _patch(current):
        _say(f"patch: newest final 2.0 release is {newest}; this run used {current}")
        return
    script = str(Path(__file__).resolve())
    for branch, fold, expected in (("A", False, "loud"), ("B", True, "folded")):
        _say(f"patch {newest} branch {branch}: copy {baseline} -> {working}")
        shutil.copyfile(baseline, working)
        command = [*_uv_python(newest), script, "--reproduce-child", str(working)]
        lines = _run_command(
            f"duckdb {newest}",
            [*command, *(["--fold"] if fold else [])],
            timeout=None,
        )
        _require_version(lines, newest)
        if f"label {expected}" not in lines:
            raise PhaseError(f"patch {newest} branch {branch}: expected {expected}")
        _remove(working)


def _pypi_versions() -> list[str]:
    request = urllib.request.Request(
        PYPI_SIMPLE, headers={"Accept": "application/vnd.pypi.simple.v1+json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return list(json.load(response).get("versions", []))
    except OSError as exc:
        raise PhaseError(f"could not read {PYPI_SIMPLE}: {exc}") from exc


def _patch(version: str) -> int:
    match = _FINAL_PATCH.match(version)
    return int(match.group(1)) if match else -1


def _uv_python(version: str) -> list[str]:
    """A ``uv run`` prefix whose Python runs the engine project with ``duckdb==version``."""
    return [
        "uv",
        "run",
        "--project",
        str(ENGINE),
        "--no-config",
        "--no-sync",
        "--with",
        f"duckdb=={version}",
        "python",
    ]


def _require_version(lines: list[str], version: str) -> None:
    if f"duckdb {version}" not in lines:
        raise PhaseError(f"the child did not report duckdb {version}")


def _reproduce_child(db: Path, *, fold: bool) -> int:
    """The patch repeat's child: print this DuckDB version, then the label."""
    import duckdb

    _say(f"duckdb {duckdb.__version__}")
    try:
        label = reproduce(db, threshold=None, fold=fold)
    except PhaseError as exc:
        print(f"shadow: FAILED: {exc}", file=sys.stderr, flush=True)
        return 1
    _say(f"label {label}")
    return 0


def _remove(working: Path) -> None:
    for path in (working, _wal_path(working)):
        path.unlink(missing_ok=True)


# --- the kill protocol -------------------------------------------------------------


def _kill_after_insert(db: Path) -> int:
    """Start the insert child, wait for its flushed count, then SIGKILL it."""
    proc = _spawn(_INSERT_CHILD, str(db))
    try:
        return read_count_line(proc.stdout, PROBE_SECONDS)
    finally:
        _stop(proc)


def _observe(db: Path, *, tag: str, timeout: float | None) -> list[Probe]:
    """Run the four statements in one child; return one probe per started statement.

    The parent kills the child once, when a statement is still running after
    ``timeout`` seconds, and records that statement as hung. Statements after
    it never started and are absent.
    """
    proc = _spawn(_PROBE_CHILD, str(db), tag)
    reader = _LineReader(proc.stdout)
    probes: list[Probe] = []
    try:
        line = reader.readline(timeout)
        if line is None:
            return [Probe("open", opened=False, hung=True, error=None)]
        if line != "open ok":
            error = line.removeprefix("open error ").strip() or "exited before open"
            return [Probe("open", opened=False, hung=False, error=error)]
        for name in STATEMENTS:
            line = reader.readline(timeout)
            if line is None:
                probes.append(Probe(name, opened=True, hung=True, error=None))
                break
            if line == "":
                error = f"the child exited with status {proc.wait()}"
                probes.append(Probe(name, opened=True, hung=False, error=error))
                break
            if line == f"{name} ok":
                probes.append(Probe(name, opened=True, hung=False, error=None))
            elif line.startswith(f"{name} error"):
                error = line.removeprefix(f"{name} error").strip() or "error"
                probes.append(Probe(name, opened=True, hung=False, error=error))
            else:
                raise PhaseError(f"unexpected probe line {line!r}")
        else:
            _finish(proc, timeout)
    finally:
        _stop(proc)
    return probes


def _repair(db: Path, flushed: int) -> None:
    """Drop, recreate, and checkpoint the index; then prove the four statements."""
    lines = _run_child(
        "repair",
        _REPAIR_CHILD,
        str(db),
        INDEX_SQL.read_text(encoding="utf-8"),
        timeout=None,
        required="checkpoint ok",
    )
    rows, index = _parse_counts(lines)
    if rows != flushed:
        raise PhaseError(f"repair: embeddings has {rows} rows; {flushed} were flushed")
    if index != rows:
        raise PhaseError(f"repair: the index holds {index} of {rows} rows")
    proof = _observe(db, tag="proof", timeout=None)
    for probe in proof:
        _say(f"  proof: {_describe(probe)}")
    if [probe.name for probe in proof] != list(STATEMENTS) or any(
        probe.hung or probe.error is not None for probe in proof
    ):
        raise PhaseError("repair: a statement after the repair did not finish cleanly")


def _parse_counts(lines: list[str]) -> tuple[int, int | None]:
    """Return ``(rows, index count)`` from a child's ``counts`` line."""
    for line in reversed(lines):
        if line.startswith("counts "):
            _, rows, index = line.split()
            return int(rows), None if index == "none" else int(index)
    raise PhaseError("the child printed no counts line")


def _describe(probe: Probe) -> str:
    if not probe.opened:
        return f"{probe.name} did not open ({probe.error or 'no answer'})"
    if probe.hung:
        return f"{probe.name} hung and was killed"
    if probe.error is not None:
        return f"{probe.name} raised {probe.error}"
    return f"{probe.name} ok"


# --- children ------------------------------------------------------------------------


class _LineReader:
    """Whole lines from a child's stdout pipe, read without Python's buffering."""

    def __init__(self, stream: IO[bytes]) -> None:
        self._fd = stream.fileno()
        self._buffer = b""

    def readline(self, timeout: float | None) -> str | None:
        """Return the next line, ``""`` at end of stream, or ``None`` at timeout."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while b"\n" not in self._buffer:
            remaining = None
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
            ready, _, _ = select.select([self._fd], [], [], remaining)
            if not ready:
                return None
            chunk = os.read(self._fd, 65536)
            if not chunk:
                line, self._buffer = self._buffer, b""
                return line.decode("utf-8", errors="replace")
            self._buffer += chunk
        line, _, self._buffer = self._buffer.partition(b"\n")
        return line.decode("utf-8", errors="replace")


def _spawn(code: str, *args: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-c", code, *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
    )


def _stop(proc: subprocess.Popen[bytes]) -> None:
    """SIGKILL ``proc`` if it is still running, and reap it."""
    if proc.poll() is None:
        proc.kill()
    proc.wait()


def _finish(proc: subprocess.Popen[bytes], timeout: float | None) -> None:
    """Let ``proc`` exit on its own within ``timeout`` before the caller stops it."""
    try:
        proc.wait(timeout)
    except subprocess.TimeoutExpired:
        _say("  the child did not exit after its last statement and was killed")


def _run_child(
    label: str,
    code: str,
    *args: str,
    timeout: float | None,
    required: str | None = None,
) -> list[str]:
    """Run a DuckDB child program of this interpreter; return its lines."""
    return _run_command(
        label, [sys.executable, "-c", code, *args], timeout=timeout, required=required
    )


def _run_command(
    label: str,
    command: list[str],
    *,
    timeout: float | None,
    env: dict[str, str] | None = None,
    merge_stderr: bool = False,
    required: str | None = None,
) -> list[str]:
    """Run ``command``, echo each line it prints, and return the lines.

    ``timeout`` bounds the wait for each line. Raises :class:`PhaseError` when
    a wait ends, when the command exits non-zero, or when no line starts with
    ``required``.
    """
    proc = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_stderr else None,
    )
    reader = _LineReader(proc.stdout)
    lines: list[str] = []
    try:
        while (line := reader.readline(timeout)) != "":
            if line is None:
                raise PhaseError(f"{label}: no output for {timeout:g} seconds")
            _say(f"  {label}: {line}")
            lines.append(line)
        status = proc.wait()
    finally:
        _stop(proc)
    if status != 0:
        raise PhaseError(f"{label}: exited with status {status}")
    if required is not None and not any(line.startswith(required) for line in lines):
        raise PhaseError(f"{label}: no line starts with {required!r}")
    return lines


# --- DuckDB in this process ---------------------------------------------------------


def _connect(db: Path, *, read_only: bool = False, **config: str) -> Any:
    """Connect to ``db`` with ``vss`` loaded and HNSW persistence enabled."""
    import duckdb

    con = duckdb.connect(str(db), read_only=read_only, config=config)
    try:
        con.execute("LOAD vss")
    except duckdb.Error:
        con.execute("INSTALL vss")
        con.execute("LOAD vss")
    con.execute("SET hnsw_enable_experimental_persistence = true")
    return con


def _storage_tag(con: Any) -> str | None:
    tags = con.execute(
        "SELECT tags FROM duckdb_databases() WHERE database_name = current_database()"
    ).fetchone()[0]
    return tags.get("storage_version")


def _literal(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _say(line: str) -> None:
    print(line, flush=True)


# --- the synthetic section -----------------------------------------------------------


def _synthetic(work: Path) -> None:
    """Print each measurement, then require ``loud`` and ``folded`` on small files."""
    work.mkdir()
    try:
        for measure in _MEASUREMENTS:
            try:
                for name, text in measure(work):
                    _say(f"measure {name}: {text}")
            except Exception as exc:  # a measurement reports; it does not gate
                _say(f"measure {measure.__name__}: error {type(exc).__name__}: {exc}")
        for fold, expected in ((False, "loud"), (True, "folded")):
            db = work / f"reproduce-{expected}.duckdb"
            _synthetic_warehouse(db, rows=200)
            label = reproduce(db, threshold=SYNTHETIC_THRESHOLD, fold=fold)
            if label != expected:
                raise PhaseError(f"synthetic: expected {expected}, got {label}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _synthetic_warehouse(db: Path, *, rows: int, storage: str = "v1.0.0") -> None:
    """Create a migrated warehouse at ``storage`` with ``rows`` random embeddings."""
    _engine_on_path()
    from stockroom.migrate import apply_pending

    con = _connect(db, storage_compatibility_version=storage)
    try:
        apply_pending(con)
        _insert_random_embeddings(con, rows)
        con.execute("CHECKPOINT")
    finally:
        con.close()


def _insert_random_embeddings(con: Any, rows: int, *, start: int = 0) -> None:
    con.execute(
        "INSERT INTO embeddings "
        "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
        "SELECT 'synthetic', 'messages', 'synthetic#' || range, 0, 'synthetic', "
        "list_transform(range(384), lambda x: random()::FLOAT)::FLOAT[384] "
        f"FROM range({int(start)}, {int(start) + int(rows)})"
    )


def _used_blocks(con: Any) -> int:
    return con.execute(
        "SELECT used_blocks FROM pragma_database_size() "
        "WHERE database_name = current_database()"
    ).fetchone()[0]


def _codecs(con: Any, table: str, column: str) -> list[str]:
    return sorted(
        row[0]
        for row in con.execute(
            f"SELECT DISTINCT compression FROM pragma_storage_info('{table}') "
            f"WHERE column_name = '{column}' AND segment_type = 'VARCHAR'"
        ).fetchall()
    )


def _index_count(con: Any) -> int | None:
    row = con.execute(
        f"SELECT count FROM pragma_hnsw_index_info() WHERE index_name = '{INDEX_NAME}'"
    ).fetchone()
    return row[0] if row else None


_Measurement = Iterator[tuple[str, str]]


def _measure_storage_tags(work: Path) -> _Measurement:
    import duckdb

    new = work / "tag-new.duckdb"
    con = duckdb.connect(str(new))
    con.execute("CREATE TABLE t (a INTEGER)")
    new_tag = _storage_tag(con)
    con.close()
    old = work / "tag-old.duckdb"
    con = duckdb.connect(str(old), config={"storage_compatibility_version": "v1.0.0"})
    con.execute("CREATE TABLE t (a INTEGER)")
    con.close()
    con = duckdb.connect(str(old))
    con.execute("INSERT INTO t VALUES (1)")
    con.execute("CHECKPOINT")
    con.close()
    con = duckdb.connect(str(old), config={"storage_compatibility_version": "latest"})
    con.execute("INSERT INTO t VALUES (2)")
    con.execute("CHECKPOINT")
    latest_tag = _storage_tag(con)
    try:
        duckdb.connect(
            str(old), config={"storage_compatibility_version": "v1.0.0"}
        ).close()
        second = "accepted"
    except duckdb.Error as exc:
        second = type(exc).__name__
    con.close()
    con = duckdb.connect(str(old), read_only=True)
    old_tag = _storage_tag(con)
    con.close()
    yield (
        "storage tag",
        f"new file {new_tag}; v1.0.0 file after a write without the setting and a "
        f"write with 'latest' {old_tag} (seen as {latest_tag} while open)",
    )
    yield (
        "second connection with another storage setting in one process",
        second,
    )


def _measure_zstd_after_add_column(work: Path) -> _Measurement:
    import duckdb

    con = duckdb.connect(str(work / "zstd-alter.duckdb"))
    con.execute("CREATE TABLE m (id INTEGER, text VARCHAR USING COMPRESSION zstd)")
    text = "'message ' || (range % 97) || repeat(' lorem ipsum dolor', 20)"
    con.execute(f"INSERT INTO m SELECT range, {text} FROM range(5000)")
    con.execute("ALTER TABLE m ADD COLUMN extra INTEGER")
    con.execute(f"INSERT INTO m SELECT range, {text}, range FROM range(5000, 10000)")
    con.execute("CHECKPOINT")
    yield (
        "zstd after ALTER TABLE ADD COLUMN",
        f"{_storage_tag(con)} file, text codecs {_codecs(con, 'm', 'text')}",
    )
    con.close()


def _measure_zstd_by_storage(work: Path) -> _Measurement:
    import duckdb

    for storage in ("v1.0.0", "v1.2.0"):
        con = duckdb.connect(
            str(work / f"zstd-{storage}.duckdb"),
            config={"storage_compatibility_version": storage},
        )
        try:
            con.execute("CREATE TABLE z (t VARCHAR USING COMPRESSION zstd)")
            con.execute(
                "INSERT INTO z SELECT 'row ' || range || repeat(' text', 30) "
                "FROM range(5000)"
            )
            con.execute("CHECKPOINT")
            result = f"accepted, codecs {_codecs(con, 'z', 't')}"
        except duckdb.Error as exc:
            result = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
        finally:
            con.close()
        yield (f"zstd clause on a {storage} file", result)


def _measure_delete_leak(work: Path) -> _Measurement:
    db = work / "leak.duckdb"
    _synthetic_warehouse(db, rows=1500)
    con = _connect(db)
    try:
        start = _used_blocks(con)
        con.execute("DELETE FROM embeddings WHERE owner_id = 'no-such-owner'")
        con.execute("CHECKPOINT")
        no_match = _used_blocks(con)
        con.execute(
            "DELETE FROM embeddings WHERE owner_id IN "
            "(SELECT owner_id FROM embeddings ORDER BY owner_id LIMIT 100)"
        )
        con.execute("CHECKPOINT")
        leaked = _used_blocks(con)
    finally:
        con.close()
    yield (
        "embedding delete with the index up",
        f"used blocks {start} at start, {no_match} after a no-match delete and "
        f"checkpoint, {leaked} after deleting 100 rows and checkpoint",
    )
    con = _connect(db, read_only=True)
    try:
        tables = _table_names(con, "current_database()")
        union = " UNION ALL ".join(
            f"SELECT block_id FROM pragma_storage_info('{table}') "
            "WHERE persistent AND block_id >= 0"
            for table in tables
        )
        distinct = con.execute(
            f"SELECT count(DISTINCT block_id) FROM ({union})"
        ).fetchone()[0]
        index_bytes = con.execute(
            "SELECT approx_memory_usage FROM pragma_hnsw_index_info()"
        ).fetchone()[0]
        size = con.execute(
            "SELECT block_size, used_blocks, free_blocks FROM pragma_database_size() "
            "WHERE database_name = current_database()"
        ).fetchone()
    finally:
        con.close()
    yield (
        "read-only facts after that delete",
        f"block size {size[0]}, used blocks {size[1]}, free blocks {size[2]}, "
        f"distinct data blocks {distinct}, HNSW approx_memory_usage {index_bytes} "
        f"bytes, file {db.stat().st_size} bytes",
    )


def _measure_drop_delete_create(work: Path) -> _Measurement:
    db = work / "cycle.duckdb"
    _synthetic_warehouse(db, rows=1500)
    con = _connect(db)
    try:
        used = [_used_blocks(con)]
        sizes = [db.stat().st_size]
        index_sql = INDEX_SQL.read_text(encoding="utf-8")
        for cycle in range(3):
            con.execute(f"DROP INDEX {INDEX_NAME}")
            con.execute(
                "DELETE FROM embeddings WHERE owner_id IN "
                "(SELECT owner_id FROM embeddings ORDER BY owner_id LIMIT 50)"
            )
            _insert_random_embeddings(con, 50, start=10_000 + cycle * 50)
            con.execute(index_sql)
            con.execute("CHECKPOINT")
            used.append(_used_blocks(con))
            sizes.append(db.stat().st_size)
    finally:
        con.close()
    yield (
        "drop, delete, insert, create, checkpoint cycles",
        f"used blocks {used}; file bytes {sizes}",
    )


def _measure_index_count(work: Path) -> _Measurement:
    db = work / "count.duckdb"
    _synthetic_warehouse(db, rows=300)
    con = _connect(db, read_only=True)
    try:
        rows = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        yield (
            "pragma_hnsw_index_info on a healthy index",
            f"count {_index_count(con)}, count(*) {rows}",
        )
    finally:
        con.close()


def _measure_plans(work: Path) -> _Measurement:
    db = work / "plans.duckdb"
    _synthetic_warehouse(db, rows=0)
    query = [1.0] + [0.0] * 383
    nearer = [1.0, 0.01] + [0.0] * 382
    farther = [1.0, 1.0] + [0.0] * 382
    insert = (
        "INSERT INTO embeddings "
        "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
        "VALUES (?, 'messages', ?, 0, 'fake', ?)"
    )
    con = _connect(db)
    try:
        con.execute(insert, ["claude", "in#0", farther])
        for ordinal in range(32):
            con.execute(insert, ["cursor", f"out#{ordinal}", nearer])
        distance = "array_cosine_distance(vector, ?::FLOAT[384])"
        unscoped = (
            f"SELECT owner_id, {distance} AS d FROM embeddings "
            "WHERE owner_table = 'messages' ORDER BY d LIMIT 100"
        )
        scoped = (
            f"SELECT owner_id, {distance} AS d FROM embeddings "
            "WHERE harness = 'claude' ORDER BY d LIMIT 5"
        )
        plans = {}
        for name, sql in (("unscoped", unscoped), ("scoped", scoped)):
            plan = "\n".join(
                row[1] for row in con.execute(f"EXPLAIN {sql}", [query]).fetchall()
            )
            plans[name] = [
                line.strip(" │|")
                for line in plan.splitlines()
                if "HNSW" in line or "Hnsw" in line
            ]
        returned = len(con.execute(scoped, [query]).fetchall())
    finally:
        con.close()
    yield ("unscoped plan", f"HNSW lines {plans['unscoped']}")
    yield (
        "scoped plan",
        f"WHERE harness = 'claude' ... LIMIT 5 behind 32 nearer rows returned "
        f"{returned} of 1 matching row; HNSW lines {plans['scoped']}",
    )


def _measure_copy_from_database(work: Path) -> _Measurement:
    import duckdb

    source = work / "copy-source.duckdb"
    _synthetic_warehouse(source, rows=200)
    con = _connect(source)
    try:
        con.execute(
            "INSERT INTO messages (harness, session_id, message_id, ordinal, role, text) "
            "SELECT 'synthetic', 's', 's#' || range, range, 'user', "
            "'message ' || (range % 97) || repeat(' lorem ipsum dolor', 20) "
            "FROM range(5000)"
        )
        con.execute("CHECKPOINT")
    finally:
        con.close()
    target = work / "copy-target.duckdb"
    con = duckdb.connect()
    try:
        con.execute("LOAD vss")
        con.execute("SET hnsw_enable_experimental_persistence = true")
        con.execute(f"ATTACH {_literal(source)} AS src (READ_ONLY)")
        con.execute(f"ATTACH {_literal(target)} AS dst")
        con.execute("COPY FROM DATABASE src TO dst")
        con.execute("CHECKPOINT dst")
        indexes = [
            row[0]
            for row in con.execute(
                "SELECT index_name FROM duckdb_indexes() WHERE database_name = 'dst'"
            ).fetchall()
        ]
        tags = con.execute(
            "SELECT tags FROM duckdb_databases() WHERE database_name = 'dst'"
        ).fetchone()[0]
        con.execute("USE dst")
        codecs = _codecs(con, "messages", "text")
    finally:
        con.close()
    yield (
        "COPY FROM DATABASE",
        f"into a new {tags.get('storage_version')} file: indexes {indexes}; "
        f"messages.text codecs {codecs}",
    )


def _measure_interrupt_index_build(work: Path) -> _Measurement:
    con = _connect(work / "interrupt.duckdb")
    try:
        con.execute(
            "CREATE TABLE e AS SELECT "
            "list_transform(range(384), lambda x: random()::FLOAT)::FLOAT[384] AS v "
            "FROM range(20000)"
        )
        started = time.monotonic()
        con.execute("CREATE INDEX i ON e USING HNSW (v)")
        build = time.monotonic() - started
        con.execute("DROP INDEX i")
        delay = min(0.5, build / 4)
        timer = threading.Timer(delay, con.interrupt)
        started = time.monotonic()
        timer.start()
        try:
            con.execute("CREATE INDEX i ON e USING HNSW (v)")
            outcome = "the build completed"
        except Exception as exc:
            outcome = type(exc).__name__
        returned = time.monotonic() - started
        timer.cancel()
    finally:
        con.close()
    yield (
        "interrupt during CREATE INDEX USING HNSW",
        f"build alone {build:.2f}s; interrupt at {delay:.2f}s; the call returned "
        f"after {returned:.2f}s with {outcome}",
    )


_MEASUREMENTS: tuple[Callable[[Path], _Measurement], ...] = (
    _measure_storage_tags,
    _measure_zstd_after_add_column,
    _measure_zstd_by_storage,
    _measure_delete_leak,
    _measure_drop_delete_create,
    _measure_index_count,
    _measure_plans,
    _measure_copy_from_database,
    _measure_interrupt_index_build,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="python scripts/shadow_duckdb_20.py",
        description=(
            "Shadow-test DuckDB 2.0 on a copy of a stockroom warehouse. Never "
            "opens the source with DuckDB."
        ),
    )
    parser.add_argument("--source", type=Path, help="The warehouse file to copy.")
    parser.add_argument(
        "--home",
        type=Path,
        help="A new empty scratch directory. Every write lands here.",
    )
    parser.add_argument(
        "--stop-after",
        choices=("copy", "checkpoint", "all"),
        default="all",
        help="Stop after this phase (default: all).",
    )
    parser.add_argument(
        "--min-free-bytes",
        type=int,
        default=None,
        help="Free bytes required under --home (default: twice the source plus 1 GiB).",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Run only the measurements and the small-file reproduction.",
    )
    parser.add_argument("--reproduce-child", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--fold", action="store_true", help=argparse.SUPPRESS)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
