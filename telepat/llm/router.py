from __future__ import annotations

import logging
from time import perf_counter

from telepat.config.settings import settings
from telepat.core.models import ContextPacket
from telepat.observability.metrics import runtime_metrics
from telepat.observability.usage import usage_registry

from .base import ConversationProvider, ConversationResult
from .claude import ClaudeConversationProvider
from .gemini import GeminiConversationProvider
from .groq import GroqConversationProvider
from .mock import MockConversationProvider
from .openai import OpenAIConversationProvider


logger = logging.getLogger(__name__)


class ConversationUnavailableError(RuntimeError):
    """Configured conversation providers exist but none can answer."""


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
        order = self._order(provider)

        explicit_name = (
            provider
            or settings.conversation_provider
            or "auto"
        ).lower()
        explicit_mock = explicit_name == "mock"

        configured_real = {
            name
            for name in order
            if name != "mock"
            and (candidate := self.get(name)) is not None
            and candidate.configured
        }

        for name in order:
            candidate = self.get(name)
            if candidate is None:
                continue
            if not candidate.configured:
                continue

            # A configured real provider failing must surface as a real error,
            # not silently turn TELEPAT into the development mock persona.
            if (
                candidate.name == "mock"
                and configured_real
                and not explicit_mock
            ):
                continue

            started = perf_counter()
            try:
                result = await candidate.generate(context)
                if isinstance(result, str):
                    # Backward-compatible bridge for diagnostic/custom
                    # providers. Production providers return ConversationResult.
                    result = ConversationResult(
                        text=result,
                        model=candidate.name,
                    )

                runtime_metrics.record(
                    "llm",
                    (perf_counter() - started) * 1000,
                    ok=True,
                    provider=candidate.name,
                )
                usage_registry.record(
                    context.session_id,
                    provider=candidate.name,
                    model=result.model,
                    usage=result.usage,
                )
                return result.text, candidate.name
            except Exception as exc:
                runtime_metrics.record(
                    "llm",
                    (perf_counter() - started) * 1000,
                    ok=False,
                    provider=candidate.name,
                )
                logger.warning(
                    "LLM provider %s failed: %s",
                    candidate.name,
                    type(exc).__name__,
                )
                errors.append(f"{candidate.name}:{type(exc).__name__}")

        raise ConversationUnavailableError(
            "No conversation provider succeeded"
            + (f" ({', '.join(errors)})" if errors else "")
        )


llm_router = LLMRouter()
