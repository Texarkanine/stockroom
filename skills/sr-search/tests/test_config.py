"""Tests for XDG config-home resolution and ``config.toml`` settings load.

Permanent machine settings live under XDG config home (distinct from data
``STOCKROOM_HOME``). Missing or malformed files fail soft to empty settings.
"""

from pathlib import Path

import pytest

from stockroom import config, home


def test_resolve_config_home_uses_xdg_config_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When ``XDG_CONFIG_HOME`` is set, config home is ``$XDG_CONFIG_HOME/stockroom``."""
    xdg = tmp_path / "xdg-config"
    monkeypatch.setenv(home.XDG_CONFIG_HOME_ENV_VAR, str(xdg))
    path, source = home.resolve_config_home()
    assert path == xdg / "stockroom"
    assert source == home.CONFIG_HOME_SOURCE_XDG


def test_resolve_config_home_defaults_under_dot_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unset ``XDG_CONFIG_HOME`` → ``~/.config/stockroom``."""
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    monkeypatch.delenv(home.XDG_CONFIG_HOME_ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    path, source = home.resolve_config_home()
    assert path == fake_home / ".config" / "stockroom"
    assert source == home.CONFIG_HOME_SOURCE_DEFAULT


def test_resolve_config_home_does_not_create_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``resolve_config_home`` is pure: reports the path without creating it."""
    xdg = tmp_path / "xdg-config"
    target = xdg / "stockroom"
    monkeypatch.setenv(home.XDG_CONFIG_HOME_ENV_VAR, str(xdg))
    path, _source = home.resolve_config_home()
    assert path == target
    assert not target.exists()
    assert not xdg.exists()


def test_load_settings_missing_file_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing ``config.toml`` yields empty settings rather than raising."""
    config_home = tmp_path / "stockroom"
    monkeypatch.setenv(home.XDG_CONFIG_HOME_ENV_VAR, str(tmp_path))
    assert config.load_settings(config_home) == config.Settings()


def test_load_settings_reads_ai_tracking_dbs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Valid ``[cursor].ai_tracking_dbs`` strings become Paths on Settings."""
    config_home = tmp_path / "stockroom"
    config_home.mkdir()
    pin_a = tmp_path / "a" / "ai-code-tracking.db"
    pin_b = tmp_path / "b" / "ai-code-tracking.db"
    (config_home / "config.toml").write_text(
        "[cursor]\n"
        "ai_tracking_dbs = [\n"
        f'  "{pin_a.as_posix()}",\n'
        f'  "{pin_b.as_posix()}",\n'
        "]\n",
        encoding="utf-8",
    )
    settings = config.load_settings(config_home)
    assert settings.cursor_ai_tracking_dbs == (pin_a, pin_b)


def test_load_settings_malformed_toml_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Malformed TOML yields empty settings rather than raising."""
    config_home = tmp_path / "stockroom"
    config_home.mkdir()
    (config_home / "config.toml").write_text("[[[not valid", encoding="utf-8")
    assert config.load_settings(config_home) == config.Settings()


def test_load_settings_ignores_non_string_ai_tracking_entries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Non-string / empty ``ai_tracking_dbs`` entries are skipped."""
    config_home = tmp_path / "stockroom"
    config_home.mkdir()
    pin = tmp_path / "only.db"
    (config_home / "config.toml").write_text(
        f'[cursor]\nai_tracking_dbs = [\n  "{pin.as_posix()}",\n  "",\n  123,\n]\n',
        encoding="utf-8",
    )
    settings = config.load_settings(config_home)
    assert settings.cursor_ai_tracking_dbs == (pin,)


def test_settings_has_no_state_vscdb_field() -> None:
    """Settings exposes ``ai_tracking_dbs`` only — no aborted ``state_vscdb``."""
    assert not hasattr(config.Settings(), "cursor_state_vscdb")
    assert "cursor_state_vscdb" not in config.Settings.__dataclass_fields__
