"""Shared read-time output truncation for the warehouse read surfaces.

The Phase-2 milestone-3 mechanism: a single, tested helper that bounds a wide
output cell to a context-safe width with a **visible, informative elision
marker**, selectable via discrete detail levels. It is consumed by the shared
:mod:`stockroom.render` presentation chokepoint (which renders both read surfaces'
output in every ``--format``) so the two surfaces share one truncation policy
rather than each rolling their own.

Truncation is strictly a **read-time** concern — it shapes *rendered* output only.
Full content always stays whole at rest (in the warehouse) and in the returned
data objects (``QueryResult.rows``, ``SemanticHit.text``); the no-truncation-at-rest
invariant is never touched here.

Detail levels (``compact | snippet | full | raw``) select a per-cell character
budget via :data:`LEVEL_WIDTHS`. ``full`` is the unbounded single-line escape
(table/TSV-safe). ``raw`` is the unbounded **exact-whitespace** escape — newlines
and other internal whitespace match storage. When a cell exceeds its budget, the
kept content (exactly the level's width in characters) is followed by a marker
that reports how many characters were hidden — e.g. ``…(+482)`` — so a downstream
LLM surface can tell that content was elided, and roughly how much, and decide
whether to re-fetch at ``--detail full`` / ``--detail raw`` or narrow its query.
Non-``raw`` levels always collapse to a single line so column-aligned table
rendering stays intact; multi-line fidelity is ``raw`` (prefer ``--format json``).
"""

from typing import Literal

#: A selectable read-time truncation level. ``full`` and ``raw`` are unbounded;
#: ``raw`` additionally preserves internal whitespace.
DetailLevel = Literal["compact", "snippet", "full", "raw"]

#: Ordered ``--detail`` choices for the CLIs (terse → verbose). The first entry is
#: not the default — :data:`DEFAULT_DETAIL` is — this is just the option list.
DETAIL_LEVELS: tuple[str, ...] = ("compact", "snippet", "full", "raw")

#: Per-level cell character budget. ``None`` means unbounded (no truncation).
#: Tunable: these are the starting widths, not a contract.
LEVEL_WIDTHS: dict[str, int | None] = {
    "compact": 40,
    "snippet": 120,
    "full": None,
    "raw": None,
}

#: On-by-default posture: the context-safe middle level, with ``full`` one flag away.
DEFAULT_DETAIL: DetailLevel = "snippet"

#: The glyph that opens the elision marker; the marker itself reports the hidden
#: character count, e.g. ``…(+482)``.
ELISION = "…"


def truncate_cell(value: str, detail: DetailLevel = DEFAULT_DETAIL) -> str:
    """Bound ``value`` to ``detail``'s width, optionally collapsing whitespace.

    For every level except ``raw``, internal whitespace runs (including newlines)
    are collapsed to single spaces so the result is one physical line
    (table/TSV-rendering requirement). ``raw`` skips that collapse and returns
    the value with whitespace matching storage. The (possibly single-lined)
    result is then bounded to the level's width from :data:`LEVEL_WIDTHS`:

    * ``full`` / ``raw`` (width ``None``) or a result already within budget →
      returned as-is (no marker).
    * Over budget → the first ``width`` characters of content, followed by the
      hidden-count marker ``f"{ELISION}(+{hidden})"`` where ``hidden`` is the
      number of characters dropped. The marker is appended **beyond** the width,
      so a truncated cell's rendered width is ``width`` plus the short marker.
    """
    text = value if detail == "raw" else " ".join(value.split())
    width = LEVEL_WIDTHS[detail]
    if width is None or len(text) <= width:
        return text
    hidden = len(text) - width
    return f"{text[:width]}{ELISION}(+{hidden})"
