from __future__ import annotations

import os

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from telepat.api.session import (
    SessionBootstrapRequest,
    SessionBootstrapResponse,
    bootstrap_session,
    prepare_session_astro,
)
from telepat.api.status import (
    privacy_status,
    production_readiness_status,
    provider_contract,
    provider_status,
    readiness_status,
)
from telepat.astro.models import AstroSummary, BirthData
from telepat.config.preflight import configuration_preflight
from telepat.config.settings import settings
from telepat.core.models import ChatRequest, ChatResponse
from telepat.core.orchestrator import orchestrator
from telepat.core.session_service import session_store
from telepat.llm.router import ConversationUnavailableError
from telepat.observability.metrics import runtime_metrics
from telepat.observability.usage import usage_registry
from telepat.security.rate_limit import (
    astro_limit,
    chat_limit,
    rate_limiter,
    voice_connect_limit,
)
from telepat.voice.session import VoiceSession


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await orchestrator.drain_background()


app = FastAPI(
    lifespan=lifespan,
    title="QUANTAREON TELEPAT",
    version="0.4.0",
    description="Live AI astropsychologist integration backend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class AstroSessionRequest(BaseModel):
    birth: BirthData
    user_id: str | None = None
    session_id: str | None = None
    language: str = "ru"


class AstroSessionResponse(BaseModel):
    user_id: str
    session_id: str
    summary: AstroSummary


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "ok": True,
        "service": "quantareon-telepat",
        "version": "0.4.0",
        "build_sha": os.getenv("TELEPAT_BUILD_SHA", "local"),
        "phase": 5,
        "features": {
            "chat": True,
            "astrofractal": True,
            "memory_adapter": True,
            "voice_websocket": True,
            "avatar_gpu": False,
        },
    }


@app.get("/health/providers")
async def health_providers() -> dict[str, bool]:
    return provider_status()


@app.get("/health/provider-contract")
async def health_provider_contract() -> dict[str, object]:
    return provider_contract()


@app.get("/health/config-preflight")
async def health_config_preflight() -> dict[str, object]:
    return configuration_preflight()


@app.get("/health/readiness")
async def health_readiness() -> dict[str, object]:
    return readiness_status()


@app.get("/health/production-readiness")
async def health_production_readiness() -> dict[str, object]:
    return production_readiness_status()


@app.get("/health/metrics")
async def health_metrics() -> dict[str, object]:
    return {
        "privacy": "no_user_content",
        "stages": runtime_metrics.snapshot(),
    }


@app.get("/health/privacy")
async def health_privacy() -> dict[str, object]:
    return privacy_status()


@app.get("/session/usage")
async def session_usage(
    session_id: str,
    user_id: str,
) -> dict[str, object]:
    session = session_store.get(session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="session_not_found",
        )

    usage = usage_registry.snapshot(session_id)
    if usage is None:
        usage = {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "thought_tokens": 0,
            "total_tokens": 0,
            "providers": {},
            "models": {},
            "priced_calls": 0,
            "unpriced_calls": 0,
            "fully_priced": True,
            "priced_cost_usd": 0.0,
        }

    return {
        "session_id": session_id,
        "usage": usage,
    }


@app.post("/session/bootstrap", response_model=SessionBootstrapResponse)
async def session_bootstrap(
    request: SessionBootstrapRequest,
) -> SessionBootstrapResponse:
    return await bootstrap_session(request)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    identity = request.user_id or request.session_id or "anonymous-chat"
    if not rate_limiter.allow(
        "chat",
        identity,
        limit=chat_limit(),
    ):
        raise HTTPException(
            status_code=429,
            detail="chat_rate_limited",
            headers={"Retry-After": "60"},
        )

    try:
        return await orchestrator.handle_chat(request)
    except ConversationUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="conversation_provider_unavailable",
        ) from exc


@app.post("/session/astro", response_model=AstroSessionResponse)
async def prepare_astro_session(
    request: AstroSessionRequest,
) -> AstroSessionResponse:
    """Precompute Astrofractal context once while the greeting can play."""
    identity = request.user_id or request.session_id or "anonymous-astro"
    if not rate_limiter.allow(
        "astro",
        identity,
        limit=astro_limit(),
    ):
        raise HTTPException(
            status_code=429,
            detail="astro_rate_limited",
            headers={"Retry-After": "60"},
        )

    session = session_store.get_or_create(
        session_id=request.session_id,
        user_id=request.user_id,
        language=request.language,
    )

    try:
        summary, _cached = await prepare_session_astro(
            session_id=session.session_id,
            birth=request.birth,
            language=session.language,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Astrofractal preparation failed",
        ) from exc

    return AstroSessionResponse(
        user_id=session.user_id,
        session_id=session.session_id,
        summary=summary,
    )


@app.websocket("/ws/voice")
async def voice_socket(websocket: WebSocket) -> None:
    params = websocket.query_params
    identity = (
        params.get("user_id")
        or params.get("session_id")
        or "anonymous-voice"
    )
    if not rate_limiter.allow(
        "voice_connect",
        identity,
        limit=voice_connect_limit(),
    ):
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "stage": "rate_limit",
                "message": "voice_connect_rate_limited",
            }
        )
        await websocket.close(
            code=1008,
            reason="voice connect rate limited",
        )
        return

    voice_session = VoiceSession(
        websocket,
        user_id=params.get("user_id") or None,
        session_id=params.get("session_id") or None,
        language=params.get("language") or "ru",
    )
    await voice_session.run()
