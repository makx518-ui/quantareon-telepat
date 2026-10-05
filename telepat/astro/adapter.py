from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import AstroCalculation, AstroSummary, BirthData


@runtime_checkable
class AstroAdapter(Protocol):
    """Stable boundary for deterministic Astrofractal + interpretation."""

    async def calculate(
        self,
        birth: BirthData,
    ) -> AstroCalculation: ...

    async def calculate_and_interpret(
        self,
        birth: BirthData,
        *,
        language: str = "ru",
    ) -> tuple[AstroCalculation, AstroSummary]: ...
