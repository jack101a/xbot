"""
Session Post and Mock Action Handlers.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import xbot.tasks as tasks
from xbot.ai.hook_optimizer import extract_links
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.session import Action, ActionStatus, ActionType, Session

logger = logging.getLogger("xbot.tasks.session_post_handler")


async def handle_post_action(
    db: AsyncSession,
    profile_id: uuid.UUID,
    profile_slug: str,
    p_action: Any,
    db_action: Action,
    session: Session,
    page: Any,
    config: Any,
    persona: Any,
    t_start: datetime.datetime,
) -> bool:
    """Handles standard standalone post actions with anti-duplication, link extraction, and 1st reply staging/publishing."""
    raw_content = getattr(p_action, "content", "") or ""
    clean_post_text, extracted_link = extract_links(raw_content.strip())
    post_text = clean_post_text

    if not post_text or len(post_text.strip()) < 5:
        logger.warning("Post action skipped: content is empty or invalid.")
        db_action.status = ActionStatus.SKIPPED
        db_action.error = "Post content was empty. Skipped to prevent posting empty or template content."
        await db.commit()
        return True

    # Anti-duplication check against recent posts/drafts (last 7 days)
    cutoff_7d = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    stmt_dup = select(Content).where(
        Content.profile_id == profile_id,
        Content.created_at >= cutoff_7d,
    )
    res_dup = await db.execute(stmt_dup)
    existing_posts = res_dup.scalars().all()

    for ep in existing_posts:
        if ep.body:
            clean_ep = ep.body.lower().strip()
            clean_pt = post_text.lower().strip()
            if clean_ep == clean_pt or (len(clean_pt) > 30 and clean_pt in clean_ep) or (len(clean_ep) > 30 and clean_ep in clean_pt):
                logger.info("Skipping duplicate post '%s' - already drafted/posted in last 7 days", post_text[:50])
                db_action.status = ActionStatus.SKIPPED
                db_action.error = "Duplicate post content detected from recent history."
                return True

    require_approval = getattr(config, "require_post_approval", False)
    if require_approval:
        logger.info("Staging new standalone post for user approval on dashboard: '%s'", post_text[:50])
        gif_query = getattr(p_action, "gif_query", None)
        media_paths = []
        research_report_dict = None
        try:
            from xbot.ai.x_researcher import research_topic_comprehensively
            r_report = await research_topic_comprehensively(
                topic=post_text,
                persona=persona,
                max_tweets=25,
                profile_slug=profile_slug,
            )
            if r_report:
                research_report_dict = r_report.model_dump()
                # Scraped media from other tweets is NOT attached to our original posts
        except Exception as r_err:
            logger.debug("Topic media research on X skipped or failed: %s", r_err)

        draft_c = Content(
            profile_id=profile_id,
            content_type=ContentType.ORIGINAL,
            body=post_text,
            status=ContentStatus.DRAFT,
            ai_metadata={
                "require_approval": True,
                "staged_at": datetime.datetime.utcnow().isoformat(),
                "reasoning": getattr(p_action, "reasoning", None),
                "gif_query": gif_query,
                "research_report": research_report_dict,
                "media_paths": media_paths if media_paths else None,
                "extracted_link": extracted_link,
                "first_reply_text": f"Link / source breakdown: {extracted_link}" if extracted_link else None,
            },
        )
        db.add(draft_c)
        await db.commit()
        await db.refresh(draft_c)
        db_action.result = {
            "staged": True,
            "content_id": str(draft_c.id),
            "message": "Post draft created and queued for user approval before publishing to live X.",
            "extracted_link": extracted_link,
        }
        tasks.broadcast_session_log(session.id, "post_staged_for_approval", {
            "content_id": str(draft_c.id),
            "body": post_text,
            "reasoning": getattr(p_action, "reasoning", None),
            "extracted_link": extracted_link,
        })
        return True

    success = await tasks.ComposePost().execute(
        page,
        post_text,
        gif_query=getattr(p_action, "gif_query", None),
    )
    if success:
        c_rec = Content(
            profile_id=profile_id,
            content_type=ContentType.ORIGINAL,
            body=post_text,
            status=ContentStatus.POSTED,
            posted_at=t_start,
            ai_metadata={"direct_publish": True, "extracted_link": extracted_link},
        )
        db.add(c_rec)
        await db.commit()

        if extracted_link:
            try:
                await tasks.sleep_with_jitter(2500)
                first_reply_msg = f"Link / source breakdown: {extracted_link}"
                reply_ok = await tasks.ReplyToTweet().execute(page, first_reply_msg)
                if reply_ok:
                    reply_rec = Content(
                        profile_id=profile_id,
                        content_type=ContentType.REPLY,
                        body=first_reply_msg,
                        status=ContentStatus.POSTED,
                        posted_at=datetime.datetime.utcnow(),
                        ai_metadata={"is_1st_reply_injection": True, "direct_publish": True},
                    )
                    db.add(reply_rec)
                    await db.commit()
                    logger.info("1st-reply link injection successfully posted: '%s'", first_reply_msg)
            except Exception as link_e:
                logger.warning("Failed to post 1st-reply link injection: %s", link_e)
    return success


async def handle_mock_action(
    db: AsyncSession,
    profile_id: uuid.UUID,
    profile_slug: str,
    p_action: Any,
    db_action: Action,
    session: Session,
    manager: Any,
    t_start: datetime.datetime,
) -> bool:
    """Simulates action execution in mock/demo mode."""
    await asyncio.sleep(0.5)
    if p_action.type == "post" and p_action.content:
        clean_mock_content, mock_extracted_link = extract_links(p_action.content)
        db.add(Content(
            profile_id=profile_id,
            content_type=ContentType.ORIGINAL,
            body=clean_mock_content,
            status=ContentStatus.POSTED,
            posted_at=t_start,
            ai_metadata={"mock_mode": True, "extracted_link": mock_extracted_link},
        ))
        await db.commit()
        if mock_extracted_link:
            db.add(Content(
                profile_id=profile_id,
                content_type=ContentType.REPLY,
                body=f"Link / source breakdown: {mock_extracted_link}",
                status=ContentStatus.POSTED,
                posted_at=t_start,
                ai_metadata={"mock_mode": True, "is_1st_reply_injection": True},
            ))
            await db.commit()
    elif p_action.type in ("poll", ActionType.POLL):
        full_q, options, duration_days, context_hook, reasoning = await tasks._extract_or_generate_poll_data(
            p_action, profile_slug, manager.base_profile_dir
        )
        db_action.content = full_q
        db_action.result = {
            "poll": {
                "question": full_q,
                "options": options,
                "duration_days": duration_days,
                "context_hook": context_hook,
                "reasoning": reasoning,
            }
        }
        db.add(Content(
            profile_id=profile_id,
            content_type=ContentType.POLL,
            body=f"{full_q}\n" + "\n".join(f"🔘 {opt}" for opt in options),
            status=ContentStatus.POSTED,
            posted_at=t_start,
            ai_metadata={
                "mock_mode": True,
                "poll_options": options,
                "duration_days": duration_days,
                "context_hook": context_hook,
            },
        ))
        await db.commit()

    tasks.broadcast_session_log(session.id, "mock_action_executed", {
        "message": f"🧪 [MOCK / DEMO MODE] Simulated execution of '{p_action.type}' on '{p_action.target or 'feed'}'.",
        "action_type": p_action.type,
        "target": p_action.target,
        "content": p_action.content,
    })
    return True
