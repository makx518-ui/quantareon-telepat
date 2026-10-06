from __future__ import annotations

import asyncio


async def run_provider_probe() -> dict[str, object]:
    """Exercise configured TELEPAT providers without exposing user content."""
    from telepat.api.status import provider_status
    from telepat.astro.models import BirthData
    from telepat.astro.service import astro_service
    from telepat.core.models import ChatRequest
    from telepat.core.orchestrator import orchestrator
    from telepat.core.session_service import session_store
    from telepat.memory.service import memory_adapter
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
        session = session_store.get_or_create(
            session_id="telepat-provider-probe",
            user_id="telepat-provider-probe",
            language="ru",
        )
        if summary is not None:
            session_store.set_astro_summary(
                session.session_id,
                summary.as_context(),
            )

        response = await asyncio.wait_for(
            orchestrator.handle_chat(
                ChatRequest(
                    message=(
                        "Коротко поздоровайся и скажи, "
                        "что TELEPAT готов к диалогу."
                    ),
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

    if providers.get("memory"):
        try:
            report["memory"] = await asyncio.wait_for(
                memory_adapter.probe(),
                timeout=30,
            )
        except Exception as exc:
            report["memory"] = {
                "configured": True,
                "required": bool(
                    getattr(memory_adapter, "recall_enabled", False)
                    and getattr(memory_adapter, "store_enabled", False)
                ),
                "overall_ok": False,
                "error": type(exc).__name__,
            }
    else:
        report["memory"] = {
            "configured": False,
            "required": False,
            "overall_ok": True,
            "recall": {"skipped": True},
            "store": {"skipped": True},
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

    real_conversation_configured = any(
        providers.get(name)
        for name in ("gemini", "groq", "openai", "claude")
    )
    if (
        real_conversation_configured
        and not report.get("chat", {}).get("real_provider")
    ):
        failures.append("conversation_provider")

    if (
        providers.get("astro_gemini")
        and not report.get("astro_interpreter", {}).get("ok")
    ):
        failures.append("astro_interpreter")

    if (
        providers.get("yandex_ermil")
        or providers.get("microsoft_andrew")
    ) and not report.get("tts", {}).get("ok"):
        failures.append("tts")

    if (
        providers.get("deepgram")
        and not report.get("deepgram", {}).get("ok")
    ):
        failures.append("deepgram")

    memory_report = report.get("memory") or {}
    if (
        memory_report.get("required")
        and not memory_report.get("overall_ok")
    ):
        failures.append("memory")

    report["overall_ok"] = not failures
    report["required_failures"] = failures
    return report
