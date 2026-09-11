from __future__ import annotations

import asyncio
import datetime
import logging
import random
import re
import uuid
from typing import Any

from sqlalchemy import select
import xbot.tasks as tasks
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.utils.time import now_ist

logger = logging.getLogger("xbot.tasks")


async def _sniper_check_targets_async() -> dict[str, Any]:
    """
    Periodically checks target Key Opinion Leader (KOL) profiles across all active profiles,
    extracts fresh tweets, verifies rate limits and Redis deduplication,
    generates persona-aligned high-retention sniper replies, and posts them via browser.
    """
    from xbot.contracts.browser import BrowserActionType, BrowserRequest
    from xbot.container import get_container
    from pathlib import Path

    r = tasks.redis.from_url(settings.REDIS_URL)
    container = get_container()

    # Distributed Task Mutex Lock: Prevent concurrent Celery workers from overlapping
    task_lock = r.lock("xbot:lock:sniper_check_targets", timeout=900, blocking=False)
    acquired = False
    try:
        acquired = task_lock.acquire(blocking=False)
    except Exception as lock_err:
        logger.warning("Could not acquire sniper task lock: %s", lock_err)
    if not acquired:
        logger.info("Sniper check targets already running in another worker; skipping this invocation.")
        return {
            "status": "skipped",
            "reason": "already_running",
            "profiles_processed": 0,
            "replies_posted": 0,
        }

    total_profiles = 0
    replies_posted = 0
    errors: list[str] = []

    try:
        async with tasks.AsyncSessionLocal() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            res = await db.execute(stmt)
            active_profiles = res.scalars().all()

            if not active_profiles:
                logger.info("No active profiles found for sniper target checking.")
                return {
                    "status": "success",
                    "profiles_processed": 0,
                    "replies_posted": 0,
                }

            for profile in active_profiles:
                profile_slug = profile.profile_slug
                profile_id = profile.id
                profile_dir = Path(settings.BASE_PROFILE_DIR) / profile_slug

                try:
                    persona = tasks.load_persona(profile_dir)
                except Exception as ex:
                    logger.warning("Failed to load persona for profile %s: %s", profile_slug, ex)
                    continue

                if not persona.target_kols:
                    logger.debug("Profile %s has no target KOLs configured; skipping sniper check.", profile_slug)
                    continue

                guard = tasks.SafetyGuard(redis_url=settings.REDIS_URL, base_profile_dir=str(settings.BASE_PROFILE_DIR))
                if not await guard.is_action_safe(db, profile_slug, "reply"):
                    logger.info("Safety guard rate limit or cooldown active for profile %s; skipping sniper run.", profile_slug)
                    continue

                total_profiles += 1
                try:
                    config = tasks.load_config(profile_dir)
                    is_mock = getattr(config, "mock_mode", False)

                    for kol in persona.target_kols:
                        kol_handle = kol.handle.lstrip("@").strip()
                        if not kol_handle:
                            continue

                        # Verify safety limit before checking each target KOL
                        if not await guard.is_action_safe(db, profile_slug, "reply"):
                            logger.info("Rate limit reached for %s during target scan; halting sniper loop.", profile_slug)
                            break

                        tweet_data = None
                        if is_mock:
                            tweet_data = {
                                "tweet_id": f"mock_{kol_handle}_{int(datetime.datetime.utcnow().timestamp())}",
                                "text": f"Simulated latest tweet from @{kol_handle} on technical innovations.",
                                "url": f"https://x.com/{kol_handle}/status/mock_{kol_handle}",
                                "handle": kol_handle,
                                "is_pinned": False,
                                "created_at": "1m",
                            }
                        else:
                            req = BrowserRequest(
                                profile_slug=profile_slug,
                                action=BrowserActionType.CHECK_USER_LATEST,
                                params={"username": kol_handle, "max_age_minutes": 60},
                                timeout_seconds=45,
                            )
                            res = await container.browser.execute(req)
                            tweet_data = res.action_result.raw if (res.action_result and res.action_result.raw) else None

                        if not tweet_data or not tweet_data.get("tweet_id"):
                            logger.info("No tweet found for target KOL @%s", kol_handle)
                            continue

                        tweet_id = str(tweet_data["tweet_id"])
                        tweet_url = tweet_data.get("url") or f"https://x.com/{kol_handle}/status/{tweet_id}"

                        # Redis & DB Lifetime Deduplication + 12h Failure Cooldown
                        seen_key = f"xbot:seen_tweets:{profile_id}:{tweet_id}"
                        seen_set_key = f"xbot:seen_tweets:{profile_id}"
                        failed_key = f"xbot:failed_tweets:{profile_id}:{tweet_id}"
                        inflight_key = f"xbot:inflight_tweet:{profile_id}:{tweet_id}"

                        if (
                            r.exists(seen_key)
                            or r.exists(failed_key)
                            or r.sismember(seen_set_key, tweet_id)
                            or await tasks.has_already_acted(db, profile_id, tweet_url, "reply", hours=None, include_failed_cooldown_hours=12)
                        ):
                            logger.info("Tweet %s from @%s already acted upon or in failure cooldown for %s; skipping.", tweet_id, kol_handle, profile_slug)
                            continue

                        # Atomic In-Flight Lock: Ensure only 1 worker can process this tweet at any time
                        if not r.set(inflight_key, "1", nx=True, ex=600):
                            logger.info("Tweet %s from @%s is currently being processed by another worker/task; skipping.", tweet_id, kol_handle)
                            continue

                        tweet_text = tweet_data.get("text", "")
                        from xbot.safety.topic_blacklist import topic_blacklist_filter
                        is_blocked, block_reason = topic_blacklist_filter.is_blocked(tweet_text, persona)
                        if is_blocked:
                            logger.info(
                                "TopicBlacklistFilter skipped target KOL @%s tweet %s: %s",
                                kol_handle,
                                tweet_id,
                                block_reason,
                            )
                            r.delete(inflight_key)
                            continue

                        # Evaluate algorithmic opportunity score (Phoenix Recommender weights)
                        opp_score = score_tweet_opportunity(tweet_data)
                        if opp_score.recommended_action == "skip" and opp_score.score < 25.0:
                            logger.info(
                                "Phoenix Growth Scorer skipped target KOL @%s tweet %s (score=%.1f): %s",
                                kol_handle,
                                tweet_id,
                                opp_score.score,
                                opp_score.reasoning,
                            )
                            r.delete(inflight_key)
                            continue

                        # AI Sniper Reply Generation
                        reply_result = await tasks.generate_sniper_reply(
                            persona=persona,
                            target_tweet=tweet_data,
                            preferred_angle=kol.preferred_angle,
                            opportunity_score=opp_score,
                        )

                        if not reply_result or not reply_result.reply_text:
                            logger.warning("Empty sniper reply generated for @%s tweet %s; skipping.", kol_handle, tweet_id)
                            r.delete(inflight_key)
                            continue

                        # Pre-Flight Double Check: Verify tweet was not acted upon while AI was generating
                        if await tasks.has_already_acted(db, profile_id, tweet_url, "reply", hours=None, include_failed_cooldown_hours=12):
                            logger.warning("Pre-flight check: Tweet %s was already replied to during generation; aborting duplicate.", tweet_id)
                            r.delete(inflight_key)
                            continue

                        # Atomic Reservation: Stage session and action in DB before execution to block race conditions
                        t_now = now_ist()
                        session_rec = Session(
                            profile_id=profile_id,
                            status=SessionStatus.RUNNING,
                            actions_planned=1,
                            actions_completed=0,
                            actions_failed=0,
                            plan={"mode": "sniper_reply", "target_kol": kol_handle},
                            started_at=t_now,
                        )
                        db.add(session_rec)
                        await db.flush()

                        action_rec = Action(
                            session_id=session_rec.id,
                            profile_id=profile_id,
                            action_type=ActionType.REPLY,
                            target_url=tweet_url,
                            content=reply_result.reply_text,
                            status=ActionStatus.STAGED,
                            executed_at=t_now,
                        )
                        db.add(action_rec)
                        await db.commit()

                        # Execute Reply
                        success = False
                        error_msg = None
                        try:
                            if is_mock:
                                await asyncio.sleep(0.5)
                                success = True
                            else:
                                reply_req = BrowserRequest(
                                    profile_slug=profile_slug,
                                    action=BrowserActionType.REPLY,
                                    params={
                                        "text": reply_result.reply_text,
                                        "tweet_url": tweet_url,
                                        "gif_query": reply_result.gif_query,
                                    },
                                    timeout_seconds=150,
                                )
                                reply_res = await container.browser.execute(reply_req)
                                success = reply_res.status == "success" or (reply_res.action_result and reply_res.action_result.status == "success")
                                if not success:
                                    error_msg = reply_res.error or (reply_res.action_result.detail if reply_res.action_result else "Reply failed")
                        except Exception as ex:
                            error_msg = str(ex)
                            logger.error("Error executing sniper reply to %s: %s", tweet_url, ex)

                        if success:
                            # 1. Deduplication record & release inflight key
                            r.set(seen_key, "1", ex=604800)  # 7 days TTL
                            r.sadd(seen_set_key, tweet_id)
                            r.delete(inflight_key)

                            # 2. Record success in SafetyGuard
                            t_finish = now_ist()
                            await guard.record_action_success(profile_slug, "reply", t_finish)

                            # 3. Finalize Session and Action in DB
                            session_rec.status = SessionStatus.COMPLETED
                            session_rec.actions_completed = 1
                            session_rec.ended_at = t_finish
                            action_rec.status = ActionStatus.COMPLETED
                            action_rec.result = {
                                "sniper": True,
                                "target_kol": kol_handle,
                                "angle": reply_result.angle_used,
                                "confidence": reply_result.confidence,
                                "reasoning": reply_result.reasoning,
                                "tweet_id": tweet_id,
                                "opportunity_score": opp_score.model_dump(),
                            }
                            await db.commit()

                            replies_posted += 1
                            logger.info(
                                "Sniper reply successfully posted for profile %s -> @%s (tweet_id=%s, angle=%s)",
                                profile_slug,
                                kol_handle,
                                tweet_id,
                                reply_result.angle_used,
                            )

                            await tasks.sleep_with_jitter(3000)
                        else:
                            if not error_msg:
                                error_msg = f"Browser ReplyToTweet returned False for @{kol_handle} tweet {tweet_id}"
                            
                            # 1. Record 12-hour failure cooldown in Redis and release inflight key
                            r.set(failed_key, "1", ex=43200)
                            r.delete(inflight_key)

                            # 2. Update DB session & action as failed
                            t_finish = now_ist()
                            session_rec.status = SessionStatus.FAILED
                            session_rec.actions_failed = 1
                            session_rec.ended_at = t_finish
                            action_rec.status = ActionStatus.FAILED
                            action_rec.error = error_msg
                            await db.commit()

                            await guard.record_action_failure(db, profile_slug, error_msg)
                            logger.warning(
                                "Failed to post sniper reply for profile %s -> @%s (entering 12h cooldown): %s",
                                profile_slug,
                                kol_handle,
                                error_msg,
                            )

                except Exception as ex:
                    logger.error("Error in sniper check loop for profile %s: %s", profile_slug, ex)
                    errors.append(f"{profile_slug}: {ex}")

        return {
            "status": "success" if not errors else "partial_success",
            "profiles_processed": total_profiles,
            "replies_posted": replies_posted,
            "errors": errors if errors else None,
        }

    except Exception as overall_ex:
        logger.error("Sniper check targets task encountered critical error: %s", overall_ex)
        return {"status": "failed", "error": str(overall_ex)}
    finally:
        if acquired:
            try:
                task_lock.release()
            except Exception:
                pass


@celery_app.task(name="xbot.tasks.sniper_check_targets")
def sniper_check_targets() -> dict[str, Any]:
    """Celery periodic task scanning target KOL profiles for fresh tweets and executing sniper replies."""
    logger.info("Starting Celery sniper check targets task.")
    return asyncio.run(tasks._sniper_check_targets_async())
