"""Tests for XDG config-home resolution and ``config.toml`` settings load.

Permanent machine settings live under XDG config home (distinct from data
``STOCKROOM_HOME``). Missing or malformed files fail soft to empty settings.
"""

import logging
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


def test_load_settings_malformed_toml_logs_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A present but unparseable ``config.toml`` warns before fail-soft empty."""
    config_home = tmp_path / "stockroom"
    config_home.mkdir()
    (config_home / "config.toml").write_text("[[[not valid", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="stockroom.config"):
        assert config.load_settings(config_home) == config.Settings()
    assert any("config.toml" in r.getMessage() for r in caplog.records)


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


def _write_config(config_home: Path, body: str) -> None:
    """Materialize ``config.toml`` under a fresh ``config_home``."""
    config_home.mkdir(exist_ok=True)
    (config_home / "config.toml").write_text(body, encoding="utf-8")


def test_load_settings_reads_state_vscdb(tmp_path: Path) -> None:
    """A valid ``[cursor].state_vscdb`` string becomes a Path on Settings."""
    config_home = tmp_path / "stockroom"
    vscdb = tmp_path / "globalStorage" / "state.vscdb"
    _write_config(config_home, f'[cursor]\nstate_vscdb = "{vscdb.as_posix()}"\n')
    assert config.load_settings(config_home).cursor_state_vscdb == vscdb


def test_load_settings_expands_user_in_state_vscdb(tmp_path: Path) -> None:
    """``~`` in ``state_vscdb`` is expanded, matching the ai_tracking_dbs rule."""
    config_home = tmp_path / "stockroom"
    _write_config(config_home, '[cursor]\nstate_vscdb = "~/state.vscdb"\n')
    settings = config.load_settings(config_home)
    assert settings.cursor_state_vscdb == Path.home() / "state.vscdb"


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("non-string", "[cursor]\nstate_vscdb = 123\n"),
        ("empty string", '[cursor]\nstate_vscdb = ""\n'),
        ("absent key", '[cursor]\nai_tracking_dbs = ["/a.db"]\n'),
        ("absent cursor table", "[other]\nkey = 1\n"),
    ],
)
def test_load_settings_state_vscdb_is_none_when_unusable(
    tmp_path: Path, label: str, body: str
) -> None:
    """Non-string, empty, absent key, or absent ``[cursor]`` table → ``None``."""
    config_home = tmp_path / "stockroom"
    _write_config(config_home, body)
    assert config.load_settings(config_home).cursor_state_vscdb is None, label
