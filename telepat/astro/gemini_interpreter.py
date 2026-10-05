from __future__ import annotations

import asyncio
import json
import os

from telepat.config.prompt_loader import load_prompt
from telepat.config.settings import settings

from .models import AstroCalculation, AstroSummary


def _clean_json(text: str) -> str:
    value = text.strip()
    fence = chr(96) * 3
    if value.startswith(fence):
        value = value[len(fence):].lstrip()
        if value.lower().startswith("json"):
            value = value[4:].lstrip()
        if value.endswith(fence):
            value = value[:-len(fence)].rstrip()
    return value


class GeminiAstroInterpreter:
    name = "gemini"

    @property
    def configured(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    async def interpret(
        self,
        calculation: AstroCalculation,
        *,
        language: str = "ru",
    ) -> AstroSummary:
        if not self.configured:
            raise RuntimeError("Gemini Astro interpreter is not configured")

        system_instruction = load_prompt("astro.md")
        user_input = (
            f"Answer language: {language}.\n\n"
            "ASTROFRACTAL MACHINE OUTPUT:\n"
            + calculation.raw_text
        )

        def _call() -> str:
            from google import genai

            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            interaction = client.interactions.create(
                model=settings.astro_model,
                input=user_input,
                system_instruction=system_instruction,
                store=False,
            )
            text = (interaction.output_text or "").strip()
            if not text:
                raise RuntimeError("Gemini Astro returned an empty response")
            return text

        text = await asyncio.to_thread(_call)
        parsed = json.loads(_clean_json(text))

        return AstroSummary(
            overview=str(parsed.get("overview", "")),
            core_themes=[
                str(item) for item in (parsed.get("core_themes") or [])
            ],
            tensions=[
                str(item) for item in (parsed.get("tensions") or [])
            ],
            resources=[
                str(item) for item in (parsed.get("resources") or [])
            ],
            reflection_questions=[
                str(item)
                for item in (parsed.get("reflection_questions") or [])
            ],
            provider=self.name,
        )


gemini_astro_interpreter = GeminiAstroInterpreter()
