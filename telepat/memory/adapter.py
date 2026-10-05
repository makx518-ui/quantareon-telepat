from __future__ import annotations

from typing import Any, Protocol


class MemoryAdapter(Protocol):
    async def recall_user(self, user_id: str) -> dict[str, Any]: ...

    async def store_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> None: ...

    async def store_summary(self, *, user_id: str, session_id: str, summary: str) -> None: ...


class NullMemoryAdapter:
    async def recall_user(self, user_id: str) -> dict[str, Any]:
        return {}

    async def store_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        return None

    async def store_summary(self, *, user_id: str, session_id: str, summary: str) -> None:
        return None
