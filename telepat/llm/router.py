from __future__ import annotations

from telepat.config.settings import settings
from .base import ConversationProvider
from .mock import MockConversationProvider


class LLMRouter:
    def __init__(self) -> None:
        self._providers: dict[str, ConversationProvider] = {
            "mock": MockConversationProvider(),
        }

    def register(self, provider: ConversationProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str | None = None) -> ConversationProvider:
        provider_name = (name or settings.conversation_provider or "mock").lower()
        return self._providers.get(provider_name, self._providers["mock"])


llm_router = LLMRouter()
