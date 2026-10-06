from __future__ import annotations

import os

from telepat.astro.gemini_interpreter import gemini_astro_interpreter
from telepat.config.settings import settings
from telepat.memory.service import memory_adapter
from telepat.observability.usage import usage_registry
from telepat.voice.microsoft_tts import microsoft_tts
from telepat.voice.yandex_tts import yandex_tts


def provider_status() -> dict[str, bool]:
    """Return provider configuration readiness without exposing credentials."""
    return {
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "claude": bool(
            os.getenv("ANTHROPIC_API_KEY")
            and settings.model_for("claude", settings.claude_model)
        ),
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
    memory_ready = bool(
        providers["memory"]
        and getattr(memory_adapter, "recall_enabled", False)
        and getattr(memory_adapter, "store_enabled", False)
    )

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


def provider_contract() -> dict[str, object]:
    """Describe missing provider configuration without exposing any values."""
    providers = provider_status()

    claude_model_ready = bool(
        settings.model_for("claude", settings.claude_model)
    )
    yandex_api_key = bool(os.getenv("YANDEX_SPEECHKIT_API_KEY"))
    yandex_iam = bool(os.getenv("YANDEX_IAM_TOKEN"))
    yandex_folder = bool(os.getenv("YANDEX_FOLDER_ID"))

    contract = {
        "gemini": {
            "ready": providers["gemini"],
            "missing": [] if providers["gemini"] else ["GEMINI_API_KEY"],
        },
        "groq": {
            "ready": providers["groq"],
            "missing": [] if providers["groq"] else ["GROQ_API_KEY"],
        },
        "openai": {
            "ready": providers["openai"],
            "missing": [] if providers["openai"] else ["OPENAI_API_KEY"],
        },
        "claude": {
            "ready": providers["claude"],
            "missing": [
                name
                for name, present in (
                    ("ANTHROPIC_API_KEY", bool(os.getenv("ANTHROPIC_API_KEY"))),
                    ("TELEPAT_CLAUDE_MODEL", claude_model_ready),
                )
                if not present
            ],
        },
        "astro_gemini": {
            "ready": providers["astro_gemini"],
            "missing": (
                []
                if providers["astro_gemini"]
                else ["GEMINI_API_KEY"]
            ),
        },
        "deepgram": {
            "ready": providers["deepgram"],
            "missing": (
                []
                if providers["deepgram"]
                else ["DEEPGRAM_API_KEY"]
            ),
        },
        "yandex_ermil": {
            "ready": providers["yandex_ermil"],
            "missing": [],
            "alternatives": [
                {
                    "name": "api_key",
                    "ready": yandex_api_key,
                    "requires": ["YANDEX_SPEECHKIT_API_KEY"],
                },
                {
                    "name": "iam",
                    "ready": yandex_iam and yandex_folder,
                    "requires": ["YANDEX_IAM_TOKEN", "YANDEX_FOLDER_ID"],
                },
            ],
        },
        "microsoft_andrew": {
            "ready": providers["microsoft_andrew"],
            "missing": [
                name
                for name, present in (
                    ("AZURE_SPEECH_KEY", bool(os.getenv("AZURE_SPEECH_KEY"))),
                    (
                        "AZURE_SPEECH_REGION",
                        bool(os.getenv("AZURE_SPEECH_REGION")),
                    ),
                )
                if not present
            ],
        },
        "memory": {
            "ready": providers["memory"],
            "operational": bool(
                providers["memory"]
                and getattr(memory_adapter, "recall_enabled", False)
                and getattr(memory_adapter, "store_enabled", False)
            ),
            "controls": {
                "recall_enabled": bool(
                    getattr(memory_adapter, "recall_enabled", False)
                ),
                "store_enabled": bool(
                    getattr(memory_adapter, "store_enabled", False)
                ),
            },
            "missing": (
                []
                if providers["memory"]
                else ["MEMORY_API_URL"]
            ),
            "optional": [
                "MEMORY_API_KEY",
                "MEMORY_API_AUTH_HEADER",
                "MEMORY_API_AUTH_SCHEME",
            ],
        },
    }

    conversation_candidates = [
        name
        for name in ("groq", "gemini", "openai", "claude")
        if contract[name]["ready"]
    ]
    tts_candidates = [
        name
        for name in ("yandex_ermil", "microsoft_andrew")
        if contract[name]["ready"]
    ]

    return {
        "providers": contract,
        "capabilities": {
            "conversation": {
                "ready": bool(conversation_candidates),
                "candidates": conversation_candidates,
            },
            "astro_interpreter": {
                "ready": bool(contract["astro_gemini"]["ready"]),
                "provider": "gemini",
            },
            "voice_input": {
                "ready": bool(contract["deepgram"]["ready"]),
                "provider": "deepgram",
            },
            "voice_output": {
                "ready": bool(tts_candidates),
                "candidates": tts_candidates,
            },
            "memory": {
                "ready": bool(contract["memory"]["operational"]),
                "provider": "remote-memory",
            },
        },
    }


def production_readiness_status() -> dict[str, object]:
    """Return the remaining runtime blockers for a complete TELEPAT product."""
    readiness = readiness_status()

    avatar_engine = os.getenv("TELEPAT_AVATAR_ENGINE", "").strip()
    avatar_gpu_enabled = os.getenv(
        "TELEPAT_AVATAR_GPU_ENABLED",
        "0",
    ).strip().lower() in {"1", "true", "yes", "on"}

    blockers: list[str] = []
    warnings: list[str] = []

    production_mode = settings.env.strip().lower() == "production"
    cors_ready = (
        not production_mode
        or "*" not in settings.cors_origins
    )
    cost_rates_raw = os.getenv(
        "TELEPAT_COST_RATES_JSON",
        "",
    ).strip()
    cost_rates_configured = bool(
        cost_rates_raw
        and cost_rates_raw != "{}"
    )

    if not readiness["conversation_ready"]:
        blockers.append("conversation_provider")
    if not readiness["astro_interpreter_ready"]:
        blockers.append("astro_interpreter")
    if not readiness["voice_input_ready"]:
        blockers.append("voice_input")
    if not readiness["voice_output_ready"]:
        blockers.append("voice_output")
    if not readiness["memory_ready"]:
        blockers.append("memory")
    if not avatar_engine:
        blockers.append("avatar_engine")
    if not avatar_gpu_enabled:
        blockers.append("avatar_gpu")
    if not cors_ready:
        blockers.append("cors_policy")

    if readiness["conversation_ready"] and not cost_rates_configured:
        warnings.append("llm_cost_rates_unconfigured")
    if production_mode:
        warnings.append("single_container_session_store")

    return {
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "environment": settings.env,
        "capabilities": {
            "conversation": readiness["conversation_ready"],
            "astrofractal_engine": True,
            "astro_interpreter": readiness["astro_interpreter_ready"],
            "voice_input": readiness["voice_input_ready"],
            "voice_output": readiness["voice_output_ready"],
            "memory": readiness["memory_ready"],
            "avatar_engine": bool(avatar_engine),
            "avatar_gpu": avatar_gpu_enabled,
            "cors_policy": cors_ready,
            "llm_cost_rates": cost_rates_configured,
        },
        "avatar": {
            "engine": avatar_engine or None,
            "gpu_enabled": avatar_gpu_enabled,
        },
    }



def privacy_status() -> dict[str, object]:
    """Describe runtime retention/privacy controls without user data."""
    from telepat.core.session_service import session_store

    recall_enabled = bool(
        getattr(memory_adapter, "recall_enabled", False)
    )
    store_enabled = bool(
        getattr(memory_adapter, "store_enabled", False)
    )

    return {
        "metrics_store_user_content": False,
        "rate_limit_identity_hashed": True,
        "session_store": "in_process",
        "session_ttl_seconds": session_store.ttl_seconds,
        "max_sessions": session_store.max_sessions,
        "max_history_turns": session_store.max_history_turns,
        "usage_retention": {
            "ttl_seconds": usage_registry.ttl_seconds,
            "max_sessions": usage_registry.max_sessions,
            "stores_user_content": False,
        },
        "memory": {
            "configured": memory_adapter.configured,
            "recall_enabled": recall_enabled,
            "store_enabled": store_enabled,
            "external_persistence": (
                memory_adapter.configured and store_enabled
            ),
        },
    }
