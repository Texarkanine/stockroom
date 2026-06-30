"""Unit tests for the shared ``stockroom.render`` presentation chokepoint.

Covers all three output shapes (``tsv`` / ``json`` / ``table``) for both
``format_query`` and ``format_semantic``, plus the orthogonal ``--detail``
truncation behaving uniformly across formats. The ``table`` cases are the
relocated former ``query._format_table`` / ``semantic._format_hits`` behaviors.
Pure renderers, exercised against literals (no DB, no torch).
"""

import json

from stockroom import render
from stockroom.semantic import SemanticHit
from stockroom.truncate import ELISION


def _hit(
    text: str,
    *,
    rank: int = 1,
    distance: float = 0.0,
    harness: str = "claude",
    session_id: str = "s1",
    message_id: str = "s1#0",
    role: str = "user",
) -> SemanticHit:
    """Build one ``SemanticHit`` with sensible defaults for render tests."""
    return SemanticHit(
        rank=rank,
        distance=distance,
        harness=harness,
        session_id=session_id,
        message_id=message_id,
        role=role,
        text=text,
    )


# --- defaults ---------------------------------------------------------------


def test_default_format_is_tsv() -> None:
    """The module default output shape is ``tsv``."""
    assert render.DEFAULT_FORMAT == "tsv"


def test_query_defaults_to_tsv() -> None:
    """``format_query`` with no ``fmt`` renders identically to explicit ``tsv``."""
    assert render.format_query(["a"], [("1",)]) == render.format_query(
        ["a"], [("1",)], fmt="tsv"
    )


def test_semantic_defaults_to_tsv() -> None:
    """``format_semantic`` with no ``fmt`` renders identically to explicit ``tsv``."""
    assert render.format_semantic([_hit("hello")]) == render.format_semantic(
        [_hit("hello")], fmt="tsv"
    )


# --- format_query: tsv ------------------------------------------------------


def test_query_tsv_header_and_rows() -> None:
    """tsv is a header line + one tab-separated record line, no trailer/pipes."""
    out = render.format_query(["a", "b"], [("1", "2")], fmt="tsv")
    assert out.splitlines() == ["a\tb", "1\t2"]
    assert " | " not in out


def test_query_tsv_empty_is_header_only() -> None:
    """An empty result renders the header line alone — no row-count trailer."""
    out = render.format_query(["n"], [], fmt="tsv")
    assert out.splitlines() == ["n"]


def test_query_tsv_truncates_wide_cell_by_default() -> None:
    """A wide cell is elided at the default (snippet) detail; full value absent."""
    out = render.format_query(["c"], [("x" * 600,)], fmt="tsv")
    assert ELISION in out
    assert "x" * 600 not in out


def test_query_tsv_full_detail_keeps_whole_cell() -> None:
    """``detail="full"`` keeps the whole cell, no elision marker."""
    out = render.format_query(["c"], [("x" * 600,)], fmt="tsv", detail="full")
    assert "x" * 600 in out
    assert ELISION not in out


# --- format_query: json -----------------------------------------------------


def test_query_json_shape() -> None:
    """json query output is a ``{"columns", "rows"}`` object of stringified cells."""
    parsed = json.loads(render.format_query(["a", "b"], [("1", "2")], fmt="json"))
    assert parsed == {"columns": ["a", "b"], "rows": [["1", "2"]]}


def test_query_json_empty_rows() -> None:
    """An empty result is a valid object with an empty ``rows`` list."""
    parsed = json.loads(render.format_query(["n"], [], fmt="json"))
    assert parsed == {"columns": ["n"], "rows": []}


def test_query_json_none_is_native_null() -> None:
    """A SQL ``NULL`` cell serializes to JSON ``null`` (not the string ``"NULL"``)."""
    parsed = json.loads(render.format_query(["c"], [(None,)], fmt="json"))
    assert parsed["rows"] == [[None]]


def test_query_json_truncates_by_default() -> None:
    """A wide string cell is elided at default detail in json too."""
    parsed = json.loads(render.format_query(["c"], [("x" * 600,)], fmt="json"))
    cell = parsed["rows"][0][0]
    assert ELISION in cell
    assert cell != "x" * 600


def test_query_json_full_detail_keeps_whole_cell() -> None:
    """``detail="full"`` keeps the whole cell value in json."""
    parsed = json.loads(
        render.format_query(["c"], [("x" * 600,)], fmt="json", detail="full")
    )
    assert parsed["rows"][0][0] == "x" * 600


# --- format_query: table (relocated _format_table behaviors) ----------------


def test_query_table_renders_header_and_row() -> None:
    """A single-row table shows the column, the value, and a ``(1 row)`` trailer."""
    out = render.format_query(["n"], [(1,)], fmt="table")
    assert "n" in out
    assert "1" in out
    assert out.rstrip().endswith("(1 row)")


def test_query_table_empty_keeps_header_and_zero_trailer() -> None:
    """An empty table still names its column and ends with ``(0 rows)``."""
    out = render.format_query(["n"], [], fmt="table")
    assert "n" in out
    assert out.rstrip().endswith("(0 rows)")


def test_query_table_row_count_trailer_pluralizes() -> None:
    """The table trailer pluralizes: ``(2 rows)`` for a two-row result."""
    out = render.format_query(["n"], [(1,), (2,)], fmt="table")
    assert out.rstrip().endswith("(2 rows)")


def test_query_table_renders_none_as_null() -> None:
    """A ``None`` cell renders as the literal ``NULL`` in the table."""
    out = render.format_query(["c"], [(None,)], fmt="table")
    assert "NULL" in out


def test_query_table_truncates_wide_cell_by_default() -> None:
    """A wide table cell is elided at default detail; full value absent."""
    out = render.format_query(["c"], [("x" * 600,)], fmt="table")
    assert ELISION in out
    assert "x" * 600 not in out


def test_query_table_full_detail_keeps_whole_cell() -> None:
    """``detail="full"`` renders the entire table cell — no marker, full value."""
    out = render.format_query(["c"], [("x" * 600,)], fmt="table", detail="full")
    assert "x" * 600 in out
    assert ELISION not in out


# --- format_semantic: tsv ---------------------------------------------------


def test_semantic_tsv_header_and_no_trailer() -> None:
    """tsv semantic output leads with the tab-separated header, no result trailer."""
    out = render.format_semantic([_hit("hello")], fmt="tsv")
    assert out.splitlines()[0] == "rank\tscore\tharness\trole\tpreview"
    assert "(1 result)" not in out
    assert " | " not in out


def test_semantic_tsv_score_is_similarity() -> None:
    """``score`` is ``1 - distance`` (a zero-distance hit scores ``1.000``)."""
    out = render.format_semantic([_hit("hello", distance=0.0)], fmt="tsv")
    assert "1.000" in out


def test_semantic_tsv_truncates_long_text() -> None:
    """A long ``text`` preview is elided at default detail in tsv."""
    out = render.format_semantic([_hit("z" * 600)], fmt="tsv")
    assert ELISION in out
    assert "z" * 600 not in out


def test_semantic_tsv_full_detail_keeps_whole_text() -> None:
    """``detail="full"`` keeps the whole preview text in tsv."""
    out = render.format_semantic([_hit("z" * 600)], fmt="tsv", detail="full")
    assert "z" * 600 in out


# --- format_semantic: json --------------------------------------------------


def test_semantic_json_shape() -> None:
    """json semantic output is ``{"results": [...]}`` with the identifying fields."""
    parsed = json.loads(
        render.format_semantic(
            [
                _hit(
                    "hello",
                    distance=0.0,
                    harness="cursor",
                    session_id="s9",
                    message_id="s9#3",
                    role="assistant",
                )
            ],
            fmt="json",
        )
    )
    assert list(parsed.keys()) == ["results"]
    [item] = parsed["results"]
    assert item["rank"] == 1
    assert item["score"] == 1.0
    assert item["harness"] == "cursor"
    assert item["session_id"] == "s9"
    assert item["message_id"] == "s9#3"
    assert item["role"] == "assistant"
    assert item["text"] == "hello"


def test_semantic_json_empty_results() -> None:
    """No hits renders a valid object with an empty ``results`` list."""
    parsed = json.loads(render.format_semantic([], fmt="json"))
    assert parsed == {"results": []}


def test_semantic_json_score_is_a_number() -> None:
    """``score`` is a JSON number (``1 - distance``), not a string."""
    parsed = json.loads(render.format_semantic([_hit("hi", distance=0.25)], fmt="json"))
    score = parsed["results"][0]["score"]
    assert score == 0.75
    assert isinstance(score, float)


def test_semantic_json_text_truncated_by_default() -> None:
    """The ``text`` field is elided at default detail in json."""
    parsed = json.loads(render.format_semantic([_hit("z" * 600)], fmt="json"))
    assert ELISION in parsed["results"][0]["text"]


def test_semantic_json_full_detail_keeps_whole_text() -> None:
    """``detail="full"`` keeps the whole ``text`` in json."""
    parsed = json.loads(
        render.format_semantic([_hit("z" * 600)], fmt="json", detail="full")
    )
    assert parsed["results"][0]["text"] == "z" * 600


# --- format_semantic: table (relocated _format_hits behaviors) --------------


def test_semantic_table_shows_similarity_score() -> None:
    """The table reports a similarity ``score`` = ``1 - distance``."""
    out = render.format_semantic([_hit("hello", distance=0.0)], fmt="table")
    assert "score" in out.lower()
    assert "1.0" in out


def test_semantic_table_previews_text_single_line() -> None:
    """A long, multi-line ``text`` is previewed truncated onto a single line."""
    out = render.format_semantic(
        [_hit("first line\nsecond line " + "z" * 500, distance=0.1)], fmt="table"
    )
    assert "first line second line" in out
    assert "z" * 500 not in out


def test_semantic_table_full_detail_keeps_whole_text() -> None:
    """``detail="full"`` renders the entire message text (no elision marker)."""
    out = render.format_semantic(
        [_hit("z" * 500, distance=0.1)], fmt="table", detail="full"
    )
    assert "z" * 500 in out
    assert ELISION not in out


def test_semantic_table_empty_is_zero_results() -> None:
    """No hits renders a ``(0 results)`` trailer rather than an empty string."""
    assert "0 results" in render.format_semantic([], fmt="table")
