from __future__ import annotations

import logging

from telepat.config.settings import settings
from telepat.core.models import ContextPacket

from .base import ConversationProvider
from .claude import ClaudeConversationProvider
from .gemini import GeminiConversationProvider
from .groq import GroqConversationProvider
from .mock import MockConversationProvider
from .openai import OpenAIConversationProvider


logger = logging.getLogger(__name__)


class LLMRouter:
    """Select a provider and return the real provider name used."""

    def __init__(self) -> None:
        providers: list[ConversationProvider] = [
            GroqConversationProvider(),
            GeminiConversationProvider(),
            OpenAIConversationProvider(),
            ClaudeConversationProvider(),
            MockConversationProvider(),
        ]
        self._providers = {provider.name: provider for provider in providers}

    def register(self, provider: ConversationProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ConversationProvider | None:
        return self._providers.get(name.lower())

    def _order(self, requested: str | None = None) -> list[str]:
        name = (requested or settings.conversation_provider or "auto").lower()
        if name != "auto":
            fallbacks = [
                item for item in settings.conversation_fallbacks
                if item != name
            ]
            return [name, *fallbacks]
        return list(settings.conversation_fallbacks)

    async def generate(
        self,
        context: ContextPacket,
        *,
        provider: str | None = None,
    ) -> tuple[str, str]:
        errors: list[str] = []

        for name in self._order(provider):
            candidate = self.get(name)
            if candidate is None:
                continue
            if not candidate.configured:
                continue

            try:
                text = await candidate.generate(context)
                return text, candidate.name
            except Exception as exc:
                logger.warning(
                    "LLM provider %s failed: %s",
                    candidate.name,
                    type(exc).__name__,
                )
                errors.append(f"{candidate.name}:{type(exc).__name__}")

        raise RuntimeError(
            "No conversation provider succeeded"
            + (f" ({', '.join(errors)})" if errors else "")
        )


llm_router = LLMRouter()
