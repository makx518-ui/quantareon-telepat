from __future__ import annotations

from telepat.core.models import ContextPacket
from .base import ConversationProvider, ConversationResult


class MockConversationProvider(ConversationProvider):
    name = "mock"

    async def generate(self, context: ContextPacket) -> ConversationResult:
        if context.language.lower().startswith("ru"):
            if context.intent in {"astropsychology", "follow_up_astro"}:
                text = (
                    "Я слышу твой вопрос. Астропсихологический слой пока подключён в режиме "
                    "каркаса: расчёт Astrofractal будет следующим этапом. Сам диалоговый контур TELEPAT уже работает."
                )
            elif context.intent == "personal_reflection":
                text = (
                    "Я рядом с твоим вопросом и не буду торопиться с выводами. "
                    "Расскажи чуть подробнее, что именно сейчас кажется самым важным."
                )
            else:
                text = "TELEPAT на связи. Текстовый контур работает, можем подключать следующий слой."
        else:
            text = "TELEPAT is online. The text conversation pipeline is working."

        return ConversationResult(
            text=text,
            model="mock",
        )
