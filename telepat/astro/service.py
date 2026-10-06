from __future__ import annotations

from time import perf_counter

from telepat.observability.metrics import runtime_metrics

from .gemini_interpreter import gemini_astro_interpreter
from .models import AstroCalculation, AstroSummary, BirthData
from .natal import calculate_natal


class AstroService:
    async def calculate(self, birth: BirthData) -> AstroCalculation:
        started = perf_counter()
        try:
            result = await calculate_natal(birth)
        except Exception:
            runtime_metrics.record(
                "astro_calculate",
                (perf_counter() - started) * 1000,
                ok=False,
                provider="astrofractal",
            )
            raise

        runtime_metrics.record(
            "astro_calculate",
            (perf_counter() - started) * 1000,
            ok=True,
            provider="astrofractal",
        )
        return result

    async def calculate_and_interpret(
        self,
        birth: BirthData,
        *,
        language: str = "ru",
    ) -> tuple[AstroCalculation, AstroSummary]:
        calculation = await self.calculate(birth)
        summary = await gemini_astro_interpreter.interpret(
            calculation,
            language=language,
        )
        return calculation, summary


astro_service = AstroService()
