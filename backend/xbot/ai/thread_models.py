from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field
from xbot.persona.loader import Persona
from xbot.ai.x_researcher import TopicResearchReport
from xbot.schemas.thread import ThreadItemCreate

class GeneratedThreadItem(BaseModel):
    position: int = Field(..., description="0-indexed tweet position in thread")
    item_type: Literal["hook", "body", "closer"] = Field(..., description="'hook', 'body', or 'closer'")
    text: str = Field(..., max_length=280, description="Tweet text strictly <= 260 chars")
    media_url: str | None = Field(None, description="Optional attached image URL or path")


class GeneratedThreadPayload(BaseModel):
    topic: str
    hook_score: int = Field(..., ge=1, le=100, description="Estimated viral hook strength (1-100)")
    archetype: str = Field(..., description="Framework, Contrarian Breakdown, Case Study, or Tactical Guide")
    tweets: list[GeneratedThreadItem] = Field(..., min_length=2, max_length=8)


class GeneratedThreadResponse(BaseModel):
    topic: str
    hook_score: int
    archetype: str
    tweets: list[str]
    items: list[ThreadItemCreate]
    research_report: dict[str, Any] | None = None
    downloaded_media: list[dict[str, Any]] = Field(default_factory=list)


