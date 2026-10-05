from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from telepat.api.session import (
    SessionBootstrapRequest,
    SessionBootstrapResponse,
    bootstrap_session,
)
from telepat.api.status import provider_status
from telepat.astro.models import AstroSummary, BirthData
from telepat.astro.service import astro_service
from telepat.core.models import ChatRequest, ChatResponse
from telepat.core.orchestrator import orchestrator
from telepat.core.session_manager import session_manager
from telepat.voice.session import VoiceSession


app = FastAPI(
    title="QUANTAREON TELEPAT",
    version="0.3.0",
    description="Live AI astropsychologist integration backend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
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
        "version": "0.3.0",
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


@app.post("/session/bootstrap", response_model=SessionBootstrapResponse)
async def session_bootstrap(
    request: SessionBootstrapRequest,
) -> SessionBootstrapResponse:
    return await bootstrap_session(request)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await orchestrator.handle_chat(request)


@app.post("/session/astro", response_model=AstroSessionResponse)
async def prepare_astro_session(
    request: AstroSessionRequest,
) -> AstroSessionResponse:
    """Precompute Astrofractal context once while the greeting can play."""
    session = session_manager.get_or_create(
        session_id=request.session_id,
        user_id=request.user_id,
        language=request.language,
    )

    try:
        _calculation, summary = await astro_service.calculate_and_interpret(
            request.birth,
            language=request.language,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Astrofractal preparation failed",
        ) from exc

    session_manager.set_astro_summary(
        session.session_id,
        summary.as_context(),
    )

    return AstroSessionResponse(
        user_id=session.user_id,
        session_id=session.session_id,
        summary=summary,
    )


@app.websocket("/ws/voice")
async def voice_socket(websocket: WebSocket) -> None:
    params = websocket.query_params
    voice_session = VoiceSession(
        websocket,
        user_id=params.get("user_id") or None,
        session_id=params.get("session_id") or None,
        language=params.get("language") or "ru",
    )
    await voice_session.run()
