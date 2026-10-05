from __future__ import annotations

import os

from telepat.astro.gemini_interpreter import gemini_astro_interpreter
from telepat.memory.service import memory_adapter
from telepat.voice.microsoft_tts import microsoft_tts
from telepat.voice.yandex_tts import yandex_tts


def provider_status() -> dict[str, bool]:
    """Return connection readiness without exposing any credential values."""
    return {
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "astro_gemini": gemini_astro_interpreter.configured,
        "deepgram": bool(os.getenv("DEEPGRAM_API_KEY")),
        "yandex_ermil": yandex_tts.configured,
        "microsoft_andrew": microsoft_tts.configured,
        "memory": memory_adapter.configured,
    }
