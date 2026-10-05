from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BirthData(BaseModel):
    year: int = Field(ge=1900, le=2100)
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1, max_length=80)


class AstroCalculation(BaseModel):
    source: str = "quantareon-engine"
    method: str = "astrofractal-natal"
    raw_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AstroSummary(BaseModel):
    overview: str = ""
    core_themes: list[str] = Field(default_factory=list)
    tensions: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    reflection_questions: list[str] = Field(default_factory=list)
    provider: str = "gemini"

    def as_context(self) -> dict[str, Any]:
        return self.model_dump()
