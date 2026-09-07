from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel, Field


class ThreadItemCreate(BaseModel):
    position: int = Field(0, description="0-indexed position in thread")
    item_type: str = Field("body", description="'hook', 'body', or 'closer'")
    text: str = Field(..., max_length=280, description="Tweet text")
    media_url: str | None = None


class ThreadDraftCreate(BaseModel):
    profile_id: uuid.UUID
    topic: str
    items: list[ThreadItemCreate] = Field(..., min_length=2)
    ai_metadata: dict[str, Any] = Field(default_factory=dict)


class ThreadItemResponse(BaseModel):
    id: uuid.UUID
    position: int
    item_type: str
    text: str
    tweet_id: str | None = None
    media_url: str | None = None


class ThreadDraftResponse(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    content_type: str
    status: str
    tweet_id: str | None = None
    items: list[ThreadItemResponse]
    ai_metadata: dict[str, Any] | None = None
    created_at: str
