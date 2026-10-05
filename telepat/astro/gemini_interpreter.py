from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from telepat.config.prompt_loader import load_prompt
from telepat.config.settings import settings

from .models import AstroCalculation, AstroSummary


_ASTRO_SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "core_themes": {"type": "array", "items": {"type": "string"}},
        "tensions": {"type": "array", "items": {"type": "string"}},
        "resources": {"type": "array", "items": {"type": "string"}},
        "reflection_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overview",
        "core_themes",
        "tensions",
        "resources",
        "reflection_questions",
    ],
    "additionalProperties": False,
}


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


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _as_overview(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(_as_list(value)[:4])
    return str(value or "").strip()


def _parse_summary_payload(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(_clean_json(text))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini Astro returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("Gemini Astro returned a non-object JSON payload")

    overview = _as_overview(
        parsed.get("overview")
        or parsed.get("psychological_themes")
        or parsed.get("dominant_patterns")
    )
    core_themes = _as_list(
        parsed.get("core_themes")
        or parsed.get("dominant_patterns")
        or parsed.get("psychological_themes")
    )
    tensions = _as_list(
        parsed.get("tensions")
        or parsed.get("current_tensions")
        or parsed.get("cautions")
    )
    resources = _as_list(parsed.get("resources"))
    reflection_questions = _as_list(
        parsed.get("reflection_questions")
        or parsed.get("questions_to_explore")
    )

    if not any(
        [overview, core_themes, tensions, resources, reflection_questions]
    ):
        raise RuntimeError("Gemini Astro returned an empty summary")

    return {
        "overview": overview,
        "core_themes": core_themes,
        "tensions": tensions,
        "resources": resources,
        "reflection_questions": reflection_questions,
    }


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
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": _ASTRO_SCHEMA,
                },
                store=False,
            )
            text = (interaction.output_text or "").strip()
            if not text:
                raise RuntimeError("Gemini Astro returned an empty response")
            return text

        text = await asyncio.to_thread(_call)
        payload = _parse_summary_payload(text)

        return AstroSummary(
            **payload,
            provider=self.name,
        )


gemini_astro_interpreter = GeminiAstroInterpreter()
