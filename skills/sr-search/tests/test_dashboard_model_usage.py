"""Pure dual-grain model attribution helpers for the dashboard."""

from __future__ import annotations

from stockroom.dashboard import model_usage


def _session(
    harness: str,
    session_id: str,
    models: list[str] | None = None,
    *,
    is_subagent: bool = False,
) -> model_usage.SessionRow:
    return model_usage.SessionRow(harness, session_id, models, is_subagent)


def _message(
    harness: str,
    session_id: str,
    role: str,
    model: str | None = None,
) -> model_usage.MessageRow:
    return model_usage.MessageRow(harness, session_id, role, model)


class TestConversationGrain:
    """Session uses a model once across sessions.models and messages.model."""

    def test_session_models_list_counts_once(self) -> None:
        session = _session("cursor", "c1", ["m1", "m2"])
        assert model_usage.conversation_models(session, []) == {"m1", "m2"}
        sets = model_usage.conversation_sets([session], [])
        assert sets == {("cursor", "c1"): {"m1", "m2"}}

    def test_message_model_only_counts_once(self) -> None:
        session = _session("claude", "a1", None)
        messages = [
            _message("claude", "a1", "assistant", "m1"),
            _message("claude", "a1", "assistant", "m1"),
            _message("claude", "a1", "assistant", "m2"),
        ]
        assert model_usage.conversation_models(
            session, [m.model for m in messages]
        ) == {"m1", "m2"}
        sets = model_usage.conversation_sets([session], messages)
        assert sets == {("claude", "a1"): {"m1", "m2"}}

    def test_same_model_on_list_and_messages_counts_once(self) -> None:
        session = _session("cursor", "c1", ["m1"])
        messages = [
            _message("cursor", "c1", "assistant", "m1"),
            _message("cursor", "c1", "user", None),
        ]
        assert model_usage.conversation_models(
            session, [m.model for m in messages]
        ) == {"m1"}

    def test_subagent_sessions_excluded(self) -> None:
        main = _session("cursor", "c1", ["m1"])
        sub = _session("cursor", "sub", ["m4"], is_subagent=True)
        messages = [
            _message("cursor", "sub", "assistant", "m4"),
            _message("cursor", "c1", "assistant", None),
        ]
        assert model_usage.conversation_models(sub, ["m4"]) == set()
        sets = model_usage.conversation_sets([main, sub], messages)
        assert ("cursor", "sub") not in sets
        assert sets == {("cursor", "c1"): {"m1"}}


class TestMessageGrain:
    """Assistant-turn attribution with sole-session-model fallback."""

    def test_assistant_turn_with_message_model(self) -> None:
        assert (
            model_usage.attributed_assistant_model("assistant", "claude-opus", None)
            == "claude-opus"
        )
        sessions = [_session("claude", "a1", None)]
        messages = [
            _message("claude", "a1", "assistant", "m1"),
            _message("claude", "a1", "assistant", "m2"),
        ]
        assert model_usage.attributed_turns(sessions, messages) == [
            ("claude", "a1", "m1"),
            ("claude", "a1", "m2"),
        ]

    def test_null_message_model_sole_session_model_fallback(self) -> None:
        assert (
            model_usage.attributed_assistant_model("assistant", None, ["composer"])
            == "composer"
        )
        sessions = [_session("cursor", "c1", ["composer"])]
        messages = [
            _message("cursor", "c1", "assistant", None),
            _message("cursor", "c1", "assistant", None),
        ]
        assert model_usage.attributed_turns(sessions, messages) == [
            ("cursor", "c1", "composer"),
            ("cursor", "c1", "composer"),
        ]

    def test_null_message_model_multi_session_models_skips(self) -> None:
        assert (
            model_usage.attributed_assistant_model(
                "assistant", None, ["m1", "m2"]
            )
            is None
        )
        sessions = [_session("cursor", "c1", ["m1", "m2"])]
        messages = [_message("cursor", "c1", "assistant", None)]
        assert model_usage.attributed_turns(sessions, messages) == []

    def test_user_turns_never_attribute(self) -> None:
        assert (
            model_usage.attributed_assistant_model("user", None, ["composer"]) is None
        )
        assert (
            model_usage.attributed_assistant_model("user", "m1", ["composer"]) is None
        )
        sessions = [_session("cursor", "c1", ["composer"])]
        messages = [
            _message("cursor", "c1", "user", None),
            _message("cursor", "c1", "user", "m1"),
        ]
        assert model_usage.attributed_turns(sessions, messages) == []

    def test_empty_session_models_skips_null_message_model(self) -> None:
        assert model_usage.attributed_assistant_model("assistant", None, None) is None
        assert model_usage.attributed_assistant_model("assistant", None, []) is None
        assert (
            model_usage.attributed_assistant_model("assistant", None, ["", ""]) is None
        )
        sessions = [_session("cursor", "c1", [])]
        messages = [_message("cursor", "c1", "assistant", None)]
        assert model_usage.attributed_turns(sessions, messages) == []
