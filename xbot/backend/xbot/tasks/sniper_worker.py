from __future__ import annotations

from .common import extract_tweet_id_from_url, _parse_x_counts, has_already_acted, broadcast_session_log, _extract_or_generate_poll_data
from .common import *
import asyncio, datetime, logging, random, uuid
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
from xbot.browser.actions.x_actions import *
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
from xbot.models.realgraph import RealGraphEdge
from xbot.persona import load_config
from xbot.persona.loader import load_persona
from xbot.safety.guard import SafetyGuard
from xbot.ai.trend_radar import fetch_rss_trends, fetch_multi_source_trends
from xbot.ai.trend_generator import generate_trend_take
import re
logger = logging.getLogger(__name__)

def _detect_language_vibe(text: str) -> str:
    return 'en'


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
                logger.info('No active profiles found for sniper target checking.')
                return {'status': 'success', 'profiles_processed': 0, 'replies_posted': 0}
            for profile in active_profiles:
                profile_slug = profile.profile_slug
                profile_id = profile.id
                profile_dir = manager.base_profile_dir / profile_slug
                try:
                    persona = load_persona(profile_dir)
                except Exception as ex:
                    logger.warning('Failed to load persona for profile %s: %s', profile_slug, ex)
                    continue
                if not persona.target_kols:
                    logger.debug('Profile %s has no target KOLs configured; skipping sniper check.', profile_slug)
                    continue
                guard = SafetyGuard(redis_url=settings.REDIS_URL, base_profile_dir=str(manager.base_profile_dir))
                if not await guard.is_action_safe(db, profile_slug, 'reply'):
                    logger.info('Safety guard rate limit or cooldown active for profile %s; skipping sniper run.', profile_slug)
                    continue
                if not manager.acquire_lock(profile_slug, timeout_seconds=600):
                    logger.warning('Could not acquire browser lock for profile %s (sniper task collision)', profile_slug)
                    continue
                total_profiles += 1
                context = None
                try:
                    config = load_config(profile_dir)
                    is_mock = getattr(config, 'mock_mode', False)
                    if not is_mock:
                        timezone_str = config.schedule.timezone or 'America/New_York'
                        context = await manager.get_context(profile_slug=profile_slug, timezone=timezone_str, proxy_url=config.proxy_url)
                        page = await context.new_page()
                    else:
                        page = None
                    for kol in persona.target_kols:
                        kol_handle = kol.handle.lstrip('@').strip()
                        if not kol_handle:
                            continue
                        if not await guard.is_action_safe(db, profile_slug, 'reply'):
                            logger.info('Rate limit reached for %s during target scan; halting sniper loop.', profile_slug)
                            break
                        tweet_data = None
                        if is_mock:
                            tweet_data = {'tweet_id': f'mock_{kol_handle}_{int(datetime.datetime.utcnow().timestamp())}', 'text': f'Simulated latest tweet from @{kol_handle} on technical innovations.', 'url': f'https://x.com/{kol_handle}/status/mock_{kol_handle}', 'handle': kol_handle, 'is_pinned': False, 'created_at': '1m'}
                        else:
                            tweet_data = await CheckUserLatestTweet().execute(page, handle=kol_handle)
                        if not tweet_data or not tweet_data.get('tweet_id'):
                            logger.info('No tweet found for target KOL @%s', kol_handle)
                            continue
                        tweet_id = str(tweet_data['tweet_id'])
                        tweet_url = tweet_data.get('url') or f'https://x.com/{kol_handle}/status/{tweet_id}'
                        seen_key = f'xbot:seen_tweets:{profile_id}:{tweet_id}'
                        seen_set_key = f'xbot:seen_tweets:{profile_id}'
                        if r.exists(seen_key) or r.sismember(seen_set_key, tweet_id) or await has_already_acted(db, profile_id, tweet_url, 'reply', hours=48):
                            logger.info('Tweet %s from @%s already replied to for profile %s; skipping.', tweet_id, kol_handle, profile_slug)
                            continue
                        opp_score = score_tweet_opportunity(tweet_data)
                        if opp_score.recommended_action == 'skip' and opp_score.score < 25.0:
                            logger.info('Phoenix Growth Scorer skipped target KOL @%s tweet %s (score=%.1f): %s', kol_handle, tweet_id, opp_score.score, opp_score.reasoning)
                            continue
                        reply_result = await generate_sniper_reply(persona=persona, target_tweet=tweet_data, preferred_angle=kol.preferred_angle, opportunity_score=opp_score)
                        if not reply_result.reply_text:
                            logger.warning('Empty sniper reply generated for @%s tweet %s; skipping.', kol_handle, tweet_id)
                            continue
                        success = False
                        error_msg = None
                        try:
                            if is_mock:
                                await asyncio.sleep(0.5)
                                success = True
                            else:
                                success = await ReplyToTweet().execute(page, reply_result.reply_text, tweet_url=tweet_url, gif_query=reply_result.gif_query)
                        except Exception as ex:
                            error_msg = str(ex)
                            logger.error('Error executing sniper reply to %s: %s', tweet_url, ex)
                        if success:
                            r.set(seen_key, '1', ex=604800)
                            r.sadd(seen_set_key, tweet_id)
                            t_now = datetime.datetime.utcnow()
                            await guard.record_action_success(profile_slug, 'reply', t_now)
                            db_session = Session(profile_id=profile_id, status=SessionStatus.COMPLETED, actions_planned=1, actions_completed=1, actions_failed=0, plan={'mode': 'sniper_reply', 'target_kol': kol_handle}, started_at=t_now, ended_at=t_now)
                            db.add(db_session)
                            await db.flush()
                            db_action = Action(session_id=db_session.id, profile_id=profile_id, action_type=ActionType.REPLY, target_url=tweet_url, content=reply_result.reply_text, status=ActionStatus.COMPLETED, result={'sniper': True, 'target_kol': kol_handle, 'angle': reply_result.angle_used, 'confidence': reply_result.confidence, 'reasoning': reply_result.reasoning, 'tweet_id': tweet_id, 'opportunity_score': opp_score.model_dump()}, executed_at=t_now)
                            db.add(db_action)
                            await db.commit()
                            replies_posted += 1
                            logger.info('Sniper reply successfully posted for profile %s -> @%s (tweet_id=%s, angle=%s)', profile_slug, kol_handle, tweet_id, reply_result.angle_used)
                            await sleep_with_jitter(3000)
                        else:
                            if not error_msg:
                                error_msg = f'Browser ReplyToTweet returned False for @{kol_handle} tweet {tweet_id}'
                            await guard.record_action_failure(db, profile_slug, error_msg)
                            logger.warning('Failed to post sniper reply for profile %s -> @%s: %s', profile_slug, kol_handle, error_msg)
                except Exception as ex:
                    import traceback; logger.error("Error: %s", traceback.format_exc())
                    errors.append(f'{profile_slug}: {ex}')
                finally:
                    if context:
                        await context.close()
                    manager.release_lock(profile_slug)
        return {'status': 'success' if not errors else 'partial_success', 'profiles_processed': total_profiles, 'replies_posted': replies_posted, 'errors': errors if errors else None}
    except Exception as overall_ex:
        logger.error('Sniper check targets task encountered critical error: %s', overall_ex)
        return {'status': 'failed', 'error': str(overall_ex)}
    finally:
        await manager.stop()

async def _fast_response_sentinel_async(base_profile_dir: Path | str | None=None) -> dict[str, Any]:
    """
    Periodically scans active conversation threads and mentions for all active profiles,
    prioritizes verified authors and accounts nearing the 15-minute response deadline,
    generates in-character debate catalyst replies, and posts them via browser.
    Captures the open-source X algorithm's +150x reply_engaged_by_author multiplier.
    """
    r = redis.from_url(settings.REDIS_URL)
    base_dir = Path(base_profile_dir) if base_profile_dir else Path('/home/ubuntu/projects/xbot/data/profiles')
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
                return {'status': 'success', 'profiles_processed': 0, 'threads_checked': 0, 'replies_posted': 0}
            now = datetime.datetime.utcnow()
            for profile in active_profiles:
                profile_slug = profile.profile_slug
                profile_id = profile.id
                profile_dir = base_dir / profile_slug
                try:
                    persona = load_persona(profile_dir)
                    config = load_config(profile_dir)
                    is_mock = getattr(config, 'mock_mode', False)
                except Exception as ex:
                    logger.warning('Failed loading persona/config for %s: %s', profile_slug, ex)
                    continue
                guard = SafetyGuard(redis_url=settings.REDIS_URL, base_profile_dir=str(manager.base_profile_dir))
                th_stmt = select(ConversationThread).where(ConversationThread.profile_id == profile_id, ConversationThread.status.in_(['active', 'awaiting_reply']), ConversationThread.deadline_15m >= now - datetime.timedelta(minutes=30), ConversationThread.turn_count < ConversationThread.max_turns).order_by(ConversationThread.target_is_verified.desc(), ConversationThread.deadline_15m.asc()).limit(3)
                th_res = await db.execute(th_stmt)
                active_threads = list(th_res.scalars().all())
                total_threads_checked += len(active_threads)
                if not active_threads:
                    continue
                for thread in active_threads:
                    if not await guard.is_action_safe(db, profile_slug, 'reply'):
                        logger.info('Rate limit active for %s; halting fast response loop.', profile_slug)
                        break
                    lock_key = f'xbot:lock:fast_reply:{thread.id}'
                    if not r.set(lock_key, '1', nx=True, ex=300):
                        continue
                    if not manager.acquire_lock(profile_slug, timeout_seconds=300):
                        continue
                    context = None
                    try:
                        if not is_mock:
                            timezone_str = config.schedule.timezone or 'America/New_York'
                            context = await manager.get_context(profile_slug=profile_slug, timezone=timezone_str, proxy_url=config.proxy_url)
                            page = await context.new_page()
                        else:
                            page = None
                        target_tweet_url = f'https://x.com/{thread.target_handle}/status/{thread.parent_tweet_id}'
                        system_prompt = f"You are {persona.display_name} (@{persona.x_handle}). You are executing a fast-response conversational counter-reply on X to an active discussion turn.\nTone: {persona.writing_style.tone}\nTraits: {', '.join(persona.personality.traits)}\nRules:\n- Character length: 120-240 characters.\n- MUST end with a compelling debate-sparking question ('?') to trigger an author reply.\n- Zero AI fluff (no 'delve', 'supercharge', 'tapestry', 'testament'). Clean sentence case.\n"
                        user_prompt = f'Conversation so far with @{thread.target_handle}:\n{json.dumps(thread.conversation_history, indent=2)}\n\nWrite an insightful in-character counter-reply that advances the discussion and ends with a question.'
                        client = get_ai_client()
                        completion = await client.chat.completions.create(model=settings.MODEL_REPLY_ANALYSIS, messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}])
                        reply_text = (completion.choices[0].message.content or '').strip()
                        if not reply_text.endswith('?'):
                            reply_text += " What's your take on this?"
                        success = False
                        if is_mock:
                            await asyncio.sleep(0.3)
                            success = True
                        else:
                            success = await ReplyToTweet().execute(page, reply_text, tweet_url=target_tweet_url)
                        if success:
                            t_now = datetime.datetime.utcnow()
                            await guard.record_action_success(profile_slug, 'reply', t_now)
                            thread.turn_count += 1
                            thread.last_action_at = t_now
                            history = list(thread.conversation_history or [])
                            history.append({'turn': thread.turn_count, 'sender': 'bot', 'text': reply_text})
                            thread.conversation_history = history
                            if thread.turn_count >= thread.max_turns:
                                thread.status = 'closed'
                            else:
                                thread.status = 'awaiting_reply'
                                thread.deadline_15m = t_now + datetime.timedelta(minutes=15)
                            rg_stmt = select(RealGraphEdge).where(RealGraphEdge.profile_id == profile_id, RealGraphEdge.target_handle == thread.target_handle)
                            rg_res = await db.execute(rg_stmt)
                            edge = rg_res.scalar_one_or_none()
                            if not edge:
                                edge = RealGraphEdge(profile_id=profile_id, target_handle=thread.target_handle, is_verified=thread.target_is_verified, outbound_replies_count=1, inbound_author_replies_count=1, reciprocal_score=25.0 if thread.target_is_verified else 10.0, author_reply_rate=1.0, first_interacted_at=t_now, last_outbound_at=t_now, last_inbound_at=t_now)
                                db.add(edge)
                            else:
                                edge.outbound_replies_count += 1
                                edge.reciprocal_score = min(150.0, edge.reciprocal_score + 15.0)
                                edge.last_outbound_at = t_now
                            act = Action(profile_id=profile_id, action_type=ActionType.REPLY, target_url=target_tweet_url, content=reply_text, status=ActionStatus.COMPLETED, result={'mode': 'fast_response_sentinel', 'target_handle': thread.target_handle, 'turn': thread.turn_count, 'thread_id': str(thread.id), 'realgraph_score': edge.reciprocal_score if edge else 1.0}, executed_at=t_now)
                            db.add(act)
                            await db.commit()
                            replies_posted += 1
                            logger.info('Fast-Response reply posted for profile %s -> @%s (turn %d/%d)', profile_slug, thread.target_handle, thread.turn_count, thread.max_turns)
                    except Exception as th_ex:
                        logger.error('Error processing thread %s: %s', thread.id, th_ex)
                        errors.append(f'Thread {thread.id}: {th_ex}')
                    finally:
                        if context:
                            await context.close()
                        manager.release_lock(profile_slug)
        return {'status': 'success' if not errors else 'partial_success', 'threads_checked': total_threads_checked, 'replies_posted': replies_posted, 'errors': errors if errors else None}
    except Exception as overall_ex:
        logger.error('Fast response sentinel encountered critical error: %s', overall_ex)
        return {'status': 'failed', 'error': str(overall_ex)}
    finally:
        await manager.stop()

    # A simple mock implementation
    return "en"
