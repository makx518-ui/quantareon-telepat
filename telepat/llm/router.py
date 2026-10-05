from __future__ import annotations

from telepat.config.settings import settings

from .base import ConversationProvider
from .fallback import FallbackConversationProvider
from .gemini import GeminiConversationProvider
from .groq import GroqConversationProvider
from .mock import MockConversationProvider


class LLMRouter:
    """Resolve conversational provider without coupling core logic."""

    def __init__(self) -> None:
        providers: list[ConversationProvider] = [
            GroqConversationProvider(),
            GeminiConversationProvider(),
            MockConversationProvider(),
        ]
        self._providers = {provider.name: provider for provider in providers}
        self._providers["auto"] = self._build_auto()

    def _build_auto(self) -> ConversationProvider:
        ordered: list[ConversationProvider] = []
        for name in settings.conversation_fallbacks:
            provider = self._providers.get(name)
            if provider is not None and provider not in ordered:
                ordered.append(provider)

        if not ordered:
            ordered.append(self._providers["mock"])

        return FallbackConversationProvider(ordered)

    def register(self, provider: ConversationProvider) -> None:
        self._providers[provider.name] = provider
        self._providers["auto"] = self._build_auto()

    def get(self, name: str | None = None) -> ConversationProvider:
        provider_name = (
            name or settings.conversation_provider or "auto"
        ).lower()
        return self._providers.get(provider_name, self._providers["auto"])


llm_router = LLMRouter()
