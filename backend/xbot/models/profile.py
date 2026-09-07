from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xbot.models.base import Base

if TYPE_CHECKING:
    from xbot.models.analytics import AnalyticsSnapshot
    from xbot.models.content import Content
    from xbot.models.follow_growth import FollowCandidate, FollowRelationship
    from xbot.models.realgraph import ConversationThread, RealGraphEdge
    from xbot.models.session import Session


class ProfileStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    LOCKED = "locked"
    SUSPENDED = "suspended"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    x_handle: Mapped[str] = mapped_column(String(100), index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[ProfileStatus] = mapped_column(
        Enum(ProfileStatus), default=ProfileStatus.ACTIVE, index=True
    )
    persona_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    proxy_url_encrypted: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    last_session_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    sessions: Mapped[list[Session]] = relationship(
        "Session", back_populates="profile", cascade="all, delete-orphan"
    )
    rate_limits: Mapped[list[RateLimit]] = relationship(
        "RateLimit", back_populates="profile", cascade="all, delete-orphan"
    )
    analytics_snapshots: Mapped[list[AnalyticsSnapshot]] = relationship(
        "AnalyticsSnapshot", back_populates="profile", cascade="all, delete-orphan"
    )
    content: Mapped[list[Content]] = relationship(
        "Content", back_populates="profile", cascade="all, delete-orphan"
    )
    follow_candidates: Mapped[list[FollowCandidate]] = relationship(
        "FollowCandidate", back_populates="profile", cascade="all, delete-orphan"
    )
    follow_relationships: Mapped[list[FollowRelationship]] = relationship(
        "FollowRelationship", back_populates="profile", cascade="all, delete-orphan"
    )
    realgraph_edges: Mapped[list[RealGraphEdge]] = relationship(
        "RealGraphEdge", back_populates="profile", cascade="all, delete-orphan"
    )
    conversation_threads: Mapped[list[ConversationThread]] = relationship(
        "ConversationThread", back_populates="profile", cascade="all, delete-orphan"
    )


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(50))
    count_today: Mapped[int] = mapped_column(default=0)
    count_this_hour: Mapped[int] = mapped_column(default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_action_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    profile: Mapped[Profile] = relationship("Profile", back_populates="rate_limits")
