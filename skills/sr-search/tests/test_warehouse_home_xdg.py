"""XDG / STOCKROOM_HOME path resolution for the warehouse home.

Pins ``resolve_home()`` (pure; no mkdir) and ``home_dir()`` (resolve + mkdir)
against the three selection sources: explicit ``STOCKROOM_HOME``, set
``XDG_DATA_HOME``, and the Freedesktop default under ``~/.local/share``.
"""

from pathlib import Path

import pytest

from stockroom import warehouse


def test_resolve_home_prefers_stockroom_home_over_xdg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``STOCKROOM_HOME`` wins even when ``XDG_DATA_HOME`` is also set."""
    override = tmp_path / "override-home"
    xdg = tmp_path / "xdg-data"
    monkeypatch.setenv(warehouse.HOME_ENV_VAR, str(override))
    monkeypatch.setenv(warehouse.XDG_DATA_HOME_ENV_VAR, str(xdg))
    path, source = warehouse.resolve_home()
    assert path == override
    assert source == warehouse.HOME_SOURCE_OVERRIDE


def test_resolve_home_uses_xdg_data_home_when_override_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unset override + set ``XDG_DATA_HOME`` → ``$XDG_DATA_HOME/stockroom``."""
    xdg = tmp_path / "xdg-data"
    monkeypatch.delenv(warehouse.HOME_ENV_VAR, raising=False)
    monkeypatch.setenv(warehouse.XDG_DATA_HOME_ENV_VAR, str(xdg))
    path, source = warehouse.resolve_home()
    assert path == xdg / "stockroom"
    assert source == warehouse.HOME_SOURCE_XDG


def test_resolve_home_defaults_under_local_share_when_xdg_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unset override and unset ``XDG_DATA_HOME`` → ``~/.local/share/stockroom``."""
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    monkeypatch.delenv(warehouse.HOME_ENV_VAR, raising=False)
    monkeypatch.delenv(warehouse.XDG_DATA_HOME_ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    path, source = warehouse.resolve_home()
    assert path == fake_home / ".local" / "share" / "stockroom"
    assert source == warehouse.HOME_SOURCE_DEFAULT


def test_resolve_home_does_not_create_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``resolve_home`` is pure: it reports the path without creating it."""
    xdg = tmp_path / "xdg-data"
    target = xdg / "stockroom"
    monkeypatch.delenv(warehouse.HOME_ENV_VAR, raising=False)
    monkeypatch.setenv(warehouse.XDG_DATA_HOME_ENV_VAR, str(xdg))
    path, _source = warehouse.resolve_home()
    assert path == target
    assert not target.exists()
    assert not xdg.exists()


def test_home_dir_creates_resolved_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``home_dir`` creates the chosen home (parents included) on first call."""
    xdg = tmp_path / "xdg-data"
    target = xdg / "stockroom"
    monkeypatch.delenv(warehouse.HOME_ENV_VAR, raising=False)
    monkeypatch.setenv(warehouse.XDG_DATA_HOME_ENV_VAR, str(xdg))
    assert not target.exists()
    resolved = warehouse.home_dir()
    assert resolved == target
    assert resolved.is_dir()


def test_warehouse_and_lock_paths_live_under_resolved_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``warehouse_path`` / ``lock_path`` nest under the resolved home."""
    xdg = tmp_path / "xdg-data"
    home = xdg / "stockroom"
    monkeypatch.delenv(warehouse.HOME_ENV_VAR, raising=False)
    monkeypatch.setenv(warehouse.XDG_DATA_HOME_ENV_VAR, str(xdg))
    assert warehouse.home_dir() == home
    assert warehouse.warehouse_path() == home / warehouse.WAREHOUSE_FILENAME
    assert warehouse.lock_path() == home / warehouse.LOCK_FILENAME
