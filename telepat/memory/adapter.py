from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryAdapter(Protocol):
    """Stable TELEPAT memory boundary used by orchestration code."""

    @property
    def configured(self) -> bool: ...

    async def recall(
        self,
        *,
        user_id: str,
        message: str,
        level: str = "medium",
    ) -> dict[str, Any]: ...

    async def store_exchange(
        self,
        *,
        user_id: str,
        message: str,
        response_text: str,
    ) -> None: ...

    async def probe(self) -> dict[str, Any]: ...


class NullMemoryAdapter:
    @property
    def configured(self) -> bool:
        return False

    async def recall(
        self,
        *,
        user_id: str,
        message: str,
        level: str = "medium",
    ) -> dict[str, Any]:
        return {}

    async def store_exchange(
        self,
        *,
        user_id: str,
        message: str,
        response_text: str,
    ) -> None:
        return None

    async def probe(self) -> dict[str, Any]:
        return {
            "configured": False,
            "required": False,
            "overall_ok": True,
            "recall": {"skipped": True},
            "store": {"skipped": True},
        }
