from __future__ import annotations

import json

from deploy.runtime import app, cpu_image


@app.function(image=cpu_image, timeout=180)
async def provider_smoke() -> dict[str, object]:
    """Exercise real TELEPAT providers inside Modal without exposing secrets.

    This is intentionally not an HTTP endpoint. Run it with `modal run` so
    credentials stay inside the named Modal Secret.
    """
    from telepat.api.status import provider_status
    from telepat.astro.models import BirthData
    from telepat.astro.service import astro_service
    from telepat.core.models import ChatRequest
    from telepat.core.orchestrator import orchestrator
    from telepat.core.session_manager import session_manager
    from telepat.voice.deepgram import DeepgramStreamingSTT
    from telepat.voice.tts_router import tts_router

    report: dict[str, object] = {
        "providers": provider_status(),
    }

    summary = None
    try:
        calculation, summary = await astro_service.calculate_and_interpret(
            BirthData(
                year=2000,
                month=1,
                day=1,
                hour=12,
                minute=0,
                latitude=0.0,
                longitude=0.0,
                timezone="UTC",
            ),
            language="ru",
        )
        report["astro"] = {
            "ok": True,
            "provider": summary.provider,
            "raw_chars": len(calculation.raw_text),
            "overview_chars": len(summary.overview),
            "themes": len(summary.core_themes),
        }
    except Exception as exc:
        report["astro"] = {
            "ok": False,
            "error": type(exc).__name__,
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

        response = await orchestrator.handle_chat(
            ChatRequest(
                message=(
                    "Коротко поздоровайся и скажи, что TELEPAT готов к диалогу."
                ),
                user_id=session.user_id,
                session_id=session.session_id,
                language="ru",
            )
        )
        report["chat"] = {
            "ok": response.provider != "mock",
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
        audio, provider = await tts_router.synthesize(
            "TELEPAT готов к разговору.",
            language="ru",
        )
        report["tts"] = {
            "ok": bool(audio),
            "provider": provider,
            "bytes": len(audio or b""),
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
            await stt.connect()
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
            await stt.close()

    return report


@app.local_entrypoint()
async def main() -> None:
    result = await provider_smoke.remote.aio()
    print(json.dumps(result, ensure_ascii=False, indent=2))
