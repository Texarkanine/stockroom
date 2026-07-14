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

The transform was locked empirically against real harness history: across a
large sample of real slugs the only non-alphanumeric character is ``-``, and
Claude's ``encode(record_cwd)`` equals its dir name on every probeable case.
Cursor strips the leading separator (its slugs start with a word, e.g.
``home-…``); Claude keeps it (e.g. ``-home-…``).

``workspace_key_for`` is a separate, extensible per-harness ETL transform that
derives a nullable cross-harness rollup key from ``cwd`` (and optionally
``project_id``). Same absolute ``cwd`` must converge across registered harnesses;
unknown harness or missing inputs yield ``None``. See migration ``0006``.
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


def _key_from_cwd_leading_sep_stripped(
    *,
    cwd: str | None,
    project_id: str | None = None,
) -> str | None:
    """Private path helper: leading-separator-stripped encode of ``cwd``.

    Shared by today's Cursor and Claude strategies so same absolute ``cwd``
    converges; kept private so a third harness can diverge without stretching
    an untyped global munge. ``project_id`` is accepted for strategy signature
    parity and unused today.
    """
    _ = project_id
    if not cwd:
        return None
    path = cwd[1:] if cwd.startswith("/") else cwd
    return encode(path)


def _strategy_cursor(*, cwd: str | None, project_id: str | None) -> str | None:
    """Cursor workspace_key strategy: path encode of cwd with leading sep stripped."""
    return _key_from_cwd_leading_sep_stripped(cwd=cwd, project_id=project_id)


def _strategy_claude(*, cwd: str | None, project_id: str | None) -> str | None:
    """Claude workspace_key strategy: same cwd-derived key as Cursor (convergence)."""
    return _key_from_cwd_leading_sep_stripped(cwd=cwd, project_id=project_id)


#: Per-harness ETL transforms for ``workspace_key``. Add a harness = add a strategy.
_WORKSPACE_KEY_STRATEGIES = {
    "cursor": _strategy_cursor,
    "claude": _strategy_claude,
}


def workspace_key_for(
    harness: str,
    *,
    cwd: str | None = None,
    project_id: str | None = None,
) -> str | None:
    """Derive a cross-harness rollup key for sessions that share a workspace path.

    Each registered harness has its own strategy (extensible registry). The
    shared convergence contract is: same machine + same absolute ``cwd`` ⇒ same
    ``workspace_key`` when both sides can derive it. Returns ``None`` when the
    harness is unknown or the strategy cannot derive a key (typically missing
    ``cwd``). Does not mutate or replace harness-native ``project_id``.

    ``project_id`` is accepted for future harness strategies that may need it;
    today's Cursor/Claude strategies key only off ``cwd``.
    """
    strategy = _WORKSPACE_KEY_STRATEGIES.get(harness)
    if strategy is None:
        return None
    return strategy(cwd=cwd, project_id=project_id)


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
