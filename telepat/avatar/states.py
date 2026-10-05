from __future__ import annotations

from typing import Literal


AvatarState = Literal[
    "idle",
    "listening",
    "thinking",
    "nod",
    "hand_chin",
    "light_gesture",
    "lean_forward",
    "soft_smile",
    "speaking",
]


def state_for_intent(intent: str) -> AvatarState:
    if intent in {"astropsychology", "follow_up_astro"}:
        return "thinking"
    if intent in {"personal_reflection", "factual_user_memory"}:
        return "listening"
    return "idle"
