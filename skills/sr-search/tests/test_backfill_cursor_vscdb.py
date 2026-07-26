"""Parser tests for the ``cursor-vscdb`` backfill adapter.

The adapter reconstructs warehouse sessions from Cursor's legacy
``globalStorage/state.vscdb`` — a store nightly ingest never reads. These tests
pin the three contracts the plan settled:

* **Read ladder (D1)** — ``mode=ro`` where it works, ``immutable=1`` where WAL
  locking is unsupported (the WSL→Windows mount), typed errors otherwise.
* **Message reconstruction (OQ1)** — one *storable* bubble becomes one message;
  thinking-only and empty bubbles are dropped; tool calls stay on their own
  bubble-message rather than being merged into the preceding turn.
* **Workspace identity (OQ2)** — ``project_id`` is the native ``workspaceId``,
  ``cwd`` comes from ``workspaceStorage/{id}/workspace.json``, and
  ``workspace_key`` is left to the writer.

Every fixture DB is synthesized in-test by the ``build_vscdb`` conftest factory
rather than committed as a binary, so each case's source shape is legible.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pytest

from stockroom.backfill import BackfillError, cursor_vscdb
from stockroom.ingest.model import NormalizedSession


def _parse_one(db_path: Path, composer_id: str) -> NormalizedSession | None:
    """Parse exactly one composer, or ``None`` when it reconstructs to nothing."""
    parsed = list(cursor_vscdb.parse_all(db_path, [composer_id]))
    assert len(parsed) <= 1, parsed
    return parsed[0] if parsed else None


def _composer(*bubble_ids: str, **fields) -> dict:
    """A ``composerData`` value whose header list references ``bubble_ids``.

    Types alternate user/assistant from ``type=1`` unless a case overrides the
    headers wholesale via ``fullConversationHeadersOnly``.
    """
    base = {
        "composerId": "c1",
        "fullConversationHeadersOnly": [
            {"bubbleId": bubble_id, "type": 1 if index % 2 == 0 else 2}
            for index, bubble_id in enumerate(bubble_ids)
        ],
    }
    base.update(fields)
    return base


def test_open_readonly_reads_a_normal_local_db(
    build_vscdb: Callable[..., Path],
) -> None:
    """A normal local SQLite file opens and reads (the ``mode=ro`` rung)."""
    db_path = build_vscdb(composers={"c1": _composer()})
    con = cursor_vscdb.open_readonly(db_path)
    try:
        count = con.execute("SELECT count(*) FROM cursorDiskKV").fetchone()[0]
    finally:
        con.close()
    assert count == 1


def test_open_readonly_falls_back_to_immutable_when_mode_ro_fails(
    build_vscdb: Callable[..., Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``mode=ro`` raises ``OperationalError``, ``immutable=1`` is tried.

    Stands in for the WSL→Windows mount, where WAL locking is unsupported and
    ``mode=ro`` fails with a disk I/O error while ``immutable=1`` succeeds.
    """
    db_path = build_vscdb(composers={"c1": _composer()})
    real_connect = sqlite3.connect
    attempted: list[str] = []

    def fake_connect(uri_string, *args, **kwargs):
        attempted.append(uri_string)
        if "mode=ro" in uri_string:
            raise sqlite3.OperationalError("disk I/O error")
        return real_connect(uri_string, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", fake_connect)
    con = cursor_vscdb.open_readonly(db_path)
    try:
        count = con.execute("SELECT count(*) FROM cursorDiskKV").fetchone()[0]
    finally:
        con.close()
    assert count == 1
    assert any("mode=ro" in attempt for attempt in attempted)
    assert any("immutable=1" in attempt for attempt in attempted)


def test_open_readonly_raises_backfill_error_for_non_sqlite_file(
    tmp_path: Path,
) -> None:
    """A non-SQLite file yields a typed ``BackfillError``, not a bare sqlite3 one."""
    junk = tmp_path / "state.vscdb"
    junk.write_text("this is not a database", encoding="utf-8")
    with pytest.raises(BackfillError) as excinfo:
        cursor_vscdb.open_readonly(junk)
    assert str(junk) in str(excinfo.value)


def test_open_readonly_raises_backfill_error_for_absent_file(tmp_path: Path) -> None:
    """An absent path yields a typed ``BackfillError`` naming the path."""
    missing = tmp_path / "nowhere" / "state.vscdb"
    with pytest.raises(BackfillError) as excinfo:
        cursor_vscdb.open_readonly(missing)
    assert str(missing) in str(excinfo.value)


def _clear_source_inputs(
    monkeypatch: pytest.MonkeyPatch, config_home: Path | None = None
) -> None:
    """Unset the env var and point config home at an empty (or given) dir."""
    monkeypatch.delenv(cursor_vscdb.STATE_VSCDB_ENV_VAR, raising=False)
    if config_home is not None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))


def test_resolve_source_prefers_the_explicit_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI flag wins over both the env var and the config key."""
    config_home = tmp_path / "xdg"
    (config_home / "stockroom").mkdir(parents=True)
    (config_home / "stockroom" / "config.toml").write_text(
        '[cursor]\nstate_vscdb = "/from/config.vscdb"\n', encoding="utf-8"
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv(cursor_vscdb.STATE_VSCDB_ENV_VAR, "/from/env.vscdb")

    override = tmp_path / "from-flag.vscdb"
    assert cursor_vscdb.resolve_source(override) == override


def test_resolve_source_falls_back_to_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without an override, ``STOCKROOM_CURSOR_STATE_VSCDB`` is used."""
    _clear_source_inputs(monkeypatch, tmp_path / "empty-xdg")
    monkeypatch.setenv(cursor_vscdb.STATE_VSCDB_ENV_VAR, "/from/env.vscdb")
    assert cursor_vscdb.resolve_source(None) == Path("/from/env.vscdb")


def test_resolve_source_falls_back_to_config_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without an override or env var, ``[cursor].state_vscdb`` is used."""
    config_home = tmp_path / "xdg"
    (config_home / "stockroom").mkdir(parents=True)
    (config_home / "stockroom" / "config.toml").write_text(
        '[cursor]\nstate_vscdb = "/from/config.vscdb"\n', encoding="utf-8"
    )
    _clear_source_inputs(monkeypatch, config_home)
    assert cursor_vscdb.resolve_source(None) == Path("/from/config.vscdb")


def test_resolve_source_error_names_flag_env_and_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unconfigured raises ``BackfillError`` naming all three inputs."""
    _clear_source_inputs(monkeypatch, tmp_path / "empty-xdg")
    with pytest.raises(BackfillError) as excinfo:
        cursor_vscdb.resolve_source(None)
    message = str(excinfo.value)
    assert cursor_vscdb.STATE_VSCDB_FLAG in message
    assert cursor_vscdb.STATE_VSCDB_ENV_VAR in message
    assert cursor_vscdb.STATE_VSCDB_CONFIG_KEY in message


def test_candidates_enumerates_composer_ids(build_vscdb: Callable[..., Path]) -> None:
    """``candidates`` lists every ``composerData:`` key's composer id."""
    db_path = build_vscdb(
        composers={"c1": _composer(), "c2": _composer(), "c3": _composer()},
        bubbles={"c1:b1": {"type": 1, "text": "hi"}},
    )
    assert sorted(cursor_vscdb.candidates(db_path)) == ["c1", "c2", "c3"]


def test_bubble_reads_use_an_index_range_not_a_scan(
    build_vscdb: Callable[..., Path],
) -> None:
    """Key reads use index range bounds (D2): the query plan is a SEARCH.

    ``LIKE 'prefix%'`` cannot use a SQLite index under the default
    case-insensitive setting; the measured cost on the live mount was 2.88 s
    per composer versus 0.05 s for range bounds. This pins the fast shape.
    """
    db_path = build_vscdb(composers={"c1": _composer()})
    low, high = cursor_vscdb._key_range("bubbleId:c1:")
    con = cursor_vscdb.open_readonly(db_path)
    try:
        plan = con.execute(
            f"EXPLAIN QUERY PLAN {cursor_vscdb._KV_RANGE_SQL}", (low, high)
        ).fetchall()
    finally:
        con.close()
    detail = " ".join(str(row[-1]) for row in plan)
    assert "SEARCH" in detail, detail
    assert "SCAN" not in detail, detail


# --- identity & structure ----------------------------------------------------


def test_parse_sets_session_identity_and_provenance(
    build_vscdb: Callable[..., Path],
) -> None:
    """A composer becomes a cursor/ide session keyed by its own composer id."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1")},
        bubbles={"c1:b1": {"type": 1, "text": "hi"}},
    )
    session = _parse_one(db_path, "c1")
    assert session.harness == "cursor"
    assert session.session_id == "c1"
    assert session.entrypoint == "ide"
    assert session.source_path == str(db_path)


def test_bubble_types_map_to_user_and_assistant_roles(
    build_vscdb: Callable[..., Path],
) -> None:
    """``type`` 1 is a user turn, 2 an assistant turn; anything else is skipped."""
    db_path = build_vscdb(
        composers={
            "c1": {
                "fullConversationHeadersOnly": [
                    {"bubbleId": "b1", "type": 1},
                    {"bubbleId": "b2", "type": 2},
                    {"bubbleId": "b3", "type": 7},
                ]
            }
        },
        bubbles={
            "c1:b1": {"type": 1, "text": "ask"},
            "c1:b2": {"type": 2, "text": "answer"},
            "c1:b3": {"type": 7, "text": "system-ish"},
        },
    )
    session = _parse_one(db_path, "c1")
    assert [(m.role, m.text) for m in session.messages] == [
        ("user", "ask"),
        ("assistant", "answer"),
    ]


def test_kept_messages_get_dense_ordinals_and_a_linear_parent_chain(
    build_vscdb: Callable[..., Path],
) -> None:
    """Ordinals are dense over kept messages; each points at its predecessor."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2", "b3", "b4")},
        bubbles={
            "c1:b1": {"type": 1, "text": "one"},
            "c1:b2": {"type": 2, "text": ""},  # dropped
            "c1:b3": {"type": 1, "text": "two"},
            "c1:b4": {"type": 2, "text": "three"},
        },
    )
    session = _parse_one(db_path, "c1")
    assert [(m.ordinal, m.parent_ordinal) for m in session.messages] == [
        (0, None),
        (1, 0),
        (2, 1),
    ]


def test_composer_name_becomes_the_session_title(
    build_vscdb: Callable[..., Path],
) -> None:
    """``composerData.name`` is the title; absent leaves it ``None``."""
    bubbles = {"c1:b1": {"type": 1, "text": "hi"}, "c2:b1": {"type": 1, "text": "hi"}}
    db_path = build_vscdb(
        composers={
            "c1": _composer("b1", name="Refactor the writer"),
            "c2": _composer("b1"),
        },
        bubbles=bubbles,
    )
    assert _parse_one(db_path, "c1").title == "Refactor the writer"
    assert _parse_one(db_path, "c2").title is None


# --- the OQ1 keep/drop contract ----------------------------------------------


def test_bubble_text_is_stored_whole(build_vscdb: Callable[..., Path]) -> None:
    """A bubble's text is stored verbatim and untruncated."""
    long_text = "paragraph\n\n" + ("x" * 20_000)
    db_path = build_vscdb(
        composers={"c1": _composer("b1")},
        bubbles={"c1:b1": {"type": 1, "text": long_text}},
    )
    assert _parse_one(db_path, "c1").messages[0].text == long_text


def test_thinking_only_bubble_yields_no_message_and_no_thinking_text(
    build_vscdb: Callable[..., Path],
) -> None:
    """A thinking-only bubble is dropped and its text is stored nowhere."""
    secret = "internal chain of thought"
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {"type": 2, "text": "", "thinking": {"text": secret}},
            "c1:b2": {"type": 2, "text": "visible"},
        },
    )
    session = _parse_one(db_path, "c1")
    assert [m.text for m in session.messages] == ["visible"]
    assert secret not in repr(session)


def test_wholly_empty_bubble_yields_no_message(
    build_vscdb: Callable[..., Path],
) -> None:
    """A bubble with neither text nor a tool call is dropped."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {"type": 1, "text": "   "},
            "c1:b2": {"type": 2, "text": "kept"},
        },
    )
    assert [m.text for m in _parse_one(db_path, "c1").messages] == ["kept"]


def test_tool_bubble_becomes_a_message_with_one_tool_call(
    build_vscdb: Callable[..., Path],
) -> None:
    """An empty-text bubble carrying ``toolFormerData`` is still a message."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1")},
        bubbles={
            "c1:b1": {
                "type": 2,
                "text": "",
                "toolFormerData": {"name": "read_file", "rawArgs": '{"path": "/a"}'},
            }
        },
    )
    session = _parse_one(db_path, "c1")
    assert len(session.messages) == 1
    message = session.messages[0]
    assert message.role == "assistant"
    assert message.text is None
    assert len(message.tool_calls) == 1


def test_tool_call_block_ordinal_reflects_whether_the_bubble_has_text(
    build_vscdb: Callable[..., Path],
) -> None:
    """Tool call sits at block 1 behind text, or at block 0 when text-free."""
    tool = {"name": "edit_file", "rawArgs": "{}"}
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {"type": 2, "text": "let me edit", "toolFormerData": tool},
            "c1:b2": {"type": 2, "text": "", "toolFormerData": tool},
        },
    )
    session = _parse_one(db_path, "c1")
    assert session.messages[0].tool_calls[0].ordinal == 1
    assert session.messages[1].tool_calls[0].ordinal == 0


def test_tool_call_carries_name_id_and_parsed_input(
    build_vscdb: Callable[..., Path],
) -> None:
    """``name`` / ``toolCallId`` / parsed ``rawArgs`` land on the tool call."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1")},
        bubbles={
            "c1:b1": {
                "type": 2,
                "text": "",
                "toolFormerData": {
                    "name": "run_terminal_command_v2",
                    "toolCallId": "call_abc123",
                    "rawArgs": '{"command": "ls -la", "cwd": "/home/u/p"}',
                },
            }
        },
    )
    call = _parse_one(db_path, "c1").messages[0].tool_calls[0]
    assert call.tool_name == "run_terminal_command_v2"
    assert call.source_tool_use_id == "call_abc123"
    assert call.tool_input == {"command": "ls -la", "cwd": "/home/u/p"}


def test_tool_input_falls_back_to_params_then_to_the_raw_string(
    build_vscdb: Callable[..., Path],
) -> None:
    """Unparseable ``rawArgs`` falls back to ``params``, then to the raw text.

    Both rungs are live shapes: the probed store had tool bubbles whose
    ``rawArgs`` was empty and whose ``params`` carried the JSON.
    """
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {
                "type": 2,
                "text": "",
                "toolFormerData": {
                    "name": "t",
                    "rawArgs": "",
                    "params": '{"command": "wc -l"}',
                },
            },
            "c1:b2": {
                "type": 2,
                "text": "",
                "toolFormerData": {"name": "t", "rawArgs": "not json at all"},
            },
        },
    )
    session = _parse_one(db_path, "c1")
    assert session.messages[0].tool_calls[0].tool_input == {"command": "wc -l"}
    assert session.messages[1].tool_calls[0].tool_input == "not json at all"


def test_tool_result_is_never_stored(build_vscdb: Callable[..., Path]) -> None:
    """``toolFormerData.result`` appears nowhere in the emitted session."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1")},
        bubbles={
            "c1:b1": {
                "type": 2,
                "text": "",
                "toolFormerData": {
                    "name": "t",
                    "rawArgs": "{}",
                    "result": '{"output": "SECRET-RESULT-PAYLOAD"}',
                },
            }
        },
    )
    assert "SECRET-RESULT-PAYLOAD" not in repr(_parse_one(db_path, "c1"))


# --- ordering & robustness ---------------------------------------------------


def test_message_order_follows_the_conversation_headers(
    build_vscdb: Callable[..., Path],
) -> None:
    """Messages come out in ``fullConversationHeadersOnly`` order, not key order."""
    db_path = build_vscdb(
        composers={"c1": _composer("b3", "b1", "b2")},
        bubbles={
            "c1:b1": {"type": 1, "text": "second"},
            "c1:b2": {"type": 1, "text": "third"},
            "c1:b3": {"type": 1, "text": "first"},
        },
    )
    assert [m.text for m in _parse_one(db_path, "c1").messages] == [
        "first",
        "second",
        "third",
    ]


def test_legacy_inline_conversation_is_used_when_headers_are_absent(
    build_vscdb: Callable[..., Path],
) -> None:
    """Older composers store whole bubbles inline; those become the messages."""
    db_path = build_vscdb(
        composers={
            "c1": {
                "conversation": [
                    {"bubbleId": "b1", "type": 1, "text": "inline ask"},
                    {"bubbleId": "b2", "type": 2, "text": "inline answer"},
                ]
            }
        }
    )
    assert [(m.role, m.text) for m in _parse_one(db_path, "c1").messages] == [
        ("user", "inline ask"),
        ("assistant", "inline answer"),
    ]


def test_header_referencing_a_missing_bubble_skips_only_that_entry(
    build_vscdb: Callable[..., Path],
) -> None:
    """Cursor prunes bubbles; a dangling header must not abort the composer."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "pruned", "b3")},
        bubbles={
            "c1:b1": {"type": 1, "text": "one"},
            "c1:b3": {"type": 1, "text": "three"},
        },
    )
    assert [m.text for m in _parse_one(db_path, "c1").messages] == ["one", "three"]


def test_corrupt_bubble_value_skips_only_that_bubble(
    build_vscdb: Callable[..., Path],
) -> None:
    """A non-JSON bubble value is skipped and the rest of the turn survives."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2", "b3")},
        bubbles={
            "c1:b1": {"type": 1, "text": "one"},
            "c1:b2": "{not json",
            "c1:b3": {"type": 1, "text": "three"},
        },
    )
    assert [m.text for m in _parse_one(db_path, "c1").messages] == ["one", "three"]


def test_composer_without_headers_or_conversation_yields_no_session(
    build_vscdb: Callable[..., Path],
) -> None:
    """An empty draft (no headers, no inline array) is skipped entirely."""
    db_path = build_vscdb(composers={"c1": {"name": "untouched draft"}})
    assert _parse_one(db_path, "c1") is None


def test_composer_with_no_storable_bubbles_yields_no_session(
    build_vscdb: Callable[..., Path],
) -> None:
    """A composer whose every bubble is dropped produces no session."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {"type": 2, "text": "", "thinking": {"text": "hmm"}},
            "c1:b2": {"type": 2, "text": ""},
        },
    )
    assert _parse_one(db_path, "c1") is None


def test_corrupt_composer_value_is_skipped_without_aborting_the_run(
    build_vscdb: Callable[..., Path],
) -> None:
    """One unreadable composer does not stop the composers after it."""
    db_path = build_vscdb(
        composers={"c2": _composer("b1")},
        bubbles={"c2:b1": {"type": 1, "text": "survivor"}},
    )
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)",
            ("composerData:c1", "{ truncated"),
        )
        con.commit()
    finally:
        con.close()

    parsed = list(cursor_vscdb.parse_all(db_path, ["c1", "c2"]))
    assert [s.session_id for s in parsed] == ["c2"]


# --- timestamps & tokens -----------------------------------------------------


def test_bubble_timestamps_become_message_ts_and_session_bounds(
    build_vscdb: Callable[..., Path],
) -> None:
    """ISO ``createdAt`` becomes naive-UTC ``ts``; session bounds are min/max."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {
                "type": 1,
                "text": "one",
                "createdAt": "2026-05-13T21:39:13.321Z",
            },
            "c1:b2": {
                "type": 2,
                "text": "two",
                "createdAt": "2026-05-13T21:41:00.000Z",
            },
        },
    )
    session = _parse_one(db_path, "c1")
    assert session.messages[0].ts == datetime(2026, 5, 13, 21, 39, 13, 321_000)
    assert session.started_at == datetime(2026, 5, 13, 21, 39, 13, 321_000)
    assert session.ended_at == datetime(2026, 5, 13, 21, 41, 0)


def test_timeless_bubbles_fall_back_to_composer_created_at(
    build_vscdb: Callable[..., Path],
) -> None:
    """Without bubble stamps, ``started_at`` uses ``composerData.createdAt`` ms."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", createdAt=1778708295179)},
        bubbles={"c1:b1": {"type": 1, "text": "one"}},
    )
    session = _parse_one(db_path, "c1")
    assert session.messages[0].ts is None
    assert session.started_at == datetime.fromtimestamp(
        1778708295.179, tz=timezone.utc
    ).replace(tzinfo=None)
    assert session.ended_at is None


def test_source_mtime_is_never_set(build_vscdb: Callable[..., Path]) -> None:
    """D8: the shared store's mtime is not any composer's activity time."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1")},
        bubbles={"c1:b1": {"type": 1, "text": "hi"}},
    )
    assert _parse_one(db_path, "c1").source_mtime is None


def test_nonzero_bubble_tokens_land_on_that_message_only(
    build_vscdb: Callable[..., Path],
) -> None:
    """Token counts attach at message grain; session ``*_tokens`` stay ``None``."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {"type": 1, "text": "ask"},
            "c1:b2": {
                "type": 2,
                "text": "answer",
                "tokenCount": {"inputTokens": 6078, "outputTokens": 512},
            },
        },
    )
    session = _parse_one(db_path, "c1")
    assert (session.messages[1].input_tokens, session.messages[1].output_tokens) == (
        6078,
        512,
    )
    assert (session.messages[0].input_tokens, session.messages[0].output_tokens) == (
        None,
        None,
    )
    assert session.input_tokens is None
    assert session.output_tokens is None


def test_zero_and_absent_token_counts_become_none_not_zero(
    build_vscdb: Callable[..., Path],
) -> None:
    """Cursor stamps ``{0,0}`` on unmetered turns; ``0`` would assert a real cost."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2", "b3")},
        bubbles={
            "c1:b1": {
                "type": 1,
                "text": "zeroed",
                "tokenCount": {"inputTokens": 0, "outputTokens": 0},
            },
            "c1:b2": {"type": 2, "text": "absent"},
            "c1:b3": {
                "type": 2,
                "text": "metered",
                "tokenCount": {"inputTokens": 10, "outputTokens": 0},
            },
        },
    )
    messages = _parse_one(db_path, "c1").messages
    assert [(m.input_tokens, m.output_tokens) for m in messages] == [
        (None, None),
        (None, None),
        (10, None),
    ]


def test_context_meter_fields_are_never_mapped_to_tokens(
    build_vscdb: Callable[..., Path],
) -> None:
    """``tokenCountUpUntilHere`` / ``contextUsagePercent`` are wrong semantics."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", contextUsagePercent=65.79)},
        bubbles={
            "c1:b1": {
                "type": 2,
                "text": "answer",
                "tokenCountUpUntilHere": 120_000,
                "contextUsagePercent": 65.79,
            }
        },
    )
    session = _parse_one(db_path, "c1")
    assert (session.messages[0].input_tokens, session.messages[0].output_tokens) == (
        None,
        None,
    )
    assert session.input_tokens is None


def test_tokens_on_a_dropped_bubble_are_not_smuggled_onto_a_neighbour(
    build_vscdb: Callable[..., Path],
) -> None:
    """A dropped thinking-only bubble's tokens do not migrate to another turn."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {
                "type": 2,
                "text": "",
                "thinking": {"text": "hmm"},
                "tokenCount": {"inputTokens": 999, "outputTokens": 888},
            },
            "c1:b2": {"type": 2, "text": "spoken"},
        },
    )
    session = _parse_one(db_path, "c1")
    assert [(m.text, m.input_tokens, m.output_tokens) for m in session.messages] == [
        ("spoken", None, None)
    ]


# --- model attribution --------------------------------------------------------


def test_composer_model_config_becomes_the_session_model(
    build_vscdb: Callable[..., Path],
) -> None:
    """``composerData.modelConfig.modelName`` is the conversation's model."""
    db_path = build_vscdb(
        composers={
            "c1": _composer(
                "b1", modelConfig={"modelName": "grok-4.5", "maxMode": False}
            )
        },
        bubbles={"c1:b1": {"type": 1, "text": "ask"}},
    )
    assert _parse_one(db_path, "c1").models == ["grok-4.5"]


def test_bubble_model_info_becomes_that_message_model(
    build_vscdb: Callable[..., Path],
) -> None:
    """A bubble's ``modelInfo.modelName`` records the model that produced it.

    Cursor stamps this where the model is set or changed rather than on every
    turn, so it is deliberately sparse: only the bubbles that carry it get a
    ``model``, and no value is carried across neighbours.
    """
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {"type": 1, "text": "ask"},
            "c1:b2": {
                "type": 2,
                "text": "answer",
                "modelInfo": {"modelName": "claude-opus-5"},
            },
        },
    )
    messages = _parse_one(db_path, "c1").messages
    assert [message.model for message in messages] == [None, "claude-opus-5"]


def test_session_models_union_the_composer_default_and_every_bubble_model(
    build_vscdb: Callable[..., Path],
) -> None:
    """A conversation that switched models reports both, deduped and ordered.

    ``sessions.models`` is a list because a conversation can use more than one.
    Order is the composer default first, then bubble order, so the list reads
    as the conversation ran.
    """
    db_path = build_vscdb(
        composers={
            "c1": _composer("b1", "b2", "b3", modelConfig={"modelName": "grok-4.5"})
        },
        bubbles={
            "c1:b1": {"type": 1, "text": "ask", "modelInfo": {"modelName": "grok-4.5"}},
            "c1:b2": {
                "type": 2,
                "text": "switched",
                "modelInfo": {"modelName": "claude-opus-5"},
            },
            "c1:b3": {
                "type": 1,
                "text": "again",
                "modelInfo": {"modelName": "claude-opus-5"},
            },
        },
    )
    assert _parse_one(db_path, "c1").models == ["grok-4.5", "claude-opus-5"]


def test_default_is_stored_as_written_not_translated(
    build_vscdb: Callable[..., Path],
) -> None:
    """Cursor's literal ``default`` is a real recorded value, not a missing one.

    It names the model picker's setting rather than a specific model, but the
    ai-code-tracking sidecar already writes it for ordinary ingest, so dropping
    it here would make the same conversation report differently depending on
    which pipeline authored it.
    """
    db_path = build_vscdb(
        composers={"c1": _composer("b1", modelConfig={"modelName": "default"})},
        bubbles={
            "c1:b1": {"type": 1, "text": "ask", "modelInfo": {"modelName": "default"}}
        },
    )
    session = _parse_one(db_path, "c1")
    assert session.models == ["default"]
    assert session.messages[0].model == "default"


def test_absent_model_data_stays_none_at_both_grains(
    build_vscdb: Callable[..., Path],
) -> None:
    """No model anywhere is ``None`` — never a guess from a sibling turn."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {"type": 1, "text": "ask"},
            "c1:b2": {"type": 2, "text": "answer"},
        },
    )
    session = _parse_one(db_path, "c1")
    assert session.models is None
    assert [message.model for message in session.messages] == [None, None]


def test_a_dropped_bubbles_model_still_counts_toward_the_session(
    build_vscdb: Callable[..., Path],
) -> None:
    """Model names survive the OQ1 drop; token counts do not. Different grains.

    A token count is a property *of one turn*, so moving it to a neighbour
    would be a lie about that turn's cost. ``sessions.models`` claims only that
    the conversation used a model — true whether or not the turn that named it
    left a storable row behind.
    """
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2")},
        bubbles={
            "c1:b1": {"type": 1, "text": "ask"},
            "c1:b2": {
                "type": 2,
                "text": "",
                "thinking": {"text": "dropped"},
                "modelInfo": {"modelName": "claude-opus-5"},
            },
        },
    )
    session = _parse_one(db_path, "c1")
    assert session.models == ["claude-opus-5"]
    assert [message.model for message in session.messages] == [None]


def test_malformed_model_fields_are_ignored_without_raising(
    build_vscdb: Callable[..., Path],
) -> None:
    """A non-dict ``modelConfig`` or a blank ``modelName`` degrades to ``None``."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1", "b2", modelConfig="grok-4.5")},
        bubbles={
            "c1:b1": {"type": 1, "text": "ask", "modelInfo": {"modelName": ""}},
            "c1:b2": {"type": 2, "text": "answer", "modelInfo": []},
        },
    )
    session = _parse_one(db_path, "c1")
    assert session.models is None
    assert [message.model for message in session.messages] == [None, None]


# --- workspace identity (OQ2) ------------------------------------------------


def _with_workspace(
    build_vscdb: Callable[..., Path], workspaces: dict[str, dict | None] | None
) -> Path:
    """One composer in workspace ``w1``, with the given ``workspaceStorage``."""
    return build_vscdb(
        composers={"c1": _composer("b1")},
        bubbles={"c1:b1": {"type": 1, "text": "hi"}},
        headers={"c1": "w1"},
        workspaces=workspaces,
    )


def test_workspace_id_becomes_the_session_project_id(
    build_vscdb: Callable[..., Path],
) -> None:
    """``composerHeaders.workspaceId`` is stored verbatim as ``project_id``."""
    db_path = _with_workspace(build_vscdb, None)
    assert _parse_one(db_path, "c1").project_id == "w1"


def test_composer_without_a_header_row_has_no_project_id(
    build_vscdb: Callable[..., Path],
) -> None:
    """No ``composerHeaders`` row leaves ``project_id`` honestly ``None``."""
    db_path = build_vscdb(
        composers={"c1": _composer("b1")},
        bubbles={"c1:b1": {"type": 1, "text": "hi"}},
    )
    assert _parse_one(db_path, "c1").project_id is None


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("vscode-remote://wsl%2Bubuntu/home/u/p", "/home/u/p"),
        ("vscode-remote://wsl%2Bubuntu/home/u/my%20project", "/home/u/my project"),
        ("file:///tmp/p", "/tmp/p"),
    ],
)
def test_single_root_folder_uri_resolves_to_the_real_path(
    build_vscdb: Callable[..., Path], uri: str, expected: str
) -> None:
    """Both live URI schemes decode (percent-decoded) to a real path."""
    db_path = _with_workspace(build_vscdb, {"w1": {"folder": uri}})
    assert _parse_one(db_path, "c1").cwd == expected


def test_multi_root_workspace_yields_no_cwd(build_vscdb: Callable[..., Path]) -> None:
    """A ``.code-workspace`` pointer names no single folder, so ``cwd`` is None."""
    db_path = _with_workspace(
        build_vscdb, {"w1": {"workspace": "file:///s%3A/Workspaces/1/workspace.json"}}
    )
    session = _parse_one(db_path, "c1")
    assert session.cwd is None
    assert session.project_id == "w1"


def test_missing_workspace_json_yields_no_cwd(
    build_vscdb: Callable[..., Path],
) -> None:
    """A workspace dir without ``workspace.json`` degrades to ``cwd = None``."""
    db_path = _with_workspace(build_vscdb, {"w1": None})
    assert _parse_one(db_path, "c1").cwd is None


def test_absent_workspace_storage_directory_yields_no_cwd(
    build_vscdb: Callable[..., Path],
) -> None:
    """An entirely absent ``workspaceStorage`` must not fail the run."""
    db_path = _with_workspace(build_vscdb, None)
    assert not (db_path.parent.parent / "workspaceStorage").exists()
    assert _parse_one(db_path, "c1").cwd is None


def test_unknown_folder_uri_scheme_yields_no_cwd(
    build_vscdb: Callable[..., Path],
) -> None:
    """An unrecognized scheme is an honest unknown, not a mangled path."""
    db_path = _with_workspace(build_vscdb, {"w1": {"folder": "ssh://host/opt/p"}})
    assert _parse_one(db_path, "c1").cwd is None


def test_workspace_key_is_left_for_the_writer_to_derive(
    build_vscdb: Callable[..., Path],
) -> None:
    """The parser never sets ``workspace_key``; the writer owns that derivation."""
    db_path = _with_workspace(
        build_vscdb, {"w1": {"folder": "vscode-remote://wsl%2Bubuntu/home/u/p"}}
    )
    assert _parse_one(db_path, "c1").workspace_key is None
