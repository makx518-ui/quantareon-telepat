from __future__ import annotations

from typing import Any

from telepat.core.models import Intent
from telepat.core.plan import OrchestrationPlan

from .communication import communication_guidance
from .empathy import empathy_guidance
from .integrator import integrator_rules
from .state import infer_state


def build_psychology_context(
    *,
    message: str,
    language: str,
    plan: OrchestrationPlan,
) -> dict[str, Any]:
    if plan.psychology_level == "none":
        return {}

    state = infer_state(message)

    context: dict[str, Any] = {
        "state_hint": {
            "label": state.label,
            "confidence": state.confidence,
            "cues": list(state.cues),
            "disclaimer": "communication cue only; not a diagnosis",
        },
        "empathy": empathy_guidance(state),
        "communication": communication_guidance(
            language=language,
            response_mode=plan.response_mode,
        ),
        "integrator": integrator_rules(),
    }

    if plan.psychology_level == "light":
        # Keep casual turns cheap and compact.
        context.pop("state_hint", None)

    return context
