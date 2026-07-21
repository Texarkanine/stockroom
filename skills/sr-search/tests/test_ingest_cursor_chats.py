"""Clean-room Cursor Agent CLI ``store.db`` parser tests.

The fixture under ``fixtures/ingest/cursor_chats/`` is a synthetic SQLite store
with a root-hash chain (system + user_info + opaque + user_query + assistant
with reasoning/text/tool-call). The parser must walk root order, keep only
user/assistant JSON leaves, drop reasoning, capture tool inputs, stamp
``entrypoint='cli'``, and recover cwd from Workspace Path when present.
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from stockroom.ingest import cursor_chats

_FIXTURE_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "ingest"
    / "cursor_chats"
    / "projhash1234567890abcdefprojhash12"
    / "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    / "store.db"
)


def test_parse_session_identity_and_entrypoint() -> None:
    """Session id/agent id come from the chat dir; entrypoint is ``cli``."""
    session = cursor_chats.parse_session(_FIXTURE_ROOT)
    assert session.harness == "cursor"
    assert session.session_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert session.agent_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert session.entrypoint == "cli"
    assert session.source_path == str(_FIXTURE_ROOT)
    assert session.is_subagent is False


def test_parse_session_title_models_started_at() -> None:
    """Meta ``name``/``lastUsedModel``/``createdAt`` map onto session fields."""
    session = cursor_chats.parse_session(_FIXTURE_ROOT)
    assert session.title == "Fixture Chat"
    assert session.models == ["gpt-5"]
    assert session.started_at == datetime(2025, 1, 1, 0, 0, 0)


def test_parse_session_messages_in_root_order() -> None:
    """Kept user/assistant ordinals follow root order (system/opaque skipped)."""
    session = cursor_chats.parse_session(_FIXTURE_ROOT)
    assert [m.role for m in session.messages] == ["user", "user", "assistant"]
    assert [m.ordinal for m in session.messages] == [0, 1, 2]
    assert [m.parent_ordinal for m in session.messages] == [None, 0, 1]
    assert "Workspace Path:" in (session.messages[0].text or "")
    assert session.messages[1].text == "<user_query>\nlist files\n</user_query>"
    assert session.messages[2].text == "I'll list the directory."


def test_parse_session_drops_reasoning_keeps_tool_call() -> None:
    """Reasoning parts are omitted; tool-call args become tool_calls rows."""
    session = cursor_chats.parse_session(_FIXTURE_ROOT)
    assistant = session.messages[2]
    assert "thinking" not in (assistant.text or "")
    assert len(assistant.tool_calls) == 1
    call = assistant.tool_calls[0]
    assert call.tool_name == "Glob"
    assert call.tool_input == {"glob_pattern": "**/*"}
    assert call.source_tool_use_id == "toolu_test_1"
    # block index: reasoning=0, text=1, tool-call=2
    assert call.ordinal == 2


def test_parse_session_cwd_from_workspace_path() -> None:
    """Workspace Path inside user_info becomes ``cwd`` when present."""
    session = cursor_chats.parse_session(_FIXTURE_ROOT)
    assert session.cwd == "/home/user/project"


def _write_store(
    path: Path,
    *,
    meta: dict,
    blobs: dict[str, bytes],
) -> Path:
    """Write a minimal meta+blobs SQLite store at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE blobs (id TEXT PRIMARY KEY, data BLOB)")
    con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    con.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        ("0", json.dumps(meta, separators=(",", ":")).encode().hex()),
    )
    for bid, data in blobs.items():
        con.execute("INSERT INTO blobs (id, data) VALUES (?, ?)", (bid, data))
    con.commit()
    con.close()
    return path


def test_parse_session_empty_when_missing_root(tmp_path: Path) -> None:
    """Missing ``latestRootBlobId`` yields a session with zero messages."""
    agent = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    store = tmp_path / agent / "store.db"
    _write_store(
        store,
        meta={"agentId": agent, "name": "Empty", "createdAt": 1735689600000},
        blobs={},
    )
    session = cursor_chats.parse_session(store)
    assert session is not None
    assert session.session_id == agent
    assert session.entrypoint == "cli"
    assert session.messages == []
    assert session.title == "Empty"


def test_parse_session_skips_corrupt_leaf_continues(tmp_path: Path) -> None:
    """A non-JSON leaf in the root chain is skipped; later leaves still parse."""
    agent = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    user = json.dumps(
        {"role": "user", "content": [{"type": "text", "text": "hi"}]}
    ).encode()
    assistant = json.dumps(
        {"role": "assistant", "content": [{"type": "text", "text": "yo"}]}
    ).encode()
    opaque = b"\xffnot-json"
    uid = hashlib.sha256(user).hexdigest()
    aid = hashlib.sha256(assistant).hexdigest()
    oid = hashlib.sha256(opaque).hexdigest()
    root = bytearray()
    for hid in (uid, oid, aid):
        root.extend(b"\x0a\x20")
        root.extend(bytes.fromhex(hid))
    root_b = bytes(root)
    rid = hashlib.sha256(root_b).hexdigest()
    store = tmp_path / agent / "store.db"
    _write_store(
        store,
        meta={
            "agentId": agent,
            "latestRootBlobId": rid,
            "name": "SkipCorrupt",
            "createdAt": 1735689600000,
        },
        blobs={uid: user, oid: opaque, aid: assistant, rid: root_b},
    )
    session = cursor_chats.parse_session(store)
    assert session is not None
    assert [m.role for m in session.messages] == ["user", "assistant"]
    assert [m.text for m in session.messages] == ["hi", "yo"]


def test_parse_session_returns_none_for_non_sqlite_file(tmp_path: Path) -> None:
    """
    A path that is not a readable SQLite database must not raise out of
    ``parse_session`` — it returns ``None`` so the orchestrator can skip
    that discovery and continue the batch.
    """
    agent = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    store = tmp_path / agent / "store.db"
    store.parent.mkdir(parents=True)
    store.write_text("this is not a sqlite database\n", encoding="utf-8")
    assert cursor_chats.parse_session(store) is None
