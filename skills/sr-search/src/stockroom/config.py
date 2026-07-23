"""Read-only load of permanent stockroom settings from XDG config home.

Settings live at ``$XDG_CONFIG_HOME/stockroom/config.toml`` (default
``~/.config/stockroom/config.toml``), distinct from the data warehouse home
under ``STOCKROOM_HOME`` / XDG data home. Missing or malformed files yield
empty settings — never raise — so ingest can fail soft. A present but
unparseable file also logs a warning.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stockroom.home import resolve_config_home

#: Filename under config home for permanent settings.
CONFIG_FILENAME = "config.toml"

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Loaded permanent settings (empty fields when unset / unloadable)."""

    cursor_ai_tracking_dbs: tuple[Path, ...] = ()


def _ai_tracking_dbs_from_table(data: dict[str, Any]) -> tuple[Path, ...]:
    """Extract ``[cursor].ai_tracking_dbs`` string paths; skip invalid entries."""
    cursor = data.get("cursor")
    if not isinstance(cursor, dict):
        return ()
    raw = cursor.get("ai_tracking_dbs")
    if not isinstance(raw, list):
        return ()
    paths: list[Path] = []
    for item in raw:
        if isinstance(item, str) and item:
            paths.append(Path(item).expanduser())
    return tuple(paths)


def load_settings(config_home: Path | None = None) -> Settings:
    """Load ``config.toml`` from config home; empty on missing/malformed.

    When ``config_home`` is ``None``, resolves via
    :func:`stockroom.home.resolve_config_home`. Reads only
    ``[cursor].ai_tracking_dbs`` in v1. Never raises for I/O or TOML errors.
    """
    if config_home is None:
        config_home, _source = resolve_config_home()
    path = Path(config_home) / CONFIG_FILENAME
    try:
        raw = path.read_bytes()
    except OSError:
        return Settings()
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        _LOG.warning("stockroom config.toml parse failed (%s): %s", path, exc)
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    return Settings(cursor_ai_tracking_dbs=_ai_tracking_dbs_from_table(data))
