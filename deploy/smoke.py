from __future__ import annotations

import asyncio
import json
import os

import modal


app = modal.App("quantareon-telepat-smoke")

attach_provider_secret = os.getenv(
    "TELEPAT_ATTACH_PROVIDER_SECRET",
    "0",
).strip().lower() in {"1", "true", "yes", "on"}
provider_secrets = (
    [modal.Secret.from_name("quantareon-telepat-secrets")]
    if attach_provider_secret
    else []
)

smoke_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "fastapi>=0.115,<1",
        "pydantic>=2.8,<3",
        "httpx>=0.27,<1",
        "google-genai>=1.0,<2",
        "websockets>=12,<16",
        "kerykeion>=5.12,<6",
        "pyswisseph==2.10.3.2",
    )
    .add_local_python_source("telepat", ignore=[])
)


@app.function(image=smoke_image, timeout=180, secrets=provider_secrets)
async def provider_smoke() -> dict[str, object]:
    """Run TELEPAT diagnostics in Modal without requiring provider secrets.

    Provider-specific checks become active automatically when their environment
    variables are present. The deterministic Astrofractal and orchestration
    kernel are always exercised.
    """
    from telepat.api.status import provider_status
    from telepat.astro.models import BirthData
    from telepat.astro.service import astro_service
    from telepat.core.models import ChatRequest
    from telepat.core.orchestrator import orchestrator
    from telepat.core.session_manager import session_manager
    from telepat.voice.deepgram import DeepgramStreamingSTT
    from telepat.voice.tts_router import tts_router

    providers = provider_status()
    report: dict[str, object] = {"providers": providers}

    birth = BirthData(
        year=2000,
        month=1,
        day=1,
        hour=12,
        minute=0,
        latitude=0.0,
        longitude=0.0,
        timezone="UTC",
    )

    calculation = None
    try:
        calculation = await asyncio.wait_for(
            astro_service.calculate(birth),
            timeout=30,
        )
        report["astro_engine"] = {
            "ok": True,
            "source": calculation.source,
            "method": calculation.method,
            "raw_chars": len(calculation.raw_text),
        }
    except Exception as exc:
        report["astro_engine"] = {
            "ok": False,
            "error": type(exc).__name__,
            "detail": str(exc)[:500],
        }

    summary = None
    if providers.get("astro_gemini") and calculation is not None:
        try:
            _calculation, summary = await asyncio.wait_for(
                astro_service.calculate_and_interpret(
                    birth,
                    language="ru",
                ),
                timeout=90,
            )
            report["astro_interpreter"] = {
                "ok": True,
                "provider": summary.provider,
                "overview_chars": len(summary.overview),
                "themes": len(summary.core_themes),
            }
        except Exception as exc:
            report["astro_interpreter"] = {
                "ok": False,
                "error": type(exc).__name__,
            }
    else:
        report["astro_interpreter"] = {
            "ok": False,
            "error": "not_configured",
        }

    try:
        session = session_manager.get_or_create(
            session_id=None,
            user_id="telepat-modal-smoke",
            language="ru",
        )
        if summary is not None:
            session_manager.set_astro_summary(
                session.session_id,
                summary.as_context(),
            )

        response = await asyncio.wait_for(
            orchestrator.handle_chat(
                ChatRequest(
                    message="Коротко поздоровайся и скажи, что TELEPAT готов к диалогу.",
                    user_id=session.user_id,
                    session_id=session.session_id,
                    language="ru",
                )
            ),
            timeout=90,
        )
        report["chat"] = {
            "ok": True,
            "real_provider": response.provider != "mock",
            "provider": response.provider,
            "reply_chars": len(response.reply),
            "intent": response.intent,
        }
    except Exception as exc:
        report["chat"] = {
            "ok": False,
            "error": type(exc).__name__,
        }

    try:
        audio, provider = await asyncio.wait_for(
            tts_router.synthesize(
                "TELEPAT готов к разговору.",
                language="ru",
            ),
            timeout=60,
        )
        report["tts"] = {
            "ok": bool(audio),
            "provider": provider,
            "bytes": len(audio or b""),
            "configured": bool(
                providers.get("yandex_ermil")
                or providers.get("microsoft_andrew")
            ),
        }
    except Exception as exc:
        report["tts"] = {
            "ok": False,
            "error": type(exc).__name__,
        }

    stt = DeepgramStreamingSTT(language="ru")
    if not stt.configured:
        report["deepgram"] = {
            "ok": False,
            "error": "not_configured",
        }
    else:
        try:
            await asyncio.wait_for(
                stt.connect(),
                timeout=20,
            )
            report["deepgram"] = {
                "ok": True,
                "connected": True,
            }
        except Exception as exc:
            report["deepgram"] = {
                "ok": False,
                "error": type(exc).__name__,
            }
        finally:
            try:
                await asyncio.wait_for(
                    stt.close(),
                    timeout=10,
                )
            except TimeoutError:
                pass

    failures: list[str] = []

    if not report.get("astro_engine", {}).get("ok"):
        failures.append("astro_engine")
    if not report.get("chat", {}).get("ok"):
        failures.append("chat_core")

    if (
        providers.get("gemini")
        or providers.get("groq")
        or providers.get("openai")
        or providers.get("claude")
    ) and not report.get("chat", {}).get("real_provider"):
        failures.append("conversation_provider")

    if providers.get("astro_gemini") and not report.get(
        "astro_interpreter",
        {},
    ).get("ok"):
        failures.append("astro_interpreter")

    if (
        providers.get("yandex_ermil")
        or providers.get("microsoft_andrew")
    ) and not report.get("tts", {}).get("ok"):
        failures.append("tts")

    if providers.get("deepgram") and not report.get(
        "deepgram",
        {},
    ).get("ok"):
        failures.append("deepgram")

    report["overall_ok"] = not failures
    report["required_failures"] = failures
    return report


@app.local_entrypoint()
async def main() -> None:
    result = await provider_smoke.remote.aio()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("overall_ok"):
        raise SystemExit(
            "TELEPAT smoke failed: "
            + ", ".join(result.get("required_failures") or [])
        )
