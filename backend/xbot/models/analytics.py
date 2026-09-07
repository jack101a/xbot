import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, Uuid, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xbot.models.base import Base

if TYPE_CHECKING:
    from xbot.models.profile import Profile


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    following: Mapped[int] = mapped_column(Integer, default=0)
    total_tweets: Mapped[int] = mapped_column(Integer, default=0)
    verified_followers: Mapped[int] = mapped_column(Integer, default=0)
    verified_impressions_90d: Mapped[int] = mapped_column(Integer, default=0)
    impressions_24h: Mapped[int] = mapped_column(Integer, default=0)
    engagements_24h: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    top_tweets: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Relationships
    profile: Mapped["Profile"] = relationship(
        "Profile", back_populates="analytics_snapshots"
    )


class FollowerSnapshot(Base):
    __tablename__ = "follower_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    snapshot_type: Mapped[str] = mapped_column(String(50), index=True) # "follower" or "following"
    handles: Mapped[list[str]] = mapped_column(JSON) # JSON array of handles
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    profile: Mapped["Profile"] = relationship("Profile")


class FollowerChangeLog(Base):
    __tablename__ = "follower_changelogs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    change_type: Mapped[str] = mapped_column(String(50), index=True) # "unfollowed_us", "new_follower", "we_unfollowed", "we_followed"
    handle: Mapped[str] = mapped_column(String(100), index=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    profile: Mapped["Profile"] = relationship("Profile")


class ReputationLog(Base):
    __tablename__ = "reputation_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0) # composite score (-1.0 to +1.0)
    total_replies_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    positive_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    profile: Mapped["Profile"] = relationship("Profile")

