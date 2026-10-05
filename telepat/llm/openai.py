from __future__ import annotations

import os
from typing import Any

import httpx

from telepat.config.prompt_loader import load_prompt
from telepat.config.settings import settings
from telepat.core.models import ContextPacket

from .base import ConversationProvider
from .prompt import build_context_payload


def _extract_response_text(data: dict[str, Any]) -> str:
    parts: list[str] = []

    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "output_text":
                text = str(block.get("text") or "").strip()
                if text:
                    parts.append(text)

    return "\n".join(parts).strip()


class OpenAIConversationProvider(ConversationProvider):
    name = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    @property
    def configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    async def generate(self, context: ContextPacket) -> str:
        if not self.configured:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        model = settings.model_for("openai", settings.openai_model)
        payload = {
            "model": model,
            "instructions": load_prompt("telepat.md"),
            "input": build_context_payload(context),
            "max_output_tokens": 1200,
            "store": False,
        }
        headers = {
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        text = _extract_response_text(data)
        if not text:
            raise RuntimeError("OpenAI returned an empty response")
        return text
