"""Shadow-test script for the DuckDB 2.0 move: guards, checkpoint equality, checks.

The checks are the ones the live phase runs on the working copy and on the
stockroom commands' output.

``scripts/shadow_duckdb_20.py`` is a contributor program at the repo root, not
part of the engine package. These tests run it as a subprocess with this
interpreter (the project's DuckDB, not a 2.0 overlay) and load its functions
with importlib from the anchored path. The acceptance run of the script is the
2.0 proof.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import duckdb
import pytest

from stockroom.migrations import discover

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "shadow_duckdb_20.py"


@pytest.fixture(scope="module")
def shadow() -> ModuleType:
    """Load ``scripts/shadow_duckdb_20.py`` as a module."""
    spec = importlib.util.spec_from_file_location("shadow_duckdb_20", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(*args: object) -> subprocess.CompletedProcess[str]:
    """Run the script with this interpreter and capture its output."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _tiny_warehouse(path: Path) -> Path:
    """Create a ``v1.0.0`` DuckDB file with one small table at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path), config={"storage_compatibility_version": "v1.0.0"})
    try:
        con.execute("CREATE TABLE t (id INTEGER, label TEXT)")
        con.execute("INSERT INTO t SELECT range, 'row ' || range FROM range(100)")
    finally:
        con.close()
    return path


def _home_is_empty(home: Path) -> bool:
    return not home.exists() or not any(home.iterdir())


# --- guards and the checkpoint proof (subprocess) ---------------------------


def test_wal_sibling_refuses_and_leaves_home_without_copy(tmp_path: Path) -> None:
    """A ``.wal`` beside the source refuses the copy and leaves ``--home`` empty."""
    source = _tiny_warehouse(tmp_path / "src" / "warehouse.duckdb")
    Path(f"{source}.wal").write_bytes(b"wal")
    home = tmp_path / "home"

    result = _run("--source", source, "--home", home, "--stop-after", "copy")

    assert result.returncode != 0
    assert ".wal" in result.stderr
    assert _home_is_empty(home)


def test_home_in_source_directory_refuses_and_changes_nothing(tmp_path: Path) -> None:
    """``--home`` equal to the source's directory refuses before writing anything.

    The source bytes and the directory's entry names stay as they were, so the
    guard runs before the writer lock file could be created there.
    """
    source = _tiny_warehouse(tmp_path / "src" / "warehouse.duckdb")
    before = source.read_bytes()
    names = sorted(entry.name for entry in source.parent.iterdir())

    result = _run("--source", source, "--home", source.parent, "--stop-after", "copy")

    assert result.returncode != 0
    assert "--home" in result.stderr
    assert source.read_bytes() == before
    assert sorted(entry.name for entry in source.parent.iterdir()) == names


def test_disk_guard_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """A free-space bar above the free space refuses and makes no copy."""
    source = _tiny_warehouse(tmp_path / "src" / "warehouse.duckdb")
    home = tmp_path / "home"

    result = _run(
        "--source",
        source,
        "--home",
        home,
        "--min-free-bytes",
        10**18,
        "--stop-after",
        "copy",
    )

    assert result.returncode != 0
    assert "free" in result.stderr
    assert _home_is_empty(home)


def test_checkpoint_stop_matches_baseline_and_leaves_source(tmp_path: Path) -> None:
    """``--stop-after checkpoint`` keeps the source and proves the copy unchanged.

    The source bytes do not change and no ``.wal`` appears beside it. The
    checkpointed working copy equals the baseline copy in both directions.
    """
    source = _tiny_warehouse(tmp_path / "src" / "warehouse.duckdb")
    before = source.read_bytes()
    home = tmp_path / "home"

    result = _run("--source", source, "--home", home, "--stop-after", "checkpoint")

    assert result.returncode == 0, result.stdout + result.stderr
    assert source.read_bytes() == before
    assert not Path(f"{source}.wal").exists()
    con = duckdb.connect(str(home / "warehouse.duckdb"), read_only=True)
    try:
        con.execute(f"ATTACH '{home / 'baseline.duckdb'}' AS baseline (READ_ONLY)")
        for left, right in (("t", "baseline.t"), ("baseline.t", "t")):
            extra = con.execute(
                f"SELECT count(*) FROM (SELECT * FROM {left} EXCEPT ALL "
                f"SELECT * FROM {right})"
            ).fetchone()[0]
            assert extra == 0
        assert con.execute("SELECT count(*) FROM t").fetchone()[0] == 100
    finally:
        con.close()


def test_missing_source_exits_nonzero(tmp_path: Path) -> None:
    """A ``--source`` that is not a file is refused."""
    result = _run(
        "--source",
        tmp_path / "missing.duckdb",
        "--home",
        tmp_path / "home",
        "--stop-after",
        "copy",
    )

    assert result.returncode != 0
    assert "not a file" in result.stderr


# --- embeddings floor ---------------------------------------------------------


def test_embeddings_held_allows_only_reported_orphans(shadow: ModuleType) -> None:
    """After embed, the count is at least the after-ingest count minus the orphans."""
    assert shadow.embeddings_held(100, 100, 0)
    assert shadow.embeddings_held(100, 120, 0)
    assert shadow.embeddings_held(100, 95, 5)
    assert not shadow.embeddings_held(100, 94, 5)
    assert not shadow.embeddings_held(100, 99, 0)


# --- the synthetic warehouse --------------------------------------------------


def test_synthetic_warehouse_builds_the_released_chain_in_a_child(
    shadow: ModuleType, tmp_path: Path
) -> None:
    """H1: ``_synthetic_warehouse`` gives a ``v1.0.0+`` head file with its rows.

    The released ``0003`` needs ``vss``, so the chain runs in a child process
    that loads it; this process only inserts the embeddings afterwards. The
    file is at the head with no index and 5 embeddings, and a connection to
    it here has no ``vss``.
    """
    db = tmp_path / "synthetic.duckdb"

    shadow._synthetic_warehouse(db, rows=5)

    con = duckdb.connect(str(db), read_only=True)
    try:
        tag = con.execute(
            "SELECT tags FROM duckdb_databases() "
            "WHERE database_name = current_database()"
        ).fetchone()[0]["storage_version"]
        version = con.execute("SELECT max(version) FROM schema_version").fetchone()[0]
        indexes = con.execute(
            "SELECT index_name FROM duckdb_indexes() WHERE NOT is_primary"
        ).fetchall()
        embeddings = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        loaded = con.execute(
            "SELECT loaded FROM duckdb_extensions() WHERE extension_name = 'vss'"
        ).fetchone()[0]
    finally:
        con.close()

    assert tag == "v1.0.0+"
    assert version == _head()
    assert indexes == []
    assert embeddings == 5
    assert loaded is False


# --- the copy after the live phase ---------------------------------------------


def _head_warehouse(released_chain_file, path: Path, storage: str = "v1.0.0") -> Path:
    """Put a warehouse at ``storage``, at the schema head, at ``path``.

    It is the released chain, built in a child that loads ``vss``
    (``released_chain_file``), since the released ``0003`` needs it.
    """
    return released_chain_file(_head(), storage=storage, dest=path)


def _execute(db: Path, sql: str) -> None:
    """Run one statement on ``db`` read-write and close it."""
    con = duckdb.connect(str(db))
    try:
        con.execute(sql)
    finally:
        con.close()


def _head() -> int:
    return max(migration.version for migration in discover())


def test_check_live_copy_passes_old_tag_at_head_without_index(
    shadow: ModuleType, tmp_path: Path, released_chain_file
) -> None:
    """A ``v1.0.0`` file at the schema head with no extra index passes.

    ``check_live_copy`` returns the storage tag it read.
    """
    db = _head_warehouse(released_chain_file, tmp_path / "warehouse.duckdb")

    assert shadow.check_live_copy(db) == "v1.0.0+"


def test_check_live_copy_names_an_extra_index(
    shadow: ModuleType, tmp_path: Path, released_chain_file
) -> None:
    """A non-primary index on the copy fails the check, which names the index."""
    db = _head_warehouse(released_chain_file, tmp_path / "warehouse.duckdb")
    _execute(db, "CREATE INDEX extra ON sessions (session_id)")

    with pytest.raises(shadow.PhaseError, match="extra"):
        shadow.check_live_copy(db)


def test_check_live_copy_names_a_schema_behind_head(
    shadow: ModuleType, tmp_path: Path, released_chain_file
) -> None:
    """A copy whose newest ``schema_version`` row is below the head fails.

    The message names the version found and the head.
    """
    head = _head()
    db = _head_warehouse(released_chain_file, tmp_path / "warehouse.duckdb")
    _execute(db, f"DELETE FROM schema_version WHERE version = {head}")

    with pytest.raises(shadow.PhaseError) as excinfo:
        shadow.check_live_copy(db)

    message = str(excinfo.value)
    assert re.search(rf"\b{head - 1}\b", message), message
    assert re.search(rf"\b{head}\b", message), message


def test_check_live_copy_names_a_new_storage_tag(
    shadow: ModuleType, tmp_path: Path, released_chain_file
) -> None:
    """A copy whose storage tag moved off ``v1.0.0+`` fails, naming both tags.

    DuckDB before 2.0 opens only the old tag, so a moved tag would lock the
    machine's older stockroom copies out of the warehouse.
    """
    db = _head_warehouse(
        released_chain_file, tmp_path / "warehouse.duckdb", storage="v1.2.0"
    )

    with pytest.raises(shadow.PhaseError, match=r"v1\.2\.0\+") as excinfo:
        shadow.check_live_copy(db)

    assert "v1.0.0+" in str(excinfo.value)


# --- reading the commands' output -------------------------------------------------

_SEMANTIC_HEADER = "rank\tscore\tharness\tsession_id\tmessage_id\trole\tpreview"


def test_semantic_answered_needs_a_rank_one_row(shadow: ModuleType) -> None:
    """Only a line that starts with rank 1 and a tab counts as an answer.

    No lines, or the TSV header alone, is no answer. A line that merely holds
    ``1<TAB>`` later on (such as a log line) is not a rank-1 row.
    """
    row = "1\t0.91\tclaude\ts1\ts1#0\tuser\thow does the warehouse lock work"

    assert not shadow.semantic_answered([])
    assert not shadow.semantic_answered([_SEMANTIC_HEADER])
    assert shadow.semantic_answered([_SEMANTIC_HEADER, row])
    assert not shadow.semantic_answered(
        [_SEMANTIC_HEADER, "Batches: 100%|##########| 1/1\t1\tdone"]
    )


def test_nanobind_lines_returns_only_nanobind_lines(shadow: ModuleType) -> None:
    """``nanobind_lines`` returns exactly the lines that start ``nanobind:``."""
    leaks = [
        "embedded 3 chunk vectors",
        "nanobind: leaked 27 instances!",
        "nanobind: leaked 6 types!",
        ' - leaked type "_duckdb.DuckDBPyConnection"',
        "nanobind: this is likely caused by a reference counting issue",
        "See https://nanobind.readthedocs.io/en/latest/refleaks.html",
    ]

    assert shadow.nanobind_lines(leaks) == [leaks[1], leaks[2], leaks[4]]
    assert shadow.nanobind_lines(["embedded 3 chunk vectors"]) == []
    assert shadow.nanobind_lines([]) == []
