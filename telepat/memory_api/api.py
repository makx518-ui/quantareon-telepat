from __future__ import annotations

import hmac
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .store import SQLiteMemoryStore


class RecallRequest(BaseModel):
    user_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=12000)
    level: str = "medium"


class StoreRequest(BaseModel):
    user_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=12000)
    response: str = Field(min_length=1, max_length=16000)


def create_memory_app(
    *,
    store: SQLiteMemoryStore,
    api_key: str,
) -> FastAPI:
    app = FastAPI(
        title="QUANTAREON TELEPAT Memory",
        version="1.0.0",
    )
    expected = str(api_key or "").strip()
    if not expected:
        raise RuntimeError("MEMORY_API_KEY is required")

    def authorize(authorization: str | None) -> None:
        supplied = str(authorization or "")
        prefix = "Bearer "
        if not supplied.startswith(prefix):
            raise HTTPException(status_code=401, detail="unauthorized")
        token = supplied[len(prefix):]
        if not hmac.compare_digest(token, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "service": "quantareon-telepat-memory",
            "persistence": "sqlite-modal-volume",
        }

    @app.post("/api/recall")
    def recall(
        request: RecallRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(authorization)
        return store.recall(
            user_id=request.user_id,
            message=request.message,
            level=request.level,
        )

    @app.post("/api/store")
    def store_exchange(
        request: StoreRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, object]:
        authorize(authorization)
        store.store_exchange(
            user_id=request.user_id,
            message=request.message,
            response=request.response,
        )
        return {"ok": True}

    return app
