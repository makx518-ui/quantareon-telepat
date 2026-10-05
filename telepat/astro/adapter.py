from __future__ import annotations

from typing import Any, Protocol


class AstroAdapter(Protocol):
    async def calculate(self, *, user_data: dict[str, Any]) -> dict[str, Any]: ...

    async def summarize(self, *, astro_data: dict[str, Any], language: str) -> dict[str, Any]: ...


class NullAstroAdapter:
    """Phase-1 placeholder. Real implementation comes from Engine + Oracle."""

    async def calculate(self, *, user_data: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def summarize(self, *, astro_data: dict[str, Any], language: str) -> dict[str, Any]:
        return {}
