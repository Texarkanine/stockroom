"""The check pass: the record, the phase choice, and the swap.

One behavior per test. ``now`` is supplied by the test. Homes are
``tmp_path`` or a fixture copy, never the live warehouse.
"""

import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import stockroom

import duckdb
import pytest

from _warehouse_worker import EARLY_ID, LATE_ID
from conftest import FakeEncoder
from stockroom import check, doctor, embed, migrate, semantic, storage, warehouse
from stockroom.ingest.__main__ import main as ingest_main


def test_no_record_chooses_phase_a() -> None:
    """No record chooses phase A."""
    assert check.next_action(None, now=0.0) == "phase-a"


def test_young_rehearsal_waits() -> None:
    """A rehearsed record younger than one day waits."""
    record = {
        "check_version": 1,
        "status": "rehearsed",
        "rehearsed_at": 1_000.0,
    }
    assert check.next_action(record, now=1_000.0 + 86_399) == "wait"


def test_day_old_rehearsal_chooses_phase_b() -> None:
    """A rehearsed record at least one day old chooses phase B."""
    record = {
        "check_version": 1,
        "status": "rehearsed",
        "rehearsed_at": 1_000.0,
    }
    assert check.next_action(record, now=1_000.0 + 86_400) == "phase-b"


def test_other_check_version_chooses_phase_a() -> None:
    """A record whose check version is not 1 chooses phase A."""
    record = {"check_version": 2, "status": "swapped"}
    assert check.next_action(record, now=10**9) == "phase-a"


def test_swapped_stops() -> None:
    """A swapped record of this check version stops."""
    record = {"check_version": 1, "status": "swapped"}
    assert check.next_action(record, now=0.0) == "stop"


def test_mismatch_stops() -> None:
    """A mismatch record of this check version stops."""
    record = {"check_version": 1, "status": "mismatch"}
    assert check.next_action(record, now=0.0) == "stop"


def test_already_new_stops() -> None:
    """An already-new record of this check version stops."""
    record = {"check_version": 1, "status": "already-new"}
    assert check.next_action(record, now=0.0) == "stop"


def test_started_inside_the_limit_is_running() -> None:
    """A started entry still inside its limit does not build."""
    record = {
        "check_version": 1,
        "status": "started",
        "started_at": 100.0,
        "limit_seconds": 14_400,
    }
    assert check.next_action(record, now=100.0 + 14_399) == "running"


def test_started_at_the_limit_stops() -> None:
    """A started entry at or past its limit stops and does not build."""
    record = {
        "check_version": 1,
        "status": "started",
        "started_at": 100.0,
        "limit_seconds": 14_400,
    }
    assert check.next_action(record, now=100.0 + 14_400) == "stop"


def test_skip_chooses_phase_a() -> None:
    """A stored skip chooses phase A so the readiness ladder can run again."""
    record = {"check_version": 1, "status": "skip", "skip_reason": "wal"}
    assert check.next_action(record, now=0.0) == "phase-a"


def test_linked_finishes_the_swap() -> None:
    """A linked record finishes the swap and does not copy again."""
    record = {"check_version": 1, "status": "linked"}
    assert check.next_action(record, now=0.0) == "finish-swap"


def test_record_round_trip(tmp_path: Path) -> None:
    """A missing file is no record. A written record reads back from check.json."""
    assert check.load_record(tmp_path) is None
    record = {
        "check_version": 1,
        "status": "rehearsed",
        "phase": "A",
        "started_at": 10.5,
        "limit_seconds": 14_400,
        "rehearsed_at": 20.5,
        "original_bytes": 100,
        "copy_bytes": 40,
        "disk_free": 1_000,
        "build_seconds": 1.5,
        "verify_seconds": 0.25,
        "lock_seconds": 2.0,
        "skip_reason": None,
    }
    check.write_record(tmp_path, record)
    assert (tmp_path / "check.json").is_file()
    assert check.load_record(tmp_path) == record


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _spy_copy(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Replace ``stockroom.storage.copy_warehouse`` and record its paths."""
    calls: list[Path] = []

    def spy(original: Path) -> storage.CopyResult:
        calls.append(original)
        return storage.CopyResult(
            path=original.with_name(storage.COPY_FILENAME),
            original_bytes=original.stat().st_size,
            copy_bytes=1,
            build_seconds=0.0,
            verify_seconds=0.0,
        )

    monkeypatch.setattr("stockroom.storage.copy_warehouse", spy)
    return calls


def test_missing_home_creates_nothing(tmp_path: Path) -> None:
    """A missing home is not created."""
    home = tmp_path / "missing"
    check.run_check(home, now=lambda: 0.0)
    assert not home.exists()


def test_missing_warehouse_skips(tmp_path: Path) -> None:
    """A home with no warehouse records skip / no-warehouse and no sibling."""
    check.run_check(tmp_path, now=lambda: 0.0)
    record = check.load_record(tmp_path)
    assert record["status"] == "skip"
    assert record["skip_reason"] == "no-warehouse"
    assert not (tmp_path / storage.COPY_FILENAME).exists()


def test_wal_skips_and_leaves_the_original(generations_file: Path) -> None:
    """A wal records skip / wal. The original bytes stay, and no sibling is built."""
    home = generations_file.parent
    wal = generations_file.with_name(generations_file.name + ".wal")
    wal.write_bytes(b"leftover")
    before = _sha256(generations_file)
    check.run_check(home, now=lambda: 0.0)
    record = check.load_record(home)
    assert record["status"] == "skip"
    assert record["skip_reason"] == "wal"
    assert _sha256(generations_file) == before
    assert not (home / storage.COPY_FILENAME).exists()


def test_wal_removed_then_copy_runs(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a wal skip, removing the wal lets the next pass call copy_warehouse."""
    home = generations_file.parent
    wal = generations_file.with_name(generations_file.name + ".wal")
    wal.write_bytes(b"leftover")
    check.run_check(home, now=lambda: 0.0)
    assert check.load_record(home)["skip_reason"] == "wal"
    wal.unlink()
    calls = _spy_copy(monkeypatch)
    check.run_check(home, now=lambda: 1.0)
    assert calls == [generations_file]


def test_read_only_filesystem_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``ST_RDONLY`` records skip / read-only and does not change the original."""
    original = tmp_path / warehouse.WAREHOUSE_FILENAME
    original.write_bytes(b"original-bytes")
    before = _sha256(original)

    class _vfs:
        f_flag = os.ST_RDONLY

    monkeypatch.setattr(os, "statvfs", lambda _path: _vfs())
    check.run_check(tmp_path, now=lambda: 0.0)
    record = check.load_record(tmp_path)
    assert record["status"] == "skip"
    assert record["skip_reason"] == "read-only"
    assert _sha256(original) == before
    assert not (tmp_path / storage.COPY_FILENAME).exists()


def test_schema_below_boundary_skips(tmp_path: Path, released_chain_file) -> None:
    """Schema 8 records skip / below-boundary and does not change the original."""
    home = tmp_path / "home"
    home.mkdir()
    original = released_chain_file(8, dest=home / warehouse.WAREHOUSE_FILENAME)
    before = _sha256(original)
    check.run_check(home, now=lambda: 0.0)
    record = check.load_record(home)
    assert record["status"] == "skip"
    assert record["skip_reason"] == "below-boundary"
    assert _sha256(original) == before
    assert not (home / storage.COPY_FILENAME).exists()


def _schema_file_home(home: Path, *, text: str | None) -> Path:
    """Build a schema-file warehouse and optionally insert one zstd text row."""
    dest = home / warehouse.WAREHOUSE_FILENAME
    storage.build_warehouse(dest)
    if text is None:
        return dest
    con = duckdb.connect(str(dest))
    try:
        con.execute(
            "INSERT INTO messages "
            "(harness, session_id, message_id, ordinal, role, text) "
            "VALUES ('claude', 's', 'm', 0, 'user', ?)",
            [text],
        )
        con.execute("CHECKPOINT")
    finally:
        con.close()
    return dest


def test_zstd_text_row_is_already_new(tmp_path: Path) -> None:
    """A schema-file warehouse with one zstd text row is already new."""
    _schema_file_home(tmp_path, text="hello")
    check.run_check(tmp_path, now=lambda: 0.0)
    record = check.load_record(tmp_path)
    assert record["status"] == "already-new"
    assert not (tmp_path / storage.COPY_FILENAME).exists()


def test_empty_schema_file_is_already_new(tmp_path: Path) -> None:
    """A schema-file warehouse with no rows is already new."""
    _schema_file_home(tmp_path, text=None)
    check.run_check(tmp_path, now=lambda: 0.0)
    record = check.load_record(tmp_path)
    assert record["status"] == "already-new"
    assert not (tmp_path / storage.COPY_FILENAME).exists()


def _strip_one_zstd_clause(sql: str, column: str) -> str:
    """Remove ``USING COMPRESSION zstd`` from the one column named ``column``."""
    kept: list[str] = []
    removed = 0
    for line in sql.splitlines(keepends=True):
        if column in line and "USING COMPRESSION zstd" in line:
            line = line.replace(" USING COMPRESSION zstd", "", 1)
            removed += 1
        kept.append(line)
    if removed != 1:
        raise AssertionError(f"removed zstd from {removed} lines for {column}")
    return "".join(kept)


def _warehouse_missing_one_zstd(home: Path, column: str) -> Path:
    """Build a ``v2.0.0`` schema-9 file whose one large column is not zstd."""
    sql = _strip_one_zstd_clause(
        storage.SCHEMA_FILE.read_text(encoding="utf-8"), column
    )
    dest = home / warehouse.WAREHOUSE_FILENAME
    con = duckdb.connect(
        str(dest), config={"storage_compatibility_version": storage.STORAGE_VERSION}
    )
    try:
        migrate.ensure_schema_version_table(con)
        con.execute(sql)
        con.execute(
            f"INSERT INTO {migrate.SCHEMA_VERSION_TABLE} (version, filename) "
            "VALUES (9, 'schema_0009.sql')"
        )
        if column == "text":
            con.execute(
                "INSERT INTO messages "
                "(harness, session_id, message_id, ordinal, role, text) "
                "VALUES ('claude', 's', 'm', 0, 'user', 'hello')"
            )
        else:
            con.execute(
                "INSERT INTO tool_calls "
                "(harness, session_id, message_id, ordinal, tool_name, tool_input) "
                "VALUES ('claude', 's', 'm', 0, 'Read', ?)",
                ['{"path": "/tmp/a.txt"}'],
            )
        con.execute("CHECKPOINT")
    finally:
        con.close()
    return dest


def test_non_zstd_text_is_not_already_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A persistent non-zstd messages.text segment is copied, not already new."""
    original = _warehouse_missing_one_zstd(tmp_path, "text")
    calls = _spy_copy(monkeypatch)
    check.run_check(tmp_path, now=lambda: 0.0)
    record = check.load_record(tmp_path)
    assert calls == [original]
    assert record is None or record["status"] != "already-new"


def test_non_zstd_tool_input_is_not_already_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A persistent non-zstd tool_calls.tool_input segment is copied."""
    original = _warehouse_missing_one_zstd(tmp_path, "tool_input")
    calls = _spy_copy(monkeypatch)
    check.run_check(tmp_path, now=lambda: 0.0)
    record = check.load_record(tmp_path)
    assert calls == [original]
    assert record is None or record["status"] != "already-new"


def _live_margin(path: Path) -> int:
    con = duckdb.connect(str(path), read_only=True)
    try:
        live = doctor.live_bytes(con)
    finally:
        con.close()
    return 2 * live + 64 * 1024 * 1024


def test_low_disk_skips(generations_file: Path) -> None:
    """Free disk below twice the live bytes plus 64 MiB records skip / low-disk."""
    home = generations_file.parent
    before = _sha256(generations_file)
    threshold = _live_margin(generations_file)
    check.run_check(home, now=lambda: 0.0, disk_free=lambda _path: threshold - 1)
    record = check.load_record(home)
    assert record["status"] == "skip"
    assert record["skip_reason"] == "low-disk"
    assert _sha256(generations_file) == before
    assert not (home / storage.COPY_FILENAME).exists()


def test_disk_at_the_threshold_is_not_low_disk(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Free disk equal to the threshold does not record a low-disk skip."""
    home = generations_file.parent
    threshold = _live_margin(generations_file)
    calls = _spy_copy(monkeypatch)
    check.run_check(home, now=lambda: 0.0, disk_free=lambda _path: threshold)
    record = check.load_record(home)
    assert calls == [generations_file]
    assert record is None or record.get("skip_reason") != "low-disk"


def test_busy_flock_writes_and_deletes_nothing(tmp_path: Path) -> None:
    """A held writer flock leaves the record and the sibling untouched."""
    original = tmp_path / warehouse.WAREHOUSE_FILENAME
    original.write_bytes(b"original-bytes")
    sibling = tmp_path / storage.COPY_FILENAME
    sibling.write_bytes(b"sibling-bytes")
    check.write_record(tmp_path, {"check_version": 1, "status": "rehearsed"})
    record_path = tmp_path / check.CHECK_RECORD_FILENAME
    before_record = record_path.read_bytes()
    before_sibling = sibling.read_bytes()
    with warehouse._flock(tmp_path / warehouse.LOCK_FILENAME):
        check.run_check(tmp_path, now=lambda: 0.0)
    assert record_path.read_bytes() == before_record
    assert sibling.read_bytes() == before_sibling
    assert sibling.exists()


_MEASUREMENTS = (
    "original_bytes",
    "copy_bytes",
    "disk_free",
    "build_seconds",
    "verify_seconds",
    "lock_seconds",
)


def test_phase_a_records_a_rehearsal(generations_file: Path) -> None:
    """Phase A records rehearsed, deletes the sibling, and leaves the original."""
    home = generations_file.parent
    before = _sha256(generations_file)
    check.run_check(home, now=lambda: 5_000.0)
    record = check.load_record(home)
    assert record["status"] == "rehearsed"
    assert record["rehearsed_at"] == 5_000.0
    assert record["original_bytes"] == generations_file.stat().st_size
    for name in _MEASUREMENTS:
        assert isinstance(record[name], int | float)
    assert not (home / storage.COPY_FILENAME).exists()
    assert not (home / f"{storage.COPY_FILENAME}.wal").exists()
    assert _sha256(generations_file) == before


def test_second_pass_inside_one_day_does_not_copy(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One second after a rehearsal, the next pass does not copy again."""
    home = generations_file.parent
    before = _sha256(generations_file)
    check.run_check(home, now=lambda: 5_000.0)
    calls = _spy_copy(monkeypatch)
    check.run_check(home, now=lambda: 5_001.0)
    assert calls == []
    record = check.load_record(home)
    assert record["status"] == "rehearsed"
    assert _sha256(generations_file) == before


def _rehearse(generations_file: Path) -> dict:
    """Run phase A at t=1000 and return the rehearsed record."""
    check.run_check(generations_file.parent, now=lambda: 1_000.0)
    record = check.load_record(generations_file.parent)
    assert record["status"] == "rehearsed"
    return record


def _day_later(record: dict):
    """A clock one day after ``record`` was rehearsed."""
    return lambda: record["rehearsed_at"] + 86_400


def _message_ids(path: Path) -> set[str]:
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute("SELECT message_id FROM messages").fetchall()
        tags = con.execute(
            "SELECT tags FROM duckdb_databases() "
            "WHERE database_name = current_database()"
        ).fetchone()[0]
        assert tags["storage_version"] == "v2.0.0+"
    finally:
        con.close()
    return {row[0] for row in rows}


def _fail_warehouse_replace(
    monkeypatch: pytest.MonkeyPatch, *, after_real: bool
) -> None:
    """Raise from ``os.replace`` only when the destination is the warehouse.

    Record writes also use ``os.replace``. Those keep the real function.
    """
    real = os.replace

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name != warehouse.WAREHOUSE_FILENAME:
            return real(src, dst, *args, **kwargs)
        if after_real:
            real(src, dst, *args, **kwargs)
        raise OSError("warehouse replace failed")

    monkeypatch.setattr(os, "replace", replace)


def test_phase_b_swaps_in_a_new_copy(generations_file: Path) -> None:
    """A day after rehearsal, phase B links the original and swaps the new copy."""
    home = generations_file.parent
    rehearsed = _rehearse(generations_file)
    before = _sha256(generations_file)
    before_inode = generations_file.stat().st_ino
    check.run_check(home, now=_day_later(rehearsed))
    backup = home / doctor.SWAP_BACKUP_FILENAME
    record = check.load_record(home)
    assert _sha256(backup) == before
    assert backup.stat().st_ino == before_inode
    assert _message_ids(generations_file) == {EARLY_ID, LATE_ID}
    assert not (home / storage.COPY_FILENAME).exists()
    assert record["status"] == "swapped"
    assert record["original_bytes"] == rehearsed["original_bytes"]


def test_phase_b_does_not_swap_a_marker_sibling(generations_file: Path) -> None:
    """A sibling planted after rehearsal is not the file that becomes the warehouse."""
    home = generations_file.parent
    rehearsed = _rehearse(generations_file)
    marker = b"not a database"
    (home / storage.COPY_FILENAME).write_bytes(marker)
    check.run_check(home, now=_day_later(rehearsed))
    assert generations_file.read_bytes() != marker
    assert _message_ids(generations_file) == {EARLY_ID, LATE_ID}


def test_failed_replace_resumes_from_linked(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replace that raises leaves linked, and the next pass swaps that sibling."""
    home = generations_file.parent
    rehearsed = _rehearse(generations_file)
    before = generations_file.read_bytes()
    before_inode = generations_file.stat().st_ino
    _fail_warehouse_replace(monkeypatch, after_real=False)
    check.run_check(home, now=_day_later(rehearsed))
    backup = home / doctor.SWAP_BACKUP_FILENAME
    sibling = home / storage.COPY_FILENAME
    record = check.load_record(home)
    assert record["status"] == "linked"
    assert generations_file.read_bytes() == before
    assert backup.stat().st_ino == before_inode
    assert sibling.is_file()
    monkeypatch.undo()
    calls = _spy_copy(monkeypatch)
    links: list[tuple] = []
    real_link = os.link

    def link(*args, **kwargs):
        links.append(args)
        return real_link(*args, **kwargs)

    monkeypatch.setattr(os, "link", link)
    check.run_check(home, now=_day_later(rehearsed))
    resumed = check.load_record(home)
    assert calls == []
    assert links == []
    assert resumed["status"] == "swapped"
    assert resumed["original_bytes"] == rehearsed["original_bytes"]
    assert _message_ids(generations_file) == {EARLY_ID, LATE_ID}


def test_replace_that_lands_resumes_without_copying(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replace that lands before swapped is written resumes as swapped."""
    home = generations_file.parent
    rehearsed = _rehearse(generations_file)
    before_inode = generations_file.stat().st_ino
    _fail_warehouse_replace(monkeypatch, after_real=True)
    check.run_check(home, now=_day_later(rehearsed))
    record = check.load_record(home)
    backup = home / doctor.SWAP_BACKUP_FILENAME
    assert record["status"] == "linked"
    assert generations_file.stat().st_ino != before_inode
    assert backup.stat().st_ino == before_inode
    monkeypatch.undo()
    stray = home / storage.COPY_FILENAME
    stray.write_bytes(b"stray sibling")
    calls = _spy_copy(monkeypatch)
    links: list[tuple] = []
    real_link = os.link

    def link(*args, **kwargs):
        links.append(args)
        return real_link(*args, **kwargs)

    monkeypatch.setattr(os, "link", link)
    check.run_check(home, now=_day_later(rehearsed))
    assert calls == []
    assert links == []
    assert check.load_record(home)["status"] == "swapped"
    assert not stray.exists()
    assert generations_file.read_bytes() != b"stray sibling"


def test_linked_without_sibling_stays_linked(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Matching inodes and a missing sibling leave the record linked."""
    home = generations_file.parent
    rehearsed = _rehearse(generations_file)
    before = generations_file.read_bytes()
    _fail_warehouse_replace(monkeypatch, after_real=False)
    check.run_check(home, now=_day_later(rehearsed))
    assert check.load_record(home)["status"] == "linked"
    (home / storage.COPY_FILENAME).unlink()
    monkeypatch.undo()
    calls = _spy_copy(monkeypatch)
    check.run_check(home, now=_day_later(rehearsed))
    assert calls == []
    assert check.load_record(home)["status"] == "linked"
    assert generations_file.read_bytes() == before


def test_copy_mismatch_is_final(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed verification records mismatch and a later pass does not copy."""
    home = generations_file.parent
    before = _sha256(generations_file)

    def fail(_original: Path, _copy: Path) -> None:
        raise storage.CopyMismatch("rows differ")

    monkeypatch.setattr(storage, "verify_copy", fail)
    check.run_check(home, now=lambda: 1_000.0)
    record = check.load_record(home)
    assert record["status"] == "mismatch"
    assert not (home / storage.COPY_FILENAME).exists()
    assert _sha256(generations_file) == before
    monkeypatch.undo()
    calls = _spy_copy(monkeypatch)
    check.run_check(home, now=lambda: 2_000.0)
    assert calls == []
    assert check.load_record(home)["status"] == "mismatch"


def test_link_failure_does_not_replace(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A link that raises leaves the original in place and writes no backup."""
    home = generations_file.parent
    rehearsed = _rehearse(generations_file)
    before = generations_file.read_bytes()

    def fail(*_args, **_kwargs):
        raise OSError("link failed")

    monkeypatch.setattr(os, "link", fail)
    check.run_check(home, now=_day_later(rehearsed))
    assert generations_file.read_bytes() == before
    assert not (home / doctor.SWAP_BACKUP_FILENAME).exists()
    assert check.load_record(home)["status"] == "started"


def test_link_that_lands_stays_started(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A link that lands and then raises does not replace, and stays started."""
    home = generations_file.parent
    rehearsed = _rehearse(generations_file)
    before = generations_file.read_bytes()
    before_hash = _sha256(generations_file)
    real = os.link

    def link(*args, **kwargs):
        real(*args, **kwargs)
        raise OSError("link failed after linking")

    monkeypatch.setattr(os, "link", link)
    check.run_check(home, now=_day_later(rehearsed))
    backup = home / doctor.SWAP_BACKUP_FILENAME
    assert _sha256(backup) == before_hash
    assert generations_file.read_bytes() == before
    assert check.load_record(home)["status"] == "started"


def test_final_swapped_record_deletes_a_leftover_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A final swapped record drops a leftover sibling and does not copy."""
    original = tmp_path / warehouse.WAREHOUSE_FILENAME
    original.write_bytes(b"original")
    sibling = tmp_path / storage.COPY_FILENAME
    sibling.write_bytes(b"leftover")
    wal = sibling.with_name(sibling.name + ".wal")
    wal.write_bytes(b"wal")
    check.write_record(
        tmp_path, {"check_version": 1, "status": "swapped", "original_bytes": 8}
    )
    before = (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes()
    calls = _spy_copy(monkeypatch)
    check.run_check(tmp_path, now=lambda: 0.0)
    assert calls == []
    assert not sibling.exists()
    assert not wal.exists()
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == before
    assert original.read_bytes() == b"original"


def test_expired_start_deletes_a_leftover_and_keeps_the_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An expired start drops the sibling, leaves a foreign backup, and does not copy.

    ``started_at`` is a fortnight old. The status is ``started``, not
    ``swapped``, so this pass does not unlink the backup.
    """
    original = tmp_path / warehouse.WAREHOUSE_FILENAME
    original.write_bytes(b"original")
    sibling = tmp_path / storage.COPY_FILENAME
    sibling.write_bytes(b"leftover")
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    backup.write_bytes(b"foreign backup")
    assert backup.stat().st_ino != original.stat().st_ino
    check.write_record(
        tmp_path,
        {
            "check_version": 1,
            "status": "started",
            "started_at": 0.0,
            "limit_seconds": 1,
        },
    )
    before_record = (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes()
    calls = _spy_copy(monkeypatch)
    check.run_check(tmp_path, now=lambda: check.SWAP_BACKUP_RETENTION_SECONDS)
    assert calls == []
    assert not sibling.exists()
    assert original.read_bytes() == b"original"
    assert backup.read_bytes() == b"foreign backup"
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == before_record


def test_unexpired_start_keeps_the_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A start still inside its limit keeps the sibling and does not copy."""
    sibling = tmp_path / storage.COPY_FILENAME
    sibling.write_bytes(b"in progress")
    check.write_record(
        tmp_path,
        {
            "check_version": 1,
            "status": "started",
            "started_at": 100.0,
            "limit_seconds": 14_400,
        },
    )
    calls = _spy_copy(monkeypatch)
    check.run_check(tmp_path, now=lambda: 100.0)
    assert calls == []
    assert sibling.read_bytes() == b"in progress"


_SRC = str(Path(stockroom.__file__).resolve().parent.parent)

_ALARM_CHILD = """
import sys
import time
from pathlib import Path

import stockroom.storage as storage
from stockroom.check import entry

def hang(_original):
    time.sleep(30)

storage.copy_warehouse = hang
entry(Path(sys.argv[1]), limit_seconds=1)
"""


def test_entry_alarm_kills_a_stuck_copy(generations_file: Path) -> None:
    """A stuck copy dies by SIGALRM, leaves started, and releases the flock."""
    home = generations_file.parent
    before = _sha256(generations_file)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    result = subprocess.run(
        [sys.executable, "-c", _ALARM_CHILD, str(home)],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == -signal.SIGALRM, result.stderr
    with warehouse._flock(home / warehouse.LOCK_FILENAME):
        record = check.load_record(home)
    assert record["status"] == "started"
    assert _sha256(generations_file) == before


def test_run_check_does_not_leave_an_alarm(tmp_path: Path) -> None:
    """A pass that returns does not leave an alarm that kills this process."""
    check.run_check(tmp_path, now=lambda: 0.0)
    time.sleep(1.1)
    assert check.load_record(tmp_path)["status"] == "skip"


def _set_child_pythonpath(monkeypatch: pytest.MonkeyPatch) -> None:
    """Put the engine ``src`` directory on ``PYTHONPATH`` for a launched child."""
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join([_SRC, os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
    )


def test_launch_on_a_swapped_record_does_not_build(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A launched pass leaves a swapped record and builds no copy."""
    _set_child_pythonpath(monkeypatch)
    home = generations_file.parent
    record = {"check_version": 1, "status": "swapped"}
    check.write_record(home, record)
    proc = check.launch(home)
    assert proc.wait(timeout=60) == 0
    assert check.load_record(home) == record
    assert not (home / storage.COPY_FILENAME).exists()


def test_launch_on_a_missing_home_creates_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A launched pass leaves a missing home missing."""
    _set_child_pythonpath(monkeypatch)
    home = tmp_path / "missing"
    proc = check.launch(home)
    assert proc.wait(timeout=60) == 0
    assert not home.exists()


def test_launch_does_not_arm_the_parent(
    generations_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The parent has no alarm after launch returns."""
    _set_child_pythonpath(monkeypatch)
    home = generations_file.parent
    check.write_record(home, {"check_version": 1, "status": "swapped"})
    proc = check.launch(home)
    assert signal.alarm(0) == 0
    assert proc.wait(timeout=60) == 0


def test_main_without_flags_launches_and_does_not_enter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No arguments launch the resolved home and do not call entry here."""
    monkeypatch.setenv("STOCKROOM_HOME", str(tmp_path))
    launched: list[Path] = []

    def fake_launch(home: Path) -> subprocess.Popen:
        launched.append(home)
        return subprocess.Popen(["true"])

    def fake_entry(
        home: Path, *, limit_seconds: int = check.TIME_LIMIT_SECONDS
    ) -> None:
        raise AssertionError(home)

    monkeypatch.setattr(check, "launch", fake_launch)
    monkeypatch.setattr(check, "entry", fake_entry)
    assert check.main([]) == 0
    assert launched == [tmp_path]


def test_new_install_records_already_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty install ingests, answers, and the launched check builds nothing."""
    home = tmp_path / "home"
    roots = tmp_path / "roots"
    home.mkdir()
    for name in ("cursor", "chats", "claude"):
        (roots / name).mkdir(parents=True)
    monkeypatch.setenv("STOCKROOM_HOME", str(home))
    monkeypatch.setenv("STOCKROOM_CURSOR_ROOT", str(roots / "cursor"))
    monkeypatch.setenv("STOCKROOM_CURSOR_CHATS_ROOT", str(roots / "chats"))
    monkeypatch.setenv("STOCKROOM_CLAUDE_ROOT", str(roots / "claude"))
    monkeypatch.setenv("STOCKROOM_AI_TRACKING_DB", str(roots / "missing.db"))
    _set_child_pythonpath(monkeypatch)
    assert ingest_main([]) == 0
    assert (home / warehouse.WAREHOUSE_FILENAME).is_file()
    assert embed.main([], encoder_factory=FakeEncoder) == 0
    assert semantic.main(["hello"], encoder_factory=FakeEncoder) == 0
    proc = check.launch(home)
    assert proc.wait(timeout=60) == 0
    assert check.load_record(home)["status"] == "already-new"
    assert not (home / storage.COPY_FILENAME).exists()


# An expired ``started`` record is not ``swapped``, so reclaim does not read
# the clock. ``test_expired_start_deletes_a_leftover_and_keeps_the_backup``
# keeps that backup when ``started_at`` is already a fortnight old.


_STARTED_AT = 1_700_000_000.0


def _deadline() -> float:
    """The instant a backup that started at :data:`_STARTED_AT` is due."""
    return _STARTED_AT + check.SWAP_BACKUP_RETENTION_SECONDS


def _finished_pair(
    home: Path,
    *,
    status: str,
    started_at: float | None,
    same_inode: bool = False,
) -> tuple[bytes, bytes]:
    """Write a live warehouse, a backup name, and a check record.

    Returns the raw ``check.json`` bytes and the warehouse bytes. A
    ``started_at`` of ``None`` omits that field. ``same_inode`` hard-links
    the backup name to the live warehouse.
    """
    original = home / warehouse.WAREHOUSE_FILENAME
    original.write_bytes(b"warehouse")
    backup = home / doctor.SWAP_BACKUP_FILENAME
    if same_inode:
        os.link(original, backup)
    else:
        backup.write_bytes(b"backup")
    record: dict = {"check_version": 1, "status": status}
    if started_at is not None:
        record["started_at"] = started_at
    check.write_record(home, record)
    raw = (home / check.CHECK_RECORD_FILENAME).read_bytes()
    return raw, original.read_bytes()


def test_reclaim_young_swap_keeps_the_backup(tmp_path: Path) -> None:
    """A swapped backup one second under a fortnight stays.

    The warehouse bytes and the raw check record stay with it.
    """
    raw, warehouse_bytes = _finished_pair(
        tmp_path, status="swapped", started_at=_STARTED_AT
    )
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    check.run_check(tmp_path, now=lambda: _deadline() - 1)
    assert backup.read_bytes() == b"backup"
    assert (tmp_path / warehouse.WAREHOUSE_FILENAME).read_bytes() == warehouse_bytes
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw


def test_reclaim_at_the_fortnight_removes_the_backup(tmp_path: Path) -> None:
    """A swapped backup at exactly a fortnight is removed.

    The warehouse bytes and the raw check record stay.
    """
    raw, warehouse_bytes = _finished_pair(
        tmp_path, status="swapped", started_at=_STARTED_AT
    )
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    check.run_check(tmp_path, now=lambda: _deadline())
    assert not backup.exists()
    assert (tmp_path / warehouse.WAREHOUSE_FILENAME).read_bytes() == warehouse_bytes
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw


def test_reclaim_same_inode_keeps_the_backup_name(tmp_path: Path) -> None:
    """A backup name that is a hard link of the live warehouse stays after the fortnight."""
    raw, warehouse_bytes = _finished_pair(
        tmp_path, status="swapped", started_at=_STARTED_AT, same_inode=True
    )
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    original = tmp_path / warehouse.WAREHOUSE_FILENAME
    check.run_check(tmp_path, now=lambda: _deadline())
    assert backup.is_file()
    assert backup.stat().st_ino == original.stat().st_ino
    assert original.read_bytes() == warehouse_bytes
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw


def test_reclaim_missing_started_at_keeps_the_backup(tmp_path: Path) -> None:
    """A swapped record with no started_at keeps the backup past the deadline."""
    raw, warehouse_bytes = _finished_pair(tmp_path, status="swapped", started_at=None)
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    check.run_check(tmp_path, now=lambda: _deadline())
    assert backup.read_bytes() == b"backup"
    assert (tmp_path / warehouse.WAREHOUSE_FILENAME).read_bytes() == warehouse_bytes
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw


def test_reclaim_bool_started_at_keeps_the_backup(tmp_path: Path) -> None:
    """A swapped record whose started_at is a bool keeps the backup."""
    original = tmp_path / warehouse.WAREHOUSE_FILENAME
    original.write_bytes(b"warehouse")
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    backup.write_bytes(b"backup")
    check.write_record(
        tmp_path,
        {"check_version": 1, "status": "swapped", "started_at": True},
    )
    raw = (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes()
    check.run_check(tmp_path, now=lambda: _deadline())
    assert backup.read_bytes() == b"backup"
    assert original.read_bytes() == b"warehouse"
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw


def test_reclaim_linked_keeps_a_fortnight_old_backup(tmp_path: Path) -> None:
    """A linked record keeps a fortnight-old backup.

    Finish-swap may write ``swapped``. This pass does not unlink the backup.
    """
    _raw, warehouse_bytes = _finished_pair(
        tmp_path, status="linked", started_at=_STARTED_AT
    )
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    check.run_check(tmp_path, now=lambda: _deadline())
    assert backup.read_bytes() == b"backup"
    assert (tmp_path / warehouse.WAREHOUSE_FILENAME).read_bytes() == warehouse_bytes


def test_reclaim_mismatch_keeps_the_backup(tmp_path: Path) -> None:
    """A mismatch record keeps a fortnight-old backup, and the record bytes stay."""
    raw, warehouse_bytes = _finished_pair(
        tmp_path, status="mismatch", started_at=_STARTED_AT
    )
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    check.run_check(tmp_path, now=lambda: _deadline())
    assert backup.read_bytes() == b"backup"
    assert (tmp_path / warehouse.WAREHOUSE_FILENAME).read_bytes() == warehouse_bytes
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw


def test_reclaim_already_new_keeps_the_backup(tmp_path: Path) -> None:
    """An already-new record keeps a fortnight-old backup, and the record bytes stay."""
    raw, warehouse_bytes = _finished_pair(
        tmp_path, status="already-new", started_at=_STARTED_AT
    )
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    check.run_check(tmp_path, now=lambda: _deadline())
    assert backup.read_bytes() == b"backup"
    assert (tmp_path / warehouse.WAREHOUSE_FILENAME).read_bytes() == warehouse_bytes
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw


def test_reclaim_second_pass_leaves_the_record(tmp_path: Path) -> None:
    """After the backup is removed, a second pass changes nothing and raises nothing."""
    raw, warehouse_bytes = _finished_pair(
        tmp_path, status="swapped", started_at=_STARTED_AT
    )
    backup = tmp_path / doctor.SWAP_BACKUP_FILENAME
    check.run_check(tmp_path, now=lambda: _deadline())
    assert not backup.exists()
    assert (tmp_path / warehouse.WAREHOUSE_FILENAME).read_bytes() == warehouse_bytes
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw
    check.run_check(tmp_path, now=lambda: _deadline() + 1)
    assert not backup.exists()
    assert (tmp_path / warehouse.WAREHOUSE_FILENAME).read_bytes() == warehouse_bytes
    assert (tmp_path / check.CHECK_RECORD_FILENAME).read_bytes() == raw


def _spy_parent(monkeypatch: pytest.MonkeyPatch, home: Path) -> list[Path]:
    """Point ``main`` at ``home`` and record ``launch`` without calling ``entry``."""
    monkeypatch.setenv("STOCKROOM_HOME", str(home))
    launched: list[Path] = []

    def fake_launch(path: Path) -> subprocess.Popen:
        launched.append(path)
        return subprocess.Popen(["true"])

    def fake_entry(
        path: Path, *, limit_seconds: int = check.TIME_LIMIT_SECONDS
    ) -> None:
        raise AssertionError(path)

    monkeypatch.setattr(check, "launch", fake_launch)
    monkeypatch.setattr(check, "entry", fake_entry)
    return launched


def _freeze_check_clock(monkeypatch: pytest.MonkeyPatch, now: float) -> None:
    """Make ``check.time.time`` return ``now`` for the parent gate."""
    monkeypatch.setattr(check.time, "time", lambda: now)


@pytest.mark.parametrize("status", ["swapped", "already-new", "mismatch"])
def test_parent_finished_without_a_backup_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    """A finished version-1 home with no backup file returns without a child."""
    (tmp_path / warehouse.WAREHOUSE_FILENAME).write_bytes(b"warehouse")
    check.write_record(
        tmp_path,
        {"check_version": 1, "status": status, "started_at": _STARTED_AT},
    )
    _freeze_check_clock(monkeypatch, _deadline())
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == []


def test_parent_young_swap_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swapped backup one second under a fortnight does not start a child."""
    _finished_pair(tmp_path, status="swapped", started_at=_STARTED_AT)
    _freeze_check_clock(monkeypatch, _deadline() - 1)
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == []


def test_parent_due_swap_starts_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swapped backup at exactly a fortnight starts the child and does not enter here."""
    _finished_pair(tmp_path, status="swapped", started_at=_STARTED_AT)
    _freeze_check_clock(monkeypatch, _deadline())
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == [tmp_path]


def test_parent_same_inode_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A backup name that is the live warehouse does not start the child after the fortnight."""
    _finished_pair(tmp_path, status="swapped", started_at=_STARTED_AT, same_inode=True)
    _freeze_check_clock(monkeypatch, _deadline())
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == []


def test_parent_missing_started_at_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swapped backup with no started_at does not start the child."""
    _finished_pair(tmp_path, status="swapped", started_at=None)
    _freeze_check_clock(monkeypatch, _deadline())
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == []


def test_parent_bool_started_at_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swapped backup whose started_at is a bool does not start the child."""
    (tmp_path / warehouse.WAREHOUSE_FILENAME).write_bytes(b"warehouse")
    (tmp_path / doctor.SWAP_BACKUP_FILENAME).write_bytes(b"backup")
    check.write_record(
        tmp_path,
        {"check_version": 1, "status": "swapped", "started_at": True},
    )
    _freeze_check_clock(monkeypatch, _deadline())
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == []


def test_parent_missing_warehouse_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A due swapped record with no live warehouse does not start the child."""
    (tmp_path / doctor.SWAP_BACKUP_FILENAME).write_bytes(b"backup")
    check.write_record(
        tmp_path,
        {"check_version": 1, "status": "swapped", "started_at": _STARTED_AT},
    )
    _freeze_check_clock(monkeypatch, _deadline())
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == []


@pytest.mark.parametrize("status", ["already-new", "mismatch"])
def test_parent_other_terminal_with_a_backup_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    """An already-new or mismatch record returns even when the backup file is present."""
    _finished_pair(tmp_path, status=status, started_at=_STARTED_AT)
    _freeze_check_clock(monkeypatch, _deadline())
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == []


@pytest.mark.parametrize("status", ["rehearsed", "linked", "started", "skip"])
def test_parent_unfinished_status_starts_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    """A version-1 home that has not finished starts the child.

    No record is ``test_main_without_flags_launches_and_does_not_enter``.
    """
    check.write_record(tmp_path, {"check_version": 1, "status": status})
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == [tmp_path]


@pytest.mark.parametrize("payload", ["[]", "not-json"])
def test_parent_unreadable_record_starts_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: str
) -> None:
    """A check record ``load_record`` cannot read starts the child."""
    (tmp_path / check.CHECK_RECORD_FILENAME).write_text(payload, encoding="utf-8")
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == [tmp_path]


def test_parent_other_check_version_starts_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swapped record whose check_version is not 1 starts the child."""
    check.write_record(tmp_path, {"check_version": 2, "status": "swapped"})
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == [tmp_path]


def test_parent_stat_error_on_a_due_backup_starts_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stat error while judging a due swapped backup starts the child."""
    _finished_pair(tmp_path, status="swapped", started_at=_STARTED_AT)
    _freeze_check_clock(monkeypatch, _deadline())
    real_stat = Path.stat
    seen = {"n": 0}

    def stat(self: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        if self.name == doctor.SWAP_BACKUP_FILENAME:
            seen["n"] += 1
            if seen["n"] > 1:
                raise FileNotFoundError(self)
        return real_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", stat)
    launched = _spy_parent(monkeypatch, tmp_path)
    assert check.main([]) == 0
    assert launched == [tmp_path]


def test_foreground_on_a_young_swap_enters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--foreground`` runs the pass here, including when the parent would return."""
    _finished_pair(tmp_path, status="swapped", started_at=_STARTED_AT)
    _freeze_check_clock(monkeypatch, _deadline() - 1)
    entered: list[Path] = []

    def fake_entry(
        home: Path, *, limit_seconds: int = check.TIME_LIMIT_SECONDS
    ) -> None:
        entered.append(home)

    def fake_launch(home: Path) -> subprocess.Popen:
        raise AssertionError(home)

    monkeypatch.setattr(check, "entry", fake_entry)
    monkeypatch.setattr(check, "launch", fake_launch)
    assert check.main(["--foreground", str(tmp_path)]) == 0
    assert entered == [tmp_path]


_QUIET_IMPORT = """
import sys

import stockroom.check as check

imported = "duckdb" in sys.modules
code = check.main([])
after = "duckdb" in sys.modules
sys.stdout.write(f"{imported} {after} {code}\\n")
"""


def test_importing_check_on_a_young_swap_does_not_import_duckdb(
    tmp_path: Path,
) -> None:
    """Importing the check and returning on a young swapped backup does not import DuckDB."""
    _finished_pair(tmp_path, status="swapped", started_at=time.time())
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_SRC, env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )
    env["STOCKROOM_HOME"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", _QUIET_IMPORT],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False False 0"
