from __future__ import annotations

import os

from telepat.astro.gemini_interpreter import gemini_astro_interpreter
from telepat.memory.service import memory_adapter
from telepat.voice.microsoft_tts import microsoft_tts
from telepat.voice.yandex_tts import yandex_tts


def provider_status() -> dict[str, bool]:
    """Return provider configuration readiness without exposing credentials."""
    return {
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
        "astro_gemini": gemini_astro_interpreter.configured,
        "deepgram": bool(os.getenv("DEEPGRAM_API_KEY")),
        "yandex_ermil": yandex_tts.configured,
        "microsoft_andrew": microsoft_tts.configured,
        "memory": memory_adapter.configured,
    }


def readiness_status() -> dict[str, object]:
    """Expose capability readiness separately from basic process health.

    TELEPAT's deterministic core can be healthy before external providers are
    attached. Consumers can use this endpoint to decide whether to enable live
    voice, real LLM conversation, Astro interpretation and persistent memory.
    """
    providers = provider_status()

    conversation_ready = bool(
        providers["gemini"]
        or providers["groq"]
        or providers["openai"]
        or providers["claude"]
    )
    voice_output_ready = bool(
        providers["yandex_ermil"]
        or providers["microsoft_andrew"]
    )
    voice_input_ready = bool(providers["deepgram"])
    astro_interpreter_ready = bool(providers["astro_gemini"])
    memory_ready = bool(providers["memory"])

    return {
        "core_ready": True,
        "conversation_ready": conversation_ready,
        "astro_engine_ready": True,
        "astro_interpreter_ready": astro_interpreter_ready,
        "voice_input_ready": voice_input_ready,
        "voice_output_ready": voice_output_ready,
        "memory_ready": memory_ready,
        "live_voice_ready": (
            conversation_ready
            and voice_input_ready
            and voice_output_ready
        ),
        "full_telepat_ready": (
            conversation_ready
            and astro_interpreter_ready
            and voice_input_ready
            and voice_output_ready
        ),
        "providers": providers,
    }
