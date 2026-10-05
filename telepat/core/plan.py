from __future__ import annotations

from dataclasses import dataclass

from .models import Intent


@dataclass(frozen=True, slots=True)
class OrchestrationPlan:
    intent: Intent
    use_memory: bool
    use_astro: bool
    psychology_level: str
    avatar_state: str
    response_mode: str


def build_plan(intent: Intent) -> OrchestrationPlan:
    if intent in {"astropsychology", "follow_up_astro"}:
        return OrchestrationPlan(
            intent=intent,
            use_memory=True,
            use_astro=True,
            psychology_level="full",
            avatar_state="thinking",
            response_mode="astropsychology",
        )

    if intent == "personal_reflection":
        return OrchestrationPlan(
            intent=intent,
            use_memory=True,
            use_astro=True,
            psychology_level="full",
            avatar_state="listening",
            response_mode="reflection",
        )

    if intent == "factual_user_memory":
        return OrchestrationPlan(
            intent=intent,
            use_memory=True,
            use_astro=False,
            psychology_level="light",
            avatar_state="listening",
            response_mode="memory",
        )

    if intent == "system_action":
        return OrchestrationPlan(
            intent=intent,
            use_memory=False,
            use_astro=False,
            psychology_level="none",
            avatar_state="idle",
            response_mode="system",
        )

    return OrchestrationPlan(
        intent=intent,
        use_memory=True,
        use_astro=False,
        psychology_level="light",
        avatar_state="idle",
        response_mode="conversation",
    )
