"""Recover a real workspace path from a harness's lossy project-dir slug.

Both harnesses file conversations under an **encoded project-dir slug** in which
every non-alphanumeric character of the real path collapses to ``-`` (path
separators *and* ``.``, ``_``, etc.). That encoding is many-to-one, so it cannot
be inverted by any string transform — a naive ``"-" -> "/"`` decode fabricates
paths that never existed (``lite-rpg`` -> ``lite/rpg``).

The fix is to stop inverting and start **verifying**: we cannot invert
``encode``, but we can compute it forward, so a candidate real path is accepted
as ``cwd`` only when ``encode_for(harness, candidate) == slug``. This is exact —
a candidate that re-encodes to the slug *is* the path the slug was made from —
so the false-decode rate is zero by construction and the failure mode is a clean
``None`` (an honest "unknown"), never a fabricated path.

Candidates come from sources that survive directory deletion (the stored
transcript text for Cursor; the authoritative record ``cwd`` for Claude), so
recovery does **not** consult the live filesystem and stays deterministic.

The transform was locked empirically against the operator's real history (see
``planning/spikes/cwd-recovery/``): across 84 real slugs the only
non-alphanumeric character is ``-``, and Claude's ``encode(record_cwd)`` equals
its dir name on every probeable case. Cursor strips the leading separator (its
slugs start with a word, e.g. ``home-…``); Claude keeps it (e.g. ``-home-…``).
"""

import re
from collections.abc import Iterable, Iterator
from pathlib import PurePosixPath

#: Matches a POSIX absolute path token in free text: a leading ``/`` followed by
#: path-ish characters (letters, digits, ``/``, ``.``, ``_``, ``-``). Stops at
#: whitespace, quotes, and other delimiters, so a path embedded in JSON or prose
#: is captured without its surrounding punctuation.
_ABS_PATH = re.compile(r"/[A-Za-z0-9._/-]+")

#: Every character the harness does not preserve in a slug collapses to this.
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")


def encode(path: str) -> str:
    """Collapse every non-alphanumeric character of ``path`` to ``-``.

    The canonical, harness-neutral half of the transform (a leading separator
    therefore becomes a leading ``-``). Idempotent on ``-`` and deterministic.
    """
    return _NON_ALNUM.sub("-", path)


def encode_for(harness: str, path: str) -> str:
    """Encode ``path`` to the slug the given harness would file it under.

    Cursor drops the leading path separator before encoding (its slugs begin
    with a word); Claude keeps it (its slugs begin with a ``-``). Every other
    harness defaults to the Claude-style leading-separator-preserving form.
    """
    if harness == "cursor" and path.startswith("/"):
        path = path[1:]
    return encode(path)


def _abs_paths_in(texts: Iterable[str]) -> Iterator[str]:
    """Yield every POSIX absolute-path token found across ``texts`` in order."""
    for text in texts:
        if not isinstance(text, str):
            continue
        yield from _ABS_PATH.findall(text)


def _ancestors(path: str) -> Iterator[str]:
    """Yield ``path`` then each of its ancestors, deepest first, down to ``/``."""
    pure = PurePosixPath(path)
    yield str(pure)
    for parent in pure.parents:
        yield str(parent)


def resolve_cwd(
    harness: str,
    slug: str,
    *,
    record_cwd: str | None = None,
    texts: Iterable[str] = (),
) -> str | None:
    """Best-effort recover the real project-root path for an encoded ``slug``.

    Returns ``record_cwd`` directly when present (Claude's authoritative,
    deletion-proof path). Otherwise scans ``texts`` for in-band absolute paths
    and returns the first ancestor of any candidate whose
    ``encode_for(harness, ancestor)`` equals ``slug`` — verification, not
    guessing. Returns ``None`` when no candidate re-encodes to the slug (an
    honest unknown; never a fabricated path). Never touches the filesystem.
    """
    if record_cwd:
        return record_cwd
    for candidate in _abs_paths_in(texts):
        for ancestor in _ancestors(candidate):
            if encode_for(harness, ancestor) == slug:
                return ancestor
    return None
