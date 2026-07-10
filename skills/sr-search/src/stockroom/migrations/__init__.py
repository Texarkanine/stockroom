"""Packaged SQL migrations for the stockroom warehouse.

This package ships the migration ``.sql`` files so they resolve with the
installed ``stockroom`` package (located via this package's directory). The
files are plain SQL executed by the migration runner (``stockroom.migrate``).

The only runtime behavior here is *discovery*: enumerating the packaged
``NNNN_<slug>.sql`` files into an ascending, version-ordered list. Discovery
is deliberately DB-free — it touches the filesystem, never a connection — so
the runner can compute "what migrations exist" independently of "which have
been applied".
"""

import re
from pathlib import Path
from typing import NamedTuple

#: A migration filename is ``NNNN_<slug>.sql``: a leading run of digits (the
#: version), an underscore, a non-empty slug, then the ``.sql`` suffix. Names
#: that do not match (``README.md``, ``0003.sql`` with no slug, ``draft_x.sql``
#: with no number) are not migrations and are ignored by discovery.
_MIGRATION_FILENAME = re.compile(r"^(\d+)_.+\.sql$")


class Migration(NamedTuple):
    """A discovered migration: its integer ``version`` and SQL file ``path``.

    A ``NamedTuple`` so a ``Migration`` compares equal to the plain
    ``(version, path)`` tuple — convenient in tests and callers that only
    care about the pair.
    """

    version: int
    path: Path


def migrations_dir() -> Path:
    """Return the directory that ships the packaged migration SQL files.

    This is the directory of this very package, so it resolves through the
    installed/located ``stockroom`` package rather than any repo-relative
    guess — the same resolution the ``schema_sql_path`` test fixture uses.
    """
    return Path(__file__).parent


def discover(directory: Path | None = None) -> list[Migration]:
    """Discover ``NNNN_<slug>.sql`` migrations, ascending by integer version.

    Scans ``directory`` (defaulting to :func:`migrations_dir`) for files whose
    names match the migration convention, parses the leading digits into an
    integer version, and returns them sorted by that version. Ordering is
    numeric, never lexical, so ``0010_*`` correctly follows ``0002_*``.
    Non-conforming filenames are silently ignored.
    """
    base = migrations_dir() if directory is None else directory
    migrations: list[Migration] = []
    for entry in base.iterdir():
        if not entry.is_file():
            continue
        match = _MIGRATION_FILENAME.match(entry.name)
        if match is None:
            continue
        migrations.append(Migration(int(match.group(1)), entry))
    migrations.sort(key=lambda m: m.version)
    return migrations
