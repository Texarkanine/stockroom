"""Dual-grain model attribution for the dashboard metrics layer.

Conversation grain: a main session uses model M when M appears in
``sessions.models`` or any child ``messages.model`` (once per session).

Message grain: each assistant turn is attributed to ``messages.model`` when
set; otherwise, when the parent session has exactly one non-empty model in
``sessions.models``, that sole model is used (Cursor enrichment honesty).
Multi-model or empty session lists contribute nothing for NULL message models.
Subagent sessions never contribute to either grain.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple


class SessionRow(NamedTuple):
    """Session fields needed for model attribution."""

    harness: str
    session_id: str
    models: Sequence[str] | None
    is_subagent: bool


class MessageRow(NamedTuple):
    """Message fields needed for model attribution."""

    harness: str
    session_id: str
    role: str
    model: str | None


def _nonempty_models(models: Sequence[str] | None) -> list[str]:
    """Return non-empty model name strings from a session list."""
    if not models:
        return []
    return [model for model in models if model]


def conversation_models(
    session: SessionRow,
    message_models: Sequence[str | None],
) -> set[str]:
    """Return the set of models a session used (conversation grain).

    Empty for subagents. Union of non-empty ``session.models`` entries and
    non-empty message model values.
    """
    if session.is_subagent:
        return set()
    used = set(_nonempty_models(session.models))
    used.update(model for model in message_models if model)
    return used


def attributed_assistant_model(
    role: str,
    message_model: str | None,
    session_models: Sequence[str] | None,
) -> str | None:
    """Return the model attributed to one message turn, or ``None``.

    Only assistant turns attribute. Prefer ``message_model`` when non-empty;
    else sole non-empty entry in ``session_models``; else skip.
    """
    if role != "assistant":
        return None
    if message_model:
        return message_model
    sole = _nonempty_models(session_models)
    if len(sole) == 1:
        return sole[0]
    return None


def conversation_sets(
    sessions: Sequence[SessionRow],
    messages: Sequence[MessageRow],
) -> dict[tuple[str, str], set[str]]:
    """Map ``(harness, session_id)`` → conversation-grain model set.

    Subagent sessions are omitted. Sessions with no attributed models are
    omitted (empty sets are not retained).
    """
    by_session: dict[tuple[str, str], list[str | None]] = {}
    for message in messages:
        key = (message.harness, message.session_id)
        by_session.setdefault(key, []).append(message.model)

    result: dict[tuple[str, str], set[str]] = {}
    for session in sessions:
        key = (session.harness, session.session_id)
        used = conversation_models(session, by_session.get(key, []))
        if used:
            result[key] = used
    return result


def attributed_turns(
    sessions: Sequence[SessionRow],
    messages: Sequence[MessageRow],
) -> list[tuple[str, str, str]]:
    """Return ``(harness, session_id, model)`` for each attributed assistant turn.

    Subagent sessions contribute nothing. Order follows ``messages`` order.
    """
    session_index = {
        (session.harness, session.session_id): session for session in sessions
    }
    turns: list[tuple[str, str, str]] = []
    for message in messages:
        session = session_index.get((message.harness, message.session_id))
        if session is None or session.is_subagent:
            continue
        model = attributed_assistant_model(message.role, message.model, session.models)
        if model is not None:
            turns.append((message.harness, message.session_id, model))
    return turns
