import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xbot.models.base import Base

if TYPE_CHECKING:
    from xbot.models.profile import Profile


class ResearchedTopic(Base):
    __tablename__ = "researched_topics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="x_search")  # "x_search", "x_trending", "rss"
    scraped_posts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    media_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pipeline_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="success", index=True)  # "success", "failed", "running", "skipped"
    actions_count: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    profile: Mapped["Profile | None"] = relationship("Profile")


class InstantTrendCampaign(Base):
    __tablename__ = "instant_trend_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)  # active, paused, stopped, completed, ready
    duration_hours: Mapped[int] = mapped_column(Integer, default=48)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=20)
    quote_percentage: Mapped[int] = mapped_column(Integer, default=70)
    sentiment_tone: Mapped[str] = mapped_column(String(50), default="balanced")
    ragebait_percentage: Mapped[int] = mapped_column(Integer, default=0)

    # Unified Campaign Studio Extensions
    campaign_type: Mapped[str] = mapped_column(String(50), default="instant", index=True)  # instant, on_demand, continuous
    source_type: Mapped[str] = mapped_column(String(50), default="custom", index=True)  # custom, trend_radar
    plan_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    deliverables: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    media_preference: Mapped[str] = mapped_column(String(50), default="x_official")  # x_official, ai_generated

    seen_tweet_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    posted_actions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile")


# Unified alias for unified AI Campaign Studio
Campaign = InstantTrendCampaign
