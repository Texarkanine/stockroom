"""Shadow-test script for the DuckDB 2.0 move: guards and checkpoint equality.

``scripts/shadow_duckdb_20.py`` is a contributor program at the repo root, not
part of the engine package. These tests run it as a subprocess with this
interpreter (the project's DuckDB, not a 2.0 overlay) and load its functions
with importlib from the anchored path. The acceptance run of the script is the
2.0 proof.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import duckdb
import pytest

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
