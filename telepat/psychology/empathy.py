from __future__ import annotations

from .state import PsychologicalState


def empathy_guidance(state: PsychologicalState) -> dict[str, str]:
    common = {
        "principle": (
            "Acknowledge the user's concern without claiming to know more "
            "about their inner state than they said."
        )
    }

    if state.label == "anxious":
        return {
            **common,
            "tone": "steady, grounding, unhurried",
            "avoid": "catastrophizing, certainty, excessive mystical framing",
        }
    if state.label == "sad":
        return {
            **common,
            "tone": "gentle, respectful, not artificially cheerful",
            "avoid": "platitudes and premature solutions",
        }
    if state.label == "angry":
        return {
            **common,
            "tone": "calm, clear, non-defensive",
            "avoid": "mirroring hostility or escalating language",
        }
    if state.label == "confused":
        return {
            **common,
            "tone": "structured, clarifying, patient",
            "avoid": "too many interpretations at once",
        }
    if state.label == "hopeful":
        return {
            **common,
            "tone": "warm, measured, constructive",
            "avoid": "overpromising outcomes",
        }

    return {
        **common,
        "tone": "calm, attentive, natural",
        "avoid": "performative empathy",
    }
