from __future__ import annotations

import json

from telepat.config.prompt_loader import load_prompt
from telepat.core.models import ContextPacket


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

    for turn in context.conversation_history[-10:]:
        role = "assistant" if turn.role == "assistant" else "user"
        messages.append({"role": role, "content": turn.content})

    messages.append(
        {"role": "user", "content": build_context_payload(context)}
    )
    return messages
