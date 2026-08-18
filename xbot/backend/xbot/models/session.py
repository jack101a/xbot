from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xbot.models.base import Base

if TYPE_CHECKING:
    from xbot.models.profile import Profile


class SessionStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class ActionType(StrEnum):
    POST = "post"
    REPLY = "reply"
    LIKE = "like"
    RETWEET = "retweet"
    QUOTE = "quote"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    BROWSE = "browse"
    SEARCH = "search"
    SCRAPE_TRENDS = "scrape_trends"
    SCRAPE_METRICS = "scrape_metrics"
    UNFOLLOW_NON_FOLLOWERS = "unfollow_non_followers"
    FOLLOW_ENGAGERS = "follow_engagers"
    POLL = "poll"


class ActionStatus(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    SUCCESS = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.RUNNING, index=True
    )
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    actions_planned: Mapped[int] = mapped_column(default=0)
    actions_completed: Mapped[int] = mapped_column(default=0)
    actions_failed: Mapped[int] = mapped_column(default=0)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    profile: Mapped[Profile] = relationship("Profile", back_populates="sessions")
    actions: Mapped[list[Action]] = relationship(
        "Action", back_populates="session", cascade="all, delete-orphan"
    )


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=True, default=None
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType), index=True)
    target_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus), default=ActionStatus.PENDING, index=True
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int] = mapped_column(default=0)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    session: Mapped[Session | None] = relationship("Session", back_populates="actions")
    action_result: Mapped[ActionResult | None] = relationship(
        "ActionResult", back_populates="action", cascade="all, delete-orphan"
    )


class ActionResult(Base):
    __tablename__ = "action_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    action_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("actions.id", ondelete="CASCADE"), unique=True, index=True
    )
    tweet_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    initial_likes: Mapped[int] = mapped_column(Integer, default=0)
    initial_retweets: Mapped[int] = mapped_column(Integer, default=0)
    initial_replies: Mapped[int] = mapped_column(Integer, default=0)
    initial_views: Mapped[int] = mapped_column(Integer, default=0)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    action: Mapped[Action] = relationship("Action", back_populates="action_result")
