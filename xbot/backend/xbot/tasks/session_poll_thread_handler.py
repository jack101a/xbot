"""
Session Poll and Multi-Tweet Thread Action Handlers.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

import xbot.tasks as tasks
from xbot.models.content import Content, ContentStatus, ContentType, ThreadItem
from xbot.models.session import Action, ActionType, Session

logger = logging.getLogger("xbot.tasks.session_poll_thread_handler")


async def handle_poll_action(
    db: AsyncSession,
    profile_id: uuid.UUID,
    profile_slug: str,
    p_action: Any,
    db_action: Action,
    session: Session,
    page: Any,
    config: Any,
    manager: Any,
    t_start: datetime.datetime,
) -> bool:
    """Handles poll creation either staged for dashboard approval or directly posted via browser."""
    full_q, options, duration_days, context_hook, reasoning = await tasks._extract_or_generate_poll_data(
        p_action, profile_slug, manager.base_profile_dir
    )
    if not full_q or not options or len(options) < 2:
        logger.warning("Poll action skipped: Poll question or options were invalid/empty.")
        db_action.status = ActionStatus.SKIPPED
        db_action.error = "Poll generation failed. Skipped to prevent posting empty or template poll."
        await db.commit()
        return True

    db_action.content = full_q
    require_approval = getattr(config, "require_post_approval", False)
    if require_approval:
        logger.info("Staging new poll for user approval on dashboard: '%s'", full_q[:50])
        draft_c = Content(
            profile_id=profile_id,
            content_type=ContentType.POLL,
            body=f"{full_q}\n" + "\n".join(f"🔘 {opt}" for opt in options),
            status=ContentStatus.DRAFT,
            ai_metadata={
                "require_approval": True,
                "poll": {
                    "question": full_q,
                    "options": options,
                    "duration_days": duration_days,
                    "context_hook": context_hook,
                    "reasoning": reasoning,
                },
                "staged_at": datetime.datetime.utcnow().isoformat(),
            },
        )
        db.add(draft_c)
        await db.commit()
        await db.refresh(draft_c)
        db_action.result = {
            "staged": True,
            "content_id": str(draft_c.id),
            "poll": {
                "question": full_q,
                "options": options,
                "duration_days": duration_days,
                "context_hook": context_hook,
                "reasoning": reasoning,
            },
            "message": "Poll draft created and queued for user approval before publishing.",
        }
        tasks.broadcast_session_log(session.id, "poll_staged_for_approval", {
            "content_id": str(draft_c.id),
            "question": full_q,
            "options": options,
        })
        return True

    screenshot_dir = str(manager.base_profile_dir / profile_slug / "screenshots")
    success = await tasks.CreatePoll(screenshot_dir=screenshot_dir).execute(
        page,
        question=full_q,
        options=options,
        duration_days=duration_days,
    )
    if success:
        db_action.result = {
            "poll": {
                "question": full_q,
                "options": options,
                "duration_days": duration_days,
                "context_hook": context_hook,
            }
        }
        db.add(Content(
            profile_id=profile_id,
            content_type=ContentType.POLL,
            body=f"{full_q}\n" + "\n".join(f"🔘 {opt}" for opt in options),
            status=ContentStatus.POSTED,
            posted_at=t_start,
            ai_metadata={
                "poll": {
                    "question": full_q,
                    "options": options,
                    "duration_days": duration_days,
                    "context_hook": context_hook,
                }
            },
        ))
        await db.commit()
    return success


async def handle_thread_action(
    db: AsyncSession,
    profile_id: uuid.UUID,
    profile_slug: str,
    p_action: Any,
    db_action: Action,
    session: Session,
    page: Any,
    config: Any,
    manager: Any,
    t_start: datetime.datetime,
) -> bool:
    """Handles multi-tweet thread creation staged for approval or posted directly."""
    raw_tweets = getattr(p_action, "thread_items", None)
    topic = getattr(p_action, "content", "") or ""
    if not raw_tweets or len(raw_tweets) < 2:
        from xbot.ai.thread_generator import generate_thread
        p_obj = tasks.load_persona(manager.base_profile_dir / profile_slug)
        gen_thread = await generate_thread(topic=topic or "Creator Strategy & Growth Breakdown", persona=p_obj, num_tweets=4)
        raw_tweets = gen_thread.tweets if gen_thread else []

    if not raw_tweets or len(raw_tweets) < 2:
        logger.warning("Thread action skipped: Thread generation failed or produced fewer than 2 tweets.")
        db_action.status = ActionStatus.SKIPPED
        db_action.error = "Thread generation failed. Skipped to prevent posting empty or template thread."
        await db.commit()
        return True

    db_action.content = f"Thread: {topic} ({len(raw_tweets)} tweets)"
    require_approval = getattr(config, "require_post_approval", False)
    if require_approval:
        logger.info("Staging new multi-tweet thread for user approval on dashboard: '%s' (%d tweets)", topic[:50], len(raw_tweets))
        draft_c = Content(
            profile_id=profile_id,
            content_type=ContentType.THREAD,
            body=raw_tweets[0] if raw_tweets else topic,
            status=ContentStatus.DRAFT,
            ai_metadata={
                "require_approval": True,
                "topic": topic,
                "tweets": raw_tweets,
                "staged_at": datetime.datetime.utcnow().isoformat(),
            },
        )
        db.add(draft_c)
        await db.commit()
        await db.refresh(draft_c)

        for idx, t_text in enumerate(raw_tweets):
            db.add(ThreadItem(
                content_id=draft_c.id,
                position=idx,
                item_type="hook" if idx == 0 else "closer" if idx == len(raw_tweets) - 1 else "body",
                text=t_text,
            ))
        await db.commit()

        db_action.result = {
            "staged": True,
            "content_id": str(draft_c.id),
            "topic": topic,
            "total_tweets": len(raw_tweets),
            "message": "Thread draft created and queued for user approval before publishing.",
        }
        tasks.broadcast_session_log(session.id, "thread_staged_for_approval", {
            "content_id": str(draft_c.id),
            "topic": topic,
            "total_tweets": len(raw_tweets),
        })
        return True

    from xbot.browser.actions.x_actions import ComposeThread
    res = await ComposeThread().execute(page, tweets=raw_tweets)
    success = res.get("status") == "success"
    if success:
        db_action.result = res
        db.add(Content(
            profile_id=profile_id,
            content_type=ContentType.THREAD,
            body=raw_tweets[0],
            status=ContentStatus.POSTED,
            tweet_id=res.get("root_tweet_id"),
            posted_at=t_start,
            ai_metadata={"tweets": raw_tweets},
        ))
        await db.commit()
    return success
