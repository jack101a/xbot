"""
Supervisor & Self-Healing API Routes.
Provides endpoints to monitor system health, view automated healing events,
and manually trigger reconciliation passes.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.database import get_db
from xbot.models.supervisor import SupervisorHealingEvent, SupervisorHealthSnapshot
from xbot.supervisor.manager import SystemSupervisor

logger = logging.getLogger("xbot.api.supervisor")

router = APIRouter(prefix="/supervisor", tags=["Supervisor"])


@router.get("/status")
async def get_supervisor_status(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns the real-time system health and supervisor status.
    Uses Redis caching for sub-millisecond response, falling back to SQLite.
    """
    supervisor = SystemSupervisor()
    cached = supervisor.get_cached_health()

    if cached.get("status") != "unknown":
        return {"source": "cache", "data": cached}

    # Fallback to DB latest snapshot
    stmt = (
        select(SupervisorHealthSnapshot)
        .order_by(desc(SupervisorHealthSnapshot.created_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    snapshot = res.scalar_one_or_none()

    if snapshot:
        data = {
            "status": snapshot.overall_status,
            "timestamp": snapshot.created_at.isoformat() if snapshot.created_at else None,
            "snapshot_id": str(snapshot.id),
            "active_workers": snapshot.active_workers,
            "issues_detected_count": snapshot.stuck_tasks_count,
            "orphans_cleared_count": snapshot.orphans_cleared_count,
            "pipelines_health": snapshot.pipelines_health,
        }
        return {"source": "database", "data": data}

    # If no snapshot exists at all, run a fast audit pass
    fresh = await supervisor.reconcile(auto_heal=False)
    return {"source": "live_audit", "data": fresh}


@router.get("/events")
async def get_healing_events(
    limit: int = Query(default=50, ge=1, le=200),
    component: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns recent autonomous self-healing events performed by the supervisor.
    """
    stmt = (
        select(SupervisorHealingEvent)
        .order_by(desc(SupervisorHealingEvent.created_at))
        .limit(limit)
    )
    if component:
        stmt = stmt.where(SupervisorHealingEvent.component == component)

    res = await db.execute(stmt)
    events = res.scalars().all()

    return {
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "profile_slug": e.profile_slug,
                "component": e.component,
                "issue_detected": e.issue_detected,
                "action_taken": e.action_taken,
                "status": e.status,
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@router.get("/history")
async def get_health_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns historical health snapshots recorded by the supervisor.
    """
    stmt = (
        select(SupervisorHealthSnapshot)
        .order_by(desc(SupervisorHealthSnapshot.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    snapshots = res.scalars().all()

    return {
        "count": len(snapshots),
        "snapshots": [
            {
                "id": str(s.id),
                "overall_status": s.overall_status,
                "active_workers": s.active_workers,
                "stuck_tasks_count": s.stuck_tasks_count,
                "orphans_cleared_count": s.orphans_cleared_count,
                "pipelines_health": s.pipelines_health,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snapshots
        ],
    }


@router.post("/reconcile-now")
async def trigger_reconciliation(
    auto_heal: bool = Query(default=True),
) -> dict[str, Any]:
    """
    Manually triggers an immediate supervisor reconciliation pass.
    Audits all system pipelines, locks, sessions, and repairs detected anomalies.
    """
    logger.info("Manual reconciliation requested via API (auto_heal=%s)", auto_heal)
    supervisor = SystemSupervisor()
    result = await supervisor.reconcile(auto_heal=auto_heal)
    return {
        "success": True,
        "message": f"Reconciliation completed with status: {result.get('status')}",
        "result": result,
    }
