from __future__ import annotations

import logging

from telepat.core.models import ContextPacket
from .base import ConversationProvider


logger = logging.getLogger(__name__)


class FallbackConversationProvider(ConversationProvider):
    """Try configured providers in order and keep the visible API stable."""

    name = "fallback"

    def __init__(self, providers: list[ConversationProvider]) -> None:
        self.providers = providers

    async def generate(self, context: ContextPacket) -> str:
        errors: list[str] = []

        for provider in self.providers:
            configured = getattr(provider, "configured", True)
            if not configured:
                continue
            try:
                return await provider.generate(context)
            except Exception as exc:
                logger.warning("LLM provider %s failed: %s", provider.name, exc)
                errors.append(f"{provider.name}: {type(exc).__name__}")

        raise RuntimeError(
            "No conversation provider succeeded"
            + (f" ({', '.join(errors)})" if errors else "")
        )
