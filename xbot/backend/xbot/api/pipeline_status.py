"""
Pipeline Status and Health Monitoring Endpoints.

Provides:
- GET /pipelines/status: Live status, queue depth, daily action metrics for all 7 pipelines.
- GET /pipelines/history: Execution history log for pipeline runs.
- POST /pipelines/{name}/trigger: Manually trigger an immediate run of any pipeline.
- POST /pipelines/{name}/pause and /resume: Controls pipeline execution.
"""

from __future__ import annotations

import datetime
from typing import Any

import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.browser_queue import get_queue_depth
from xbot.pipelines.central_guard import CentralGuard, get_current_ist_time, is_within_active_hours
from xbot.pipelines.follow_pipeline import run_follow_pipeline
from xbot.pipelines.like_pipeline import run_like_pipeline
from xbot.pipelines.quote_pipeline import run_quote_pipeline
from xbot.pipelines.reply_pipeline import run_reply_pipeline
from xbot.pipelines.trend_generator_pipeline import run_trend_generator
from xbot.pipelines.trend_researcher_pipeline import run_trend_researcher

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.get("/status")
async def get_all_pipelines_status(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Returns real-time status, health, and 24h action counts across all 7 pipelines."""
    guard = CentralGuard()
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    today_ist = get_current_ist_time().strftime("%Y-%m-%d")

    pipeline_names = [
        "like",
        "reply",
        "quote",
        "follow",
        "trend_researcher",
        "trend_generator",
    ]

    statuses: dict[str, Any] = {}

    # Query latest run for each pipeline
    for name in pipeline_names:
        stmt = (
            select(PipelineRun)
            .where(PipelineRun.pipeline_name == name)
            .order_by(desc(PipelineRun.started_at))
            .limit(1)
        )
        last_run = (await db.execute(stmt)).scalar_one_or_none()

        is_paused = bool(r.get(f"xbot:pipeline:paused:{name}"))

        # Aggregated stats today
        today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        action_sum_stmt = (
            select(func.sum(PipelineRun.actions_count))
            .where(PipelineRun.pipeline_name == name, PipelineRun.started_at >= today_start)
        )
        total_actions = (await db.execute(action_sum_stmt)).scalar() or 0

        err_stmt = (
            select(func.count(PipelineRun.id))
            .where(
                PipelineRun.pipeline_name == name,
                PipelineRun.status == "failed",
                PipelineRun.started_at >= today_start,
            )
        )
        error_count = (await db.execute(err_stmt)).scalar() or 0

        statuses[f"{name}_pipeline"] = {
            "name": name,
            "status": "paused" if is_paused else ("healthy" if error_count == 0 else "degraded"),
            "is_paused": is_paused,
            "is_within_active_hours": is_within_active_hours() if not guard.is_action_24_7(name) else True,
            "last_run_at": last_run.started_at.isoformat() if last_run else None,
            "last_status": last_run.status if last_run else "idle",
            "actions_today": total_actions,
            "errors_today": error_count,
            "last_error": last_run.error_message if last_run and last_run.status == "failed" else None,
        }

    # Browser Queue status
    queue_depth = get_queue_depth(r)
    statuses["browser_queue"] = {
        "name": "browser_queue",
        "status": "healthy",
        "queue_depth": queue_depth,
        "mode": "FIFO_priority_worker",
    }

    # System active hours state
    ist_now = get_current_ist_time()
    return {
        "system_time_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S IST"),
        "is_active_hours": is_within_active_hours(),
        "active_hours_window": "06:00 - 02:00 IST (Research & Gen are 24/7)",
        "pipelines": statuses,
    }


@router.get("/history")
async def get_pipeline_history(
    pipeline_name: str | None = Query(None, description="Filter by pipeline name"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns execution history log for pipeline runs."""
    stmt = select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(limit)
    if pipeline_name:
        stmt = stmt.where(PipelineRun.pipeline_name == pipeline_name)

    runs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(r.id),
            "pipeline_name": r.pipeline_name,
            "profile_id": str(r.profile_id) if r.profile_id else None,
            "status": r.status,
            "actions_count": r.actions_count,
            "details": r.details,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.post("/{pipeline_name}/trigger")
async def trigger_pipeline_manually(
    pipeline_name: str,
) -> dict[str, Any]:
    """Manually triggers an immediate execution of a specific pipeline."""
    clean_name = pipeline_name.lower().replace("_pipeline", "")

    runners = {
        "like": run_like_pipeline,
        "reply": run_reply_pipeline,
        "quote": run_quote_pipeline,
        "follow": run_follow_pipeline,
        "trend_researcher": run_trend_researcher,
        "trend_generator": run_trend_generator,
    }

    runner = runners.get(clean_name)
    if not runner:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown pipeline: {pipeline_name}. Valid names: {list(runners.keys())}",
        )

    # Execute in background thread
    import asyncio
    res = await asyncio.to_thread(runner)
    return {"message": f"Pipeline '{clean_name}' triggered successfully", "result": res}


@router.post("/{pipeline_name}/pause")
async def pause_pipeline(pipeline_name: str) -> dict[str, Any]:
    """Pauses a specific pipeline."""
    clean_name = pipeline_name.lower().replace("_pipeline", "")
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    r.set(f"xbot:pipeline:paused:{clean_name}", "1")
    return {"message": f"Pipeline '{clean_name}' paused."}


@router.post("/{pipeline_name}/resume")
async def resume_pipeline(pipeline_name: str) -> dict[str, Any]:
    """Resumes a paused pipeline."""
    clean_name = pipeline_name.lower().replace("_pipeline", "")
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    r.delete(f"xbot:pipeline:paused:{clean_name}")
    return {"message": f"Pipeline '{clean_name}' resumed."}
