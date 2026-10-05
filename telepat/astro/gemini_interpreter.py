from __future__ import annotations

import json
import os

import httpx

from .models import AstroCalculation, AstroSummary


_ASTRO_SYSTEM = """You are the Astrofractal interpretation layer for TELEPAT.

You receive deterministic machine output produced by QUANTAREON Astrofractal.
Your task is to compress it into psychologically useful context for a separate
conversational agent.

Rules:
- use ONLY facts present in the machine output;
- do not calculate new placements, aspects, houses or dates;
- do not invent biography or past events;
- use astrological material as an interpretive/symbolic framework, not certainty;
- write grounded psychological language suitable for a live conversation;
- avoid fatalism and dramatic prophecy;
- return valid JSON only.

Required JSON keys:
overview: string
core_themes: array of short strings
tensions: array of short strings
resources: array of short strings
reflection_questions: array of 2-5 short questions
"""


class GeminiAstroInterpreter:
    name = "gemini"

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = (
            os.getenv("TELEPAT_ASTRO_MODEL", "")
            or os.getenv("GEMINI_MODEL", "")
        )
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def interpret(
        self,
        calculation: AstroCalculation,
        *,
        language: str = "ru",
    ) -> AstroSummary:
        if not self.configured:
            raise RuntimeError("Gemini Astro interpreter is not configured")

        prompt = (
            f"Answer language: {language}.\n\n"
            "ASTROFRACTAL MACHINE OUTPUT:\n"
            + calculation.raw_text
        )

        payload = {
            "systemInstruction": {"parts": [{"text": _ASTRO_SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.25,
                "maxOutputTokens": 1800,
                "responseMimeType": "application/json",
            },
        }
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/models/{self.model}:generateContent"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini Astro returned no candidates")

        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise RuntimeError("Gemini Astro returned an empty response")

        parsed = json.loads(text)
        return AstroSummary(
            overview=str(parsed.get("overview", "")),
            core_themes=list(parsed.get("core_themes") or []),
            tensions=list(parsed.get("tensions") or []),
            resources=list(parsed.get("resources") or []),
            reflection_questions=list(parsed.get("reflection_questions") or []),
            provider=self.name,
        )


gemini_astro_interpreter = GeminiAstroInterpreter()
