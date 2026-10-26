"""Unit tests for ``stockroom.doctor`` — probe facts and the loud-failing smoke.

``probe_facts`` is exercised fully torch-free via the injectable
``nvidia-smi`` runner and torch importer: facts are reported for
every environment shape, and no subprocess or import failure ever raises.
``run_smoke``'s failure shapes are covered via injected fakes —
each failure must print exactly one stderr line that carries the *next
action* (the errmsg ratchet), not just name the problem. The single real
torch/encoder path is ``importorskip("torch")``-gated per the
engine-wide convention.
"""

import fcntl
import gc
import os
import subprocess
import sys
import types
from collections.abc import Callable
from pathlib import Path

import duckdb
import pytest

from stockroom import check, doctor, migrate, warehouse
from stockroom.embed import EMBED_DIM
from stockroom.shim import default_app_dir


@pytest.fixture
def stockroom_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate freeze lookups under a fresh STOCKROOM_HOME."""
    home = tmp_path / "stockroom-home"
    home.mkdir()
    monkeypatch.setenv("STOCKROOM_HOME", str(home))
    return home


@pytest.fixture
def empty_stockroom_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point STOCKROOM_HOME at an empty directory with no warehouse file."""
    home = tmp_path / "empty-home"
    home.mkdir()
    monkeypatch.setenv("STOCKROOM_HOME", str(home))
    return home


# --- injectable stand-ins -------------------------------------------------


def _smi_absent(args: list[str]) -> str:
    """A machine with no nvidia-smi on PATH."""
    raise FileNotFoundError("nvidia-smi")


def _smi_failing(args: list[str]) -> str:
    """nvidia-smi present but erroring (e.g. no driver loaded)."""
    raise subprocess.CalledProcessError(1, ["nvidia-smi", *args])


def _smi_garbage(args: list[str]) -> str:
    """nvidia-smi present but emitting nothing parseable."""
    return "ERR!\n"


def _smi_ok(args: list[str]) -> str:
    """A healthy CUDA box (real output shapes captured from a live machine)."""
    if any(arg.startswith("--query-gpu=") for arg in args):
        return "NVIDIA GeForce GTX 1070, 582.28, 6.1\n"
    return (
        "NVIDIA-SMI version  : 580.126.10\n"
        "NVML version        : 580.126\n"
        "DRIVER version      : 582.28\n"
        "CUDA Version        : 13.0\n"
    )


def _import_absent(name: str) -> object:
    """An importer for an environment where torch is not installed."""
    raise ImportError(f"No module named '{name}'")


def _fake_torch(version: str = "2.11.0", cuda: bool = True) -> object:
    """A minimal stand-in exposing __version__ and cuda.is_available()."""
    module = types.SimpleNamespace()
    module.__version__ = version
    module.cuda = types.SimpleNamespace(is_available=lambda: cuda)
    return module


def _importer_for(module: object):
    """An importer that returns ``module`` for 'torch'."""

    def _import(name: str) -> object:
        assert name == "torch"
        return module

    return _import


class _GoodEncoder:
    """Encodes every string to a correct-width constant vector."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.5] * EMBED_DIM for _ in texts]


class _WrongWidthEncoder:
    """Encodes to a vector of the wrong dimension (a broken setup)."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.5] * (EMBED_DIM - 1) for _ in texts]


class _ExplodingEncoder:
    """Raises from encode — the wrong-wheel kernel-crash surface."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("CUDA error: no kernel image is available")


# --- probe: facts, torch-free, never crashes ----------------------


def _probe(**kwargs) -> dict[str, str]:
    """Run probe_facts with torch absent by default; return facts as a dict."""
    kwargs.setdefault("torch_importer", _import_absent)
    kwargs.setdefault("smi_runner", _smi_absent)
    facts = doctor.probe_facts(**kwargs)
    keys = [key for key, _ in facts]
    assert len(keys) == len(set(keys)), f"duplicate fact keys: {keys}"
    return dict(facts)


def test_probe_reports_os_and_arch(empty_stockroom_home: Path) -> None:
    """Os/arch come from the platform module as stable facts."""
    import platform

    facts = _probe()
    assert facts["os"] == platform.system()
    assert facts["arch"] == platform.machine()


def test_probe_reports_gpu_and_driver_when_smi_parseable(
    empty_stockroom_home: Path,
) -> None:
    """A healthy nvidia-smi yields GPU name, driver, driver CUDA
    ceiling, and the compute capability (the sm_ generation input)."""
    facts = _probe(smi_runner=_smi_ok)
    assert facts["gpu"] == "NVIDIA GeForce GTX 1070"
    assert facts["driver"] == "582.28"
    assert facts["driver-cuda"] == "13.0"
    assert facts["gpu-compute-cap"] == "6.1"


def test_probe_reports_gpu_none_when_smi_absent(empty_stockroom_home: Path) -> None:
    """No nvidia-smi on PATH is a fact (gpu: none), never an error."""
    facts = _probe(smi_runner=_smi_absent)
    assert facts["gpu"] == "none"
    assert "driver" not in facts
    assert "driver-cuda" not in facts


@pytest.mark.parametrize("runner", [_smi_failing, _smi_garbage])
def test_probe_degrades_gracefully_on_smi_failure(
    runner, empty_stockroom_home: Path
) -> None:
    """An erroring or garbage-emitting nvidia-smi degrades to an
    'unavailable' fact — no traceback, no raise."""
    facts = _probe(smi_runner=runner)
    assert facts["gpu"] == "unavailable"


def test_probe_reports_torch_not_installed(empty_stockroom_home: Path) -> None:
    """An unimportable torch is a reported fact."""
    facts = _probe(torch_importer=_import_absent)
    assert facts["torch"] == "not installed"
    assert "torch-cuda" not in facts


def test_probe_reports_torch_version_and_cuda(empty_stockroom_home: Path) -> None:
    """An importable torch yields its version and CUDA availability."""
    facts = _probe(torch_importer=_importer_for(_fake_torch("2.11.0", cuda=True)))
    assert facts["torch"] == "2.11.0"
    assert facts["torch-cuda"] == "True"


def test_probe_reports_engine_dir(empty_stockroom_home: Path) -> None:
    """The engine dir fact names where the engine environment lives."""
    facts = _probe()
    assert facts["engine-dir"] == str(default_app_dir())


def test_probe_reports_home_and_source_from_resolve_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Probe reports ``home`` + ``home-source`` from ``warehouse.resolve_home``."""
    xdg = tmp_path / "xdg-data"
    monkeypatch.delenv(warehouse.HOME_ENV_VAR, raising=False)
    monkeypatch.setenv(warehouse.XDG_DATA_HOME_ENV_VAR, str(xdg))
    facts = _probe()
    assert facts["home"] == str(xdg / "stockroom")
    assert facts["home-source"] == warehouse.HOME_SOURCE_XDG


def test_probe_home_facts_do_not_mkdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Doctor probe must not create the resolved home directory."""
    xdg = tmp_path / "xdg-data"
    target = xdg / "stockroom"
    monkeypatch.delenv(warehouse.HOME_ENV_VAR, raising=False)
    monkeypatch.setenv(warehouse.XDG_DATA_HOME_ENV_VAR, str(xdg))
    facts = _probe()
    assert facts["home"] == str(target)
    assert not target.exists()


def test_probe_never_imports_torch_eagerly(empty_stockroom_home: Path) -> None:
    """Importing the module and probing goes through the injected
    importer only — the real torch is never touched."""
    if "torch" in sys.modules:
        pytest.skip("torch already loaded in this process")

    calls: list[str] = []

    def recording_importer(name: str) -> object:
        calls.append(name)
        raise ImportError(name)

    facts = _probe(torch_importer=recording_importer)
    assert calls == ["torch"]
    assert facts["torch"] == "not installed"
    assert "torch" not in sys.modules


def _refusing_connect() -> tuple[list[tuple[object, object]], Callable[..., object]]:
    """A connect stand-in that records every call, then raises."""
    calls: list[tuple[object, object]] = []

    def connect(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        raise AssertionError("connect was called")

    return calls, connect


def _storage(
    home: Path, *, connect: Callable[..., object] | None = None
) -> dict[str, str]:
    """Run storage_facts and return the pairs as a dict."""
    kwargs = {} if connect is None else {"connect": connect}
    facts = doctor.storage_facts(home, **kwargs)
    keys = [key for key, _ in facts]
    assert len(keys) == len(set(keys)), f"duplicate fact keys: {keys}"
    return dict(facts)


def _persistent_block_bytes(con: duckdb.DuckDBPyConnection) -> int:
    """Live bytes from distinct persistent block ids, views excluded.

    This is the oracle for ``doctor.live_bytes``: persistent ``block_id``
    values, plus a non-empty ``additional_block_ids`` list, dropping ids
    below 0, times ``block_size``.
    """
    block_size = con.execute(
        "SELECT block_size FROM pragma_database_size() "
        "WHERE database_name = current_database()"
    ).fetchone()[0]
    views = {
        name
        for (name,) in con.execute(
            "SELECT view_name FROM duckdb_views() "
            "WHERE database_name = current_database() AND schema_name = 'main'"
        ).fetchall()
    }
    tables = [
        name
        for (name,) in con.execute(
            "SELECT table_name FROM duckdb_tables() "
            "WHERE database_name = current_database() AND schema_name = 'main'"
        ).fetchall()
        if name not in views
    ]
    ids: set[int] = set()
    for name in tables:
        literal = "'" + name.replace("'", "''") + "'"
        rows = con.execute(
            "SELECT block_id, additional_block_ids "
            f"FROM pragma_storage_info({literal}) WHERE persistent"
        ).fetchall()
        for block_id, extra in rows:
            if block_id is not None and block_id >= 0:
                ids.add(int(block_id))
            if extra:
                for extra_id in extra:
                    if extra_id is not None and extra_id >= 0:
                        ids.add(int(extra_id))
    return len(ids) * int(block_size)


@pytest.fixture
def released_warehouse(warehouse_home: Path) -> Path:
    """A head warehouse whose writer flock has been released."""
    con = warehouse.open()
    path = warehouse_home / warehouse.WAREHOUSE_FILENAME
    con.close()
    del con
    gc.collect()
    return path


def test_storage_missing_home_reports_absent_without_connecting(tmp_path: Path) -> None:
    """A home that does not exist is warehouse: absent, with free disk.

    The connect is not called, blocks-used is absent, and the home, the
    warehouse file, and the lock file stay absent.
    """
    home = tmp_path / "missing-home"
    calls, connect = _refusing_connect()
    facts = _storage(home, connect=connect)
    assert calls == []
    assert facts["warehouse"] == "absent"
    assert int(facts["disk-free"]) > 0
    assert "blocks-used" not in facts
    assert not home.exists()
    assert not (home / warehouse.WAREHOUSE_FILENAME).exists()
    assert not (home / warehouse.LOCK_FILENAME).exists()


def test_storage_missing_file_reports_absent_without_connecting(tmp_path: Path) -> None:
    """A home with no warehouse file is warehouse: absent.

    The connect is not called, and probe does not create the file.
    """
    home = tmp_path / "home"
    home.mkdir()
    calls, connect = _refusing_connect()
    facts = _storage(home, connect=connect)
    assert calls == []
    assert facts["warehouse"] == "absent"
    assert not (home / warehouse.WAREHOUSE_FILENAME).exists()


def test_storage_reports_warehouse_bytes(released_warehouse: Path) -> None:
    """warehouse-bytes is the warehouse file's stat size."""
    facts = _probe()
    assert facts["warehouse-bytes"] == str(released_warehouse.stat().st_size)


def test_storage_reports_used_and_free_blocks(released_warehouse: Path) -> None:
    """blocks-used and blocks-free match pragma_database_size."""
    con = duckdb.connect(str(released_warehouse), read_only=True)
    try:
        used, free = con.execute(
            "SELECT used_blocks, free_blocks FROM pragma_database_size() "
            "WHERE database_name = current_database()"
        ).fetchone()
    finally:
        con.close()
    facts = _probe()
    assert facts["blocks-used"] == str(int(used))
    assert facts["blocks-free"] == str(int(free))


def test_storage_reports_storage_format(released_warehouse: Path) -> None:
    """storage is duckdb_databases().tags['storage_version']."""
    con = duckdb.connect(str(released_warehouse), read_only=True)
    try:
        tags = con.execute(
            "SELECT tags FROM duckdb_databases() "
            "WHERE database_name = current_database()"
        ).fetchone()[0]
    finally:
        con.close()
    facts = _probe()
    assert facts["storage"] == tags["storage_version"]


def test_storage_reports_reclaimable_bytes(released_warehouse: Path) -> None:
    """reclaimable-bytes is the file size minus the persistent-block estimate.

    The estimate unions persistent block ids, drops ids below 0, and
    includes a non-empty additional_block_ids list. The result is >= 0.
    """
    con = duckdb.connect(str(released_warehouse), read_only=True)
    try:
        expected = _persistent_block_bytes(con)
        assert doctor.live_bytes(con) == expected
    finally:
        con.close()
    facts = _probe()
    assert int(facts["reclaimable-bytes"]) == (
        released_warehouse.stat().st_size - expected
    )
    assert int(facts["reclaimable-bytes"]) >= 0


def test_storage_reports_backup_when_present(tmp_path: Path) -> None:
    """The swap backup's path and size are reported when that file exists."""
    home = tmp_path / "home"
    home.mkdir()
    backup = home / doctor.SWAP_BACKUP_FILENAME
    backup.write_bytes(b"swap-bytes")
    facts = _storage(home)
    assert facts["backup"] == str(backup)
    assert facts["backup-bytes"] == str(backup.stat().st_size)


def test_storage_reports_backup_absent(tmp_path: Path) -> None:
    """No swap backup is backup: absent, with no backup-bytes line."""
    home = tmp_path / "home"
    home.mkdir()
    facts = _storage(home)
    assert facts["backup"] == "absent"
    assert "backup-bytes" not in facts


def test_storage_ignores_other_backup_names(tmp_path: Path) -> None:
    """A user backup such as warehouse.duckdb.bak is not the swap backup."""
    home = tmp_path / "home"
    home.mkdir()
    (home / "warehouse.duckdb.bak").write_bytes(b"user-backup")
    facts = _storage(home)
    assert facts["backup"] == "absent"
    assert "backup-bytes" not in facts


def test_storage_busy_lock_does_not_connect(tmp_path: Path) -> None:
    """A held writer flock is warehouse: busy, with the file size, and no connect."""
    home = tmp_path / "home"
    home.mkdir()
    warehouse_file = home / warehouse.WAREHOUSE_FILENAME
    warehouse_file.write_bytes(b"0123456789")
    fd = os.open(home / warehouse.LOCK_FILENAME, os.O_CREAT | os.O_RDWR, 0o644)
    calls, connect = _refusing_connect()
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        facts = _storage(home, connect=connect)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    assert calls == []
    assert facts["warehouse"] == "busy"
    assert facts["warehouse-bytes"] == str(warehouse_file.stat().st_size)


def test_storage_below_head_does_not_change_the_file(warehouse_home: Path) -> None:
    """A warehouse below the schema head is not migrated.

    Probe does not raise, does not change the file's bytes, does not
    change schema_version, and still prints warehouse-bytes and disk-free.
    """
    warehouse_home.mkdir()
    path = warehouse_home / warehouse.WAREHOUSE_FILENAME
    con = duckdb.connect(str(path))
    try:
        migrate.ensure_schema_version_table(con)
        con.execute(
            f"INSERT INTO {migrate.SCHEMA_VERSION_TABLE} (version, filename) "
            "VALUES (1, '0001_test.sql')"
        )
    finally:
        con.close()
    before = path.read_bytes()
    names = sorted(entry.name for entry in warehouse_home.iterdir())
    facts = _probe()
    assert path.read_bytes() == before
    assert sorted(entry.name for entry in warehouse_home.iterdir()) == names
    con = duckdb.connect(str(path), read_only=True)
    try:
        assert migrate.current_version(con) == 1
    finally:
        con.close()
    assert facts["warehouse-bytes"] == str(path.stat().st_size)
    assert int(facts["disk-free"]) > 0


def test_storage_connect_failure_is_unavailable(tmp_path: Path) -> None:
    """A connect that raises is warehouse: unavailable and probe does not raise."""
    home = tmp_path / "home"
    home.mkdir()
    warehouse_file = home / warehouse.WAREHOUSE_FILENAME
    warehouse_file.write_bytes(b"not-a-database")

    def connect(*_args: object, **_kwargs: object) -> object:
        raise OSError("cannot open")

    facts = _storage(home, connect=connect)
    assert facts["warehouse"] == "unavailable"
    assert facts["warehouse-bytes"] == str(warehouse_file.stat().st_size)
    assert int(facts["disk-free"]) > 0


def test_storage_read_failure_is_unavailable(tmp_path: Path) -> None:
    """A pragma failure after connect is warehouse: unavailable.

    Stat facts stay, connection facts do not, and probe does not raise.
    """
    home = tmp_path / "home"
    home.mkdir()
    warehouse_file = home / warehouse.WAREHOUSE_FILENAME
    warehouse_file.write_bytes(b"x")

    class _Broken:
        def execute(self, *_args: object, **_kwargs: object) -> object:
            raise duckdb.CatalogException("pragma failed")

        def close(self) -> None:
            return None

    def connect(*_args: object, **_kwargs: object) -> _Broken:
        return _Broken()

    facts = _storage(home, connect=connect)
    assert facts["warehouse"] == "unavailable"
    assert facts["warehouse-bytes"] == str(warehouse_file.stat().st_size)
    assert int(facts["disk-free"]) > 0
    assert "blocks-used" not in facts


def test_format_facts_renders_key_value_lines() -> None:
    """format_facts emits one aligned ``key: value`` line per fact."""
    text = doctor.format_facts([("os", "Linux"), ("gpu-compute-cap", "6.1")])
    lines = text.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("os:")
    assert lines[0].endswith("Linux")
    assert lines[1].startswith("gpu-compute-cap:")
    assert lines[1].endswith("6.1")


def test_check_absent_when_no_record(tmp_path: Path) -> None:
    """No check record is the check value absent."""
    home = tmp_path / "home"
    home.mkdir()
    assert _storage(home)["check"] == "absent"


def test_check_rehearsed_line_names_the_measurement_and_path(tmp_path: Path) -> None:
    """A rehearsed record is one line with the status, a measurement, and the path."""
    home = tmp_path / "home"
    home.mkdir()
    record_path = home / check.CHECK_RECORD_FILENAME
    check.write_record(
        home,
        {"check_version": 1, "status": "rehearsed", "original_bytes": 100},
    )
    value = _storage(home)["check"]
    assert "\n" not in value
    assert "rehearsed" in value
    assert "original_bytes" in value
    assert str(record_path) in value


def test_check_started_inside_the_limit_says_running(tmp_path: Path) -> None:
    """A started entry still inside its limit says running, not crash."""
    home = tmp_path / "home"
    home.mkdir()
    moment = 1_000_000.0
    check.write_record(
        home,
        {
            "check_version": 1,
            "status": "started",
            "started_at": moment,
            "limit_seconds": 14_400,
        },
    )
    value = check.check_line(home, now=lambda: moment)
    assert value.startswith("running")
    assert "crash" not in value


def test_check_started_past_the_limit_says_overrun(tmp_path: Path) -> None:
    """A started entry past its limit says overrun."""
    home = tmp_path / "home"
    home.mkdir()
    check.write_record(
        home,
        {
            "check_version": 1,
            "status": "started",
            "started_at": 0,
            "limit_seconds": 1,
        },
    )
    value = check.check_line(home, now=lambda: 1.0)
    assert value.startswith("overrun")


def test_check_skip_names_the_reason(tmp_path: Path) -> None:
    """A low-disk skip names that reason."""
    home = tmp_path / "home"
    home.mkdir()
    check.write_record(
        home, {"check_version": 1, "status": "skip", "skip_reason": "low-disk"}
    )
    assert "low-disk" in _storage(home)["check"]


def test_check_unreadable_record(tmp_path: Path) -> None:
    """A record that is not a JSON object is unreadable."""
    home = tmp_path / "home"
    home.mkdir()
    (home / check.CHECK_RECORD_FILENAME).write_text("{", encoding="utf-8")
    assert _storage(home)["check"] == "unreadable"


def test_storage_facts_does_not_change_mtimes(tmp_path: Path) -> None:
    """Reading storage facts leaves the warehouse and the record mtimes alone."""
    home = tmp_path / "home"
    home.mkdir()
    database = home / warehouse.WAREHOUSE_FILENAME
    duckdb.connect(str(database)).close()
    check.write_record(home, {"check_version": 1, "status": "rehearsed"})
    record = home / check.CHECK_RECORD_FILENAME
    stamp = 1_700_000_000
    os.utime(database, (stamp, stamp))
    os.utime(record, (stamp, stamp))
    _storage(home)
    assert database.stat().st_mtime_ns == record.stat().st_mtime_ns
    assert database.stat().st_mtime == stamp


def test_storage_returns_include_check(tmp_path: Path) -> None:
    """Absent, busy, unavailable, and present warehouses all report check."""
    missing = tmp_path / "missing"
    assert "check" in _storage(missing)

    home = tmp_path / "home"
    home.mkdir()
    database = home / warehouse.WAREHOUSE_FILENAME
    database.write_bytes(b"0123456789")
    fd = os.open(home / warehouse.LOCK_FILENAME, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        assert "check" in _storage(home)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    def fail(*_args, **_kwargs):
        raise OSError("cannot open")

    assert "check" in _storage(home, connect=fail)

    database.unlink()
    duckdb.connect(str(database)).close()
    assert "check" in _storage(home)


# --- smoke: loud-failing verification -----------------------------


def _one_stderr_line(capsys) -> str:
    """Assert stderr is exactly one line (no traceback) and return it."""
    err = capsys.readouterr().err
    lines = [line for line in err.splitlines() if line]
    assert len(lines) == 1, f"expected one stderr line, got: {err!r}"
    assert "Traceback" not in err
    return lines[0]


def test_smoke_torch_missing_without_freeze_names_initialize(
    capsys, stockroom_home: Path
) -> None:
    """Missing torch + no freeze → exit 1, one stderr line naming sr-initialize."""
    assert not (stockroom_home / "torch-requirements.txt").exists()
    code = doctor.run_smoke(torch_importer=_import_absent, encoder_factory=_GoodEncoder)
    assert code == 1
    line = _one_stderr_line(capsys)
    assert str(default_app_dir()) in line
    assert "sr-initialize" in line
    assert "uv pip install" not in line
    assert "<build>" not in line
    assert "ensure-env" not in line


def test_smoke_torch_missing_with_freeze_names_ensure_env(
    capsys, stockroom_home: Path
) -> None:
    """Missing torch + usable freeze → recommend shim ensure-env, not raw pip."""
    (stockroom_home / "torch-requirements.txt").write_text(
        "--index-url https://download.pytorch.org/whl/cpu\n"
        "torch==2.7.1+cpu \\\n"
        "    --hash=sha256:deadbeef\n",
        encoding="utf-8",
    )
    code = doctor.run_smoke(torch_importer=_import_absent, encoder_factory=_GoodEncoder)
    assert code == 1
    line = _one_stderr_line(capsys)
    assert str(default_app_dir()) in line
    assert "stockroom shim ensure-env" in line
    assert "uv pip install torch" not in line


def test_smoke_torch_missing_with_unusable_freeze_names_initialize(
    capsys, stockroom_home: Path
) -> None:
    """Corrupt freeze (no hashes) is treated as no freeze for the remedy."""
    (stockroom_home / "torch-requirements.txt").write_text(
        "torch==2.7.1+cpu\n", encoding="utf-8"
    )
    code = doctor.run_smoke(torch_importer=_import_absent, encoder_factory=_GoodEncoder)
    assert code == 1
    line = _one_stderr_line(capsys)
    assert "sr-initialize" in line
    assert "uv pip install" not in line
    assert "ensure-env" not in line


def test_smoke_encoder_failure_names_error_and_next_action(capsys) -> None:
    """An exploding encode (the wrong-wheel crash shape) → exit 1, one
    stderr line naming the failure plus the re-pick remedy."""
    code = doctor.run_smoke(
        torch_importer=_importer_for(_fake_torch()),
        encoder_factory=_ExplodingEncoder,
    )
    assert code == 1
    line = _one_stderr_line(capsys)
    assert "no kernel image" in line
    assert "sr-initialize" in line
    assert "wheel index" not in line


def test_smoke_encoder_construction_failure_is_caught(capsys) -> None:
    """An encoder factory that raises is compressed
    to the same one-line actionable failure."""

    def exploding_factory() -> object:
        raise OSError("model download failed")

    code = doctor.run_smoke(
        torch_importer=_importer_for(_fake_torch()),
        encoder_factory=exploding_factory,
    )
    assert code == 1
    line = _one_stderr_line(capsys)
    assert "model download failed" in line
    assert "sr-initialize" in line


def test_smoke_wrong_width_vector_is_a_failure(capsys) -> None:
    """A wrong-width vector is a broken setup, not success — exit 1
    with the actionable re-pick line."""
    code = doctor.run_smoke(
        torch_importer=_importer_for(_fake_torch()),
        encoder_factory=_WrongWidthEncoder,
    )
    assert code == 1
    line = _one_stderr_line(capsys)
    assert str(EMBED_DIM) in line
    assert "sr-initialize" in line


def test_smoke_happy_path_reports_version_cuda_and_ok(capsys) -> None:
    """Torch + encoder healthy → exit 0; stdout carries the torch
    version, the CUDA availability, and an ok summary."""
    code = doctor.run_smoke(
        torch_importer=_importer_for(_fake_torch("2.11.0", cuda=False)),
        encoder_factory=_GoodEncoder,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "2.11.0" in out
    assert "False" in out
    assert "ok" in out


def test_smoke_real_model_end_to_end(capsys) -> None:
    """With real torch provisioned, the production BgeEncoder path
    encodes one string and exits 0 (machine-local; skipped on torch-free CI)."""
    pytest.importorskip("torch")
    code = doctor.run_smoke()
    assert code == 0
    out = capsys.readouterr().out
    assert "ok" in out
