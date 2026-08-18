from __future__ import annotations

import asyncio
import datetime
import logging
import random
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import json
from pathlib import Path
import redis

from xbot.ai.planner import plan_session
from xbot.ai.poll_generator import generate_poll
from xbot.ai.post_session import PostSessionProcessor
from xbot.ai.sniper import generate_sniper_reply
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.x_actions import (
    BrowseFeed,
    CheckUserLatestTweet,
    ComposePost,
    FollowUser,
    LikeTweet,
    ReplyToTweet,
    Retweet,
    SearchQuery,
    ScrapeTrends,
    ScrapeProfileMetrics,
    UnfollowUser,
    UnfollowNonFollowers,
    FollowEngagers,
    ScrapeFollowList,
)
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter
from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.persona import load_config
from xbot.persona.loader import load_persona
from xbot.safety.guard import SafetyGuard

logger = logging.getLogger(__name__)


async def _extract_or_generate_poll_data(
    p_action: Any,
    profile_slug: str,
    base_profile_dir: Path,
) -> tuple[str, list[str], int, str | None, str]:
    """
    Extracts poll question and options if specified in JSON format in the plan action,
    or generates a validated poll via AI matching the persona.
    """
    poll_question = ""
    poll_options: list[str] = []
    poll_duration_days = 1
    poll_context_hook: str | None = None
    poll_reasoning = ""

    if p_action.content:
        try:
            parsed_c = json.loads(p_action.content)
            if isinstance(parsed_c, dict) and "options" in parsed_c and "question" in parsed_c:
                poll_question = str(parsed_c["question"])
                poll_options = [str(opt) for opt in parsed_c["options"]]
                poll_duration_days = int(parsed_c.get("duration_days", 1))
                poll_context_hook = parsed_c.get("context_hook")
                poll_reasoning = parsed_c.get("reasoning", "")
        except Exception:
            pass

    if not poll_options or len(poll_options) < 2:
        persona = load_persona(base_profile_dir / profile_slug)
        topic = (
            p_action.content
            if (p_action.content and not p_action.content.startswith("{"))
            else (p_action.target or None)
        )
        gen_poll = await generate_poll(persona=persona, topic=topic)
        poll_question = gen_poll.question
        poll_options = gen_poll.options
        poll_duration_days = gen_poll.duration_days
        poll_context_hook = gen_poll.context_hook
        poll_reasoning = gen_poll.reasoning

    full_question = (
        f"{poll_context_hook}\n\n{poll_question}"
        if poll_context_hook and poll_context_hook not in poll_question
        else poll_question
    )

    return full_question, poll_options, poll_duration_days, poll_context_hook, poll_reasoning


async def _run_session_async(profile_id_str: str) -> dict[str, Any]:
    profile_id = uuid.UUID(profile_id_str)
    
    async with AsyncSessionLocal() as db:
        # 1. Fetch Profile
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found."}
            
        if profile.status in (ProfileStatus.PAUSED, ProfileStatus.LOCKED, ProfileStatus.SUSPENDED):
            return {"status": "ignored", "reason": f"Profile status is {profile.status}."}
            
        profile_slug = profile.profile_slug
        
        # 2. Create Session DB record
        session = Session(
            profile_id=profile_id,
            status=SessionStatus.RUNNING,
            started_at=datetime.datetime.utcnow(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        broadcast_session_log(session.id, "session_start", {"profile_slug": profile_slug})
        
        # 3. Open Browser, Scrape Feed Snapshot
        manager = BrowserManager()
        await manager.start()
        
        # Lock check
        if not manager.acquire_lock(profile_slug):
            session.status = SessionStatus.FAILED
            session.error_log = "Could not acquire Redis browser lock."
            session.ended_at = datetime.datetime.utcnow()
            await db.commit()
            await manager.stop()
            return {"status": "failed", "error": "Redis browser lock collision."}
            
        context = None
        page = None
        try:
            config = load_config(manager.base_profile_dir / profile_slug)
            is_mock = getattr(config, "mock_mode", False)
            
            if is_mock:
                feed_snapshot = [
                    {"author": "@tech_insider", "text": "AI agents are transforming software engineering in 2026! What are your thoughts on autonomous coding assistants?", "likes": "142", "retweets": "35", "url": "https://x.com/tech_insider/status/1234567890"},
                    {"author": "@saas_builder", "text": "Just launched our new SaaS analytics dashboard! Consistency and customer feedback are everything.", "likes": "89", "retweets": "12", "url": "https://x.com/saas_builder/status/1234567891"},
                    {"author": "@ai_researcher", "text": "Deep learning scaling laws vs algorithmic efficiency: why small specialized models are winning in production environments.", "likes": "310", "retweets": "64", "url": "https://x.com/ai_researcher/status/1234567892"}
                ]
                broadcast_session_log(session.id, "mock_mode_active", {
                    "message": "🧪 [MOCK / DEMO MODE ACTIVE] Running session with simulated X feed. No live requests sent to X."
                })
            else:
                proxy_url = config.proxy_url
                timezone_str = config.schedule.timezone or "America/New_York"
                
                context = await manager.get_context(
                    profile_slug=profile_slug,
                    timezone=timezone_str,
                    proxy_url=proxy_url,
                )
                page = await context.new_page()
                
                # Navigate to home
                await page.goto("https://x.com/home")
                
                # Scrape feed
                browse_feed = BrowseFeed()
                feed_snapshot = await browse_feed.execute(page, max_scrolls=1)
            
            # 4. Generate AI session plan
            plan = await plan_session(
                db=db,
                profile_slug=profile_slug,
                feed_snapshot=feed_snapshot,
                base_profile_dir=str(manager.base_profile_dir),
            )
            
            session.plan = plan.model_dump()
            await db.commit()
            
            broadcast_session_log(session.id, "session_planned", {
                "actions_count": len(plan.actions),
                "plan": plan.model_dump()
            })
            
            if plan.skip_reason:
                session.status = SessionStatus.ABORTED
                session.summary = {"reason": "natural_skip", "skip_reason": plan.skip_reason}
                session.ended_at = datetime.datetime.utcnow()
                await db.commit()
                await context.close()
                manager.release_lock(profile_slug)
                await manager.stop()
                broadcast_session_log(session.id, "session_complete", {
                    "status": "aborted",
                    "reason": plan.skip_reason
                })
                return {"status": "aborted", "reason": plan.skip_reason}
                
            # 5. Execute planned actions
            actions_planned = plan.actions
            session.actions_planned = len(actions_planned)
            await db.commit()
            
            guard = SafetyGuard(base_profile_dir=str(manager.base_profile_dir))
            
            completed = 0
            failed = 0
            
            for index, p_action in enumerate(actions_planned):
                # A. Verify Safety Guard limits
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
                
                broadcast_session_log(session.id, "action_start", {
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
                
                # B. Execute browser action
                success = False
                error_msg = ""
                
                try:
                    t_start = datetime.datetime.utcnow()
                    if is_mock:
                        await asyncio.sleep(0.5)
                        success = True
                        if p_action.type == "post" and p_action.content:
                            mock_c = Content(
                                profile_id=profile_id,
                                content_type=ContentType.ORIGINAL,
                                body=p_action.content,
                                status=ContentStatus.POSTED,
                                posted_at=t_start,
                                ai_metadata={"mock_mode": True}
                            )
                            db.add(mock_c)
                            await db.commit()
                        elif p_action.type in ("poll", ActionType.POLL):
                            full_q, options, duration_days, context_hook, reasoning = await _extract_or_generate_poll_data(
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
                            mock_c = Content(
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
                                }
                            )
                            db.add(mock_c)
                            await db.commit()
                        broadcast_session_log(session.id, "mock_action_executed", {
                            "message": f"🧪 [MOCK / DEMO MODE] Simulated execution of '{p_action.type}' on '{p_action.target or 'feed'}'.",
                            "action_type": p_action.type,
                            "target": p_action.target,
                            "content": p_action.content
                        })
                    else:
                        # Helper: determine if target is a tweet URL or a username
                        tweet_url = None
                        username_target = None
                        if p_action.target:
                            if "/status/" in p_action.target:
                                tweet_url = p_action.target if p_action.target.startswith("http") else f"https://x.com{p_action.target}"
                            else:
                                username_target = p_action.target

                        if p_action.type == "post" and p_action.content:
                            success = await ComposePost().execute(page, p_action.content)
                        elif p_action.type in ("poll", ActionType.POLL):
                            full_q, options, duration_days, context_hook, reasoning = await _extract_or_generate_poll_data(
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
                            screenshot_dir = str(manager.base_profile_dir / profile_slug / "screenshots")
                            success = await CreatePoll(screenshot_dir=screenshot_dir).execute(
                                page,
                                question=full_q,
                                options=options,
                                duration_days=duration_days,
                            )
                            if success:
                                c_rec = Content(
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
                                    }
                                )
                                db.add(c_rec)
                                await db.commit()
                        elif p_action.type == "like":
                            # tweet_url from planner (specific tweet) or random visible tweet
                            success = await LikeTweet().execute(page, tweet_url=tweet_url)
                        elif p_action.type == "reply" and p_action.content:
                            success = await ReplyToTweet().execute(page, p_action.content, tweet_url=tweet_url)
                        elif p_action.type == "retweet":
                            success = await Retweet().execute(page, tweet_url=tweet_url)
                        elif p_action.type == "follow" and (username_target or p_action.target):
                            success = await FollowUser().execute(page, username_target or p_action.target)
                        elif p_action.type == "search" and p_action.target:
                            results = await SearchQuery().execute(page, p_action.target)
                            success = len(results) > 0
                        elif p_action.type == "browse":
                            results = await BrowseFeed().execute(page, max_scrolls=1)
                            success = len(results) > 0
                        elif p_action.type == "unfollow" and (username_target or p_action.target):
                            success = await UnfollowUser().execute(page, username_target or p_action.target)
                        elif p_action.type == "scrape_trends":
                            results = await ScrapeTrends().execute(page)
                            success = len(results) > 0
                        elif p_action.type == "scrape_metrics" and p_action.target:
                            results = await ScrapeProfileMetrics().execute(page, p_action.target)
                            success = len(results) > 0
                        elif p_action.type == "unfollow_non_followers":
                            success = await UnfollowNonFollowers().execute(page, limit=10)
                        elif p_action.type == "follow_engagers" and (tweet_url or p_action.target):
                            success = await FollowEngagers().execute(page, tweet_url=tweet_url or p_action.target, limit=5)

                    t_end = datetime.datetime.utcnow()
                    db_action.duration_ms = int((t_end - t_start).total_seconds() * 1000)
                    
                    if success:
                        db_action.status = ActionStatus.COMPLETED
                        await db.commit()
                        completed += 1
                        # Record limit success
                        await guard.record_action_success(profile_slug, p_action.type, t_end)
                    else:
                        error_msg = "Browser action script returned False."
                        
                except Exception as ex:
                    error_msg = str(ex)
                    
                if not success:
                    db_action.status = ActionStatus.FAILED
                    db_action.error = error_msg
                    await db.commit()
                    failed += 1
                    # Record limit failure (progressive backoffs / circuit breakers)
                    await guard.record_action_failure(db, profile_slug, error_msg)
                
                broadcast_session_log(session.id, "action_complete", {
                    "action_index": index,
                    "action_id": str(db_action.id),
                    "action_type": db_action.action_type,
                    "content": db_action.content,
                    "target_url": db_action.target_url,
                    "status": db_action.status,
                    "error": db_action.error,
                    "duration_ms": db_action.duration_ms,
                })
                    
            # 6. Update Session Stats
            session.actions_completed = completed
            session.actions_failed = failed
            session.status = SessionStatus.COMPLETED
            session.ended_at = datetime.datetime.utcnow()
            await db.commit()
            
            broadcast_session_log(session.id, "session_complete", {
                "status": "completed",
                "completed": completed,
                "failed": failed,
            })
            
            # 7. Post-Session updates (monologues & memories)
            post_processor = PostSessionProcessor(base_profile_dir=str(manager.base_profile_dir))
            await post_processor.process_post_session(db, profile_slug, session.id)
            
            return {
                "status": "success",
                "profile_slug": profile_slug,
                "actions_completed": completed,
                "actions_failed": failed,
            }
            
        except Exception as ex:
            logger.error("Session crash for profile %s: %s", profile_slug, ex)
            session.status = SessionStatus.FAILED
            session.error_log = str(ex)
            session.ended_at = datetime.datetime.utcnow()
            await db.commit()
            broadcast_session_log(session.id, "session_complete", {
                "status": "failed",
                "error": str(ex),
            })
            return {"status": "failed", "error": str(ex)}
            
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)
            await manager.stop()


async def _collect_analytics_snapshot_async(profile_id_str: str) -> dict[str, Any]:
    profile_id = uuid.UUID(profile_id_str)
    
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found."}
            
        profile_slug = profile.profile_slug
        
        manager = BrowserManager()
        await manager.start()
        
        if not manager.acquire_lock(profile_slug):
            await manager.stop()
            return {"status": "failed", "error": "Redis browser lock collision."}
            
        context = None
        try:
            config = load_config(manager.base_profile_dir / profile_slug)
            is_mock = getattr(config, "mock_mode", False)
            followers_val = 0
            following_val = 0
            
            if is_mock:
                followers_val = profile.followers_count or 0
                following_val = profile.following_count or 0
                logger.info("🧪 [MOCK / DEMO MODE] Using existing actual counts for simulated analytics snapshot.")
            else:
                timezone_str = config.schedule.timezone or "America/New_York"
                
                context = await manager.get_context(
                    profile_slug=profile_slug,
                    timezone=timezone_str,
                    proxy_url=config.proxy_url,
                )
                page = await context.new_page()
                
                # Navigate to profile
                await page.goto(f"https://x.com/{profile.x_handle.lstrip('@')}")
                
                # Wait for profile data to load
                try:
                    await page.wait_for_selector('a[href*="/followers"]', timeout=8000)
                except Exception:
                    pass
                
                try:
                    # Try standard selectors
                    fol_el = await page.query_selector('a[href$="/verified_followers"] span')
                    if not fol_el:
                        fol_el = await page.query_selector('a[href$="/followers"] span')
                    if not fol_el:
                        fol_el = await page.query_selector('a[href*="/followers"]')
                    if fol_el:
                        txt = await fol_el.inner_text()
                        followers_val = _parse_x_counts(txt)
                        
                    ing_el = await page.query_selector('a[href$="/following"] span')
                    if not ing_el:
                        ing_el = await page.query_selector('a[href*="/following"]')
                    if ing_el:
                        txt = await ing_el.inner_text()
                        following_val = _parse_x_counts(txt)
                except Exception as e:
                    logger.warning("Scraping counts directly failed: %s", e)
                    
                if followers_val == 0:
                    followers_val = profile.followers_count or 0
                if following_val == 0:
                    following_val = profile.following_count or 0
                
            # Count actual tweets from DB
            from sqlalchemy import select, func
            from xbot.models import Content
            total_tweets_val = (await db.execute(select(func.count(Content.id)).where(Content.profile_id == profile_id))).scalar() or 0

            # Store Analytics Snapshot with real data (no random mock numbers)
            snapshot = AnalyticsSnapshot(
                profile_id=profile_id,
                snapshot_date=datetime.date.today(),
                followers=followers_val,
                following=following_val,
                total_tweets=total_tweets_val,
                impressions_24h=0,
                engagements_24h=0,
                engagement_rate=0.0,
            )
            db.add(snapshot)
            await db.commit()
            
            return {
                "status": "success",
                "profile_slug": profile_slug,
                "followers": followers_val,
                "following": following_val,
            }
            
        except Exception as ex:
            return {"status": "failed", "error": str(ex)}
            
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)
            await manager.stop()


def _parse_x_counts(text: str) -> int:
    """Helper to convert X counts string shorthand like 2.5K or 1M to integers."""
    import re
    # Find the first token representing a number (e.g. 2.5K, 12, 1,234, 1.2M)
    match = re.search(r'([\d.,]+[KMB]?)', text, re.IGNORECASE)
    if not match:
        return 0
    num_str = match.group(1).upper().replace(",", "")
    if "K" in num_str:
        return int(float(num_str.replace("K", "")) * 1000)
    elif "M" in num_str:
        return int(float(num_str.replace("M", "")) * 1000000)
    elif "B" in num_str:
        return int(float(num_str.replace("B", "")) * 1000000000)
    else:
        # Extract digits and decimal point if any
        digits = "".join(filter(lambda ch: ch.isdigit() or ch == '.', num_str))
        try:
            return int(float(digits))
        except ValueError:
            return 0


def broadcast_session_log(session_id: uuid.UUID, event_type: str, data: dict[str, Any]) -> None:
    """Broadcasts a real-time event to the Redis channel for live WebSocket logs."""
    try:
        import json
        import redis
        from xbot.config import settings
        r = redis.from_url(settings.REDIS_URL)
        payload = {
            "session_id": str(session_id),
            "event": event_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            **data
        }
        # Publish to single session channel
        r.publish(f"session:log:{session_id}", json.dumps(payload))
        # Publish to global live stream channel
        r.publish("session:log:live", json.dumps(payload))
    except Exception as ex:
        logger.error("Failed to broadcast session log: %s", ex)


@celery_app.task(name="xbot.tasks.run_session")  # type: ignore[untyped-decorator]
def run_session(profile_id: str) -> dict[str, Any]:
    """Celery task executing profile planning, browser runs, safety pacing, and monologue diary reviews."""
    logger.info("Starting Celery session execution for profile ID: %s", profile_id)
    return asyncio.run(_run_session_async(profile_id))


@celery_app.task(name="xbot.tasks.collect_analytics_snapshot")  # type: ignore[untyped-decorator]
def collect_analytics_snapshot(profile_id: str) -> dict[str, Any]:
    """Celery task running daily analytics scrapes and storing snapshots."""
    logger.info("Starting Celery analytics snapshot collection for profile ID: %s", profile_id)
    return asyncio.run(_collect_analytics_snapshot_async(profile_id))


@celery_app.task(name="xbot.tasks.check_schedules")  # type: ignore[untyped-decorator]
def check_schedules() -> None:
    """Periodic Celery Beat task that runs every 60 seconds to evaluate profile schedules."""
    logger.info("Starting schedule checker Celery task.")
    from xbot.scheduling.scheduler import check_and_trigger_schedules
    asyncio.run(check_and_trigger_schedules(AsyncSessionLocal()))


async def _run_evergreen_recycling_async(profile_id_str: str) -> dict[str, Any]:
    """Background task to find a high-performing past tweet and recycle it."""
    profile_id = uuid.UUID(profile_id_str)
    
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found."}
            
        profile_slug = profile.profile_slug
        
        # 1. Query posted content older than 7 days
        seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        stmt = select(Content).where(
            Content.profile_id == profile_id,
            Content.status == ContentStatus.POSTED,
            Content.posted_at < seven_days_ago
        )
        res = await db.execute(stmt)
        contents = res.scalars().all()
        
        if not contents:
            return {"status": "skipped", "reason": "No evergreen candidates found."}
            
        # 2. Score based on performance
        def score_content(c: Content) -> float:
            if not c.performance: return 0.0
            likes = c.performance.get("likes", 0)
            retweets = c.performance.get("retweets", 0)
            return likes * 1.0 + retweets * 2.0
            
        scored = sorted(contents, key=score_content, reverse=True)
        best = scored[0]
        
        if score_content(best) == 0 and len(scored) > 0:
            best = random.choice(scored)
            
        logger.info("Evergreen selected content %s for recycling (Profile: %s)", best.id, profile_slug)
        
        # 3. Post it using Playwright
        manager = BrowserManager()
        await manager.start()
        
        if not manager.acquire_lock(profile_slug):
            await manager.stop()
            return {"status": "failed", "error": "Redis browser lock collision."}
            
        context = None
        try:
            config = load_config(manager.base_profile_dir / profile_slug)
            is_mock = getattr(config, "mock_mode", False)
            recycled_text = f"🔄 Vault highlight:\n\n{best.body}"
            
            if is_mock:
                await asyncio.sleep(0.5)
                success = True
                logger.info("🧪 [MOCK / DEMO MODE] Simulated evergreen recycling post: %s", recycled_text)
            else:
                timezone_str = config.schedule.timezone or "America/New_York"
                
                context = await manager.get_context(
                    profile_slug=profile_slug,
                    timezone=timezone_str,
                    proxy_url=config.proxy_url,
                )
                page = await context.new_page()
                
                await page.goto("https://x.com/home")
                success = await ComposePost().execute(page, recycled_text)
            
            if success:
                new_c = Content(
                    profile_id=profile_id,
                    content_type=best.content_type,
                    body=recycled_text,
                    status=ContentStatus.POSTED,
                    posted_at=datetime.datetime.utcnow(),
                    ai_metadata={"evergreen_recycled_from": str(best.id)}
                )
                db.add(new_c)
                await db.commit()
                return {"status": "success", "recycled_id": str(best.id)}
            else:
                return {"status": "failed", "error": "ComposePost execution failed."}
                
        except Exception as ex:
            logger.error("Evergreen task crash: %s", ex)
            return {"status": "failed", "error": str(ex)}
            
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)
            await manager.stop()


@celery_app.task(name="xbot.tasks.run_evergreen_recycling")  # type: ignore[untyped-decorator]
def run_evergreen_recycling(profile_id: str) -> dict[str, Any]:
    """Celery task running the evergreen recycler."""
    logger.info("Starting Celery evergreen recycling for profile ID: %s", profile_id)
    return asyncio.run(_run_evergreen_recycling_async(profile_id))


async def _run_persona_reflection_async(profile_id_str: str) -> dict[str, Any]:
    try:
        profile_id = uuid.UUID(profile_id_str)
    except ValueError:
        return {"status": "failed", "error": "Invalid profile ID format."}
        
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found."}
            
        from xbot.ai.reflection import ReflectionEngine
        try:
            learned_state = await ReflectionEngine().reflect_and_update(db, profile.profile_slug)
            return {"status": "success", "reflection_count": learned_state.reflection_count}
        except Exception as ex:
            logger.error("Persona reflection task failed for '%s': %s", profile.profile_slug, ex)
            return {"status": "failed", "error": str(ex)}


@celery_app.task(name="xbot.tasks.run_persona_reflection")  # type: ignore[untyped-decorator]
def run_persona_reflection(profile_id: str) -> dict[str, Any]:
    """Celery task running the auto-learning persona reflection engine."""
    logger.info("Starting Celery persona reflection for profile ID: %s", profile_id)
    return asyncio.run(_run_persona_reflection_async(profile_id))


async def _run_follower_audit_async(profile_id_str: str) -> dict[str, Any]:
    from xbot.models.analytics import FollowerSnapshot, FollowerChangeLog
    try:
        profile_id = uuid.UUID(profile_id_str)
    except ValueError:
        return {"status": "failed", "error": "Invalid profile ID format."}
        
    async with AsyncSessionLocal() as db:
        # Load profile
        stmt = select(Profile).where(Profile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found"}
        
        profile_slug = profile.profile_slug
        x_handle = profile.x_handle
        
        # Check lock
        manager = BrowserManager()
        if not manager.acquire_lock(profile_slug, timeout_seconds=1200):
            return {"status": "failed", "error": "Profile lock active"}
            
        context = None
        try:
            # 1. Scrape followers & following lists
            context = await manager.get_context(profile_slug=profile_slug)
            page = await context.new_page()
            
            # Scrape current followers
            current_followers = await ScrapeFollowList().execute(page, username=x_handle, list_type="followers", limit=100)
            # Scrape current following
            current_following = await ScrapeFollowList().execute(page, username=x_handle, list_type="following", limit=100)
            
            # Close browser context to free memory
            await context.close()
            context = None
            
            # 2. Load last snapshots from DB
            last_followers_stmt = (
                select(FollowerSnapshot)
                .where(FollowerSnapshot.profile_id == profile_id, FollowerSnapshot.snapshot_type == "follower")
                .order_by(FollowerSnapshot.captured_at.desc())
                .limit(1)
            )
            res = await db.execute(last_followers_stmt)
            last_followers_snap = res.scalar_one_or_none()
            
            last_following_stmt = (
                select(FollowerSnapshot)
                .where(FollowerSnapshot.profile_id == profile_id, FollowerSnapshot.snapshot_type == "following")
                .order_by(FollowerSnapshot.captured_at.desc())
                .limit(1)
            )
            res = await db.execute(last_following_stmt)
            last_following_snap = res.scalar_one_or_none()
            
            # 3. Diff followers list
            new_changelogs = []
            if last_followers_snap:
                old_followers_set = set(last_followers_snap.handles)
                new_followers_set = set(current_followers)
                
                # People who unfollowed us
                unfollowers = old_followers_set - new_followers_set
                for u in unfollowers:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="unfollowed_us",
                            handle=u
                        )
                    )
                
                # New followers
                new_followers = new_followers_set - old_followers_set
                for f in new_followers:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="new_follower",
                            handle=f
                        )
                    )
            
            # 4. Diff following list
            if last_following_snap:
                old_following_set = set(last_following_snap.handles)
                new_following_set = set(current_following)
                
                # People we unfollowed
                we_unfollowed = old_following_set - new_following_set
                for u in we_unfollowed:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="we_unfollowed",
                            handle=u
                        )
                    )
                
                # New people we followed
                we_followed = new_following_set - old_following_set
                for f in we_followed:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="we_followed",
                            handle=f
                        )
                    )
            
            # 5. Save logs and snapshots
            for log in new_changelogs:
                db.add(log)
                
            # Create new snapshots
            db.add(FollowerSnapshot(profile_id=profile_id, snapshot_type="follower", handles=current_followers))
            db.add(FollowerSnapshot(profile_id=profile_id, snapshot_type="following", handles=current_following))
            
            await db.commit()
            
            return {
                "status": "success",
                "followers_count": len(current_followers),
                "following_count": len(current_following),
                "changelogs_recorded": len(new_changelogs)
            }
            
        except Exception as e:
            logger.error("Error in follower audit: %s", e)
            return {"status": "failed", "error": str(e)}
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)


@celery_app.task(name="xbot.tasks.run_follower_audit")
def run_follower_audit(profile_id: str) -> dict[str, Any]:
    """Celery task running the follower lists snapshot diffing audit."""
    logger.info("Starting Celery follower audit for profile ID: %s", profile_id)
    return asyncio.run(_run_follower_audit_async(profile_id))


async def _run_campaign_async(profile_id_str: str, campaign_id: str) -> dict[str, Any]:
    from xbot.campaign_manager import load_campaigns, save_campaigns
    try:
        profile_id = uuid.UUID(profile_id_str)
    except ValueError:
        return {"status": "failed", "error": "Invalid profile ID format."}
        
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found"}
        
        profile_slug = profile.profile_slug
        campaigns = load_campaigns(profile_slug)
        campaign = next((c for c in campaigns if c.id == campaign_id), None)
        if not campaign:
            return {"status": "failed", "error": "Campaign not found"}
        
        # Mark running
        campaign.status = "running"
        campaign.last_run = datetime.datetime.utcnow().isoformat()
        save_campaigns(profile_slug, campaigns)
        
        manager = BrowserManager()
        if not manager.acquire_lock(profile_slug, timeout_seconds=1800):
            campaign.status = "failed"
            save_campaigns(profile_slug, campaigns)
            return {"status": "failed", "error": "Lock active"}
            
        context = None
        try:
            context = await manager.get_context(profile_slug=profile_slug)
            page = await context.new_page()
            
            # Run steps
            for step in campaign.steps:
                logger.info("Executing campaign step %d: %s", step.step_index, step.type)
                
                # Determine targets
                tweet_url = None
                if step.target and "/status/" in step.target:
                    tweet_url = step.target
                
                if step.type == "search" and step.target:
                    await SearchQuery().execute(page, step.target)
                elif step.type == "follow_engagers" and step.target:
                    await FollowEngagers().execute(page, tweet_url=step.target, limit=step.limit)
                elif step.type == "unfollow_non_followers":
                    await UnfollowNonFollowers().execute(page, limit=step.limit)
                elif step.type == "like":
                    await LikeTweet().execute(page, tweet_url=tweet_url)
                elif step.type == "post" and step.content:
                    await ComposePost().execute(page, step.content)
                elif step.type == "reply" and step.content:
                    await ReplyToTweet().execute(page, step.content, tweet_url=tweet_url)
                
                # Jitter cooldown between steps
                await sleep_with_jitter(3000)
                
            campaign.status = "completed"
            save_campaigns(profile_slug, campaigns)
            return {"status": "success"}
            
        except Exception as e:
            logger.error("Campaign run failed: %s", e)
            campaign.status = "failed"
            save_campaigns(profile_slug, campaigns)
            return {"status": "failed", "error": str(e)}
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)


@celery_app.task(name="xbot.tasks.run_campaign")
def run_campaign(profile_id: str, campaign_id: str) -> dict[str, Any]:
    """Celery task running a declarative multi-step growth campaign."""
    logger.info("Starting Celery campaign run for campaign ID: %s", campaign_id)
    return asyncio.run(_run_campaign_async(profile_id, campaign_id))


async def _run_reputation_analysis_async(profile_id_str: str) -> dict[str, Any]:
    from xbot.models.analytics import ReputationLog
    from xbot.ai.sentiment import analyze_sentiment_rules
    try:
        profile_id = uuid.UUID(profile_id_str)
    except ValueError:
        return {"status": "failed", "error": "Invalid profile ID format."}
        
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found"}
        
        profile_slug = profile.profile_slug
        x_handle = profile.x_handle
        
        manager = BrowserManager()
        if not manager.acquire_lock(profile_slug, timeout_seconds=1200):
            return {"status": "failed", "error": "Lock active"}
            
        context = None
        try:
            context = await manager.get_context(profile_slug=profile_slug)
            page = await context.new_page()
            
            # Search for incoming tweets to us
            logger.info("Running reputation analysis: searching 'to:%s'", x_handle)
            results = await SearchQuery().execute(page, f"to:{x_handle}")
            
            await context.close()
            context = None
            
            if not results:
                logger.info("No incoming tweets found for reputation analysis.")
                # Save neutral log
                log = ReputationLog(
                    profile_id=profile_id,
                    sentiment_score=0.0,
                    total_replies_analyzed=0,
                    positive_count=0,
                    negative_count=0,
                    neutral_count=0
                )
                db.add(log)
                await db.commit()
                return {"status": "success", "replies_analyzed": 0}
                
            pos = 0
            neg = 0
            neu = 0
            
            for tweet in results:
                text = tweet.get("text", "")
                if text:
                    sent = analyze_sentiment_rules(text)
                    if sent == "positive":
                        pos += 1
                    elif sent == "negative":
                        neg += 1
                    else:
                        neu += 1
            
            total = pos + neg + neu
            score = (pos - neg) / max(total, 1)
            
            log = ReputationLog(
                profile_id=profile_id,
                sentiment_score=score,
                total_replies_analyzed=total,
                positive_count=pos,
                negative_count=neg,
                neutral_count=neu
            )
            db.add(log)
            await db.commit()
            
            logger.info("Reputation score calculated: %.2f (Total analyzed: %d)", score, total)
            return {
                "status": "success",
                "sentiment_score": score,
                "total_replies_analyzed": total,
                "positive": pos,
                "negative": neg,
                "neutral": neu
            }
            
        except Exception as e:
            logger.error("Reputation analysis task failed: %s", e)
            return {"status": "failed", "error": str(e)}
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)


@celery_app.task(name="xbot.tasks.run_reputation_analysis")
def run_reputation_analysis(profile_id: str) -> dict[str, Any]:
    """Celery task performing sentiment classification on profile mentions/replies."""
    logger.info("Starting Celery reputation analysis for profile ID: %s", profile_id)
    return asyncio.run(_run_reputation_analysis_async(profile_id))


async def _run_graph_crawler_async(profile_id_str: str, seed_handle: str) -> dict[str, Any]:
    import os
    profile_id = uuid.UUID(profile_id_str)
    
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found"}
        
        profile_slug = profile.profile_slug
        
        manager = BrowserManager()
        if not manager.acquire_lock(profile_slug, timeout_seconds=2400):
            return {"status": "failed", "error": "Lock active"}
            
        context = None
        try:
            context = await manager.get_context(profile_slug=profile_slug)
            page = await context.new_page()
            
            logger.info("Social graph crawler starting: seed @%s", seed_handle)
            
            # 1. Scrape who seed follows (up to 15)
            seed_following = await ScrapeFollowList().execute(page, username=seed_handle, list_type="following", limit=15)
            
            nodes = []
            links = []
            
            # Add seed node
            nodes.append({"id": seed_handle, "label": f"@{seed_handle}", "group": 1, "size": 20})
            
            for h in seed_following:
                nodes.append({"id": h, "label": f"@{h}", "group": 2, "size": 12})
                links.append({"source": seed_handle, "target": h})
                
            # 2. For the top 5 following, scrape who they follow (up to 5 each) to find overlaps
            for hub in seed_following[:5]:
                hub_following = await ScrapeFollowList().execute(page, username=hub, list_type="following", limit=5)
                for h in hub_following:
                    # Check if node already exists
                    if not any(n["id"] == h for n in nodes):
                        nodes.append({"id": h, "label": f"@{h}", "group": 3, "size": 8})
                    links.append({"source": hub, "target": h})
                    
            await context.close()
            context = None
            
            # Save graph JSON to file
            profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile_slug
            graph_file = profile_dir / "social_graph.json"
            os.makedirs(graph_file.parent, exist_ok=True)
            
            graph_data = {
                "nodes": nodes,
                "links": links,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "seed": seed_handle
            }
            
            with open(graph_file, "w") as f:
                json.dump(graph_data, f, indent=2)
                
            logger.info("Social graph crawl complete: %d nodes, %d links.", len(nodes), len(links))
            return {"status": "success", "nodes_count": len(nodes), "links_count": len(links)}
            
        except Exception as e:
            logger.error("Social graph crawl failed: %s", e)
            return {"status": "failed", "error": str(e)}
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)


@celery_app.task(name="xbot.tasks.run_graph_crawler")
def run_graph_crawler(profile_id: str, seed_handle: str) -> dict[str, Any]:
    """Celery task performing two-degree social graph connections crawl."""
    logger.info("Starting Celery social graph crawler for seed handle: %s", seed_handle)
    return asyncio.run(_run_graph_crawler_async(profile_id, seed_handle))


async def _run_autoreply_mentions_async(profile_id_str: str) -> dict[str, Any]:
    from xbot.models.session import Action, ActionStatus, ActionType
    from xbot.ai.client import get_ai_client
    from xbot.config import settings
    
    profile_id = uuid.UUID(profile_id_str)
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found"}
        
        profile_slug = profile.profile_slug
        x_handle = profile.x_handle
        profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile_slug
        persona = load_persona(profile_dir)
        
        manager = BrowserManager()
        if not manager.acquire_lock(profile_slug, timeout_seconds=1200):
            return {"status": "failed", "error": "Lock active"}
            
        context = None
        try:
            context = await manager.get_context(profile_slug=profile_slug)
            page = await context.new_page()
            
            logger.info("Auto-reply: searching for mentions for @%s", x_handle)
            results = await SearchQuery().execute(page, f"to:{x_handle}")
            
            replied_count = 0
            for tweet in results[:5]:  # Limit to top 5 mentions
                tweet_url = tweet.get("url")
                tweet_text = tweet.get("text", "")
                author = tweet.get("author", "")
                
                if not tweet_url or not tweet_text:
                    continue
                
                # Check if already replied
                stmt_check = select(Action).where(
                    Action.action_type == ActionType.REPLY,
                    Action.target_url == tweet_url,
                    Action.status == ActionStatus.COMPLETED
                )
                res_check = await db.execute(stmt_check)
                if res_check.scalar_one_or_none():
                    logger.info("Already replied to %s, skipping.", tweet_url)
                    continue
                
                logger.info("Generating reply to @%s: %s", author, tweet_text[:60])
                
                system_prompt = (
                    f"You are {persona.display_name} (@{persona.x_handle}). Reply to a mention on X.\n"
                    f"Tone: {persona.writing_style.tone}\n"
                    f"Traits: {', '.join(persona.personality.traits)}\n"
                    f"Interests: {', '.join(persona.interests.primary)}\n"
                    f"Writing Examples:\n" + "\n".join(f"- {ex}" for ex in persona.writing_style.examples[:3])
                )
                user_prompt = f"Mentions text content:\n\"{tweet_text}\"\n\nWrite a short, engaging reply (under 280 chars) to this user."
                
                client = get_ai_client()
                completion = await client.chat.completions.create(
                    model=settings.MODEL_REPLY_ANALYSIS,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                reply_text = completion.choices[0].message.content or ""
                reply_text = reply_text.strip()
                
                logger.info("Posting generated reply: %s", reply_text)
                success = await ReplyToTweet().execute(page, reply_text, tweet_url=tweet_url)
                
                if success:
                    replied_count += 1
                    # Record action in DB
                    act = Action(
                        profile_id=profile_id,
                        action_type=ActionType.REPLY,
                        target_url=tweet_url,
                        content=reply_text,
                        status=ActionStatus.COMPLETED
                    )
                    db.add(act)
                    await db.commit()
                    
                    # Cool down
                    await sleep_with_jitter(10000)
                    
            await context.close()
            context = None
            return {"status": "success", "replied_count": replied_count}
            
        except Exception as e:
            logger.error("Auto-reply task failed: %s", e)
            return {"status": "failed", "error": str(e)}
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)


@celery_app.task(name="xbot.tasks.run_autoreply_mentions")
def run_autoreply_mentions(profile_id: str) -> dict[str, Any]:
    """Celery task scanning incoming mentions/replies and posting replies aligned with the persona."""
    logger.info("Starting Celery auto-reply mentions task for profile: %s", profile_id)
    return asyncio.run(_run_autoreply_mentions_async(profile_id))


async def _sniper_check_targets_async() -> dict[str, Any]:
    """
    Periodically checks target Key Opinion Leader (KOL) profiles across all active profiles,
    extracts fresh tweets, verifies rate limits and Redis deduplication,
    generates persona-aligned high-retention sniper replies, and posts them via browser.
    """
    r = redis.from_url(settings.REDIS_URL)
    manager = BrowserManager()
    await manager.start()

    total_profiles = 0
    replies_posted = 0
    errors: list[str] = []

    try:
        async with AsyncSessionLocal() as db:
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
                    persona = load_persona(profile_dir)
                except Exception as ex:
                    logger.warning("Failed to load persona for profile %s: %s", profile_slug, ex)
                    continue

                if not persona.target_kols:
                    logger.debug("Profile %s has no target KOLs configured; skipping sniper check.", profile_slug)
                    continue

                guard = SafetyGuard(redis_url=settings.REDIS_URL, base_profile_dir=str(manager.base_profile_dir))
                if not await guard.is_action_safe(db, profile_slug, "reply"):
                    logger.info("Safety guard rate limit or cooldown active for profile %s; skipping sniper run.", profile_slug)
                    continue

                if not manager.acquire_lock(profile_slug, timeout_seconds=600):
                    logger.warning("Could not acquire browser lock for profile %s (sniper task collision)", profile_slug)
                    continue

                total_profiles += 1
                context = None
                try:
                    config = load_config(profile_dir)
                    is_mock = getattr(config, "mock_mode", False)

                    if not is_mock:
                        timezone_str = config.schedule.timezone or "America/New_York"
                        context = await manager.get_context(
                            profile_slug=profile_slug,
                            timezone=timezone_str,
                            proxy_url=config.proxy_url,
                        )
                        page = await context.new_page()
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
                            tweet_data = await CheckUserLatestTweet().execute(page, handle=kol_handle)

                        if not tweet_data or not tweet_data.get("tweet_id"):
                            logger.info("No tweet found for target KOL @%s", kol_handle)
                            continue

                        tweet_id = str(tweet_data["tweet_id"])
                        tweet_url = tweet_data.get("url") or f"https://x.com/{kol_handle}/status/{tweet_id}"

                        # Redis Deduplication
                        seen_key = f"xbot:seen_tweets:{profile_id}:{tweet_id}"
                        seen_set_key = f"xbot:seen_tweets:{profile_id}"

                        if r.exists(seen_key) or r.sismember(seen_set_key, tweet_id):
                            logger.info("Tweet %s from @%s already seen for profile %s; skipping.", tweet_id, kol_handle, profile_slug)
                            continue

                        # AI Sniper Reply Generation
                        reply_result = await generate_sniper_reply(
                            persona=persona,
                            target_tweet=tweet_data,
                            preferred_angle=kol.preferred_angle,
                        )

                        if not reply_result.reply_text:
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
                                success = await ReplyToTweet().execute(page, reply_result.reply_text, tweet_url=tweet_url)
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

                            # 3. Record Action in DB
                            db_action = Action(
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
                                },
                                executed_at=t_now,
                            )
                            db.add(db_action)
                            await db.commit()

                            replies_posted += 1
                            logger.info(
                                "Sniper reply successfully posted for profile %s -> @%s (tweet_id=%s, angle=%s)",
                                profile_slug,
                                kol_handle,
                                tweet_id,
                                reply_result.angle_used,
                            )

                            await sleep_with_jitter(3000)
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
    return asyncio.run(_sniper_check_targets_async())






