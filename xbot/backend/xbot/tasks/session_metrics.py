"""
Session Metrics, Reciprocity Audits, Alignment Pruning, and Storage Cleanup.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

import xbot.tasks as tasks
from xbot.models.follow_growth import FollowRelationship
from xbot.models.session import Action, ActionStatus, ActionType

logger = logging.getLogger("xbot.tasks.session_metrics")


async def audit_reciprocity_and_prune(
    db: AsyncSession,
    profile_id: uuid.UUID,
    profile_slug: str,
    session_id: uuid.UUID,
    page: Any,
    is_mock: bool = False,
) -> None:
    """Audits follow relationships past grace period and unfollows non-reciprocating accounts."""
    if is_mock or not page:
        return

    try:
        from xbot.browser.actions.x_actions import CheckProfileFollowsYou, UnfollowUser

        now_time = datetime.datetime.utcnow()
        stmt_expired = (
            select(FollowRelationship)
            .where(
                FollowRelationship.profile_id == profile_id,
                FollowRelationship.status == "following",
                FollowRelationship.grace_period_expires_at <= now_time,
            )
            .limit(3)  # Prune at most 3 per session to stay within stealth limits
        )
        res_expired = await db.execute(stmt_expired)
        expired_rels = res_expired.scalars().all()

        if expired_rels:
            logger.info("Auditing %d relationships with expired 4-day grace period for @%s", len(expired_rels), profile_slug)
            checker = CheckProfileFollowsYou()
            unfollower = UnfollowUser()

            for rel in expired_rels:
                target = rel.target_handle.lstrip("@")
                rel.last_checked_at = now_time
                follows_us = await checker.execute(page, username=target)

                if follows_us:
                    logger.info("Mutual follow confirmed: @%s follows us back!", target)
                    rel.status = "followed_back"
                    await db.commit()
                else:
                    logger.info("Grace period (4 days) expired without follow-back from @%s. Pruning unfollow...", target)
                    unfollow_ok = await unfollower.execute(page, username=target)
                    if unfollow_ok:
                        rel.status = "unfollowed"
                        rel.unfollowed_at = now_time

                        unf_action = Action(
                            profile_id=profile_id,
                            session_id=session_id,
                            action_type=ActionType.UNFOLLOW,
                            target_url=f"https://x.com/{target}",
                            status=ActionStatus.COMPLETED,
                            executed_at=now_time,
                        )
                        db.add(unf_action)
                        await db.commit()

                        tasks.broadcast_session_log(session_id, "unfollow_pruned", {
                            "target": f"@{target}",
                            "reason": "Grace period (4 days) expired without reciprocity. Unfollowed to maintain ratio.",
                        })
    except Exception as audit_err:
        logger.warning("Reciprocity audit and unfollow pruning encountered non-fatal error: %s", audit_err)


async def audit_and_prune_misaligned_actions(
    db: AsyncSession,
    profile_id: uuid.UUID,
    page: Any,
    is_mock: bool = False,
) -> None:
    """Scans recent replies for policy or domain misalignment and auto-deletes them if needed."""
    if is_mock or not page:
        return

    try:
        from xbot.ai.sniper import ANIME_KEYWORDS, BANNED_POLITICS_REGEX, TECH_KEYWORDS
        from xbot.browser.actions.x_actions import human_click

        cutoff_recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        stmt_recent_replies = (
            select(Action)
            .where(
                Action.profile_id == profile_id,
                Action.action_type == ActionType.REPLY,
                Action.status == ActionStatus.COMPLETED,
                Action.executed_at >= cutoff_recent,
            )
            .order_by(desc(Action.executed_at))
            .limit(10)
        )
        res_rr = await db.execute(stmt_recent_replies)
        recent_actions = res_rr.scalars().all()

        for act in recent_actions:
            if not act.content:
                continue

            has_politics = bool(BANNED_POLITICS_REGEX.search(act.content))
            has_cross_domain = False
            if act.target_url:
                t_url_lower = act.target_url.lower()
                c_lower = act.content.lower()
                if any(k in t_url_lower for k in TECH_KEYWORDS) and any(k in c_lower for k in {"oda", "god valley", "luffy", "zoro"}):
                    has_cross_domain = True
                if any(k in t_url_lower for k in ANIME_KEYWORDS) and any(k in c_lower for k in {"snapdragon", "m4 max", "benchmark"}):
                    has_cross_domain = True

            if has_politics or has_cross_domain:
                logger.warning("Integrity auditor flagged misaligned action %s: politics=%s, cross_domain=%s. Auto-pruning from live X...", act.id, has_politics, has_cross_domain)
                try:
                    await page.goto("https://x.com/jackds1234/with_replies", wait_until="domcontentloaded", timeout=25000)
                    await tasks.sleep_think_time(2000, 4000)
                    tweets = await page.query_selector_all('[data-testid="tweet"]')
                    for tw in tweets:
                        t_txt_el = await tw.query_selector('[data-testid="tweetText"]')
                        if t_txt_el:
                            t_txt = await t_txt_el.inner_text()
                            if act.content[:25].lower() in t_txt.lower():
                                caret = await tw.query_selector('button[aria-label="More"], [data-testid="caret"]')
                                if caret:
                                    await human_click(page, caret, 200, 400)
                                    await tasks.sleep_think_time(600, 1200)
                                    del_btn = await page.query_selector('[data-testid="Dropdown"] [role="menuitem"]:has-text("Delete")')
                                    if del_btn:
                                        await human_click(page, del_btn, 200, 400)
                                        await tasks.sleep_think_time(600, 1000)
                                        confirm = await page.query_selector('[data-testid="confirmationSheetConfirm"]')
                                        if confirm:
                                            await human_click(page, confirm, 200, 400)
                                            await tasks.sleep_with_jitter(1500)
                                            logger.info("Successfully auto-deleted misaligned tweet from live X.")
                                            act.status = ActionStatus.FAILED
                                            act.error = "Auto-pruned by post-publishing integrity auditor."
                                            await db.commit()
                                            break
                except Exception as del_err:
                    logger.warning("Could not auto-delete misaligned tweet: %s", del_err)
    except Exception as prune_err:
        logger.debug("Post-session self-healing pruner skipped: %s", prune_err)


def clean_temp_storage_and_logs() -> None:
    """Prunes temporary media and log files older than 7 days."""
    try:
        temp_storage_dirs = [
            Path("/home/ubuntu/projects/xbot/data/temp_media"),
            Path("/home/ubuntu/projects/xbot/backend/logs"),
        ]
        now_ts = datetime.datetime.utcnow().timestamp()
        cutoff_7d = now_ts - (7 * 86400)
        for sdir in temp_storage_dirs:
            if sdir.exists():
                for f in sdir.glob("*"):
                    if f.is_file() and f.stat().st_mtime < cutoff_7d:
                        try:
                            f.unlink()
                        except Exception:
                            pass
    except Exception as store_err:
        logger.debug("Storage maintenance pruner skipped: %s", store_err)
