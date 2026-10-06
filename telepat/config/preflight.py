from __future__ import annotations

import json
import os
from typing import Any

from telepat.config.settings import settings


_REAL_CONVERSATION_PROVIDERS = {
    "groq",
    "gemini",
    "openai",
    "claude",
}
_ALLOWED_CONVERSATION_PROVIDERS = {
    "auto",
    "mock",
    *_REAL_CONVERSATION_PROVIDERS,
}


def _enabled(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _positive_number(
    name: str,
    *,
    default: str,
    allow_zero: bool = False,
) -> tuple[bool, float | None]:
    raw = os.getenv(name, default).strip()
    try:
        value = float(raw)
    except ValueError:
        return False, None

    if allow_zero:
        return value >= 0, value
    return value > 0, value


def _cost_rates_status() -> dict[str, Any]:
    raw = os.getenv("TELEPAT_COST_RATES_JSON", "").strip()
    if not raw or raw == "{}":
        return {
            "configured": False,
            "valid": True,
            "models": 0,
        }

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "configured": True,
            "valid": False,
            "models": 0,
            "error": "invalid_json",
        }

    if not isinstance(payload, dict):
        return {
            "configured": True,
            "valid": False,
            "models": 0,
            "error": "must_be_object",
        }

    allowed_rates = {
        "input",
        "cached_input",
        "cache_write",
        "output",
        "thought",
    }
    for model, rates in payload.items():
        if not isinstance(model, str) or not model.strip():
            return {
                "configured": True,
                "valid": False,
                "models": 0,
                "error": "invalid_model_id",
            }
        if not isinstance(rates, dict):
            return {
                "configured": True,
                "valid": False,
                "models": 0,
                "error": "invalid_rate_object",
            }
        for key, value in rates.items():
            if key not in allowed_rates:
                return {
                    "configured": True,
                    "valid": False,
                    "models": 0,
                    "error": "unknown_rate_key",
                }
            if not isinstance(value, (int, float)) or value < 0:
                return {
                    "configured": True,
                    "valid": False,
                    "models": 0,
                    "error": "invalid_rate_value",
                }

    return {
        "configured": True,
        "valid": True,
        "models": len(payload),
    }


def configuration_preflight() -> dict[str, Any]:
    """Validate TELEPAT runtime policy without exposing credential values."""
    errors: list[str] = []
    warnings: list[str] = []

    provider = settings.conversation_provider.strip().lower()
    if provider not in _ALLOWED_CONVERSATION_PROVIDERS:
        errors.append("conversation_provider_unknown")

    configured = {
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
    }

    if provider in _REAL_CONVERSATION_PROVIDERS:
        if not configured[provider]:
            errors.append("conversation_provider_key_missing")
        if not settings.model_for(
            provider,
            {
                "groq": settings.groq_model,
                "gemini": settings.gemini_model,
                "openai": settings.openai_model,
                "claude": settings.claude_model,
            }[provider],
        ):
            errors.append("conversation_provider_model_missing")

    if provider == "auto" and settings.conversation_model:
        warnings.append("conversation_model_ignored_in_auto")

    unknown_fallbacks = [
        name
        for name in settings.conversation_fallbacks
        if name not in _ALLOWED_CONVERSATION_PROVIDERS - {"auto"}
    ]
    if unknown_fallbacks:
        errors.append("conversation_fallback_unknown")

    if settings.astro_provider != "gemini":
        errors.append("astro_provider_must_be_gemini")
    if not settings.astro_model:
        errors.append("astro_model_missing")

    yandex_api = bool(os.getenv("YANDEX_SPEECHKIT_API_KEY"))
    yandex_iam = bool(os.getenv("YANDEX_IAM_TOKEN"))
    yandex_folder = bool(os.getenv("YANDEX_FOLDER_ID"))
    if yandex_iam != yandex_folder and not yandex_api:
        errors.append("yandex_iam_pair_incomplete")
    if yandex_api and yandex_iam and yandex_folder:
        warnings.append("yandex_multiple_auth_modes")

    azure_key = bool(os.getenv("AZURE_SPEECH_KEY"))
    azure_region = bool(os.getenv("AZURE_SPEECH_REGION"))
    if azure_key != azure_region:
        errors.append("azure_speech_pair_incomplete")

    memory_url = bool(os.getenv("MEMORY_API_URL", "").strip())
    memory_key = bool(os.getenv("MEMORY_API_KEY", "").strip())
    memory_header = os.getenv(
        "MEMORY_API_AUTH_HEADER",
        "Authorization",
    ).strip()
    recall_enabled = _enabled("TELEPAT_MEMORY_RECALL_ENABLED", "1")
    store_enabled = _enabled("TELEPAT_MEMORY_STORE_ENABLED", "1")

    if (recall_enabled or store_enabled) and not memory_url:
        warnings.append("memory_enabled_without_url")
    if memory_key and not memory_header:
        errors.append("memory_auth_header_missing")

    production = settings.env.strip().lower() == "production"
    cors_origins = settings.cors_origins
    if production and (not cors_origins or "*" in cors_origins):
        errors.append("production_cors_not_restricted")

    guards: dict[str, dict[str, Any]] = {}
    for name, default in (
        ("TELEPAT_CHAT_RPM", "30"),
        ("TELEPAT_ASTRO_RPM", "6"),
        ("TELEPAT_VOICE_CONNECT_RPM", "12"),
        ("TELEPAT_VOICE_IDLE_TIMEOUT_SECONDS", "120"),
        ("TELEPAT_VOICE_MAX_SESSION_SECONDS", "1800"),
        ("TELEPAT_VOICE_MAX_FRAME_BYTES", "65536"),
        ("TELEPAT_VOICE_MAX_CONTROL_CHARS", "4096"),
        ("TELEPAT_VOICE_MAX_REALTIME_FACTOR", "2.0"),
        ("TELEPAT_VOICE_AUDIO_BURST_SECONDS", "3.0"),
        ("TELEPAT_SESSION_TTL_SECONDS", "21600"),
        ("TELEPAT_MAX_SESSIONS", "1000"),
        ("TELEPAT_MAX_HISTORY_TURNS", "60"),
        ("TELEPAT_MAX_REPLY_CHARS", "6000"),
        ("TELEPAT_IDEMPOTENCY_ENTRIES", "32"),
    ):
        ok, value = _positive_number(name, default=default)
        guards[name] = {"valid": ok, "value": value}
        if not ok:
            errors.append(f"{name.lower()}_invalid")

    usage_ok, usage_ttl = _positive_number(
        "TELEPAT_USAGE_TTL_SECONDS",
        default=os.getenv("TELEPAT_SESSION_TTL_SECONDS", "21600"),
    )
    guards["TELEPAT_USAGE_TTL_SECONDS"] = {
        "valid": usage_ok,
        "value": usage_ttl,
    }
    if not usage_ok:
        errors.append("telepat_usage_ttl_seconds_invalid")

    session_ttl = guards["TELEPAT_SESSION_TTL_SECONDS"]["value"]
    if (
        usage_ok
        and usage_ttl is not None
        and session_ttl is not None
        and usage_ttl > session_ttl
    ):
        warnings.append("usage_retention_exceeds_session_retention")

    cost_rates = _cost_rates_status()
    if not cost_rates["valid"]:
        errors.append("cost_rates_invalid")
    elif any(configured.values()) and not cost_rates["configured"]:
        warnings.append("llm_cost_rates_unconfigured")

    avatar_engine = os.getenv("TELEPAT_AVATAR_ENGINE", "").strip()
    avatar_gpu = _enabled("TELEPAT_AVATAR_GPU_ENABLED", "0")
    if avatar_gpu and not avatar_engine:
        errors.append("avatar_gpu_enabled_without_engine")
    if avatar_engine and not avatar_gpu:
        warnings.append("avatar_engine_selected_but_gpu_disabled")

    return {
        "ok": not errors,
        "environment": settings.env,
        "errors": errors,
        "warnings": warnings,
        "conversation": {
            "provider": provider,
            "configured_real_candidates": [
                name
                for name, ready in configured.items()
                if ready
            ],
            "fallbacks": list(settings.conversation_fallbacks),
        },
        "memory": {
            "url_configured": memory_url,
            "auth_configured": memory_key,
            "recall_enabled": recall_enabled,
            "store_enabled": store_enabled,
        },
        "cost_rates": cost_rates,
        "guards": guards,
        "avatar": {
            "engine_selected": bool(avatar_engine),
            "gpu_enabled": avatar_gpu,
        },
    }
