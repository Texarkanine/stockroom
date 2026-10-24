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
from stockroom import check, doctor, migrate, storage, warehouse


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
    """An expired start drops the sibling, leaves a foreign backup, and does not copy."""
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
    check.run_check(tmp_path, now=lambda: 10.0)
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
