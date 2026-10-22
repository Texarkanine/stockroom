"""Shadow-test script for the DuckDB 2.0 move: guards, checkpoint equality, kill protocol.

``scripts/shadow_duckdb_20.py`` is a contributor program at the repo root, not
part of the engine package. These tests run it as a subprocess with this
interpreter (the project's DuckDB, not a 2.0 overlay) and load its functions
with importlib from the anchored path. The DuckDB 2.0 replay bug is not
required here: the acceptance run of the script is the 2.0 proof.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import duckdb
import pytest

from stockroom import warehouse
from stockroom.migrate import apply_pending

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "shadow_duckdb_20.py"

_LABELS = {"loud", "folded", "blocked", "healthy"}
_STATEMENTS = ("cosine", "delete", "insert", "checkpoint")


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


def _child_env() -> dict[str, str]:
    """This environment without ``PYTHONUNBUFFERED``, so a bare print stays buffered."""
    return {
        key: value for key, value in os.environ.items() if key != "PYTHONUNBUFFERED"
    }


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


# --- classify ---------------------------------------------------------------


def _ok(shadow: ModuleType, name: str):
    return shadow.Probe(name, opened=True, hung=False, error=None)


def test_classify_unopened_or_lock_error_is_blocked(shadow: ModuleType) -> None:
    """A probe that did not open, or that reports a lock error, is ``blocked``."""
    probe = shadow.Probe
    unopened = probe("open", opened=False, hung=False, error="IO Error: disk")
    open_hung = probe("open", opened=False, hung=True, error=None)
    locked = probe(
        "cosine",
        opened=True,
        hung=False,
        error='IO Error: Could not set lock on file "warehouse.duckdb"',
    )

    assert shadow.classify(True, [unopened], None, None) == "blocked"
    assert shadow.classify(True, [open_hung], None, None) == "blocked"
    assert shadow.classify(False, [locked], 5, 5) == "blocked"


def test_classify_wal_with_hung_or_raised_probe_is_loud(shadow: ModuleType) -> None:
    """The ``.wal`` remains and an opened probe hung or raised: ``loud``."""
    hung = shadow.Probe("cosine", opened=True, hung=True, error=None)
    raised = shadow.Probe(
        "delete",
        opened=True,
        hung=False,
        error="INTERNAL Error: Operation requires a flat or constant vector",
    )

    assert shadow.classify(True, [hung], None, None) == "loud"
    assert shadow.classify(True, [_ok(shadow, "cosine"), raised], None, None) == "loud"


def test_classify_wal_gone_and_index_short_is_folded(shadow: ModuleType) -> None:
    """The ``.wal`` is gone and the index holds fewer rows than the table: ``folded``."""
    probes = [_ok(shadow, name) for name in _STATEMENTS]

    assert shadow.classify(False, probes, 9, 10) == "folded"


def test_classify_other_states_are_healthy(shadow: ModuleType) -> None:
    """Every other combination is ``healthy``, which no repair may follow."""
    probes = [_ok(shadow, name) for name in _STATEMENTS]
    hung = [shadow.Probe("cosine", opened=True, hung=True, error=None)]

    assert shadow.classify(False, probes, 10, 10) == "healthy"
    assert shadow.classify(True, probes, None, None) == "healthy"
    assert shadow.classify(False, hung, 10, 10) == "healthy"
    assert shadow.classify(False, probes, None, None) == "healthy"


# --- the count line -----------------------------------------------------------


def test_read_count_line_returns_flushed_integer(shadow: ModuleType) -> None:
    """A child that printed with ``flush=True`` and sleeps is read within 5 seconds."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; print(42, flush=True); time.sleep(60)"],
        stdout=subprocess.PIPE,
        env=_child_env(),
    )
    try:
        started = time.monotonic()
        assert shadow.read_count_line(proc.stdout, 5.0) == 42
        assert time.monotonic() - started < 5.0
    finally:
        proc.kill()
        proc.wait()


def test_read_count_line_fails_on_unflushed_print(shadow: ModuleType) -> None:
    """A child that printed without flushing and stays alive fails the 5-second read."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; print(42); time.sleep(60)"],
        stdout=subprocess.PIPE,
        env=_child_env(),
    )
    try:
        started = time.monotonic()
        with pytest.raises(shadow.PhaseError):
            shadow.read_count_line(proc.stdout, 5.0)
        elapsed = time.monotonic() - started
    finally:
        proc.kill()
        proc.wait()

    assert 5.0 <= elapsed < 15.0


# --- embeddings floor ---------------------------------------------------------


def test_embeddings_held_allows_only_reported_orphans(shadow: ModuleType) -> None:
    """After embed, the count is at least the after-ingest count minus the orphans."""
    assert shadow.embeddings_held(100, 100, 0)
    assert shadow.embeddings_held(100, 120, 0)
    assert shadow.embeddings_held(100, 95, 5)
    assert not shadow.embeddings_held(100, 94, 5)
    assert not shadow.embeddings_held(100, 99, 0)


# --- newest patch ---------------------------------------------------------------


def test_newest_final_patch_ignores_prereleases(shadow: ModuleType) -> None:
    """Only final ``2.0.N`` uploads count, compared by patch number.

    ``2.0.0.dev*`` sorts after ``2.0.0`` as a string and is not a newer patch.
    """
    uploads = ["1.5.4", "2.0.0", "2.0.0.dev12", "2.0.1rc1", "2.0.2a1", "2.0.3b2"]

    assert shadow.newest_final_patch([*uploads, "2.1.0"]) == "2.0.0"
    assert shadow.newest_final_patch(["2.0.0", "2.0.9", "2.0.10", "2.0.11.dev3"]) == (
        "2.0.10"
    )
    assert shadow.newest_final_patch(["1.5.4", "2.1.0"]) is None


# --- reproduce ------------------------------------------------------------------


def test_reproduce_on_tiny_file_returns_a_label(
    shadow: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One kill protocol on a tiny HNSW warehouse returns one of the four labels.

    DuckDB 1.5.4 replays the log without the bug, so ``healthy`` is a valid
    result here. The kill child's count line is awaited for the probe budget,
    not the 5-second deadline of the unit tests above.
    """
    db = tmp_path / "warehouse.duckdb"
    con = duckdb.connect(str(db), config={"storage_compatibility_version": "v1.0.0"})
    try:
        warehouse.ensure_vss(con)
        apply_pending(con)
        con.execute(
            "INSERT INTO embeddings "
            "(harness, owner_table, owner_id, chunk_index, embed_model, vector) "
            "SELECT 'tiny', 'messages', 'tiny#' || range, 0, 'tiny', "
            "list_transform(range(384), lambda x: random()::FLOAT)::FLOAT[384] "
            "FROM range(50)"
        )
        con.execute("CHECKPOINT")
    finally:
        con.close()
    deadlines: list[float] = []
    real_read = shadow.read_count_line

    def spy(stream, deadline: float) -> int:
        deadlines.append(deadline)
        return real_read(stream, deadline)

    monkeypatch.setattr(shadow, "read_count_line", spy)

    label = shadow.reproduce(db, threshold=4096, fold=False)

    assert label in _LABELS
    assert deadlines
    assert min(deadlines) >= 180.0
