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
2. Synthetic measurements: one line per DuckDB behaviour the later milestones
   state. A measurement reports; it does not gate. ``--synthetic`` runs only
   phases 1 and 2.
3. Copy under the writer flock, refusing a source with a ``.wal``.
4. Checkpoint the working copy with DuckDB 2.0 and compare every table with
   the baseline copy in both directions.
5. Ingest, ``embed --verbose``, a checkpoint, and semantic search on the
   working copy, then a DuckDB 1.5.4 writer and a 2.0 reader.

The script exits 0 only when every phase it ran passed. Stdlib at import:
DuckDB and the engine are imported inside the functions that use them, so the
guards run on any interpreter.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import re
import select
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE = REPO_ROOT / "skills" / "sr-search"
ENGINE_SRC = ENGINE / "src"

#: Seconds a DuckDB child may go without printing before the parent stops it.
PROBE_SECONDS = 180.0

#: Free space the copy needs beyond twice the source's size.
MARGIN_BYTES = 1 << 30

WAREHOUSE_NAME = "warehouse.duckdb"
BASELINE_NAME = "baseline.duckdb"
LOCK_NAME = ".warehouse.lock"
OLD_TAG = "v1.0.0+"
OLD_DUCKDB = "1.5.4"

_ORPHAN_LINE = re.compile(r"embed: removed (\d+) orphaned embedding rows")

#: Shared head of every DuckDB child program. A child prints each fact as one
#: flushed line, so the parent can read it while the child keeps running.
_CHILD_PRELUDE = r"""
import random
import sys

import duckdb

COSINE_SQL = (
    "SELECT harness, owner_id, array_cosine_distance(vector, ?::FLOAT[384]) "
    "AS distance FROM embeddings WHERE owner_table = 'messages' "
    "ORDER BY distance LIMIT 100"
)


def say(line):
    print(line, flush=True)


def connect(db, read_only=False):
    # No extension: stockroom loads none, and exact search needs none.
    return duckdb.connect(db, read_only=read_only)


def vector(seed):
    rng = random.Random(seed)
    return [rng.random() for _ in range(384)]
"""

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


def embeddings_held(after_ingest: int, after_embed: int, removed_orphans: int) -> bool:
    """True when embed kept every embedding row except the orphans it reported."""
    return after_embed >= after_ingest - removed_orphans


def main(argv: list[str] | None = None) -> int:
    """Run the guards and the phases named by ``--stop-after``; return the exit code."""
    args = _build_parser().parse_args(argv)
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


def _remove(working: Path) -> None:
    for path in (working, _wal_path(working)):
        path.unlink(missing_ok=True)


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


def _stop(proc: subprocess.Popen[bytes]) -> None:
    """SIGKILL ``proc`` if it is still running, and reap it."""
    if proc.poll() is None:
        proc.kill()
    proc.wait()


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
    """Connect to ``db`` with no extension loaded, as stockroom itself does."""
    import duckdb

    return duckdb.connect(str(db), read_only=read_only, config=config)


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
    """Print each measurement. A measurement reports; it does not gate."""
    work.mkdir()
    try:
        for measure in _MEASUREMENTS:
            try:
                for name, text in measure(work):
                    _say(f"measure {name}: {text}")
            except Exception as exc:  # a measurement reports; it does not gate
                _say(f"measure {measure.__name__}: error {type(exc).__name__}: {exc}")
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


def _codecs(con: Any, table: str, column: str) -> list[str]:
    return sorted(
        row[0]
        for row in con.execute(
            f"SELECT DISTINCT compression FROM pragma_storage_info('{table}') "
            f"WHERE column_name = '{column}' AND segment_type = 'VARCHAR'"
        ).fetchall()
    )


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
        con.execute(f"ATTACH {_literal(source)} AS src (READ_ONLY)")
        con.execute(f"ATTACH {_literal(target)} AS dst")
        con.execute("COPY FROM DATABASE src TO dst")
        con.execute("CHECKPOINT dst")
        tags = con.execute(
            "SELECT tags FROM duckdb_databases() WHERE database_name = 'dst'"
        ).fetchone()[0]
        con.execute("USE dst")
        codecs = _codecs(con, "messages", "text")
    finally:
        con.close()
    yield (
        "COPY FROM DATABASE",
        f"into a new {tags.get('storage_version')} file: messages.text codecs {codecs}",
    )


_MEASUREMENTS: tuple[Callable[[Path], _Measurement], ...] = (
    _measure_storage_tags,
    _measure_zstd_after_add_column,
    _measure_zstd_by_storage,
    _measure_copy_from_database,
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
        help="Run only the overlay check and the measurements.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
