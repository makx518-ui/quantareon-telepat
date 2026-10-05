from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip().lower() for item in raw.split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    env: str = os.getenv("TELEPAT_ENV", "development")

    conversation_provider: str = os.getenv("TELEPAT_CONVERSATION_PROVIDER", "gemini").lower()
    conversation_fallbacks: tuple[str, ...] = _csv(
        "TELEPAT_CONVERSATION_FALLBACKS", "groq,mock"
    )
    conversation_model: str = os.getenv("TELEPAT_CONVERSATION_MODEL", "")

    gemini_model: str = os.getenv("TELEPAT_GEMINI_MODEL", "gemini-3.8-flash")
    groq_model: str = os.getenv("TELEPAT_GROQ_MODEL", "openai/gpt-oss-120b")

    astro_provider: str = os.getenv("TELEPAT_ASTRO_PROVIDER", "gemini").lower()
    astro_model: str = os.getenv("TELEPAT_ASTRO_MODEL", "gemini-3.8-flash")

    memory_api_url: str = os.getenv("MEMORY_API_URL", "")


settings = Settings()
