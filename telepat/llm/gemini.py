from __future__ import annotations

import asyncio
import os

from telepat.config.prompt_loader import load_prompt
from telepat.config.settings import settings
from telepat.core.models import ContextPacket

from .base import ConversationProvider
from .prompt import build_context_payload


class GeminiConversationProvider(ConversationProvider):
    name = "gemini"

    @property
    def configured(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    async def generate(self, context: ContextPacket) -> str:
        if not self.configured:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        model = settings.conversation_model or settings.gemini_model
        prompt = build_context_payload(context)
        system_instruction = load_prompt("telepat.md")

        def _call() -> str:
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
            return text

        return await asyncio.to_thread(_call)
