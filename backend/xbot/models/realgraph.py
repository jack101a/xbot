"""
SQLAlchemy models for RealGraph Edge Affinity and Fast-Response Conversation Threads.
"""

from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xbot.models.base import Base

if TYPE_CHECKING:
    from xbot.models.profile import Profile


class RealGraphEdge(Base):
    """
    Tracks direct user-to-user graph edge affinity, reciprocal interaction history,
    and Phoenix multipliers for X's RealGraph recommendation layer.
    """

    __tablename__ = "realgraph_edges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_handle: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    niche: Mapped[str | None] = mapped_column(String(32), default="tech", index=True)

    # Interaction metrics
    outbound_replies_count: Mapped[int] = mapped_column(Integer, default=0)
    inbound_author_replies_count: Mapped[int] = mapped_column(Integer, default=0)
    reciprocal_score: Mapped[float] = mapped_column(Float, default=1.0, index=True)  # 1.0 to 150.0
    author_reply_rate: Mapped[float] = mapped_column(Float, default=0.0)  # inbound / outbound ratio

    # Timestamps
    first_interacted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    last_outbound_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    last_inbound_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    # Memory & Context
    topics_discussed: Mapped[list[str]] = mapped_column(JSON, default=list)
    recent_interactions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="realgraph_edges")

    def __repr__(self) -> str:
        return f"<RealGraphEdge @{self.target_handle} score={self.reciprocal_score:.1f} verified={self.is_verified}>"


class ConversationThread(Base):
    """
    Tracks active multi-turn conversations and enforces the <15m response SLA
    to capture the +150x reply_engaged_by_author multiplier.
    """

    __tablename__ = "conversation_threads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    root_tweet_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    parent_tweet_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_handle: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_is_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Multi-turn state
    turn_count: Mapped[int] = mapped_column(Integer, default=1)  # 1 to 5
    max_turns: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(
        String(32), default="active", index=True
    )  # active, awaiting_reply, closed, expired

    # Fast SLA tracking
    last_action_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    deadline_15m: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
        index=True,
    )

    # Conversation buffer
    conversation_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="conversation_threads")

    def __repr__(self) -> str:
        return f"<ConversationThread @{self.target_handle} turn={self.turn_count}/{self.max_turns} status={self.status}>"
