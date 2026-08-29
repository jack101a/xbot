"""
SQLAlchemy models for Follow-for-Follow (F4F) Growth & Blue Tick Targeting Engine.
"""

from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xbot.models.base import Base

if TYPE_CHECKING:
    from xbot.models.profile import Profile


class FollowCandidate(Base):
    """
    Discovered community discussion engager identified as a high-potential Blue Tick follow candidate.
    """

    __tablename__ = "follow_candidates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    handle: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    niche: Mapped[str] = mapped_column(String(32), default="ai", index=True)  # anime, movies, tech, ai
    is_blue_tick: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    follower_count: Mapped[int] = mapped_column(Integer, default=500)
    following_count: Mapped[int] = mapped_column(Integer, default=500)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_discussion: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_tweet_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reciprocity_score: Mapped[float] = mapped_column(Float, default=50.0)
    status: Mapped[str] = mapped_column(
        String(32), default="discovered", index=True
    )  # discovered, queued, followed, ignored
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    discovered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="follow_candidates")

    def __repr__(self) -> str:
        return f"<FollowCandidate @{self.handle} niche={self.niche} verified={self.is_blue_tick}>"


class FollowRelationship(Base):
    """
    Tracks active followed accounts, grace period status, and mutual follow-back reciprocity.
    """

    __tablename__ = "follow_relationships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_handle: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_blue_tick: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    niche: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    followed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    grace_period_expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=4),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), default="following", index=True
    )  # following, followed_back, grace_period_expired, unfollowed, whitelisted
    last_checked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    unfollowed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="follow_relationships")

    def __repr__(self) -> str:
        return f"<FollowRelationship @{self.target_handle} status={self.status} verified={self.is_blue_tick}>"
