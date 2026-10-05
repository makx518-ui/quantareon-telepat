from __future__ import annotations

from .models import ContextPacket, Intent, SessionState


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


def build_psychology_context(intent: Intent) -> dict[str, str]:
    if intent == "personal_reflection":
        return {
            "stance": "calm, attentive, non-judgmental",
            "method": "reflect the concern, clarify gently, avoid overclaiming",
        }
    if intent in {"astropsychology", "follow_up_astro"}:
        return {
            "stance": "grounded astropsychological interpretation",
            "method": "connect symbolic patterns with lived experience; do not present astrology as certainty",
        }
    return {
        "stance": "warm, concise, attentive",
        "method": "answer directly and keep continuity with the session",
    }


def build_context_packet(session: SessionState, message: str) -> ContextPacket:
    intent = classify_intent(message, has_astro=session.astro_summary is not None)
    return ContextPacket(
        session_id=session.session_id,
        user_id=session.user_id,
        language=session.language,
        current_message=message,
        intent=intent,
        conversation_history=session.history[-12:],
        user_memory=session.user_memory,
        astro_summary=session.astro_summary,
        psychology=build_psychology_context(intent),
        response_style={
            "persona": "TELEPAT astropsychologist",
            "tone": "calm, intelligent, empathic",
            "verbosity": "concise",
        },
    )
