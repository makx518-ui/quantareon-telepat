from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from telepat.core.models import ContextPacket


_PROMPTS = Path(__file__).resolve().parents[1] / "config" / "prompts"


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    path = _PROMPTS / name
    return path.read_text(encoding="utf-8").strip()


def context_to_text(context: ContextPacket) -> str:
    history = [
        {"role": turn.role, "content": turn.content}
        for turn in context.conversation_history[-10:]
    ]
    payload = {
        "language": context.language,
        "intent": context.intent,
        "user_memory": context.user_memory,
        "astro_summary": context.astro_summary,
        "psychology": context.psychology,
        "recent_history": history,
        "current_message": context.current_message,
        "response_style": context.response_style,
    }
    return json.dumps(payload, ensure_ascii=False, default=str)


def build_conversation_prompt(context: ContextPacket) -> str:
    persona = load_prompt("telepat.md")
    return (
        f"{persona}\n\n"
        "Below is an internal context packet. Use it as context, not as text to quote.\n"
        f"{context_to_text(context)}\n\n"
        "Respond only with TELEPAT's user-facing reply."
    )
