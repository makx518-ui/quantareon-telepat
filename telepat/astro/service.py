from __future__ import annotations

from .gemini_interpreter import gemini_astro_interpreter
from .models import AstroCalculation, AstroSummary, BirthData
from .natal import calculate_natal


class AstroService:
    async def calculate(self, birth: BirthData) -> AstroCalculation:
        return await calculate_natal(birth)

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
