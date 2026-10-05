from __future__ import annotations

import os

import httpx

from telepat.core.models import ContextPacket
from .base import ConversationProvider
from .prompt import build_system_prompt


class GeminiConversationProvider(ConversationProvider):
    name = "gemini"

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def generate(self, context: ContextPacket) -> str:
        if not self.configured:
            raise RuntimeError("Gemini provider is not configured")

        contents: list[dict] = []
        for turn in context.conversation_history:
            role = "model" if turn.role == "assistant" else "user"
            contents.append(
                {
                    "role": role,
                    "parts": [{"text": turn.content}],
                }
            )

        if not contents or (
            contents[-1].get("role") != "user"
            or contents[-1]["parts"][0].get("text") != context.current_message
        ):
            contents.append(
                {"role": "user", "parts": [{"text": context.current_message}]}
            )

        payload = {
            "systemInstruction": {
                "parts": [{"text": build_system_prompt(context)}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.55,
                "maxOutputTokens": 1200,
            },
        }

        url = f"{self.base_url}/models/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no candidates")

        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text
