from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from telepat.core.models import ChatRequest, ChatResponse
from telepat.core.orchestrator import orchestrator


app = FastAPI(
    title="QUANTAREON TELEPAT",
    version="0.1.0",
    description="Live AI astropsychologist integration backend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "ok": True,
        "service": "quantareon-telepat",
        "version": "0.1.0",
        "phase": 1,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await orchestrator.handle_chat(request)
