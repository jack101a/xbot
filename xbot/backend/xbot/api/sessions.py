from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.session import Action, Session
from xbot.tasks import run_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sessions"])

@router.post("/profiles/{profile_id}/sessions", response_model=dict[str, Any])
async def trigger_profile_session(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually triggers a new background automation session."""
    # We delay the Celery task so it runs in the background
    task = run_session.delay(str(profile_id))
    return {
        "status": "queued", 
        "message": "Session queued successfully", 
        "session_id": str(task.id)
    }

@router.get("/profiles/{profile_id}/sessions", response_model=list[dict[str, Any]])
async def list_profile_sessions(
    profile_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists recent execution sessions for a specific profile."""
    stmt = (
        select(Session)
        .where(Session.profile_id == profile_id)
        .order_by(Session.started_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    # Form list
    return [
        {
            "id": s.id,
            "profile_id": s.profile_id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "status": s.status,
            "actions_planned": s.actions_planned,
            "actions_completed": s.actions_completed,
            "actions_failed": s.actions_failed,
            "summary": s.summary,
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=dict[str, Any])
async def get_session_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Gets detailed information of a single session."""
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )

    return {
        "id": s.id,
        "profile_id": s.profile_id,
        "started_at": s.started_at,
        "ended_at": s.ended_at,
        "status": s.status,
        "actions_planned": s.actions_planned,
        "actions_completed": s.actions_completed,
        "actions_failed": s.actions_failed,
        "plan": s.plan,
        "summary": s.summary,
        "error_log": s.error_log,
    }


@router.get("/sessions/{session_id}/actions", response_model=list[dict[str, Any]])
async def get_session_actions(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists all actions executed within a specific session."""
    stmt = (
        select(Action)
        .where(Action.session_id == session_id)
        .order_by(Action.executed_at.asc())
    )
    result = await db.execute(stmt)
    actions = result.scalars().all()

    return [
        {
            "id": a.id,
            "session_id": a.session_id,
            "profile_id": a.profile_id,
            "action_type": a.action_type,
            "target_url": a.target_url,
            "content": a.content,
            "status": a.status,
            "duration_ms": a.duration_ms,
            "executed_at": a.executed_at,
            "error": a.error,
        }
        for a in actions
    ]


@router.websocket("/ws/sessions/{session_id}")
async def websocket_session_logs(websocket: WebSocket, session_id: str) -> None:
    """Streams real-time updates for a single session execution."""
    await websocket.accept()
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    channel = f"session:log:{session_id}"
    await pubsub.subscribe(channel)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg:
                data = msg["data"].decode("utf-8")
                await websocket.send_text(data)
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    except Exception as ex:
        logger.error("Error in websocket session logging stream: %s", ex)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@router.websocket("/ws/live")
async def websocket_live_global_logs(websocket: WebSocket) -> None:
    """Streams live session updates system-wide."""
    await websocket.accept()
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    channel = "session:log:live"
    await pubsub.subscribe(channel)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg:
                data = msg["data"].decode("utf-8")
                await websocket.send_text(data)
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    except Exception as ex:
        logger.error("Error in websocket live global logging stream: %s", ex)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
