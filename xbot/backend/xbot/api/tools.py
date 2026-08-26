from __future__ import annotations

import asyncio
import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.hook_optimizer import optimize_post_hook, HookOptimizationResult
from xbot.ai.poll_generator import generate_poll, GeneratedPoll
from xbot.ai.sniper import generate_sniper_reply, SniperReplyResult
from xbot.ai.thread_generator import generate_thread, GeneratedThreadResponse
from xbot.ai.trend_generator import generate_trend_take, TrendEvaluation
from xbot.ai.trend_radar import fetch_rss_trends, TrendItem
from xbot.database import get_db
from xbot.models.profile import Profile
from xbot.persona.loader import load_persona

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["Growth Tools"])


class SniperRequest(BaseModel):
    profile_id: str | None = None
    profile_slug: str | None = "test_profile1"
    tweet_text: str = Field(..., min_length=3, description="Target tweet text to snipe")
    author: str = Field(default="creator", description="Author handle of target tweet")
    angle: str | None = Field(default="insight", description="Sniper angle: contrarian, framework, witty, data, insight")
    likes: int = Field(default=1500, description="Approximate engagement on target tweet")


class HookOptimizeRequest(BaseModel):
    profile_id: str | None = None
    profile_slug: str | None = "test_profile1"
    draft_content: str = Field(..., min_length=5, description="Initial draft text or idea")
    topic: str = Field(default="", description="Topic or niche context")


class PollGenerateRequest(BaseModel):
    profile_id: str | None = None
    profile_slug: str | None = "test_profile1"
    topic: str = Field(default="", description="Topic or theme for poll")


class ThreadGenerateRequest(BaseModel):
    profile_id: str | None = None
    profile_slug: str | None = "test_profile1"
    topic: str = Field(..., min_length=3, description="Topic or breakdown premise for thread")
    num_tweets: int = Field(default=4, ge=3, le=6)
    archetype: str = Field(default="Framework", description="Framework, Contrarian Breakdown, Case Study, Tactical Guide")
    deep_research: bool = Field(default=True, description="Whether to conduct live deep research on X")


class TopicResearchRequest(BaseModel):
    profile_id: str | None = None
    profile_slug: str | None = "test_profile1"
    topic: str = Field(..., min_length=3, description="Topic or breaking controversy")
    max_tweets: int = Field(default=20, ge=5, le=30)


class TrendRadarRequest(BaseModel):
    profile_id: str | None = None
    profile_slug: str | None = "test_profile1"
    rss_urls: list[str] | None = None
    limit: int = Field(default=6, ge=1, le=20)


DEFAULT_RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://news.ycombinator.com/rss",
    "https://feeds.arstechnica.com/arstechnica/index"
]


import uuid

async def _resolve_persona(db: AsyncSession, profile_id: str | None, profile_slug: str | None):
    slug = profile_slug
    if profile_id:
        try:
            pid = uuid.UUID(profile_id) if isinstance(profile_id, str) else profile_id
            stmt = select(Profile).where(Profile.id == pid)
            res = await db.execute(stmt)
            p = res.scalar_one_or_none()
            if p:
                slug = p.profile_slug
        except Exception:
            pass
    slug = slug or "test_profile1"
    try:
        return load_persona(slug), slug
    except Exception:
        return load_persona("test_profile1"), "test_profile1"



@router.post("/sniper-reply", response_model=dict[str, Any])
async def create_sniper_reply(req: SniperRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Generates an algorithm-optimized sniper reply for a target tweet using the persona voice."""
    try:
        persona, slug = await _resolve_persona(db, req.profile_id, req.profile_slug)
        result: SniperReplyResult = await generate_sniper_reply(
            persona=persona,
            target_tweet={"author": req.author.lstrip("@"), "text": req.tweet_text, "likes": req.likes},
            preferred_angle=req.angle,
        )
        return {
            "status": "success",
            "reply_text": result.reply_text,
            "angle_used": result.angle_used,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "profile_slug": slug,
        }
    except Exception as e:
        logger.error(f"Error in sniper-reply endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize-hook", response_model=dict[str, Any])
async def create_optimized_hook(req: HookOptimizeRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Evaluates 6 viral hook archetypes and generates high-retention post variants."""
    try:
        persona, slug = await _resolve_persona(db, req.profile_id, req.profile_slug)
        result: HookOptimizationResult = await optimize_post_hook(
            draft_content=req.draft_content,
            topic=req.topic or req.draft_content[:60],
            persona=persona,
        )
        candidates = [
            {
                "archetype": c.archetype,
                "hook_text": c.hook_text,
                "score": c.score,
                "reasoning": c.reasoning,
            }
            for c in result.candidates
        ]
        return {
            "status": "success",
            "candidates": candidates,
            "winning_hook": {
                "archetype": result.winning_hook.archetype,
                "hook_text": result.winning_hook.hook_text,
                "score": result.winning_hook.score,
                "reasoning": result.winning_hook.reasoning,
            },
            "optimized_content": result.optimized_content,
            "profile_slug": slug,
        }
    except Exception as e:
        logger.error(f"Error in optimize-hook endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-poll", response_model=dict[str, Any])
async def create_interactive_poll(req: PollGenerateRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Generates a debate-provoking native X poll with options under 25 chars."""
    try:
        persona, slug = await _resolve_persona(db, req.profile_id, req.profile_slug)
        result: GeneratedPoll = await generate_poll(
            persona=persona,
            topic=req.topic or None,
        )
        return {
            "status": "success",
            "question": result.question,
            "options": result.options,
            "duration_days": result.duration_days,
            "context_hook": result.context_hook,
            "reasoning": result.reasoning,
            "profile_slug": slug,
        }
    except Exception as e:
        logger.error(f"Error in generate-poll endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trend-radar", response_model=dict[str, Any])
async def scan_trends_and_generate(req: TrendRadarRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Scans live RSS/trend feeds, scores alignment to persona, and produces timely commentary takes."""
    try:
        persona, slug = await _resolve_persona(db, req.profile_id, req.profile_slug)
        feed_urls = req.rss_urls or DEFAULT_RSS_FEEDS
        raw_trends = await fetch_rss_trends(feed_urls=feed_urls, max_items_per_feed=3)
        
        trends_to_process = raw_trends[:req.limit]
        
        async def _eval_single(t: TrendItem):
            try:
                eval_res = await generate_trend_take(persona, t)
                return t, eval_res
            except Exception as e:
                logger.warning(f"Error evaluating trend take for {t.title}: {e}")
                return t, None

        eval_results = await asyncio.gather(*[_eval_single(t) for t in trends_to_process], return_exceptions=True)
        
        trends_out = []
        draft_posts = []
        for res in eval_results:
            if isinstance(res, tuple) and len(res) == 2:
                t, eval_res = res
                if eval_res and eval_res.is_relevant:
                    trends_out.append({
                        "title": t.title,
                        "summary": t.summary,
                        "url": t.source_url,
                        "alignment_score": round(eval_res.relevance_score * 100),
                        "category": t.source_name,
                        "recommended_angle": eval_res.hot_take or "insight",
                    })
                    draft_posts.append({
                        "trend_title": t.title,
                        "post_text": eval_res.optimized_post or eval_res.draft_post,
                        "angle": eval_res.hot_take or "industry_insight",
                        "rationale": eval_res.reasoning,
                    })
                elif eval_res:
                    trends_out.append({
                        "title": t.title,
                        "summary": t.summary,
                        "url": t.source_url,
                        "alignment_score": round(eval_res.relevance_score * 100),
                        "category": t.source_name,
                        "recommended_angle": "general",
                    })

        return {
            "status": "success",
            "trends": trends_out,
            "draft_posts": draft_posts,
            "profile_slug": slug,
        }
    except Exception as e:
        logger.error(f"Error in trend-radar endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-thread", response_model=GeneratedThreadResponse)
async def api_generate_thread(
    req: ThreadGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> GeneratedThreadResponse:
    try:
        persona, slug = await _resolve_persona(db, req.profile_id, req.profile_slug)
        return await generate_thread(
            topic=req.topic,
            persona=persona,
            num_tweets=req.num_tweets,
            archetype=req.archetype,
            deep_research=req.deep_research,
            profile_slug=slug,
        )
    except Exception as e:
        logger.error(f"Error in generate-thread endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research-topic", response_model=dict[str, Any])
async def api_research_topic(
    req: TopicResearchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Conducts live deep research on X & web for any topic or controversy."""
    try:
        from xbot.ai.x_researcher import research_topic_comprehensively
        persona, slug = await _resolve_persona(db, req.profile_id, req.profile_slug)
        report = await research_topic_comprehensively(
            topic=req.topic,
            persona=persona,
            max_tweets=req.max_tweets,
            profile_slug=slug,
        )
        return {
            "status": "success",
            "report": report.model_dump(),
            "profile_slug": slug,
        }
    except Exception as e:
        logger.error(f"Error in research-topic endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


