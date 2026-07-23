"""Harness-neutral stockroom home path resolution (XDG / STOCKROOM_HOME).

Stdlib-only on purpose: heal imports (``shim`` → ``engine_env`` →
``torch_source``) must resolve stockroom home on a bare ``uv python find``
interpreter with no project site-packages — any third-party import
dies before ``ensure_engine_env`` can sync.
The warehouse module re-exports these names for existing callers.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Env var that overrides the warehouse home.
HOME_ENV_VAR = "STOCKROOM_HOME"

#: Freedesktop XDG data-home env var; when set (and ``STOCKROOM_HOME`` is not),
#: the warehouse lives at ``$XDG_DATA_HOME/stockroom``.
XDG_DATA_HOME_ENV_VAR = "XDG_DATA_HOME"

#: Freedesktop XDG config-home env var; when set, permanent settings live at
#: ``$XDG_CONFIG_HOME/stockroom`` (distinct from data ``STOCKROOM_HOME``).
XDG_CONFIG_HOME_ENV_VAR = "XDG_CONFIG_HOME"

#: Labels returned by :func:`resolve_home` describing how the home was chosen.
HOME_SOURCE_OVERRIDE = "STOCKROOM_HOME"
HOME_SOURCE_XDG = "XDG_DATA_HOME"
HOME_SOURCE_DEFAULT = "default"

#: Labels returned by :func:`resolve_config_home` describing how config home
#: was chosen.
CONFIG_HOME_SOURCE_XDG = "XDG_CONFIG_HOME"
CONFIG_HOME_SOURCE_DEFAULT = "default"


def resolve_home() -> tuple[Path, str]:
    """Return ``(home_path, source)`` without creating directories.

    Selection order:

    1. ``STOCKROOM_HOME`` when set → source ``STOCKROOM_HOME``
    2. ``$XDG_DATA_HOME/stockroom`` when ``XDG_DATA_HOME`` is set →
       source ``XDG_DATA_HOME``
    3. ``~/.local/share/stockroom`` otherwise → source ``default``

    Pure: never mkdir. Prefer this for diagnostics (``doctor probe``); use
    :func:`home_dir` when the directory must exist.
    """
    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override), HOME_SOURCE_OVERRIDE
    xdg = os.environ.get(XDG_DATA_HOME_ENV_VAR)
    if xdg:
        return Path(xdg) / "stockroom", HOME_SOURCE_XDG
    return Path.home() / ".local" / "share" / "stockroom", HOME_SOURCE_DEFAULT


def home_dir() -> Path:
    """Return the warehouse home directory, creating it if absent.

    Resolves via :func:`resolve_home`, then creates the path (with parents)
    so callers can rely on it existing.
    """
    base, _source = resolve_home()
    base.mkdir(parents=True, exist_ok=True)
    return base


def resolve_config_home() -> tuple[Path, str]:
    """Return ``(config_home_path, source)`` without creating directories.

    Selection order:

    1. ``$XDG_CONFIG_HOME/stockroom`` when ``XDG_CONFIG_HOME`` is set →
       source ``XDG_CONFIG_HOME``
    2. ``~/.config/stockroom`` otherwise → source ``default``

    Pure: never mkdir. Distinct from data :func:`resolve_home` /
    ``STOCKROOM_HOME``.
    """
    xdg = os.environ.get(XDG_CONFIG_HOME_ENV_VAR)
    if xdg:
        return Path(xdg) / "stockroom", CONFIG_HOME_SOURCE_XDG
    return Path.home() / ".config" / "stockroom", CONFIG_HOME_SOURCE_DEFAULT
