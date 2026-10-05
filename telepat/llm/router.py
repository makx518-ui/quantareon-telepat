from __future__ import annotations

from telepat.config.settings import settings
from .base import ConversationProvider
from .fallback import FallbackConversationProvider
from .gemini import GeminiConversationProvider
from .groq import GroqConversationProvider
from .mock import MockConversationProvider


class LLMRouter:
    """Resolve the visible conversational model without coupling core logic."""

    def __init__(self) -> None:
        mock = MockConversationProvider()
        groq = GroqConversationProvider()
        gemini = GeminiConversationProvider()

        self._providers: dict[str, ConversationProvider] = {
            "mock": mock,
            "groq": groq,
            "gemini": gemini,
            "auto": FallbackConversationProvider([groq, gemini, mock]),
        }

    def register(self, provider: ConversationProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str | None = None) -> ConversationProvider:
        provider_name = (name or settings.conversation_provider or "auto").lower()
        return self._providers.get(provider_name, self._providers["auto"])


llm_router = LLMRouter()
