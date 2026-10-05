from __future__ import annotations


def communication_guidance(
    *,
    language: str,
    response_mode: str,
) -> dict[str, str]:
    guidance = {
        "spoken_style": (
            "Use natural spoken sentences suitable for TTS. "
            "Prefer one clear idea at a time."
        ),
        "questions": (
            "Ask at most one useful follow-up question unless the user "
            "explicitly asks for a detailed analysis."
        ),
        "length": "short-to-medium by default",
    }

    if response_mode == "astropsychology":
        guidance["structure"] = (
            "Start from the user's lived concern, then connect the relevant "
            "Astrofractal pattern, then return to practical reflection."
        )
    elif response_mode == "reflection":
        guidance["structure"] = (
            "Reflect the core concern, offer one interpretation or distinction, "
            "then invite the next useful step."
        )
    else:
        guidance["structure"] = "Answer directly without ceremonial framing."

    guidance["language"] = language
    return guidance
