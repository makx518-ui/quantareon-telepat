from telepat.core.context_builder import build_context_packet
from telepat.core.models import ConversationTurn, SessionState
from telepat.core.plan import build_plan
from telepat.llm.prompt import build_chat_messages, build_context_payload


def test_context_packet_separates_current_turn_from_history() -> None:
    session = SessionState(
        session_id="s",
        user_id="u",
        language="ru",
        history=[
            ConversationTurn(role="user", content="Предыдущий вопрос"),
            ConversationTurn(role="assistant", content="Предыдущий ответ"),
            ConversationTurn(role="user", content="Текущий вопрос"),
        ],
    )

    packet = build_context_packet(
        session,
        "Текущий вопрос",
        build_plan("casual_conversation"),
    )

    assert packet.current_message == "Текущий вопрос"
    assert [turn.content for turn in packet.conversation_history] == [
        "Предыдущий вопрос",
        "Предыдущий ответ",
    ]


def test_chat_messages_do_not_duplicate_history_inside_packet() -> None:
    session = SessionState(
        session_id="s",
        user_id="u",
        language="ru",
        history=[
            ConversationTurn(role="user", content="Старый вопрос"),
            ConversationTurn(role="assistant", content="Старый ответ"),
            ConversationTurn(role="user", content="Новый вопрос"),
        ],
    )
    packet = build_context_packet(
        session,
        "Новый вопрос",
        build_plan("casual_conversation"),
    )

    messages = build_chat_messages(packet)
    final_payload = messages[-1]["content"]

    assert messages[1]["content"] == "Старый вопрос"
    assert messages[2]["content"] == "Старый ответ"
    assert "Новый вопрос" in final_payload
    assert "Старый вопрос" not in final_payload
    assert "recent_history" not in final_payload


def test_stateless_payload_keeps_previous_history_for_gemini() -> None:
    session = SessionState(
        session_id="s",
        user_id="u",
        language="ru",
        history=[
            ConversationTurn(role="user", content="Вопрос один"),
            ConversationTurn(role="assistant", content="Ответ один"),
            ConversationTurn(role="user", content="Вопрос два"),
        ],
    )
    packet = build_context_packet(
        session,
        "Вопрос два",
        build_plan("casual_conversation"),
    )

    payload = build_context_payload(packet)

    assert "recent_history" in payload
    assert "Вопрос один" in payload
    assert "Ответ один" in payload
    assert payload.count("Вопрос два") == 1
