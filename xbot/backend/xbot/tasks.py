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

from xbot.ai.client import get_ai_client
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.ai.hook_optimizer import extract_links
from xbot.ai.planner import plan_session
from xbot.ai.poll_generator import generate_poll
from xbot.ai.post_session import PostSessionProcessor
from xbot.ai.sniper import generate_sniper_reply
from xbot.ai.trend_generator import generate_trend_take
from xbot.ai.trend_radar import fetch_rss_trends
from xbot.ai.visual_engine import generate_visual_post_spec
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.x_actions import (
    BrowseFeed,
    CheckUserLatestTweet,
    ComposePost,
    FollowEngagers,
    FollowUser,
    LikeTweet,
    QuoteTweet,
    ReplyToTweet,
    Retweet,
    ScrapeFollowList,
    ScrapeProfileMetrics,
    ScrapeTrends,
    SearchQuery,
    UnfollowNonFollowers,
    UnfollowUser,
)
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter, sleep_think_time
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

from xbot.ai.trend_radar import fetch_rss_trends, fetch_multi_source_trends
from xbot.ai.trend_generator import generate_trend_take

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


async def has_already_acted(
    db: AsyncSession,
    profile_id: uuid.UUID,
    target_url: str | None,
    action_type: Any,
    hours: int = 48,
) -> bool:
    """
    Checks if an action of the specified type has already been executed
    against the given target_url within the last `hours` (default 48h).
    Prevents duplicate likes, replies, and quotes on the exact same tweets.
    """
    if not target_url:
        return False
    clean_target = target_url.strip().rstrip("/")
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    act_type_str = action_type.value if hasattr(action_type, "value") else str(action_type)

    stmt = (
        select(Action)
        .where(
            Action.profile_id == profile_id,
            Action.action_type == act_type_str,
            Action.status == ActionStatus.COMPLETED,
            Action.executed_at >= cutoff,
            (Action.target_url == clean_target) | (Action.target_url == f"{clean_target}/"),
        )
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


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
                
                # 1. Scrape feed
                browse_feed = BrowseFeed()
                try:
                    feed_snapshot = await browse_feed.execute(page, max_scrolls=1)
                except Exception as e:
                    logger.warning("Feed browsing encountered non-fatal error: %s", e)
                    feed_snapshot = []

                if feed_snapshot is None:
                    feed_snapshot = []

                # 2. Live Opportunity Hunting: Scan target creators (KOLs) defined in persona
                try:
                    persona = load_persona(manager.base_profile_dir / profile_slug)
                    if persona and getattr(persona, "target_kols", None):
                        checker = CheckUserLatestTweet()
                        # Shuffle and rotate target KOLs so we don't scan the same creators in the same order
                        shuffled_kols = list(persona.target_kols)
                        random.shuffle(shuffled_kols)

                        for kol in shuffled_kols[:5]:
                            clean_h = kol.handle.lstrip("@")
                            try:
                                logger.info("Scanning target creator @%s for live reply opportunities...", clean_h)
                                kol_tweet = await checker.execute(page, handle=clean_h)
                                if kol_tweet and kol_tweet.get("text"):
                                    t_url = kol_tweet.get("url") or f"https://x.com/{clean_h}"

                                    # Deduplication: check if we already replied to this exact tweet in last 48h
                                    already_replied = await has_already_acted(db, profile_id, t_url, "reply", hours=48)
                                    already_liked = await has_already_acted(db, profile_id, t_url, "like", hours=48)

                                    if already_replied or already_liked:
                                        logger.info("Skipping creator tweet %s: already replied/liked in last 48h", t_url)
                                        continue

                                    already_quoted = await has_already_acted(db, profile_id, t_url, "quote", hours=48)

                                    feed_snapshot.append({
                                        "author": clean_h,
                                        "text": kol_tweet.get("text"),
                                        "url": t_url,
                                        "likes": kol_tweet.get("likes", 0),
                                        "retweets": kol_tweet.get("retweets", 0),
                                        "replies": kol_tweet.get("replies", 0),
                                        "top_comments": kol_tweet.get("top_comments", []),
                                        "already_replied": already_replied,
                                        "already_quoted": already_quoted,
                                    })
                            except Exception as k_err:
                                logger.warning("Could not check target creator @%s: %s", clean_h, k_err)
                except Exception as p_err:
                    logger.warning("Error during KOL opportunity scanning: %s", p_err)

                # 2b. Live Growth & Follow-Back Search Hunting: Scan live Twitter Search for active mutuals/f4f posts
                try:
                    growth_queries = [
                        '("drop your handle" OR "follow back") (tech OR anime OR "blue tick" OR mutuals)',
                        '("looking for mutuals" OR "verified mutuals") (anime OR tech OR AI)',
                        '("follow back everyone" OR "f4f") (tech OR anime OR "blue tick")',
                        '("drop your handle" OR "mutuals connect")',
                    ]
                    chosen_query = random.choice(growth_queries)
                    logger.info("Hunting active follow-back posts on live X Search: %s", chosen_query)
                    searcher = SearchQuery()
                    growth_results = await searcher.execute(page, query=chosen_query)
                    for gr in growth_results[:5]:
                        g_url = gr.get("url")
                        if g_url and await has_already_acted(db, profile_id, g_url, "reply", hours=48):
                            logger.info("Skipping growth thread %s: already replied in last 48h", g_url)
                            continue
                        feed_snapshot.append({
                            "author": gr.get("author", "mutuals_creator"),
                            "text": f"🤝 [ACTIVE FOLLOW-BACK / MUTUALS THREAD]: {gr.get('text', '')}",
                            "url": g_url,
                            "is_blue_tick": gr.get("is_blue_tick", True),
                            "likes": gr.get("likes", 25),
                            "retweets": gr.get("retweets", 15),
                            "replies": gr.get("replies", 20),
                            "is_growth_thread": True,
                        })

                    # Harvest active commenters from the top growth thread into FollowCandidate table
                    if growth_results:
                        top_growth_url = growth_results[0].get("url")
                        if top_growth_url:
                            from xbot.browser.actions.x_actions import HarvestFollowBackThread
                            from xbot.models.follow_growth import FollowCandidate
                            harvester = HarvestFollowBackThread()
                            thread_candidates = await harvester.execute(page, tweet_url=top_growth_url, max_candidates=6)
                            for tc in thread_candidates:
                                c_handle = tc["handle"]
                                ex_stmt = select(FollowCandidate).where(
                                    FollowCandidate.profile_id == profile_id,
                                    FollowCandidate.handle == c_handle
                                )
                                ex_res = await db.execute(ex_stmt)
                                if not ex_res.scalar_one_or_none():
                                    cand = FollowCandidate(
                                        profile_id=profile_id,
                                        handle=c_handle,
                                        display_name=tc.get("display_name"),
                                        niche="growth_mutuals",
                                        is_blue_tick=tc.get("is_blue_tick", True),
                                        source_discussion=f"Commenter in follow-back thread: {top_growth_url}",
                                        source_tweet_url=top_growth_url,
                                        reciprocity_score=tc.get("reciprocity_score", 85.0),
                                        status="discovered"
                                    )
                                    db.add(cand)
                            await db.commit()
                except Exception as s_err:
                    logger.warning("Live follow-back search scan encountered non-fatal error: %s", s_err)

                # 3. Live Trends Ingestion: Fetch breaking trends and viral discussions
                try:
                    from xbot.ai.trend_radar import fetch_rss_trends
                    rss_urls = [
                        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-IN&gl=IN&ceid=IN%3Aen",
                        "https://feeds.feedburner.com/TechCrunch/",
                    ]
                    live_trends = await fetch_rss_trends(rss_urls[:2], max_items_per_feed=3)
                    for tr in live_trends[:4]:
                        feed_snapshot.append({
                            "author": f"LiveNews ({tr.source_name})",
                            "text": f"🔥 [BREAKING NEWS/TOPIC FOR STANDALONE POST ONLY]: {tr.title}",
                            "url": None,  # Non-tweet URL nullified so it cannot be chosen as a reply/like/quote target
                            "type": "trend_topic",
                            "is_news_article": True,
                        })
                except Exception as t_err:
                    logger.debug("Trend pre-scan skipped or failed: %s", t_err)

                logger.info("Total live opportunities & trends assembled in feed snapshot: %d items", len(feed_snapshot))
            
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
                            clean_mock_content, mock_extracted_link = extract_links(p_action.content)
                            mock_c = Content(
                                profile_id=profile_id,
                                content_type=ContentType.ORIGINAL,
                                body=clean_mock_content,
                                status=ContentStatus.POSTED,
                                posted_at=t_start,
                                ai_metadata={"mock_mode": True, "extracted_link": mock_extracted_link}
                            )
                            db.add(mock_c)
                            await db.commit()

                            if mock_extracted_link:
                                mock_reply_c = Content(
                                    profile_id=profile_id,
                                    content_type=ContentType.REPLY,
                                    body=f"Link / source breakdown: {mock_extracted_link}",
                                    status=ContentStatus.POSTED,
                                    posted_at=t_start,
                                    ai_metadata={"mock_mode": True, "is_1st_reply_injection": True}
                                )
                                db.add(mock_reply_c)
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
                            elif p_action.target.startswith("http"):
                                tweet_url = None
                                username_target = None
                            else:
                                username_target = p_action.target

                        if p_action.type == "post" and p_action.content:
                            clean_post_text, extracted_link = extract_links(p_action.content.strip())
                            post_text = clean_post_text
                            
                            # Anti-duplication check against recent posts/drafts (last 7 days)
                            cutoff_7d = datetime.datetime.utcnow() - datetime.timedelta(days=7)
                            stmt_dup = select(Content).where(
                                Content.profile_id == profile_id,
                                Content.created_at >= cutoff_7d
                            )
                            res_dup = await db.execute(stmt_dup)
                            existing_posts = res_dup.scalars().all()
                            
                            is_duplicate = False
                            for ep in existing_posts:
                                if ep.body:
                                    clean_ep = ep.body.lower().strip()
                                    clean_pt = post_text.lower().strip()
                                    if clean_ep == clean_pt or (len(clean_pt) > 30 and clean_pt in clean_ep) or (len(clean_ep) > 30 and clean_ep in clean_pt):
                                        is_duplicate = True
                                        break
                            
                            if is_duplicate:
                                logger.info("Skipping duplicate post '%s' - already drafted/posted in last 7 days", post_text[:50])
                                db_action.status = ActionStatus.SKIPPED
                                db_action.error = "Duplicate post content detected from recent history."
                                success = True
                                continue

                            require_approval = getattr(config, "require_post_approval", True)
                            if require_approval:
                                logger.info("Staging new standalone post for user approval on dashboard: '%s'", post_text[:50])
                                
                                # Synthesize 4:5 visual meme spec or fallback GIF query to maximize algorithmic impressions
                                visual_spec_dict = None
                                gif_query = getattr(p_action, "gif_query", None)
                                media_paths = []
                                try:
                                    v_spec = await generate_visual_post_spec(
                                        topic=post_text,
                                        persona=persona,
                                    )
                                    if v_spec:
                                        visual_spec_dict = v_spec.model_dump()
                                        if not gif_query and v_spec.gif_search_query:
                                            gif_query = v_spec.gif_search_query
                                        
                                        # Render physical 4:5 vertical meme/infographic image to disk
                                        from xbot.ai.meme_renderer import render_visual_spec_to_image
                                        rendered_img = render_visual_spec_to_image(visual_spec_dict)
                                        if rendered_img and os.path.exists(rendered_img):
                                            media_paths.append(os.path.abspath(rendered_img))
                                except Exception as v_err:
                                    logger.debug("Visual spec synthesis skipped: %s", v_err)

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
                                        "visual_spec": visual_spec_dict,
                                        "media_paths": media_paths if media_paths else None,
                                        "extracted_link": extracted_link,
                                        "first_reply_text": f"Link / source breakdown: {extracted_link}" if extracted_link else None,
                                    }
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
                                success = True
                                broadcast_session_log(session.id, "post_staged_for_approval", {
                                    "content_id": str(draft_c.id),
                                    "body": post_text,
                                    "reasoning": getattr(p_action, "reasoning", None),
                                    "extracted_link": extracted_link,
                                })
                            else:
                                success = await ComposePost().execute(
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
                                        ai_metadata={
                                            "direct_publish": True,
                                            "extracted_link": extracted_link,
                                        }
                                    )
                                    db.add(c_rec)
                                    await db.commit()

                                    if extracted_link:
                                        try:
                                            await sleep_with_jitter(2500)
                                            first_reply_msg = f"Link / source breakdown: {extracted_link}"
                                            reply_ok = await ReplyToTweet().execute(page, first_reply_msg)
                                            if reply_ok:
                                                reply_rec = Content(
                                                    profile_id=profile_id,
                                                    content_type=ContentType.REPLY,
                                                    body=first_reply_msg,
                                                    status=ContentStatus.POSTED,
                                                    posted_at=datetime.datetime.utcnow(),
                                                    ai_metadata={"is_1st_reply_injection": True, "direct_publish": True}
                                                )
                                                db.add(reply_rec)
                                                await db.commit()
                                                logger.info("1st-reply link injection successfully posted: '%s'", first_reply_msg)
                                        except Exception as link_e:
                                            logger.warning("Failed to post 1st-reply link injection: %s", link_e)
                        elif p_action.type in ("poll", ActionType.POLL):
                            full_q, options, duration_days, context_hook, reasoning = await _extract_or_generate_poll_data(
                                p_action, profile_slug, manager.base_profile_dir
                            )
                            db_action.content = full_q
                            require_approval = getattr(config, "require_post_approval", True)
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
                                    }
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
                                success = True
                                broadcast_session_log(session.id, "poll_staged_for_approval", {
                                    "content_id": str(draft_c.id),
                                    "question": full_q,
                                    "options": options,
                                })
                            else:
                                screenshot_dir = str(manager.base_profile_dir / profile_slug / "screenshots")
                                success = await CreatePoll(screenshot_dir=screenshot_dir).execute(
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
                        elif p_action.type == "thread":
                            raw_tweets = getattr(p_action, "thread_items", None)
                            topic = p_action.content or "Creator Strategy & Growth Breakdown"
                            if not raw_tweets or len(raw_tweets) < 2:
                                from xbot.ai.thread_generator import generate_thread
                                persona = load_persona(manager.base_profile_dir / profile_slug)
                                gen_thread = await generate_thread(topic=topic, persona=persona, num_tweets=4)
                                raw_tweets = gen_thread.tweets

                            db_action.content = f"Thread: {topic} ({len(raw_tweets)} tweets)"
                            require_approval = getattr(config, "require_post_approval", True)
                            if require_approval:
                                logger.info("Staging new multi-tweet thread for user approval on dashboard: '%s' (%d tweets)", topic[:50], len(raw_tweets))
                                from xbot.models.content import ThreadItem
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
                                    }
                                )
                                db.add(draft_c)
                                await db.commit()
                                await db.refresh(draft_c)

                                for idx, t_text in enumerate(raw_tweets):
                                    t_item = ThreadItem(
                                        content_id=draft_c.id,
                                        position=idx,
                                        item_type="hook" if idx == 0 else "closer" if idx == len(raw_tweets) - 1 else "body",
                                        text=t_text,
                                    )
                                    db.add(t_item)
                                await db.commit()

                                db_action.result = {
                                    "staged": True,
                                    "content_id": str(draft_c.id),
                                    "topic": topic,
                                    "total_tweets": len(raw_tweets),
                                    "message": "Thread draft created and queued for user approval before publishing.",
                                }
                                success = True
                                broadcast_session_log(session.id, "thread_staged_for_approval", {
                                    "content_id": str(draft_c.id),
                                    "topic": topic,
                                    "total_tweets": len(raw_tweets),
                                })
                            else:
                                from xbot.browser.actions.x_actions import ComposeThread
                                res = await ComposeThread().execute(page, tweets=raw_tweets)
                                success = res.get("status") == "success"
                                if success:
                                    db_action.result = res
                                    c_rec = Content(
                                        profile_id=profile_id,
                                        content_type=ContentType.THREAD,
                                        body=raw_tweets[0],
                                        status=ContentStatus.POSTED,
                                        tweet_id=res.get("root_tweet_id"),
                                        posted_at=t_start,
                                        ai_metadata={"tweets": raw_tweets}
                                    )
                                    db.add(c_rec)
                                    await db.commit()
                        elif p_action.type == "like":
                            if not tweet_url or "/status/" not in tweet_url:
                                logger.warning("Like action skipped: target '%s' is not a valid X tweet status URL.", p_action.target)
                                db_action.status = ActionStatus.SKIPPED
                                db_action.error = f"Invalid like target: '{p_action.target}' is not an X tweet status URL."
                                success = True
                                continue
                            if await has_already_acted(db, profile_id, tweet_url, "like", hours=48):
                                logger.info("Target tweet %s already liked in last 48h. Skipping duplicate.", tweet_url)
                                db_action.status = ActionStatus.SKIPPED
                                db_action.error = "Already liked this tweet in last 48 hours."
                                success = True
                                continue
                            success = await LikeTweet().execute(page, tweet_url=tweet_url)

                        elif p_action.type == "reply":
                            if not tweet_url or "/status/" not in tweet_url:
                                logger.warning("Reply action skipped: target '%s' is not a valid X tweet status URL.", p_action.target)
                                db_action.status = ActionStatus.SKIPPED
                                db_action.error = f"Invalid reply target: '{p_action.target}' is not an X tweet status URL."
                                success = True
                                continue

                            if await has_already_acted(db, profile_id, tweet_url, "reply", hours=48):
                                logger.info("Target tweet %s already replied to in last 48h. Skipping duplicate.", tweet_url)
                                db_action.status = ActionStatus.SKIPPED
                                db_action.error = "Already replied to this tweet in last 48 hours."
                                success = True
                                continue

                            reply_action = ReplyToTweet()
                            logger.info("Navigating directly to target tweet URL to reply: %s", tweet_url)
                            try:
                                await page.goto(tweet_url, wait_until="commit", timeout=20000)
                                await page.wait_for_selector(SELECTORS["tweet"], timeout=15000)
                            except Exception as nav_e:
                                logger.warning("Target tweet navigation / selector wait warning: %s", nav_e)
                            await sleep_think_time(1000, 2500)

                            # Scrape live tweet context & top comments directly from THIS specific tweet page
                            live_ctx = await reply_action.scrape_target_tweet_context(page, target_idx=0)

                            persona = load_persona(manager.base_profile_dir / profile_slug)
                            if persona and live_ctx.get("text"):
                                # Evaluate algorithmic opportunity score (Phoenix Recommender weights)
                                opp_score = score_tweet_opportunity(live_ctx)
                                if opp_score.recommended_action == "skip" and opp_score.score < 25.0:
                                    logger.info(
                                        "Phoenix Growth Scorer recommended skipping target tweet %s (score=%.1f): %s",
                                        tweet_url,
                                        opp_score.score,
                                        opp_score.reasoning,
                                    )
                                    db_action.status = ActionStatus.SKIPPED
                                    db_action.error = f"Opportunity score too low ({opp_score.score:.1f}/100): {opp_score.reasoning}"
                                    db_action.result = {"opportunity_score": opp_score.model_dump()}
                                    await db.commit()
                                    success = True
                                    continue

                                logger.info(
                                    "Synthesizing JIT Sniper Reply for live tweet by @%s (opp_score=%.1f): '%s'",
                                    live_ctx.get("author"),
                                    opp_score.score,
                                    live_ctx.get("text", "")[:60],
                                )
                                sniper_res = await generate_sniper_reply(
                                    persona=persona,
                                    target_tweet=live_ctx,
                                    preferred_angle=getattr(p_action, "preferred_angle", None) or getattr(p_action, "angle", None),
                                    opportunity_score=opp_score,
                                )
                                final_reply_text = sniper_res.reply_text
                                final_gif_query = sniper_res.gif_query or getattr(p_action, "gif_query", None)
                                db_action.content = final_reply_text
                                res_dict = sniper_res.model_dump()
                                res_dict["opportunity_score"] = opp_score.model_dump()
                                db_action.result = res_dict
                                await db.commit()

                                # If top-tier writing models failed/timed out, safely skip this action
                                if not final_reply_text or sniper_res.confidence == 0.0:
                                    logger.warning("Sniper reply safely skipped: Top-tier writing models timed out. Will retry in next session.")
                                    db_action.status = ActionStatus.SKIPPED
                                    db_action.error = "Top-tier writing models busy/unavailable after retries. Discarded to prevent posting low quality."
                                    await db.commit()
                                    success = True
                                    continue
                            else:
                                final_reply_text = p_action.content
                                final_gif_query = getattr(p_action, "gif_query", None)

                                if not final_reply_text:
                                    logger.warning("Reply skipped: No content provided or planned.")
                                    db_action.status = ActionStatus.SKIPPED
                                    db_action.error = "No reply content available."
                                    await db.commit()
                                    success = True
                                    continue

                            success = await reply_action.execute(
                                page,
                                reply_text=final_reply_text,
                                tweet_url=tweet_url,
                                tweet_index=0,
                                gif_query=final_gif_query,
                            )
                        elif p_action.type == "retweet":
                            success = await Retweet().execute(page, tweet_url=tweet_url)
                        elif p_action.type == "quote":
                            if not tweet_url or "/status/" not in tweet_url:
                                logger.warning("Quote action skipped: target '%s' is not a valid X tweet status URL.", p_action.target)
                                db_action.status = ActionStatus.SKIPPED
                                db_action.error = f"Invalid quote target: '{p_action.target}' is not an X tweet status URL."
                                success = True
                                continue
                            if await has_already_acted(db, profile_id, tweet_url, "quote", hours=48):
                                logger.info("Target tweet %s already quote-tweeted in last 48h. Skipping duplicate.", tweet_url)
                                db_action.status = ActionStatus.SKIPPED
                                db_action.error = "Already quoted this tweet in last 48 hours."
                                success = True
                                continue

                            # Check target tweet popularity before quoting (minimum 100k views threshold & no F4F trains)
                            if not is_mock:
                                live_ctx = await ReplyToTweet().scrape_target_tweet_context(page, tweet_url=tweet_url, target_idx=0)
                                target_text = live_ctx.get("text", "")
                                from xbot.ai.growth_scorer import is_f4f_or_engagement_growth_post
                                if is_f4f_or_engagement_growth_post(target_text) or is_f4f_or_engagement_growth_post(p_action.content or ""):
                                    logger.info("Target tweet is a follow-for-follow / engagement-growth train. Quoting forbidden. Skipping quote action.")
                                    db_action.status = ActionStatus.SKIPPED
                                    db_action.error = "Quoting F4F / engagement-growth posts is forbidden. Synthesize original posts instead."
                                    success = True
                                    continue

                                target_views = int(live_ctx.get("impressions", 0) or live_ctx.get("views", 0) or 0)
                                if 0 < target_views < 100_000:
                                    logger.info("Target tweet %s has only %d views (< 100,000 required for quote-tweeting). Skipping quote action.", tweet_url, target_views)
                                    db_action.status = ActionStatus.SKIPPED
                                    db_action.error = f"Target tweet has only {target_views:,} views (< 100,000 required for quote-tweet virality)."
                                    success = True
                                    continue

                            quote_text = p_action.content or "Sharp perspective on this. Adding to the discussion."
                            success = await QuoteTweet().execute(page, quote_text=quote_text, tweet_url=tweet_url)
                        elif p_action.type == "follow":
                            from xbot.models.follow_growth import FollowCandidate, FollowRelationship
                            target_to_follow = username_target or p_action.target
                            if target_to_follow:
                                clean_target = target_to_follow.lstrip("@")
                                rel_chk = await db.execute(
                                    select(FollowRelationship).where(
                                        FollowRelationship.profile_id == profile_id,
                                        FollowRelationship.target_handle == clean_target,
                                    )
                                )
                                if rel_chk.scalar_one_or_none():
                                    logger.info("Account @%s already followed. Finding next un-followed candidate...", clean_target)
                                    target_to_follow = None

                            if not target_to_follow:
                                c_stmt = (
                                    select(FollowCandidate)
                                    .where(FollowCandidate.profile_id == profile_id)
                                    .where(FollowCandidate.status.in_(["discovered", "queued"]))
                                    .order_by(FollowCandidate.is_blue_tick.desc(), FollowCandidate.reciprocity_score.desc())
                                    .limit(1)
                                )
                                c_res = await db.execute(c_stmt)
                                top_c = c_res.scalar_one_or_none()
                                if top_c:
                                    target_to_follow = top_c.handle
                                    top_c.status = "followed"
                                    await db.commit()

                            if target_to_follow:
                                clean_f_handle = target_to_follow.lstrip("@")
                                success = await FollowUser().execute(page, clean_f_handle)
                                if success:
                                    from xbot.growth.f4f_engine import record_follow_action
                                    await record_follow_action(
                                        profile_id=profile_id,
                                        target_handle=clean_f_handle,
                                        db=db,
                                        is_blue_tick=True,
                                    )
                            else:
                                success = False
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
                        if not error_msg:
                            if p_action.type == "like":
                                error_msg = "Tweet could not be liked (target unavailable or button not reachable)."
                            elif p_action.type == "follow":
                                error_msg = f"User @{username_target or p_action.target} could not be followed (account private, suspended, or button unavailable)."
                            elif p_action.type == "reply":
                                error_msg = "Reply could not be posted (target tweet unavailable or editor failed to mount)."
                            elif p_action.type in ("retweet", "quote"):
                                error_msg = f"{p_action.type.capitalize()} could not be posted (target tweet unavailable or menu failed)."
                            else:
                                error_msg = f"Browser action '{p_action.type}' returned False."
                        
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
                    
            # 6b. Reciprocity Audit & Automated 4-5 Day Unfollow Pruning
            if not is_mock and page:
                try:
                    from xbot.models.follow_growth import FollowRelationship
                    from xbot.browser.actions.x_actions import CheckProfileFollowsYou, UnfollowUser
                    
                    now_time = datetime.datetime.utcnow()
                    stmt_expired = (
                        select(FollowRelationship)
                        .where(
                            FollowRelationship.profile_id == profile_id,
                            FollowRelationship.status == "following",
                            FollowRelationship.grace_period_expires_at <= now_time
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
                                        session_id=session.id,
                                        action_type=ActionType.UNFOLLOW,
                                        target_url=f"https://x.com/{target}",
                                        status=ActionStatus.COMPLETED,
                                        executed_at=now_time,
                                    )
                                    db.add(unf_action)
                                    await db.commit()
                                    
                                    broadcast_session_log(session.id, "unfollow_pruned", {
                                        "target": f"@{target}",
                                        "reason": "Grace period (4 days) expired without reciprocity. Unfollowed to maintain ratio.",
                                    })
                except Exception as audit_err:
                    logger.warning("Reciprocity audit and unfollow pruning encountered non-fatal error: %s", audit_err)

            # 6c. Automated Post-Publishing Self-Healing & Misalignment Pruner
            if not is_mock and page:
                try:
                    from xbot.ai.sniper import BANNED_POLITICS_REGEX, TECH_KEYWORDS, ANIME_KEYWORDS
                    from xbot.browser.actions.x_actions import human_click

                    cutoff_recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
                    stmt_recent_replies = (
                        select(Action)
                        .where(
                            Action.profile_id == profile_id,
                            Action.action_type == ActionType.REPLY,
                            Action.status == ActionStatus.COMPLETED,
                            Action.executed_at >= cutoff_recent
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
                                await sleep_think_time(2000, 4000)
                                tweets = await page.query_selector_all('[data-testid="tweet"]')
                                for tw in tweets:
                                    t_txt_el = await tw.query_selector('[data-testid="tweetText"]')
                                    if t_txt_el:
                                        t_txt = await t_txt_el.inner_text()
                                        if act.content[:25].lower() in t_txt.lower():
                                            caret = await tw.query_selector('button[aria-label="More"], [data-testid="caret"]')
                                            if caret:
                                                await human_click(page, caret, 200, 400)
                                                await sleep_think_time(600, 1200)
                                                del_btn = await page.query_selector('[data-testid="Dropdown"] [role="menuitem"]:has-text("Delete")')
                                                if del_btn:
                                                    await human_click(page, del_btn, 200, 400)
                                                    await sleep_think_time(600, 1000)
                                                    confirm = await page.query_selector('[data-testid="confirmationSheetConfirm"]')
                                                    if confirm:
                                                        await human_click(page, confirm, 200, 400)
                                                        await sleep_with_jitter(1500)
                                                        logger.info("Successfully auto-deleted misaligned tweet from live X.")
                                                        act.status = ActionStatus.FAILED
                                                        act.error = "Auto-pruned by post-publishing integrity auditor."
                                                        await db.commit()
                                                        break
                            except Exception as del_err:
                                logger.warning("Could not auto-delete misaligned tweet: %s", del_err)
                except Exception as prune_err:
                    logger.debug("Post-session self-healing pruner skipped: %s", prune_err)

            # 6d. Storage Maintenance & Temp Artifacts Cleaner (Zero Disk Bloat)
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


def broadcast_session_log(
    session_id: uuid.UUID | str,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Broadcasts a real-time event to the Redis channel for live WebSocket logs with standardized payload keys."""
    try:
        import json
        import redis
        from xbot.config import settings
        r = redis.from_url(settings.REDIS_URL)
        payload_data = data or {}
        payload = {
            "event": event_type,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": str(session_id),
            "action_type": payload_data.get("action_type"),
            "status": payload_data.get("status"),
            "content": payload_data.get("content"),
            "error": payload_data.get("error"),
            **payload_data,
        }
        json_str = json.dumps(payload)
        # Publish to single session channel
        r.publish(f"session:log:{session_id}", json_str)
        # Publish to global live stream channel
        r.publish("session:log:live", json_str)
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
                
                # New followers: record log and queue for immediate reciprocal follow-back
                new_followers = new_followers_set - old_followers_set
                from xbot.models.follow_growth import FollowCandidate
                for f in new_followers:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="new_follower",
                            handle=f
                        )
                    )
                    clean_f = f.lstrip("@")
                    if clean_f not in current_following:
                        chk_c = await db.execute(
                            select(FollowCandidate).where(
                                FollowCandidate.profile_id == profile_id,
                                FollowCandidate.handle == clean_f,
                            )
                        )
                        if not chk_c.scalar_one_or_none():
                            db.add(
                                FollowCandidate(
                                    profile_id=profile_id,
                                    handle=clean_f,
                                    display_name=clean_f,
                                    niche="incoming_follower",
                                    is_blue_tick=True,
                                    reciprocity_score=100.0,
                                    status="queued",
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

                        if r.exists(seen_key) or r.sismember(seen_set_key, tweet_id) or await has_already_acted(db, profile_id, tweet_url, "reply", hours=48):
                            logger.info("Tweet %s from @%s already replied to for profile %s; skipping.", tweet_id, kol_handle, profile_slug)
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
                        reply_result = await generate_sniper_reply(
                            persona=persona,
                            target_tweet=tweet_data,
                            preferred_angle=kol.preferred_angle,
                            opportunity_score=opp_score,
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
                                success = await ReplyToTweet().execute(
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
                            db_session = Session(
                                profile_id=profile_id,
                                status=SessionStatus.COMPLETED,
                                actions_planned=1,
                                actions_completed=1,
                                actions_failed=0,
                                plan={"mode": "sniper_reply", "target_kol": kol_handle},
                                started_at=t_now,
                                ended_at=t_now,
                            )
                            db.add(db_session)
                            await db.flush()

                            db_action = Action(
                                session_id=db_session.id,
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


async def _check_trend_radar_async(base_profile_dir: Path | str | None = None) -> dict[str, Any]:
    """
    Periodically checks RSS and trend radar sources for all active profiles,
    evaluates relevance against each persona niche, synthesizes 3-bullet takes + hot takes with optimized hooks,
    and stages approved content into the Content database table with Redis deduplication.
    """
    r = redis.from_url(settings.REDIS_URL)
    base_dir = Path(base_profile_dir) if base_profile_dir else Path("/home/ubuntu/projects/xbot/data/profiles")

    total_profiles = 0
    items_scanned = 0
    items_staged = 0
    errors: list[str] = []

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            res = await db.execute(stmt)
            active_profiles = res.scalars().all()

            if not active_profiles:
                logger.info("No active profiles found for trend radar checking.")
                return {
                    "status": "success",
                    "profiles_processed": 0,
                    "items_scanned": 0,
                    "items_staged": 0,
                }

            for profile in active_profiles:
                profile_slug = profile.profile_slug
                profile_id = profile.id
                profile_dir = base_dir / profile_slug

                try:
                    total_profiles += 1

                    # 1. Load persona
                    try:
                        persona = load_persona(profile_dir)
                    except Exception as ex:
                        logger.warning("Failed to load persona for profile %s: %s", profile_slug, ex)
                        errors.append(f"{profile_slug}: {ex}")
                        continue

                    # 2. Extract configured trend sources or fallback to defaults
                    feed_urls: list[str] = []
                    keywords: list[str] = []

                    trend_sources = getattr(persona, "trend_sources", None)
                    if isinstance(trend_sources, dict):
                        feed_urls = trend_sources.get("rss_feeds", []) or []
                        keywords = trend_sources.get("keywords", []) or []
                    elif hasattr(trend_sources, "rss_feeds"):
                        feed_urls = getattr(trend_sources, "rss_feeds", []) or []
                        keywords = getattr(trend_sources, "keywords", []) or []
                    elif isinstance(getattr(persona, "raw_character_card", None), dict):
                        raw_ts = persona.raw_character_card.get("trend_sources", {})
                        if isinstance(raw_ts, dict):
                            feed_urls = raw_ts.get("rss_feeds", []) or []
                            keywords = raw_ts.get("keywords", []) or []

                    if not feed_urls:
                        feed_urls = ["https://hnrss.org/frontpage"]

                    if not keywords and persona.interests and persona.interests.primary:
                        keywords = list(persona.interests.primary)

                    # 3. Fetch trends from RSS/Atom feeds or multi-source real-time radar
                    try:
                        trends = await fetch_rss_trends(feed_urls, keywords=keywords)
                        if not trends and feed_urls == ["https://hnrss.org/frontpage"]:
                            trends = await fetch_multi_source_trends(
                                feed_urls=feed_urls if feed_urls else None,
                                keywords=keywords,
                                max_total=12,
                            )
                    except Exception as ex:
                        logger.warning("Failed to fetch trends for profile %s: %s", profile_slug, ex)
                        errors.append(f"{profile_slug} trend fetch: {ex}")
                        continue

                    items_scanned += len(trends)

                    # 4. Process each trend item
                    breaking_trend_summaries = []
                    for item in trends:
                        item_id = item.id
                        seen_key = f"xbot:seen_trends:{profile_id}:{item_id}"
                        seen_set_key = f"xbot:seen_trends:{profile_id}"

                        # Redis Deduplication
                        try:
                            if r.exists(seen_key) or r.sismember(seen_set_key, item_id):
                                logger.debug("Trend item %s already seen for profile %s; skipping.", item_id, profile_slug)
                                continue
                        except Exception as r_err:
                            logger.warning("Redis dedup check error: %s", r_err)

                        # Evaluate Take via LLM
                        eval_result = await generate_trend_take(persona, item)

                        # Cache in Redis with 7-day TTL
                        try:
                            r.set(seen_key, "1", ex=604800)
                            r.sadd(seen_set_key, item_id)
                        except Exception as r_err:
                            logger.warning("Redis cache error: %s", r_err)

                        # If relevant, record for session planner
                        if eval_result.is_relevant and eval_result.relevance_score >= 0.65:
                            breaking_trend_summaries.append({
                                "topic": item.title,
                                "summary": item.summary,
                                "hot_take": eval_result.hot_take,
                                "quote_hook": eval_result.quote_hook,
                            })

                        # If highly relevant and post produced, synthesize visual spec and stage Content record in DB (max 3 per run)
                        if eval_result.is_relevant and eval_result.relevance_score >= 0.70 and eval_result.optimized_post and items_staged < 3:
                            post_text = eval_result.optimized_post
                            
                            # Synthesize rich 4:5 visual meme / infographic spec
                            visual_spec_dict = None
                            gif_query = None
                            media_paths = []
                            try:
                                v_spec = await generate_visual_post_spec(
                                    topic=post_text,
                                    persona=persona,
                                )
                                if v_spec:
                                    visual_spec_dict = v_spec.model_dump()
                                    gif_query = v_spec.gif_search_query
                                    
                                    # Render physical 4:5 vertical meme/infographic image to disk
                                    from xbot.ai.meme_renderer import render_visual_spec_to_image
                                    rendered_img = render_visual_spec_to_image(visual_spec_dict)
                                    if rendered_img and os.path.exists(rendered_img):
                                        media_paths.append(os.path.abspath(rendered_img))
                            except Exception as v_err:
                                logger.debug("Trend visual spec synthesis skipped: %s", v_err)

                            metadata = {
                                "trend_id": item.id,
                                "trend_title": item.title,
                                "source_url": item.source_url,
                                "source_name": item.source_name,
                                "published_at": item.published_at,
                                "relevance_score": eval_result.relevance_score,
                                "reasoning": eval_result.reasoning,
                                "key_takeaways": eval_result.key_takeaways,
                                "hot_take": eval_result.hot_take,
                                "draft_post": eval_result.draft_post,
                                "optimized_post": eval_result.optimized_post,
                                "visual_spec": visual_spec_dict,
                                "gif_query": gif_query,
                                "media_paths": media_paths if media_paths else None,
                            }

                            cfg_path = manager.base_profile_dir / profile_slug
                            prof_config = load_config(cfg_path) if cfg_path.exists() else None
                            req_appr = getattr(prof_config, "require_post_approval", True) if prof_config else True
                            staged_status = ContentStatus.DRAFT if req_appr else ContentStatus.APPROVED

                            content_record = Content(
                                profile_id=profile_id,
                                content_type=ContentType.ORIGINAL,
                                body=post_text,
                                status=staged_status,
                                ai_metadata=metadata,
                                created_at=datetime.datetime.utcnow(),
                            )
                            db.add(content_record)

                            # If a high-value thread was generated, stage the thread as well
                            if eval_result.thread_items and len(eval_result.thread_items) >= 3:
                                thread_root = eval_result.thread_items[0]
                                thread_meta = {
                                    **metadata,
                                    "thread_items": eval_result.thread_items,
                                    "is_thread": True,
                                }
                                thread_record = Content(
                                    profile_id=profile_id,
                                    content_type=ContentType.THREAD,
                                    body=thread_root,
                                    status=staged_status,
                                    ai_metadata=thread_meta,
                                    created_at=datetime.datetime.utcnow(),
                                )
                                db.add(thread_record)
                                logger.info(
                                    "Staged trend thread (%d parts, status=%s) for profile %s: '%s'",
                                    len(eval_result.thread_items),
                                    staged_status.value,
                                    profile_slug,
                                    item.title,
                                )

                            await db.commit()
                            items_staged += 1
                            logger.info(
                                "Staged high-relevance trend visual content %s for profile %s: '%s' (relevance=%.2f)",
                                content_record.id,
                                profile_slug,
                                item.title,
                                eval_result.relevance_score,
                            )

                    # Store breaking trends in Redis for live session planner
                    if breaking_trend_summaries:
                        try:
                            r.set(f"xbot:breaking_trends:{profile_id}", json.dumps(breaking_trend_summaries), ex=14400)
                        except Exception as r_err:
                            logger.debug("Failed to store breaking trends in Redis: %s", r_err)

                except Exception as p_ex:
                    logger.error("Error in trend radar loop for profile %s: %s", profile_slug, p_ex)
                    errors.append(f"{profile_slug}: {p_ex}")

        return {
            "status": "success" if not errors else "partial_success",
            "profiles_processed": total_profiles,
            "items_scanned": items_scanned,
            "items_staged": items_staged,
            "errors": errors if errors else None,
        }

    except Exception as overall_ex:
        logger.error("Trend radar task encountered critical error: %s", overall_ex)
        return {"status": "failed", "error": str(overall_ex)}


@celery_app.task(name="xbot.tasks.check_trend_radar")
def check_trend_radar() -> dict[str, Any]:
    """Celery periodic task scanning RSS feeds and trend radar sources for active profiles, generating takes, and staging content."""
    logger.info("Starting Celery check trend radar task.")
    return asyncio.run(_check_trend_radar_async())









async def _fast_response_sentinel_async(base_profile_dir: Path | str | None = None) -> dict[str, Any]:
    """
    Periodically scans active conversation threads and mentions for all active profiles,
    prioritizes verified authors and accounts nearing the 15-minute response deadline,
    generates in-character debate catalyst replies, and posts them via browser.
    Captures the open-source X algorithm's +150x reply_engaged_by_author multiplier.
    """
    r = redis.from_url(settings.REDIS_URL)
    base_dir = Path(base_profile_dir) if base_profile_dir else Path("/home/ubuntu/projects/xbot/data/profiles")
    manager = BrowserManager()
    await manager.start()

    total_threads_checked = 0
    replies_posted = 0
    errors: list[str] = []

    try:
        from xbot.models.realgraph import ConversationThread, RealGraphEdge
        async with AsyncSessionLocal() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            res = await db.execute(stmt)
            active_profiles = res.scalars().all()

            if not active_profiles:
                return {
                    "status": "success",
                    "profiles_processed": 0,
                    "threads_checked": 0,
                    "replies_posted": 0,
                }

            now = datetime.datetime.utcnow()

            for profile in active_profiles:
                profile_slug = profile.profile_slug
                profile_id = profile.id
                profile_dir = base_dir / profile_slug

                try:
                    persona = load_persona(profile_dir)
                    config = load_config(profile_dir)
                    is_mock = getattr(config, "mock_mode", False)
                except Exception as ex:
                    logger.warning("Failed loading persona/config for %s: %s", profile_slug, ex)
                    continue

                guard = SafetyGuard(redis_url=settings.REDIS_URL, base_profile_dir=str(manager.base_profile_dir))

                # 1. Fetch active conversation threads nearing deadline (<15m window)
                th_stmt = (
                    select(ConversationThread)
                    .where(
                        ConversationThread.profile_id == profile_id,
                        ConversationThread.status.in_(["active", "awaiting_reply"]),
                        ConversationThread.deadline_15m >= now - datetime.timedelta(minutes=30),
                        ConversationThread.turn_count < ConversationThread.max_turns,
                    )
                    .order_by(
                        ConversationThread.target_is_verified.desc(),
                        ConversationThread.deadline_15m.asc(),
                    )
                    .limit(3)
                )
                th_res = await db.execute(th_stmt)
                active_threads = list(th_res.scalars().all())
                total_threads_checked += len(active_threads)

                if not active_threads:
                    continue

                for thread in active_threads:
                    # Check safety rate limits
                    if not await guard.is_action_safe(db, profile_slug, "reply"):
                        logger.info("Rate limit active for %s; halting fast response loop.", profile_slug)
                        break

                    # Check distributed lock
                    lock_key = f"xbot:lock:fast_reply:{thread.id}"
                    if not r.set(lock_key, "1", nx=True, ex=300):
                        continue

                    if not manager.acquire_lock(profile_slug, timeout_seconds=300):
                        continue

                    context = None
                    try:
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

                        # Synthesize fast conversational counter-take (Value Hook -> Trade-off -> Debate Catalyst '?')
                        target_tweet_url = f"https://x.com/{thread.target_handle}/status/{thread.parent_tweet_id}"
                        
                        system_prompt = (
                            f"You are {persona.display_name} (@{persona.x_handle}). You are executing a fast-response "
                            f"conversational counter-reply on X to an active discussion turn.\n"
                            f"Tone: {persona.writing_style.tone}\n"
                            f"Traits: {', '.join(persona.personality.traits)}\n"
                            f"Rules:\n"
                            f"- Character length: 120-240 characters.\n"
                            f"- MUST end with a compelling debate-sparking question ('?') to trigger an author reply.\n"
                            f"- Zero AI fluff (no 'delve', 'supercharge', 'tapestry', 'testament'). Clean sentence case.\n"
                        )
                        user_prompt = (
                            f"Conversation so far with @{thread.target_handle}:\n"
                            f"{json.dumps(thread.conversation_history, indent=2)}\n\n"
                            f"Write an insightful in-character counter-reply that advances the discussion and ends with a question."
                        )

                        client = get_ai_client()
                        completion = await client.chat.completions.create(
                            model=settings.MODEL_REPLY_ANALYSIS,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        )
                        reply_text = (completion.choices[0].message.content or "").strip()
                        if not reply_text.endswith("?"):
                            reply_text += " What's your take on this?"

                        # Execute reply via browser
                        success = False
                        if is_mock:
                            await asyncio.sleep(0.3)
                            success = True
                        else:
                            success = await ReplyToTweet().execute(
                                page,
                                reply_text,
                                tweet_url=target_tweet_url,
                            )

                        if success:
                            t_now = datetime.datetime.utcnow()
                            await guard.record_action_success(profile_slug, "reply", t_now)

                            # Advance thread state
                            thread.turn_count += 1
                            thread.last_action_at = t_now
                            history = list(thread.conversation_history or [])
                            history.append({"turn": thread.turn_count, "sender": "bot", "text": reply_text})
                            thread.conversation_history = history
                            if thread.turn_count >= thread.max_turns:
                                thread.status = "closed"
                            else:
                                thread.status = "awaiting_reply"
                                thread.deadline_15m = t_now + datetime.timedelta(minutes=15)

                            # Update or create RealGraphEdge
                            rg_stmt = select(RealGraphEdge).where(
                                RealGraphEdge.profile_id == profile_id,
                                RealGraphEdge.target_handle == thread.target_handle,
                            )
                            rg_res = await db.execute(rg_stmt)
                            edge = rg_res.scalar_one_or_none()
                            if not edge:
                                edge = RealGraphEdge(
                                    profile_id=profile_id,
                                    target_handle=thread.target_handle,
                                    is_verified=thread.target_is_verified,
                                    outbound_replies_count=1,
                                    inbound_author_replies_count=1,
                                    reciprocal_score=25.0 if thread.target_is_verified else 10.0,
                                    author_reply_rate=1.0,
                                    first_interacted_at=t_now,
                                    last_outbound_at=t_now,
                                    last_inbound_at=t_now,
                                )
                                db.add(edge)
                            else:
                                edge.outbound_replies_count += 1
                                edge.reciprocal_score = min(150.0, edge.reciprocal_score + 15.0)
                                edge.last_outbound_at = t_now

                            # Record action
                            act = Action(
                                profile_id=profile_id,
                                action_type=ActionType.REPLY,
                                target_url=target_tweet_url,
                                content=reply_text,
                                status=ActionStatus.COMPLETED,
                                result={
                                    "mode": "fast_response_sentinel",
                                    "target_handle": thread.target_handle,
                                    "turn": thread.turn_count,
                                    "thread_id": str(thread.id),
                                    "realgraph_score": edge.reciprocal_score if edge else 1.0,
                                },
                                executed_at=t_now,
                            )
                            db.add(act)
                            await db.commit()

                            replies_posted += 1
                            logger.info(
                                "Fast-Response reply posted for profile %s -> @%s (turn %d/%d)",
                                profile_slug,
                                thread.target_handle,
                                thread.turn_count,
                                thread.max_turns,
                            )
                    except Exception as th_ex:
                        logger.error("Error processing thread %s: %s", thread.id, th_ex)
                        errors.append(f"Thread {thread.id}: {th_ex}")
                    finally:
                        if context:
                            await context.close()
                        manager.release_lock(profile_slug)

        return {
            "status": "success" if not errors else "partial_success",
            "threads_checked": total_threads_checked,
            "replies_posted": replies_posted,
            "errors": errors if errors else None,
        }

    except Exception as overall_ex:
        logger.error("Fast response sentinel encountered critical error: %s", overall_ex)
        return {"status": "failed", "error": str(overall_ex)}
    finally:
        await manager.stop()


@celery_app.task(name="xbot.tasks.fast_response_sentinel")
def fast_response_sentinel() -> dict[str, Any]:
    """Celery periodic task executing sub-15 minute conversational fast responses to capture +150x reply multipliers."""
    logger.info("Starting Celery fast-response sentinel task.")
    return asyncio.run(_fast_response_sentinel_async())


async def _sync_all_profiles_creator_studio_async() -> dict[str, Any]:
    """
    Periodic task (every 12 hours):
    Visits https://x.com/i/jf/creators/studio in 1 gentle single browser visit per profile,
    extracts official verified followers and 90-day verified home timeline impressions,
    and saves an AnalyticsSnapshot.
    """
    from datetime import date, datetime
    from xbot.models.analytics import AnalyticsSnapshot
    from xbot.browser.actions.x_actions import ScrapeCreatorStudioMetrics

    logger.info("Starting 12-hour Creator Studio official metric sync...")
    results = []
    manager = BrowserManager()

    try:
        await manager.start()
        async with AsyncSessionLocal() as db:
            p_res = await db.execute(select(Profile))
            profiles = p_res.scalars().all()

            for prof in profiles:
                if not manager.acquire_lock(prof.profile_slug, timeout_seconds=15):
                    logger.info("Skipping sync for %s; browser lock busy.", prof.profile_slug)
                    continue

                context = None
                try:
                    context = await manager.get_context(prof.profile_slug)
                    page = await context.new_page()

                    studio_action = ScrapeCreatorStudioMetrics()
                    data = await studio_action.execute(page)

                    if data.get("status") == "success":
                        vf = data.get("verified_followers", 0)
                        imp = data.get("verified_impressions_90d", 0)

                        snapshot = AnalyticsSnapshot(
                            profile_id=prof.id,
                            snapshot_date=date.today(),
                            verified_followers=vf,
                            verified_impressions_90d=imp,
                            captured_at=datetime.utcnow(),
                        )
                        db.add(snapshot)
                        await db.commit()
                        logger.info("Successfully updated Creator Studio metrics for %s: %d verified followers, %d 90d impressions", prof.x_handle, vf, imp)
                        results.append({"handle": prof.x_handle, "verified_followers": vf, "verified_impressions_90d": imp})
                except Exception as ex:
                    logger.warning("Error syncing Creator Studio for %s: %s", prof.x_handle, ex)
                finally:
                    if context:
                        await context.close()
                    manager.release_lock(prof.profile_slug)

        return {"status": "success", "synced_profiles": results}
    except Exception as e:
        logger.error("Failed 12-hour Creator Studio sync: %s", e)
        return {"status": "failed", "error": str(e)}
    finally:
        await manager.stop()


@celery_app.task(name="xbot.tasks.sync_all_profiles_creator_studio")
def sync_all_profiles_creator_studio() -> dict[str, Any]:
    """Celery periodic task syncing official Creator Studio metrics every 12 hours."""
    return asyncio.run(_sync_all_profiles_creator_studio_async())


async def _auto_publish_pending_drafts_async() -> dict[str, Any]:
    """
    Automated continuous draft publisher:
    Periodically checks for profiles where `require_post_approval == False` or where drafts are APPROVED.
    Picks the next pending draft, acquires the browser lock, executes via Playwright,
    and marks Content.status = ContentStatus.POSTED!
    """
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ComposePost, ComposeThread, ReplyToTweet
    from xbot.browser.actions.poll_action import CreatePoll
    from xbot.models.content import Content, ContentStatus, ContentType
    from xbot.models.profile import Profile, ProfileStatus
    from xbot.safety.guard import SafetyGuard

    manager = BrowserManager()
    guard = SafetyGuard()
    published_count = 0
    errors = []

    try:
        await manager.start()
        async with AsyncSessionLocal() as db:
            p_res = await db.execute(select(Profile).where(Profile.status == ProfileStatus.ACTIVE))
            profiles = p_res.scalars().all()

            for prof in profiles:
                cfg_path = manager.base_profile_dir / prof.profile_slug
                config = load_config(cfg_path) if cfg_path.exists() else None
                require_approval = getattr(config, "require_post_approval", True) if config else True

                # Allow auto-publishing if require_post_approval is False or if draft status is explicitly APPROVED
                allowed_statuses = [ContentStatus.APPROVED]
                if not require_approval:
                    allowed_statuses.append(ContentStatus.DRAFT)

                stmt_draft = (
                    select(Content)
                    .where(
                        Content.profile_id == prof.id,
                        Content.status.in_(allowed_statuses),
                    )
                    .order_by(Content.created_at.asc())
                    .limit(1)
                )
                d_res = await db.execute(stmt_draft)
                draft = d_res.scalar_one_or_none()
                if not draft:
                    continue

                # Check safety guard limits
                can_post = await guard.is_action_safe(db, prof.profile_slug, "post")
                if not can_post:
                    logger.info("Auto-publish postponed for %s: rate limits/cooldown active.", prof.profile_slug)
                    continue

                lock_acquired = False
                for _ in range(12):
                    if manager.acquire_lock(prof.profile_slug, timeout_seconds=120):
                        lock_acquired = True
                        break
                    import asyncio as _aio
                    await _aio.sleep(2.5)

                if not lock_acquired:
                    logger.info("Auto-publish postponed for %s: browser lock busy.", prof.profile_slug)
                    continue

                context = None
                success = False
                try:
                    logger.info("Auto-publishing staged %s draft %s for profile %s: '%s'", draft.content_type, draft.id, prof.profile_slug, draft.body[:50])
                    context = await manager.get_context(prof.profile_slug)
                    page = await context.new_page()

                    if draft.content_type == ContentType.POLL:
                        meta_poll = draft.ai_metadata.get("poll", {}) if draft.ai_metadata else {}
                        question = meta_poll.get("question") or draft.body.split("\n")[0]
                        options = meta_poll.get("options") or ["Yes", "No"]
                        duration_days = meta_poll.get("duration_days", 1)
                        screenshot_dir = str(Path(manager.base_profile_dir) / prof.profile_slug / "screenshots")
                        action = CreatePoll(screenshot_dir=screenshot_dir)
                        success = await action.execute(page, question=question, options=options, duration_days=duration_days)
                    elif draft.content_type in (ContentType.THREAD, "thread"):
                        tweets = []
                        if getattr(draft, "thread_items", None):
                            tweets = [item.text for item in draft.thread_items]
                        elif draft.ai_metadata and "thread_items" in draft.ai_metadata:
                            tweets = draft.ai_metadata["thread_items"]
                        elif draft.ai_metadata and "tweets" in draft.ai_metadata:
                            tweets = draft.ai_metadata["tweets"]
                        else:
                            tweets = [p.strip() for p in draft.body.split("\n\n") if p.strip()]
                        action = ComposeThread()
                        media_paths = draft.ai_metadata.get("media_paths") if draft.ai_metadata else None
                        res = await action.execute(page, tweets=tweets, media_paths=media_paths)
                        success = res.get("status") == "success"
                        if success and res.get("root_tweet_id"):
                            draft.tweet_id = res.get("root_tweet_id")
                    else:
                        action = ComposePost()
                        gif_q = draft.ai_metadata.get("gif_query") if draft.ai_metadata else None
                        media_paths = draft.ai_metadata.get("media_paths") if draft.ai_metadata else None
                        success = await action.execute(page, text=draft.body, media_paths=media_paths, gif_query=gif_q)

                    if success:
                        draft.status = ContentStatus.POSTED
                        draft.posted_at = datetime.datetime.utcnow()
                        await db.commit()
                        await guard.record_action_success(prof.profile_slug, "post")
                        published_count += 1
                        logger.info("Successfully auto-published draft %s to live X for profile %s!", draft.id, prof.profile_slug)

                        extracted_link = draft.ai_metadata.get("extracted_link") if draft.ai_metadata else None
                        if extracted_link:
                            try:
                                await sleep_with_jitter(2500)
                                first_reply_msg = f"Link / source breakdown: {extracted_link}"
                                reply_ok = await ReplyToTweet().execute(page, first_reply_msg)
                                if reply_ok:
                                    reply_rec = Content(
                                        profile_id=prof.id,
                                        content_type=ContentType.REPLY,
                                        body=first_reply_msg,
                                        status=ContentStatus.POSTED,
                                        posted_at=datetime.datetime.utcnow(),
                                        ai_metadata={"is_1st_reply_injection": True, "direct_publish": True}
                                    )
                                    db.add(reply_rec)
                                    await db.commit()
                            except Exception as link_e:
                                logger.warning("Failed to post 1st-reply link injection: %s", link_e)
                except Exception as ex:
                    logger.error("Error auto-publishing draft for %s: %s", prof.profile_slug, ex)
                    errors.append(f"{prof.profile_slug}: {ex}")
                finally:
                    if context:
                        await context.close()
                    manager.release_lock(prof.profile_slug)

        return {"status": "success", "published_count": published_count, "errors": errors if errors else None}
    except Exception as e:
        logger.error("Failed auto-publish cycle: %s", e)
        return {"status": "failed", "error": str(e)}
    finally:
        await manager.stop()


@celery_app.task(name="xbot.tasks.auto_publish_pending_drafts")
def auto_publish_pending_drafts() -> dict[str, Any]:
    """Celery periodic task to automatically publish pending/approved drafts when require_post_approval is disabled."""
    logger.info("Starting auto-publish pending drafts Celery task...")
    return asyncio.run(_auto_publish_pending_drafts_async())


async def _run_growth_and_autofollowback_async() -> dict[str, Any]:
    """
    Periodic Growth & Follow-Back Engine (runs every 10-15 minutes):
    1. Audits our profile's followers on X. If anyone new followed us, instantly executes reciprocal follow-back!
    2. Proactively advances the 500+ Verified Blue-Tick Followers mission by following 1-2 top reciprocity candidates from target communities.
    3. Prunes non-mutual accounts outside the 4-day grace period to protect TweepCred PageRank (>65).
    """
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ScrapeFollowList, FollowUser, UnfollowUser
    from xbot.models.profile import Profile, ProfileStatus
    from xbot.models.follow_growth import FollowCandidate, FollowRelationship
    from xbot.models.analytics import FollowerChangeLog
    from xbot.growth.f4f_engine import populate_f4f_candidates, record_follow_action, record_unfollow_action
    from xbot.safety.guard import SafetyGuard

    manager = BrowserManager()
    guard = SafetyGuard()
    results = {}

    try:
        await manager.start()
        async with AsyncSessionLocal() as db:
            p_res = await db.execute(select(Profile).where(Profile.status == ProfileStatus.ACTIVE))
            profiles = p_res.scalars().all()

            for prof in profiles:
                clean_handle = prof.x_handle.lstrip("@")
                lock_acquired = False
                for _ in range(5):
                    if manager.acquire_lock(prof.profile_slug, timeout_seconds=120):
                        lock_acquired = True
                        break
                    import asyncio as _aio
                    await _aio.sleep(2.0)

                if not lock_acquired:
                    logger.info("Skipping growth cycle for %s: browser lock busy.", prof.profile_slug)
                    continue

                context = None
                followed_back_count = 0
                proactive_followed_count = 0
                pruned_count = 0

                try:
                    context = await manager.get_context(prof.profile_slug)
                    page = await context.new_page()
                    page.set_default_timeout(25000)

                    # 1. Scrape current verified followers & following lists from live profile
                    logger.info("Scanning live verified followers & following for @%s...", clean_handle)
                    current_followers = await ScrapeFollowList().execute(page, username=clean_handle, list_type="followers", limit=50, verified_only=True)
                    current_following = await ScrapeFollowList().execute(page, username=clean_handle, list_type="following", limit=50, verified_only=False)

                    followers_set = {f.lstrip("@").lower() for f in current_followers}
                    following_set = {f.lstrip("@").lower() for f in current_following}

                    # Record updated snapshot in AnalyticsSnapshot
                    if current_followers or current_following:
                        from xbot.models.analytics import AnalyticsSnapshot
                        import datetime as _dt
                        snap = AnalyticsSnapshot(
                            profile_id=prof.id,
                            snapshot_date=_dt.date.today(),
                            followers=len(current_followers),
                            following=len(current_following),
                            captured_at=_dt.datetime.utcnow(),
                        )
                        db.add(snap)
                        await db.commit()

                    # 2. AUTO FOLLOW-BACK (VERIFIED-ONLY): Identify verified accounts who follow us!
                    unfollowed_followers = [f for f in current_followers if f.lstrip("@").lower() not in following_set and f.lstrip("@").lower() != clean_handle.lower()]
                    logger.info("Total incoming verified followers needing reciprocal follow-back: %d", len(unfollowed_followers))
                    for target_follower in unfollowed_followers:
                        can_follow = await guard.is_action_safe(db, prof.profile_slug, "follow")
                        if not can_follow:
                            logger.info("Daily follow safety limit reached for %s. Pausing follow-back.", prof.profile_slug)
                            break

                        logger.info("🤝 Auto Follow-Back triggered for Verified Blue-Tick follower @%s!", target_follower)
                        f_ok = await FollowUser().execute(page, username=target_follower)
                        if f_ok:
                            followed_back_count += 1
                            following_set.add(target_follower.lstrip("@").lower())
                            await record_follow_action(prof.id, target_follower, db, is_blue_tick=True, niche="verified_incoming_follower")
                            await guard.record_action_success(prof.profile_slug, "follow")
                            db.add(FollowerChangeLog(profile_id=prof.id, change_type="new_follower", handle=target_follower))
                            await db.commit()
                            await sleep_with_jitter(3000)

                    # 3. PROACTIVE 500+ VERIFIED FOLLOWER GROWTH MISSION:
                    # If daily follow limit allows, harvest & follow 1-2 top verified blue-tick candidates
                    can_follow_more = await guard.is_action_safe(db, prof.profile_slug, "follow")
                    if can_follow_more and (followed_back_count < 2):
                        # Ensure candidate pool is populated with verified creators only
                        c_stmt = (
                            select(FollowCandidate)
                            .where(
                                FollowCandidate.profile_id == prof.id,
                                FollowCandidate.status == "discovered",
                                FollowCandidate.is_blue_tick == True,
                            )
                            .order_by(FollowCandidate.reciprocity_score.desc())
                            .limit(5)
                        )
                        c_res = await db.execute(c_stmt)
                        candidates = list(c_res.scalars().all())

                        if len(candidates) < 3:
                            await populate_f4f_candidates(prof.id, db, niche="all", limit=15)
                            c_res = await db.execute(c_stmt)
                            candidates = list(c_res.scalars().all())

                        for cand in candidates[:2]:
                            cand_handle = cand.handle.lstrip("@").lower()
                            if cand_handle in following_set:
                                cand.status = "followed"
                                continue

                            if not await guard.is_action_safe(db, prof.profile_slug, "follow"):
                                break

                            logger.info("🎯 Proactive Verified Follow targeting @%s (Reciprocity Score: %.1f, Niche: %s)...", cand.handle, cand.reciprocity_score, cand.niche)
                            f_ok = await FollowUser().execute(page, username=cand.handle)
                            if f_ok:
                                proactive_followed_count += 1
                                following_set.add(cand_handle)
                                cand.status = "followed"
                                await record_follow_action(prof.id, cand.handle, db, is_blue_tick=cand.is_blue_tick, niche=cand.niche)
                                await guard.record_action_success(prof.profile_slug, "follow")
                                await db.commit()
                                await sleep_with_jitter(3500)

                    # 4. GRACE PERIOD PRUNING (Protect TweepCred > 65):
                    # Check for accounts we followed > 4 days ago that did NOT follow back
                    now = datetime.datetime.utcnow()
                    exp_stmt = (
                        select(FollowRelationship)
                        .where(
                            FollowRelationship.profile_id == prof.id,
                            FollowRelationship.status == "following",
                            FollowRelationship.grace_period_expires_at <= now,
                        )
                        .limit(3)
                    )
                    exp_res = await db.execute(exp_stmt)
                    expired_rels = exp_res.scalars().all()

                    for exp_rel in expired_rels:
                        clean_exp = exp_rel.target_handle.lstrip("@").lower()
                        # If they actually followed back, mark as mutual
                        if clean_exp in followers_set:
                            exp_rel.status = "followed_back"
                            await db.commit()
                            continue

                        # Otherwise safely unfollow to maintain ratio
                        can_unfollow = await guard.is_action_safe(db, prof.profile_slug, "unfollow")
                        if not can_unfollow:
                            break

                        logger.info("✂️ Grace period expired (4 days) for @%s without reciprocal follow. Unfollowing to protect TweepCred...", exp_rel.target_handle)
                        unf_ok = await UnfollowUser().execute(page, username=exp_rel.target_handle)
                        if unf_ok:
                            pruned_count += 1
                            await record_unfollow_action(prof.id, exp_rel.target_handle, db)
                            await guard.record_action_success(prof.profile_slug, "unfollow")
                            await db.commit()
                            await sleep_with_jitter(2500)

                    results[prof.profile_slug] = {
                        "followed_back": followed_back_count,
                        "proactive_followed": proactive_followed_count,
                        "pruned": pruned_count,
                        "current_followers": len(current_followers),
                        "current_following": len(current_following),
                    }
                    logger.info("Completed growth cycle for %s: %s", prof.profile_slug, results[prof.profile_slug])

                except Exception as p_err:
                    logger.error("Error during growth cycle for %s: %s", prof.profile_slug, p_err, exc_info=True)
                    results[prof.profile_slug] = {"error": str(p_err)}
                finally:
                    if context:
                        await context.close()
                    manager.release_lock(prof.profile_slug)

        return {"status": "success", "results": results}
    except Exception as e:
        logger.error("Failed overall growth cycle: %s", e)
        return {"status": "failed", "error": str(e)}
    finally:
        await manager.stop()


@celery_app.task(name="xbot.tasks.run_growth_and_autofollowback")
def run_growth_and_autofollowback() -> dict[str, Any]:
    """Celery periodic task executing Auto Follow-Back and Proactive 500+ Verified Follower Growth."""
    logger.info("Starting Auto Follow-Back & Growth Celery task...")
    return asyncio.run(_run_growth_and_autofollowback_async())

