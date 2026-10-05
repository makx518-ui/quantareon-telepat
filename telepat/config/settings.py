from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    env: str = os.getenv("TELEPAT_ENV", "development")
    conversation_provider: str = os.getenv("TELEPAT_CONVERSATION_PROVIDER", "mock")
    conversation_model: str = os.getenv("TELEPAT_CONVERSATION_MODEL", "")
    astro_provider: str = os.getenv("TELEPAT_ASTRO_PROVIDER", "gemini")
    memory_api_url: str = os.getenv("MEMORY_API_URL", "")


settings = Settings()
