from __future__ import annotations
from pydantic import BaseModel, Field, field_validator

class GeneratedPoll(BaseModel):
    question: str = Field(..., max_length=200, description="Engaging poll question (<200 chars)")
    options: list[str] = Field(..., min_length=2, max_length=4, description="2 to 4 options, each max 25 chars")
    duration_days: int = Field(default=1, ge=1, le=7, description="Poll duration in days (1 to 7)")
    context_hook: str | None = Field(default=None, description="Optional opening hook before question")
    reasoning: str = Field(default="", description="Strategic reasoning for why this poll drives debate")

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[str]) -> list[str]:
        cleaned = [opt.strip()[:25] for opt in v if isinstance(opt, str) and opt.strip()]
        if not (2 <= len(cleaned) <= 4):
            raise ValueError("Poll must have between 2 and 4 options")
        return cleaned
