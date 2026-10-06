from __future__ import annotations

from pydantic import BaseModel, Field

from .states import AvatarState


class AvatarRenderRequest(BaseModel):
    turn_id: int | None = Field(default=None, ge=1)
    audio_format: str = "mp3"
    state: AvatarState = "speaking"
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class AvatarRenderResult(BaseModel):
    turn_id: int | None = Field(default=None, ge=1)
    media_type: str
    engine: str
    latency_ms: float
    data: bytes
