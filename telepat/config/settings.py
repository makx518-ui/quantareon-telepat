from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    env: str = os.getenv("TELEPAT_ENV", "development")

    # Visible conversational agent. "auto" currently prefers Groq, then Gemini,
    # then the local mock. The provider can be changed without touching core.
    conversation_provider: str = os.getenv(
        "TELEPAT_CONVERSATION_PROVIDER", "auto"
    )

    # Provider-specific model ids.
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    gemini_model: str = os.getenv("GEMINI_MODEL", "")

    # Astrofractal interpretation is intentionally a separate AI role.
    astro_provider: str = os.getenv("TELEPAT_ASTRO_PROVIDER", "gemini")
    astro_model: str = os.getenv("TELEPAT_ASTRO_MODEL", "")

    # Existing remote memory service will be connected through MemoryAdapter.
    memory_api_url: str = os.getenv("MEMORY_API_URL", "")


settings = Settings()
