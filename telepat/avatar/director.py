from __future__ import annotations

import hashlib

from telepat.core.models import Intent

from .states import AvatarState


def _bucket(seed: str) -> int:
    digest = hashlib.blake2s(seed.encode("utf-8"), digest_size=2).digest()
    return int.from_bytes(digest, "big") % 100


def select_speaking_state(
    *,
    intent: Intent,
    user_message: str,
    reply: str,
    session_id: str,
) -> AvatarState:
    """Choose restrained body language without another AI call.

    TELEPAT should not gesture on every answer. The choice is deterministic for
    a given turn, easy to test and cheap to run.
    """
    score = _bucket(f"{session_id}|{user_message}|{reply[:300]}")

    # Long reflective answers can occasionally use the thoughtful pose.
    if intent == "personal_reflection":
        if score < 22:
            return "hand_chin"
        if score < 34:
            return "lean_forward"
        return "speaking"

    # Astro interpretation benefits from a small explanatory gesture, but most
    # of the time TELEPAT remains composed.
    if intent in {"astropsychology", "follow_up_astro"}:
        if score < 20:
            return "light_gesture"
        if score < 30:
            return "hand_chin"
        return "speaking"

    # Explicit recollection often reads better with a small acknowledgement.
    if intent == "factual_user_memory":
        return "nod" if score < 25 else "speaking"

    # Casual positive replies may very occasionally soften the expression.
    lowered = reply.lower()
    positive = any(
        token in lowered
        for token in ("рад", "хорош", "отлич", "glad", "good", "great")
    )
    if positive and score < 18:
        return "soft_smile"

    # Short direct replies can use a restrained nod.
    if len(reply) < 180 and score < 12:
        return "nod"

    return "speaking"
