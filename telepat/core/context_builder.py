from __future__ import annotations

from telepat.psychology.service import build_psychology_context

from .models import ContextPacket, Intent, SessionState
from .plan import OrchestrationPlan


def classify_intent(message: str, *, has_astro: bool) -> Intent:
    text = message.lower().strip()

    astro_markers = (
        "астро", "натал", "транзит", "аспект", "планет", "знак", "дом",
        "astro", "natal", "transit", "planet", "aspect",
    )
    reflection_markers = (
        "мне тяжело", "я чувствую", "почему я", "что со мной", "отношен",
        "страх", "тревог", "выбор", "не понимаю себя", "что делать",
    )
    memory_markers = (
        "помнишь", "мы говорили", "я рассказывал", "в прошлый раз",
        "remember", "last time",
    )

    if any(marker in text for marker in memory_markers):
        return "factual_user_memory"
    if any(marker in text for marker in astro_markers):
        return "follow_up_astro" if has_astro else "astropsychology"
    if any(marker in text for marker in reflection_markers):
        return "personal_reflection"
    if len(text) <= 400:
        return "casual_conversation"
    return "unknown"


def build_context_packet(
    session: SessionState,
    message: str,
    plan: OrchestrationPlan,
) -> ContextPacket:
    history = session.history
    if (
        history
        and history[-1].role == "user"
        and history[-1].content == message
    ):
        history = history[:-1]

    return ContextPacket(
        session_id=session.session_id,
        user_id=session.user_id,
        language=session.language,
        current_message=message,
        intent=plan.intent,
        conversation_history=history[-12:],
        user_memory=session.user_memory if plan.use_memory else {},
        astro_summary=session.astro_summary if plan.use_astro else None,
        psychology=build_psychology_context(
            message=message,
            language=session.language,
            plan=plan,
        ),
        response_style={
            "persona": "TELEPAT astropsychologist",
            "tone": "calm, intelligent, empathic",
            "verbosity": "concise",
            "mode": plan.response_mode,
        },
    )
