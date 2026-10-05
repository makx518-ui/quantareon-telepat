from __future__ import annotations

from .states import AvatarState


_ACK = (
    "понимаю", "верно", "да,", "соглас", "точно", "именно",
    "i understand", "exactly", "that's right",
)
_THINK = (
    "подума", "глубже", "смысл", "паттерн", "причин", "напряж",
    "consider", "pattern", "deeper", "tension",
)
_ENUM = (
    "во-первых", "во-вторых", "несколько", "вариант", "с одной стороны",
    "first,", "second,", "several", "options",
)
_WARM = (
    "рад", "хорошо", "прекрас", "добро пожаловать",
    "glad", "welcome", "good",
)


def select_avatar_state(
    *,
    intent: str,
    user_message: str,
    reply: str,
    fallback: str = "idle",
) -> AvatarState:
    """Select one restrained gesture state for the current answer.

    This is deliberately deterministic. The avatar should feel composed,
    not randomly animated.
    """
    text = reply.lower()
    user = user_message.lower()

    if any(marker in text for marker in _ACK):
        return "nod"

    if any(marker in text for marker in _ENUM):
        return "light_gesture"

    if intent in {"astropsychology", "follow_up_astro"}:
        if any(marker in text for marker in _THINK) or len(reply) > 650:
            return "hand_chin"
        return "thinking"

    if intent == "personal_reflection":
        if "?" in reply or len(user_message) > 300:
            return "lean_forward"
        return "listening"

    if intent == "factual_user_memory":
        return "listening"

    if any(marker in text for marker in _WARM):
        return "soft_smile"

    allowed = {
        "idle", "listening", "thinking", "nod", "hand_chin",
        "light_gesture", "lean_forward", "soft_smile", "speaking",
    }
    return fallback if fallback in allowed else "idle"
