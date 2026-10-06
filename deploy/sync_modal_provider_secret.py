from __future__ import annotations

import os

import modal


SECRET_NAME = "quantareon-telepat-secrets"

PROVIDER_KEYS = (
    # Provider credentials.
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPGRAM_API_KEY",
    "YANDEX_SPEECHKIT_API_KEY",
    "YANDEX_IAM_TOKEN",
    "YANDEX_FOLDER_ID",
    "AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION",
    "MEMORY_API_URL",
    "MEMORY_API_KEY",

    # Provider/model routing.
    "MEMORY_API_AUTH_HEADER",
    "MEMORY_API_AUTH_SCHEME",
    "TELEPAT_CLAUDE_MODEL",
    "TELEPAT_CONVERSATION_PROVIDER",
    "TELEPAT_CONVERSATION_MODEL",
    "TELEPAT_GEMINI_MODEL",
    "TELEPAT_GROQ_MODEL",
    "TELEPAT_OPENAI_MODEL",
    "TELEPAT_ASTRO_MODEL",

    # Voice identity/tuning.
    "YANDEX_TTS_VOICE",
    "YANDEX_TTS_EMOTION",
    "YANDEX_TTS_SPEED",
    "AZURE_TTS_VOICE",
    "AZURE_TTS_STYLE",

    # Privacy and memory policy.
    "TELEPAT_MEMORY_RECALL_ENABLED",
    "TELEPAT_MEMORY_STORE_ENABLED",

    # Web/runtime policy.
    "TELEPAT_ENV",
    "TELEPAT_CORS_ORIGINS",
    "TELEPAT_RATE_LIMIT_WINDOW_SECONDS",
    "TELEPAT_RATE_LIMIT_MAX_ENTRIES",
    "TELEPAT_CHAT_RPM",
    "TELEPAT_ASTRO_RPM",
    "TELEPAT_VOICE_CONNECT_RPM",
    "TELEPAT_VOICE_IDLE_TIMEOUT_SECONDS",
    "TELEPAT_VOICE_MAX_SESSION_SECONDS",

    # Session / observability policy.
    "TELEPAT_METRICS_SAMPLE_LIMIT",
    "TELEPAT_SESSION_TTL_SECONDS",
    "TELEPAT_MAX_SESSIONS",
    "TELEPAT_MAX_HISTORY_TURNS",
    "TELEPAT_IDEMPOTENCY_ENTRIES",
    "TELEPAT_USAGE_MAX_SESSIONS",
    "TELEPAT_USAGE_TTL_SECONDS",
    "TELEPAT_COST_RATES_JSON",

    # Avatar readiness metadata. GPU registration remains a deploy concern.
    "TELEPAT_AVATAR_ENGINE",
    "TELEPAT_AVATAR_GPU_ENABLED",
)


def collect_provider_values() -> dict[str, str]:
    values = {
        key: value.strip()
        for key in PROVIDER_KEYS
        if (value := os.getenv(key, "")).strip()
    }

    # Harmless marker ensures the named container can be created before
    # provider credentials are attached.
    values["TELEPAT_PROVIDER_SECRET_MANAGED"] = "1"
    return values


def sync_provider_secret() -> tuple[str, int]:
    values = collect_provider_values()
    existing = {
        secret.name
        for secret in modal.Secret.objects.list()
    }

    if SECRET_NAME in existing:
        modal.Secret.from_name(SECRET_NAME).update(values)
        action = "updated"
    else:
        modal.Secret.objects.create(SECRET_NAME, values)
        action = "created"

    return action, len(values)


def main() -> None:
    action, count = sync_provider_secret()
    # Report metadata only; never print values.
    print(
        f"Modal provider secret {action}; "
        f"{count} non-empty configuration entries synchronized."
    )


if __name__ == "__main__":
    main()
