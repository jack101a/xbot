"""
Session Action Executor Submodule.
Executes planned session actions in priority sequence with safety guard verification and error recording.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

import xbot.tasks as tasks
from xbot.models.session import Action, ActionStatus, ActionType, Session
from xbot.tasks.session_interaction_handler import (
    handle_follow_action,
    handle_quote_action,
    handle_reply_action,
    handle_simple_action,
)
from xbot.tasks.session_poll_thread_handler import (
    handle_poll_action,
    handle_thread_action,
)
from xbot.tasks.session_post_handler import (
    handle_mock_action,
    handle_post_action,
)

logger = logging.getLogger("xbot.tasks.session_executor")


def _parse_target_urls(target: str | None) -> tuple[str | None, str | None]:
    tweet_url = None
    username_target = None
    if target:
        if "/status/" in target:
            tweet_url = target if target.startswith("http") else f"https://x.com{target}"
        elif target.startswith("http"):
            tweet_url = None
            username_target = None
        else:
            username_target = target
    return tweet_url, username_target


async def execute_planned_actions(
    db: AsyncSession,
    session: Session,
    profile: Any,
    actions_planned: list[Any],
    page: Any,
    manager: Any,
    config: Any,
    persona: Any,
    is_mock: bool = False,
) -> tuple[int, int]:
    """Executes planned session actions in order, recording status, metrics, and logs."""
    profile_id = profile.id
    profile_slug = profile.profile_slug
    guard = tasks.SafetyGuard(base_profile_dir=str(manager.base_profile_dir))
    completed = 0
    failed = 0

    for index, p_action in enumerate(actions_planned):
        safe = await guard.is_action_safe(db, profile_slug, p_action.type)

        db_action = Action(
            session_id=session.id,
            profile_id=profile_id,
            action_type=ActionType(p_action.type),
            target_url=p_action.target,
            content=p_action.content,
            status=ActionStatus.PENDING,
        )
        db.add(db_action)
        await db.commit()
        await db.refresh(db_action)

        tasks.broadcast_session_log(session.id, "action_start", {
            "action_index": index,
            "action_id": str(db_action.id),
            "action_type": p_action.type,
            "target_url": p_action.target,
            "content": p_action.content,
            "reasoning": getattr(p_action, "reasoning", None),
            "priority": getattr(p_action, "priority", index + 1),
        })

        if not safe:
            db_action.status = ActionStatus.SKIPPED
            db_action.error = "Safety Guard rate limit or cooldown active."
            await db.commit()
            continue

        db_action.status = ActionStatus.EXECUTING
        db_action.executed_at = datetime.datetime.utcnow()
        await db.commit()

        success = False
        error_msg = ""

        try:
            t_start = datetime.datetime.utcnow()
            if is_mock:
                success = await handle_mock_action(db, profile_id, profile_slug, p_action, db_action, session, manager, t_start)
            else:
                tweet_url, username_target = _parse_target_urls(p_action.target)

                if p_action.type == "post" and p_action.content:
                    success = await handle_post_action(db, profile_id, profile_slug, p_action, db_action, session, page, config, persona, t_start)
                    if db_action.status == ActionStatus.SKIPPED:
                        continue
                elif p_action.type in ("poll", ActionType.POLL):
                    success = await handle_poll_action(db, profile_id, profile_slug, p_action, db_action, session, page, config, manager, t_start)
                elif p_action.type == "thread":
                    success = await handle_thread_action(db, profile_id, profile_slug, p_action, db_action, session, page, config, manager, t_start)
                elif p_action.type == "like":
                    if not tweet_url or "/status/" not in tweet_url:
                        db_action.status = ActionStatus.SKIPPED
                        db_action.error = f"Invalid like target: '{p_action.target}' is not an X tweet status URL."
                        continue
                    if await tasks.has_already_acted(db, profile_id, tweet_url, "like", hours=48):
                        db_action.status = ActionStatus.SKIPPED
                        db_action.error = "Already liked this tweet in last 48 hours."
                        continue
                    success = await handle_simple_action(p_action, tweet_url, username_target, page)
                elif p_action.type == "reply":
                    success = await handle_reply_action(db, profile_id, profile_slug, p_action, db_action, page, manager, tweet_url)
                    if db_action.status == ActionStatus.SKIPPED:
                        continue
                elif p_action.type == "quote":
                    success = await handle_quote_action(db, profile_id, p_action, db_action, page, persona, tweet_url, is_mock)
                    if db_action.status == ActionStatus.SKIPPED:
                        continue
                elif p_action.type == "follow":
                    success = await handle_follow_action(db, profile_id, p_action, username_target, page)
                else:
                    success = await handle_simple_action(p_action, tweet_url, username_target, page)

            t_end = datetime.datetime.utcnow()
            db_action.duration_ms = int((t_end - t_start).total_seconds() * 1000)

            if success:
                db_action.status = ActionStatus.COMPLETED
                await db.commit()
                completed += 1
                await guard.record_action_success(profile_slug, p_action.type, t_end)
            else:
                if not error_msg:
                    error_msg = f"Browser action '{p_action.type}' returned False."
        except Exception as ex:
            error_msg = str(ex)

        if not success:
            db_action.status = ActionStatus.FAILED
            db_action.error = error_msg
            await db.commit()
            failed += 1
            await guard.record_action_failure(db, profile_slug, error_msg)

        tasks.broadcast_session_log(session.id, "action_complete", {
            "action_index": index,
            "action_id": str(db_action.id),
            "action_type": db_action.action_type,
            "content": db_action.content,
            "target_url": db_action.target_url,
            "status": db_action.status,
            "error": db_action.error,
            "duration_ms": db_action.duration_ms,
        })

    return completed, failed