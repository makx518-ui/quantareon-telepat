from __future__ import annotations

import asyncio
import os

from telepat.config.prompt_loader import load_prompt
from telepat.config.settings import settings
from telepat.core.models import ContextPacket

from .base import ConversationProvider, ConversationResult, ProviderUsage
from .prompt import build_context_payload


def _normalize_gemini_usage(usage) -> ProviderUsage:
    total_input = int(
        getattr(usage, "total_input_tokens", 0) or 0
    )
    cached_input = int(
        getattr(usage, "total_cached_tokens", 0) or 0
    )
    cached_input = min(
        max(0, cached_input),
        max(0, total_input),
    )

    return ProviderUsage(
        input_tokens=max(0, total_input - cached_input),
        output_tokens=int(
            getattr(usage, "total_output_tokens", 0) or 0
        ),
        cached_input_tokens=cached_input,
        # Gemini reports thinking separately from output tokens and prices
        # generated thinking in addition to visible output.
        thought_tokens=int(
            getattr(usage, "total_thought_tokens", 0) or 0
        ),
    )


class GeminiConversationProvider(ConversationProvider):
    name = "gemini"

    @property
    def configured(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    async def generate(self, context: ContextPacket) -> ConversationResult:
        if not self.configured:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        model = settings.model_for("gemini", settings.gemini_model)
        prompt = build_context_payload(context)
        system_instruction = load_prompt("telepat.md")

        def _call() -> ConversationResult:
            from google import genai

            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            interaction = client.interactions.create(
                model=model,
                input=prompt,
                system_instruction=system_instruction,
                store=False,
            )
            text = (interaction.output_text or "").strip()
            if not text:
                raise RuntimeError("Gemini returned an empty response")

            usage = getattr(interaction, "usage", None)

            return ConversationResult(
                text=text,
                model=str(getattr(interaction, "model", None) or model),
                usage=_normalize_gemini_usage(usage),
            )

        return await asyncio.to_thread(_call)
