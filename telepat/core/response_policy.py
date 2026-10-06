from __future__ import annotations

import os
import re
from dataclasses import dataclass


class ResponsePolicyError(RuntimeError):
    """Conversation provider produced no usable user-facing response."""


@dataclass(frozen=True, slots=True)
class ResponsePolicyResult:
    text: str
    truncated: bool
    duplicate_paragraphs_removed: int


def _max_reply_chars() -> int:
    try:
        value = int(os.getenv("TELEPAT_MAX_REPLY_CHARS", "6000"))
    except ValueError:
        value = 6000
    return max(200, value)


def _dedupe_consecutive_paragraphs(text: str) -> tuple[str, int]:
    paragraphs = [
        part.strip()
        for part in re.split(r"\n\s*\n", text)
        if part.strip()
    ]

    output: list[str] = []
    removed = 0
    previous_key: str | None = None

    for paragraph in paragraphs:
        key = re.sub(r"\s+", " ", paragraph).strip().casefold()
        if key and key == previous_key:
            removed += 1
            continue
        output.append(paragraph)
        previous_key = key

    return "\n\n".join(output), removed


def _truncate_at_boundary(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False

    candidate = text[:limit]
    floor = max(0, int(limit * 0.55))

    boundary = -1
    for marker in (". ", "! ", "? ", "。", "！", "？", "\n"):
        position = candidate.rfind(marker, floor)
        if position > boundary:
            boundary = position + len(marker.rstrip())

    if boundary < floor:
        space = candidate.rfind(" ", floor)
        boundary = space if space >= floor else limit

    trimmed = candidate[:boundary].rstrip(" \t\r\n.,;:!?")
    if not trimmed:
        trimmed = candidate.rstrip()

    return trimmed + "…", True


def apply_response_policy(
    text: str,
    *,
    max_chars: int | None = None,
) -> ResponsePolicyResult:
    """Normalize one TELEPAT reply without another model call."""
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()

    if not normalized:
        raise ResponsePolicyError("Conversation provider returned an empty reply")

    normalized, removed = _dedupe_consecutive_paragraphs(normalized)

    limit = max_chars if max_chars is not None else _max_reply_chars()
    limit = max(200, int(limit))
    normalized, truncated = _truncate_at_boundary(normalized, limit)

    if not normalized.strip():
        raise ResponsePolicyError("Conversation reply became empty after policy")

    return ResponsePolicyResult(
        text=normalized,
        truncated=truncated,
        duplicate_paragraphs_removed=removed,
    )
