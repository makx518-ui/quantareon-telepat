from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Intent = Literal[
    "casual_conversation",
    "personal_reflection",
    "astropsychology",
    "follow_up_astro",
    "factual_user_memory",
    "system_action",
    "unknown",
]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    user_id: str | None = None
    session_id: str | None = None
    language: str = "ru"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str
    intent: Intent
    avatar_state: str = "idle"
    provider: str = "mock"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    language: str = "ru"
    history: list[ConversationTurn] = Field(default_factory=list)
    astro_summary: dict[str, Any] | None = None
    user_memory: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextPacket(BaseModel):
    session_id: str
    user_id: str
    language: str
    current_message: str
    intent: Intent
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    user_memory: dict[str, Any] = Field(default_factory=dict)
    astro_summary: dict[str, Any] | None = None
    psychology: dict[str, Any] = Field(default_factory=dict)
    response_style: dict[str, Any] = Field(default_factory=dict)
