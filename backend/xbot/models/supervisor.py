from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from xbot.models.base import Base
from xbot.utils.time import now_ist


class SupervisorHealingEvent(Base):
    __tablename__ = "supervisor_healing_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_slug: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    component: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    issue_detected: Mapped[str] = mapped_column(String(255), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="resolved", index=True)  # resolved, warning, escalated
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_ist, index=True)


class SupervisorHealthSnapshot(Base):
    __tablename__ = "supervisor_health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    overall_status: Mapped[str] = mapped_column(String(50), default="healthy", index=True)  # healthy, degraded, recovering, critical
    active_workers: Mapped[list[str]] = mapped_column(JSON, default=list)
    stuck_tasks_count: Mapped[int] = mapped_column(Integer, default=0)
    orphans_cleared_count: Mapped[int] = mapped_column(Integer, default=0)
    pipelines_health: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_ist, index=True)
