from __future__ import annotations

import os
from typing import Any

import httpx

from telepat.config.prompt_loader import load_prompt
from telepat.config.settings import settings
from telepat.core.models import ContextPacket

from .base import ConversationProvider
from .prompt import build_context_payload


def _extract_claude_text(data: dict[str, Any]) -> str:
    parts: list[str] = []

    for block in data.get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = str(block.get("text") or "").strip()
            if text:
                parts.append(text)

    return "\n".join(parts).strip()


class ClaudeConversationProvider(ConversationProvider):
    name = "claude"
    endpoint = "https://api.anthropic.com/v1/messages"

    @property
    def configured(self) -> bool:
        return bool(
            os.getenv("ANTHROPIC_API_KEY")
            and settings.claude_model
        )

    async def generate(self, context: ContextPacket) -> str:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        if not settings.claude_model:
            raise RuntimeError("TELEPAT_CLAUDE_MODEL is not configured")

        model = settings.conversation_model or settings.claude_model
        payload = {
            "model": model,
            "max_tokens": 1200,
            "system": load_prompt("telepat.md"),
            "messages": [
                {
                    "role": "user",
                    "content": build_context_payload(context),
                }
            ],
        }
        headers = {
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
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

        text = _extract_claude_text(data)
        if not text:
            raise RuntimeError("Claude returned an empty response")
        return text
