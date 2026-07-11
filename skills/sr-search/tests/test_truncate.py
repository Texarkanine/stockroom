"""Unit tests for the shared read-time truncation mechanism (``stockroom.truncate``).

A pure, torch-free, DB-free helper, so every case runs against plain string
literals. Covers the single-line collapse, the per-level width budget, the
unbounded ``full`` escape, and the informative hidden-count elision marker.
"""

from stockroom.truncate import (
    DEFAULT_DETAIL,
    DETAIL_LEVELS,
    ELISION,
    LEVEL_WIDTHS,
    truncate_cell,
)

# --- module constants -------------------------------------------------------


def test_level_widths_keys_match_detail_levels() -> None:
    """Every advertised ``--detail`` choice has a configured width and vice versa."""
    assert set(LEVEL_WIDTHS) == set(DETAIL_LEVELS)


def test_default_detail_is_snippet() -> None:
    """The on-by-default posture is the context-safe middle level."""
    assert DEFAULT_DETAIL == "snippet"


def test_full_is_unbounded() -> None:
    """``full`` carries no width budget — it is the unbounded escape."""
    assert LEVEL_WIDTHS["full"] is None


# --- truncate_cell ----------------------------------------------------------


def test_short_value_returned_unchanged() -> None:
    """A value within budget is returned verbatim (single-lined), with no marker."""
    assert truncate_cell("hi", "snippet") == "hi"
    assert ELISION not in truncate_cell("hi", "snippet")


def test_over_width_keeps_width_chars_then_marker() -> None:
    """An over-budget value keeps exactly ``width`` content chars, then the marker."""
    width = LEVEL_WIDTHS["snippet"]
    assert width is not None
    out = truncate_cell("x" * 602, "snippet")
    assert out.startswith("x" * width)
    assert "x" * 602 not in out  # the full run is not present
    assert ELISION in out


def test_hidden_count_is_accurate() -> None:
    """The marker reports exactly how many characters were dropped."""
    width = LEVEL_WIDTHS["snippet"]
    assert width is not None
    out = truncate_cell("x" * 602, "snippet")
    hidden = 602 - width
    assert out == "x" * width + f"{ELISION}(+{hidden})"


def test_full_level_never_truncates() -> None:
    """``full`` preserves the whole content length and adds no marker."""
    out = truncate_cell("x" * 5000, "full")
    assert out == "x" * 5000
    assert ELISION not in out


def test_collapses_whitespace_and_newlines_at_bounded_and_full() -> None:
    """Internal whitespace runs (incl. newlines) collapse for non-``raw`` levels."""
    for level in ("compact", "snippet", "full"):
        assert truncate_cell("a\n\nb  c", level) == "a b c"


def test_level_ordering_keeps_fewer_chars_for_terser_levels() -> None:
    """compact keeps fewer content chars than snippet; full is unbounded."""
    long = "z" * 1000
    compact_kept = LEVEL_WIDTHS["compact"]
    snippet_kept = LEVEL_WIDTHS["snippet"]
    assert compact_kept is not None and snippet_kept is not None
    assert compact_kept < snippet_kept
    # The marker reports a larger hidden count for the terser level.
    assert f"(+{1000 - compact_kept})" in truncate_cell(long, "compact")
    assert f"(+{1000 - snippet_kept})" in truncate_cell(long, "snippet")
    assert truncate_cell(long, "full") == long


def test_exact_width_boundary_not_truncated() -> None:
    """A value exactly the level width is unchanged; one char over is truncated."""
    width = LEVEL_WIDTHS["snippet"]
    assert width is not None
    assert truncate_cell("y" * width, "snippet") == "y" * width
    assert truncate_cell("y" * (width + 1), "snippet") == "y" * width + f"{ELISION}(+1)"


def test_empty_string() -> None:
    """An empty value renders as empty (no marker, no error)."""
    assert truncate_cell("", "snippet") == ""


def test_raw_preserves_whitespace() -> None:
    """``raw`` keeps newlines and multi-space runs exactly as stored."""
    assert truncate_cell("a\n\nb  c", "raw") == "a\n\nb  c"


def test_raw_is_unbounded() -> None:
    """``raw`` has no width budget and never adds an elision marker."""
    assert LEVEL_WIDTHS["raw"] is None
    out = truncate_cell("x" * 5000, "raw")
    assert out == "x" * 5000
    assert ELISION not in out
