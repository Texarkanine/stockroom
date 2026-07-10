"""Durable identity record for the machine-scoped dashboard listener.

The session/workspace start hook launches ``stockroom dashboard`` after shim
rectify. A detached child may outlive a plugin-root move; this module records
which engine owns the listener under stockroom home so the launcher can
replace a stale owned process without killing foreign listeners.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import stockroom
from stockroom.warehouse import home_dir

#: Filename prefix under stockroom home; full name is ``dashboard-{port}.identity``.
IDENTITY_PREFIX = "dashboard-"
IDENTITY_SUFFIX = ".identity"


@dataclass(frozen=True)
class DashboardIdentity:
    """Recorded owner of a dashboard listener on a given port."""

    pid: int
    app_dir: Path
    version: str
    port: int


def path(port: int) -> Path:
    """Return the identity file path for ``port`` (may not exist yet)."""
    return home_dir() / f"{IDENTITY_PREFIX}{port}{IDENTITY_SUFFIX}"


def read(port: int) -> DashboardIdentity | None:
    """Return the stored identity for ``port``, or ``None`` if absent/invalid."""
    try:
        text = path(port).read_text(encoding="utf-8")
    except OSError:
        return None
    return _parse(text, expected_port=port)


def write(identity: DashboardIdentity) -> Path:
    """Atomically persist ``identity`` for its port; return the file path."""
    dest = path(identity.port)
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"pid={identity.pid}\n"
        f"app_dir={identity.app_dir.resolve()}\n"
        f"version={identity.version}\n"
        f"port={identity.port}\n"
    )
    fd, tmp_name = tempfile.mkstemp(
        dir=dest.parent,
        prefix=".dashboard-identity-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, dest)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return dest


def clear(port: int) -> None:
    """Remove the identity file for ``port`` if it exists."""
    try:
        path(port).unlink()
    except FileNotFoundError:
        return


def current_app_dir() -> Path:
    """Return the absolute engine app dir for this running stockroom package.

    Layout is ``{app_dir}/src/stockroom/__init__.py``.
    """
    return Path(stockroom.__file__).resolve().parents[2]


def _parse(text: str, *, expected_port: int) -> DashboardIdentity | None:
    """Parse identity file body; return None when required fields are missing."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        fields[key.strip()] = value.strip()
    try:
        pid = int(fields["pid"])
        port = int(fields["port"])
        version = fields["version"]
        app_dir = Path(fields["app_dir"])
    except (KeyError, ValueError):
        return None
    if not version or port != expected_port:
        return None
    return DashboardIdentity(pid=pid, app_dir=app_dir, version=version, port=port)
