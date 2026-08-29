from __future__ import annotations
import difflib
from pydantic import BaseModel, Field

class GeneratedContent(BaseModel):
    primary_text: str = Field(..., description="The main tweet or reply text generated")
    alternatives: list[str] = Field(default_factory=list, description="Exactly 2 alternative versions for A/B testing")
    suggested_hashtags: list[str] = Field(default_factory=list, description="Suggested hashtags")


class ContentGenerationResponse(BaseModel):
    content: GeneratedContent


def calculate_similarity(a: str, b: str) -> float:
    """Calculates similarity ratio between two strings using difflib."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def clean_text_for_json(text: str) -> str:
    """Clean markdown json wrap."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


