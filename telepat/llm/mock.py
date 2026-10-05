from __future__ import annotations

from telepat.core.models import ContextPacket
from .base import ConversationProvider


class MockConversationProvider(ConversationProvider):
    name = "mock"

    async def generate(self, context: ContextPacket) -> str:
        if context.language.lower().startswith("ru"):
            if context.intent in {"astropsychology", "follow_up_astro"}:
                return (
                    "Я слышу твой вопрос. Астропсихологический слой пока подключён в режиме "
                    "каркаса: расчёт Astrofractal будет следующим этапом. Сам диалоговый контур TELEPAT уже работает."
                )
            if context.intent == "personal_reflection":
                return (
                    "Я рядом с твоим вопросом и не буду торопиться с выводами. "
                    "Расскажи чуть подробнее, что именно сейчас кажется самым важным."
                )
            return "TELEPAT на связи. Текстовый контур работает, можем подключать следующий слой."
        return "TELEPAT is online. The text conversation pipeline is working."
