"""Harness-neutral stockroom home path resolution (XDG / STOCKROOM_HOME).

Dep-light on purpose: heal imports (``shim`` → ``engine_env`` →
``torch_source``) must resolve stockroom home without pulling DuckDB. The
warehouse module re-exports these names for existing callers.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Env var that overrides the warehouse home.
HOME_ENV_VAR = "STOCKROOM_HOME"

#: Freedesktop XDG data-home env var; when set (and ``STOCKROOM_HOME`` is not),
#: the warehouse lives at ``$XDG_DATA_HOME/stockroom``.
XDG_DATA_HOME_ENV_VAR = "XDG_DATA_HOME"

#: Labels returned by :func:`resolve_home` describing how the home was chosen.
HOME_SOURCE_OVERRIDE = "STOCKROOM_HOME"
HOME_SOURCE_XDG = "XDG_DATA_HOME"
HOME_SOURCE_DEFAULT = "default"


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
