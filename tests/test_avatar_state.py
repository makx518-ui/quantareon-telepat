from telepat.avatar.state_selector import select_avatar_state


def test_astro_deep_answer_uses_thoughtful_state() -> None:
    state = select_avatar_state(
        intent="astropsychology",
        user_message="Что сейчас происходит со мной?",
        reply="Здесь важно посмотреть глубже на главный паттерн напряжения.",
        fallback="thinking",
    )
    assert state == "hand_chin"


def test_acknowledgement_prefers_nod() -> None:
    state = select_avatar_state(
        intent="casual_conversation",
        user_message="Ты меня понял?",
        reply="Да, понимаю тебя.",
        fallback="idle",
    )
    assert state == "nod"


def test_enumeration_prefers_light_gesture() -> None:
    state = select_avatar_state(
        intent="casual_conversation",
        user_message="Какие есть пути?",
        reply="Есть несколько вариантов, и каждый стоит рассмотреть отдельно.",
        fallback="idle",
    )
    assert state == "light_gesture"
