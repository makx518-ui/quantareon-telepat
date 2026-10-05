from __future__ import annotations

from typing import Any


def _trim_text(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "…"


def compact_memory(data: dict[str, Any]) -> dict[str, Any]:
    """Bound memory context before it reaches the conversational model."""
    if not data:
        return {}

    facts = []
    for fact in (data.get("facts") or [])[:30]:
        if isinstance(fact, dict):
            facts.append(
                {
                    "key": _trim_text(fact.get("key"), 120),
                    "value": _trim_text(fact.get("value"), 500),
                }
            )

    semantic = []
    for item in (data.get("semantic_context") or [])[:5]:
        if isinstance(item, dict):
            semantic.append(
                {
                    "text": _trim_text(item.get("text"), 800),
                    "score": item.get("score"),
                }
            )
        else:
            semantic.append({"text": _trim_text(item, 800)})

    recent = []
    for item in (data.get("recent_messages") or [])[-10:]:
        if isinstance(item, dict):
            recent.append(
                {
                    "role": _trim_text(item.get("role"), 20),
                    "content": _trim_text(item.get("content"), 800),
                }
            )

    return {
        "context_text": _trim_text(data.get("context_text"), 5000),
        "facts": facts,
        "emotion": data.get("emotion"),
        "insights": (data.get("insights") or [])[:4],
        "semantic_context": semantic,
        "resonance_context": _trim_text(data.get("resonance_context"), 1200),
        "pattern_summary": _trim_text(data.get("pattern_summary"), 1200),
        "recent_messages": recent,
    }
