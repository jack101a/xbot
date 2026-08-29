"""
Session Wrapup Submodule.
Finalizes session stats, triggers post-session reflection/monologues, and broadcasts completion telemetry.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

import xbot.tasks as tasks
from xbot.ai.post_session import PostSessionProcessor
from xbot.models.session import Session, SessionStatus

logger = logging.getLogger("xbot.tasks.session_wrapup")


async def finalize_session(
    db: AsyncSession,
    session: Session,
    profile_slug: str,
    completed: int,
    failed: int,
    base_profile_dir: str,
) -> dict[str, Any]:
    """Finalizes successful session, broadcasts completion log, and triggers PostSessionProcessor."""
    session.actions_completed = completed
    session.actions_failed = failed
    session.status = SessionStatus.COMPLETED
    session.ended_at = datetime.datetime.utcnow()
    await db.commit()

    tasks.broadcast_session_log(session.id, "session_complete", {
        "status": "completed",
        "completed": completed,
        "failed": failed,
    })

    # Post-Session updates (monologues & memories)
    post_processor = PostSessionProcessor(base_profile_dir=base_profile_dir)
    await post_processor.process_post_session(db, profile_slug, session.id)

    return {
        "status": "success",
        "profile_slug": profile_slug,
        "actions_completed": completed,
        "actions_failed": failed,
    }


async def handle_session_abort(
    db: AsyncSession,
    session: Session,
    skip_reason: str,
) -> dict[str, Any]:
    """Handles natural skip / plan abort for a session."""
    session.status = SessionStatus.ABORTED
    session.summary = {"reason": "natural_skip", "skip_reason": skip_reason}
    session.ended_at = datetime.datetime.utcnow()
    await db.commit()

    tasks.broadcast_session_log(session.id, "session_complete", {
        "status": "aborted",
        "reason": skip_reason,
    })
    return {"status": "aborted", "reason": skip_reason}


async def handle_session_failure(
    db: AsyncSession,
    session: Session,
    error_msg: str,
    profile_slug: str,
) -> dict[str, Any]:
    """Handles unhandled exception during session execution."""
    logger.error("Session crash for profile %s: %s", profile_slug, error_msg)
    session.status = SessionStatus.FAILED
    session.error_log = error_msg
    session.ended_at = datetime.datetime.utcnow()
    await db.commit()

    tasks.broadcast_session_log(session.id, "session_complete", {
        "status": "failed",
        "error": error_msg,
    })
    return {"status": "failed", "error": error_msg}
