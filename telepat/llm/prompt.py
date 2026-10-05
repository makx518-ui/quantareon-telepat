from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from telepat.core.models import ContextPacket


_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "config" / "prompts"


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def build_context_payload(context: ContextPacket) -> str:
    history = [
        {"role": turn.role, "content": turn.content}
        for turn in context.conversation_history[-10:]
    ]
    payload = {
        "language": context.language,
        "intent": context.intent,
        "psychology": context.psychology,
        "response_style": context.response_style,
        "user_memory": context.user_memory,
        "astrofractal_summary": context.astro_summary,
        "recent_history": history,
        "current_message": context.current_message,
    }
    return (
        "INTERNAL CONTEXT PACKET — use it, do not quote its structure:\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
        + "\n\nReply only to the user."
    )


def build_chat_messages(context: ContextPacket) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": load_prompt("telepat.md")}
    ]

    # Groq/OpenAI-style APIs receive the normalized history directly.
    for turn in context.conversation_history[-10:]:
        role = "assistant" if turn.role == "assistant" else "user"
        messages.append({"role": role, "content": turn.content})

    # Add internal context as the final user payload. The visible current
    # message is already included inside the packet.
    messages.append({"role": "user", "content": build_context_payload(context)})
    return messages
