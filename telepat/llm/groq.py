from __future__ import annotations

import os

import httpx

from telepat.core.models import ContextPacket
from .base import ConversationProvider
from .prompt import build_chat_messages


class GroqConversationProvider(ConversationProvider):
    name = "groq"

    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def generate(self, context: ContextPacket) -> str:
        if not self.configured:
            raise RuntimeError("Groq provider is not configured")

        payload = {
            "model": self.model,
            "messages": build_chat_messages(context),
            "temperature": 0.55,
            "max_completion_tokens": 1200,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Groq returned no choices")

        text = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not text:
            raise RuntimeError("Groq returned an empty response")
        return text
