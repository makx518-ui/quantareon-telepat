from __future__ import annotations

from typing import Protocol

from .states import AvatarState


class AvatarAdapter(Protocol):
    name: str

    async def render(self, *, audio: bytes, state: AvatarState = "speaking") -> bytes: ...
