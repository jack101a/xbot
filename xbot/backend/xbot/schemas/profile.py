import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from xbot.models.profile import ProfileStatus


class ProfileBase(BaseModel):
    profile_slug: str = Field(..., max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    x_handle: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=100)
    status: ProfileStatus = ProfileStatus.ACTIVE
    persona_summary: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    proxy_url_encrypted: str | None = None
    avatar_url: str | None = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    status: ProfileStatus | None = None
    persona_summary: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    proxy_url_encrypted: str | None = None
    avatar_url: str | None = None


class ProfileResponse(ProfileBase):
    id: uuid.UUID
    created_at: datetime
    last_session_at: datetime | None
    followers_count: int | None = None
    following_count: int | None = None

    model_config = ConfigDict(from_attributes=True)
