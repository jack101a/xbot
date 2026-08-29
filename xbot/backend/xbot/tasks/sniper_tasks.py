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

logger = logging.getLogger("xbot.tasks")


async def _sniper_check_targets_async() -> dict[str, Any]:
    """
    Periodically checks target Key Opinion Leader (KOL) profiles across all active profiles,
    extracts fresh tweets, verifies rate limits and Redis deduplication,
    generates persona-aligned high-retention sniper replies, and posts them via browser.
    """
    r = tasks.redis.from_url(settings.REDIS_URL)
    manager = tasks.BrowserManager()
    await manager.start()

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
                profile_dir = manager.base_profile_dir / profile_slug

                try:
                    persona = tasks.load_persona(profile_dir)
                except Exception as ex:
                    logger.warning("Failed to load persona for profile %s: %s", profile_slug, ex)
                    continue

                if not persona.target_kols:
                    logger.debug("Profile %s has no target KOLs configured; skipping sniper check.", profile_slug)
                    continue

                guard = tasks.SafetyGuard(redis_url=settings.REDIS_URL, base_profile_dir=str(manager.base_profile_dir))
                if not await guard.is_action_safe(db, profile_slug, "reply"):
                    logger.info("Safety guard rate limit or cooldown active for profile %s; skipping sniper run.", profile_slug)
                    continue

                if not manager.acquire_lock(profile_slug, timeout_seconds=600):
                    logger.warning("Could not acquire browser lock for profile %s (sniper task collision)", profile_slug)
                    continue

                total_profiles += 1
                context = None
                try:
                    config = tasks.load_config(profile_dir)
                    is_mock = getattr(config, "mock_mode", False)

                    if not is_mock:
                        timezone_str = config.schedule.timezone or "America/New_York"
                        context = await manager.get_context(
                            profile_slug=profile_slug,
                            timezone=timezone_str,
                            proxy_url=config.proxy_url,
                        )
                        page = await context.new_page() if context else None
                    else:
                        page = None

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
                            checker = tasks.CheckUserLatestTweet()
                            tweet_data = await checker.execute(page, handle=kol_handle)

                        if not tweet_data or not tweet_data.get("tweet_id"):
                            logger.info("No tweet found for target KOL @%s", kol_handle)
                            continue

                        tweet_id = str(tweet_data["tweet_id"])
                        tweet_url = tweet_data.get("url") or f"https://x.com/{kol_handle}/status/{tweet_id}"

                        # Redis Deduplication
                        seen_key = f"xbot:seen_tweets:{profile_id}:{tweet_id}"
                        seen_set_key = f"xbot:seen_tweets:{profile_id}"

                        if r.exists(seen_key) or r.sismember(seen_set_key, tweet_id) or await tasks.has_already_acted(db, profile_id, tweet_url, "reply", hours=48):
                            logger.info("Tweet %s from @%s already replied to for profile %s; skipping.", tweet_id, kol_handle, profile_slug)
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
                            continue

                        # Execute Reply
                        success = False
                        error_msg = None
                        try:
                            if is_mock:
                                await asyncio.sleep(0.5)
                                success = True
                            else:
                                reply_action = tasks.ReplyToTweet()
                                success = await reply_action.execute(
                                    page,
                                    reply_result.reply_text,
                                    tweet_url=tweet_url,
                                    gif_query=reply_result.gif_query,
                                )
                        except Exception as ex:
                            error_msg = str(ex)
                            logger.error("Error executing sniper reply to %s: %s", tweet_url, ex)

                        if success:
                            # 1. Deduplication record
                            r.set(seen_key, "1", ex=604800)  # 7 days TTL
                            r.sadd(seen_set_key, tweet_id)

                            # 2. Record success in SafetyGuard
                            t_now = datetime.datetime.utcnow()
                            await guard.record_action_success(profile_slug, "reply", t_now)

                            # 3. Create Session and Record Action in DB
                            session_rec = Session(
                                profile_id=profile_id,
                                status=SessionStatus.COMPLETED,
                                actions_planned=1,
                                actions_completed=1,
                                actions_failed=0,
                                plan={"mode": "sniper_reply", "target_kol": kol_handle},
                                started_at=t_now,
                                ended_at=t_now,
                            )
                            db.add(session_rec)
                            await db.flush()

                            action_rec = Action(
                                session_id=session_rec.id,
                                profile_id=profile_id,
                                action_type=ActionType.REPLY,
                                target_url=tweet_url,
                                content=reply_result.reply_text,
                                status=ActionStatus.COMPLETED,
                                result={
                                    "sniper": True,
                                    "target_kol": kol_handle,
                                    "angle": reply_result.angle_used,
                                    "confidence": reply_result.confidence,
                                    "reasoning": reply_result.reasoning,
                                    "tweet_id": tweet_id,
                                    "opportunity_score": opp_score.model_dump(),
                                },
                                executed_at=t_now,
                            )
                            db.add(action_rec)
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
                            await guard.record_action_failure(db, profile_slug, error_msg)
                            logger.warning(
                                "Failed to post sniper reply for profile %s -> @%s: %s",
                                profile_slug,
                                kol_handle,
                                error_msg,
                            )

                except Exception as ex:
                    logger.error("Error in sniper check loop for profile %s: %s", profile_slug, ex)
                    errors.append(f"{profile_slug}: {ex}")
                finally:
                    if context:
                        await context.close()
                    manager.release_lock(profile_slug)

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
        await manager.stop()


@celery_app.task(name="xbot.tasks.sniper_check_targets")
def sniper_check_targets() -> dict[str, Any]:
    """Celery periodic task scanning target KOL profiles for fresh tweets and executing sniper replies."""
    logger.info("Starting Celery sniper check targets task.")
    return asyncio.run(tasks._sniper_check_targets_async())
