from __future__ import annotations

import os

import httpx

from telepat.config.settings import settings
from telepat.core.models import ContextPacket

from .base import ConversationProvider, ConversationResult, ProviderUsage
from .prompt import build_chat_messages


class GroqConversationProvider(ConversationProvider):
    name = "groq"
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def configured(self) -> bool:
        return bool(os.getenv("GROQ_API_KEY"))

    async def generate(self, context: ContextPacket) -> ConversationResult:
        if not self.configured:
            raise RuntimeError("GROQ_API_KEY is not configured")

        model = settings.model_for("groq", settings.groq_model)
        payload = {
            "model": model,
            "messages": build_chat_messages(context),
            "temperature": 0.55,
            "max_completion_tokens": 1200,
        }
        headers = {
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Groq returned no choices")

        text = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not text:
            raise RuntimeError("Groq returned an empty response")

        usage = data.get("usage") or {}
        prompt_details = usage.get("prompt_tokens_details") or {}

        return ConversationResult(
            text=text,
            model=model,
            usage=ProviderUsage(
                input_tokens=int(usage.get("prompt_tokens") or 0),
                output_tokens=int(usage.get("completion_tokens") or 0),
                cached_input_tokens=int(
                    prompt_details.get("cached_tokens") or 0
                ),
            ),
        )
