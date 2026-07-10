"""Contracts for durable dashboard listener identity under stockroom home."""

from pathlib import Path

import stockroom
from stockroom.dashboard import identity as dash_identity


def test_identity_round_trip_under_stockroom_home(warehouse_home: Path) -> None:
    """Write then read returns the same pid, app_dir, version, and port."""
    record = dash_identity.DashboardIdentity(
        pid=4242,
        app_dir=Path("/tmp/fake-engine"),
        version="1.2.3",
        port=6767,
    )
    written = dash_identity.write(record)
    assert written.is_file()
    assert written.parent == warehouse_home
    assert dash_identity.read(6767) == record


def test_identity_missing_file_reads_as_none(warehouse_home: Path) -> None:
    """Absent identity file yields None."""
    assert dash_identity.read(6767) is None


def test_identity_corrupt_file_reads_as_none(warehouse_home: Path) -> None:
    """Unparseable identity content yields None."""
    path = dash_identity.path(6767)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-a-valid-identity\n", encoding="utf-8")
    assert dash_identity.read(6767) is None


def test_identity_clear_removes_file(warehouse_home: Path) -> None:
    """clear() deletes the identity file when present."""
    dash_identity.write(
        dash_identity.DashboardIdentity(
            pid=1,
            app_dir=Path("/x"),
            version="0",
            port=7777,
        )
    )
    assert dash_identity.path(7777).is_file()
    dash_identity.clear(7777)
    assert not dash_identity.path(7777).exists()
    assert dash_identity.read(7777) is None


def test_current_app_dir_is_engine_root() -> None:
    """current_app_dir() resolves to the engine dir that contains src/stockroom."""
    app_dir = dash_identity.current_app_dir()
    assert (app_dir / "src" / "stockroom" / "__init__.py").is_file()
    assert Path(stockroom.__file__).resolve().is_relative_to(app_dir)
