"""Shared pytest fixtures for the stockroom engine test suite.

The engine lives inside ``skills/sr-search/`` but several tests
(packaging, licensing) assert against repo-root artifacts. The
``repo_root`` fixture lets those tests reach the root without brittle
relative-path arithmetic.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the repository root: the nearest ancestor containing ``.git``.

    Walks up from this file until it finds a directory holding a ``.git``
    entry (directory or file, to support worktrees/submodules). Raises if
    no such ancestor exists, which would mean the tests are running outside
    the repository.
    """
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("Could not locate repository root (no .git ancestor found)")
