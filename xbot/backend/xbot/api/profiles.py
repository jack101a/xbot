import asyncio
import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from ruamel.yaml import YAML
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.auth import (
    format_storage_state,
    inspect_profile_auth_status,
    parse_cookie_string,
)
from xbot.browser.manager import BrowserManager
from xbot.database import get_db
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import (
    DiaryManager,
    MemoryManager,
    load_config,
    save_config,
    Config,
    LimitsConfig,
    ScheduleConfig,
    load_persona,
    load_relationships,
    load_strategy,
    save_strategy,
    load_learned_state,
    save_learned_state,
    LearnedState,
)
from pydantic import BaseModel, Field
from xbot.persona.card_parser import load_raw_card, map_card_to_persona
from xbot.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate

logger = logging.getLogger(__name__)

yaml = YAML(typ="safe")
yaml.default_flow_style = False

router = APIRouter(prefix="/profiles", tags=["Profiles"])


async def _populate_profile_metrics(db: AsyncSession, p: Profile) -> Profile:
    from xbot.models.content import Content, ContentStatus
    from sqlalchemy import func

    stmt_snap = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == p.id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(1)
    )
    res_snap = await db.execute(stmt_snap)
    snap = res_snap.scalar_one_or_none()
    p.followers_count = snap.followers if snap else 0
    p.following_count = snap.following if snap else 0
    p.posts_count = snap.total_tweets if (snap and snap.total_tweets > 0) else 0
    
    # Fallback to direct Content table count if snapshot not yet recorded
    if not p.posts_count:
        cnt_stmt = select(func.count(Content.id)).where(Content.profile_id == p.id, Content.status == ContentStatus.POSTED)
        cnt_res = await db.execute(cnt_stmt)
        p.posts_count = cnt_res.scalar() or 0

    p.impressions_24h = snap.impressions_24h if snap else 0
    p.engagements_24h = snap.engagements_24h if snap else 0
    p.engagement_rate = snap.engagement_rate if snap else 0.0
    p.likes_count = (snap.top_tweets or {}).get("likes_count", 0) if snap else 0
    p.retweets_count = (snap.top_tweets or {}).get("retweets_count", 0) if snap else 0
    p.recent_tweets = (snap.top_tweets or {}).get("recent_tweets", []) if snap else []
    return p


@router.get("", response_model=list[ProfileResponse])
async def list_profiles(db: AsyncSession = Depends(get_db)) -> list[Profile]:
    """
    List all profiles in the system.
    """
    result = await db.execute(select(Profile))
    profiles = list(result.scalars().all())
    for p in profiles:
        await _populate_profile_metrics(db, p)
    return profiles


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_in: ProfileCreate, db: AsyncSession = Depends(get_db)
) -> Profile:
    """
    Create a new profile.
    """
    # Check if profile slug already exists
    existing = await db.execute(
        select(Profile).where(Profile.profile_slug == profile_in.profile_slug)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile with this slug already exists",
        )

    db_profile = Profile(**profile_in.model_dump())
    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)
    await _populate_profile_metrics(db, db_profile)

    # Automatically create profile directory and initial persona.yaml if missing
    try:
        import yaml
        profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
        profile_dir.mkdir(parents=True, exist_ok=True)
        persona_path = profile_dir / "persona.yaml"
        if not persona_path.exists():
            default_persona = {
                "id": db_profile.profile_slug,
                "display_name": db_profile.display_name or db_profile.profile_slug,
                "x_handle": db_profile.x_handle,
                "identity": {
                    "background": "Autonomous AI creator and domain specialist."
                },
                "personality": {
                    "traits": ["analytical", "sharp", "witty", "curious"],
                    "values": ["high_signal", "transparency"],
                    "communication_style": "punchy_and_insightful"
                },
                "interests": {
                    "primary": ["AI", "technology", "growth", "automation"],
                    "secondary": ["coding", "systems"],
                    "will_not_discuss": ["spam", "generic buzzwords"]
                },
                "writing_style": {
                    "tone": "authoritative_yet_accessible",
                    "typical_length": "concise",
                    "formatting": ["micro_spacing", "punchy_lines"]
                },
                "goals": {
                    "short_term": ["grow to 10k followers organically"],
                    "long_term": ["establish authority in target niche"],
                    "content_pillars": ["Industry Trends", "Analysis", "Best Practices"]
                },
                "rules": {
                    "always": ["add value", "cite specific data or clear logic"],
                    "never": ["generic praise", "hashtag spam"]
                },
                "target_kols": [
                    {"handle": "elonmusk", "category": "tech", "priority": "high", "preferred_angle": "witty"},
                    {"handle": "sama", "category": "ai", "priority": "high", "preferred_angle": "contrarian"}
                ]
            }
            with open(persona_path, "w") as f:
                yaml.safe_dump(default_persona, f, sort_keys=False)
    except Exception as ex:
        logger.warning("Could not auto-generate persona.yaml for %s: %s", db_profile.profile_slug, ex)

    return db_profile


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Profile:
    """
    Get a profile by UUID.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    await _populate_profile_metrics(db, db_profile)
    return db_profile


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    profile_in: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """
    Update a profile.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    update_data = profile_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_profile, key, value)

    await db.commit()
    await db.refresh(db_profile)
    return db_profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a profile.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    await db.delete(db_profile)
    await db.commit()


@router.post("/{profile_id}/pause", response_model=ProfileResponse)
async def pause_profile(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Profile:
    """
    Pause a profile's active scheduling.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    db_profile.status = ProfileStatus.PAUSED
    await db.commit()
    await db.refresh(db_profile)
    return db_profile


@router.post("/{profile_id}/resume", response_model=ProfileResponse)
async def resume_profile(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Profile:
    """
    Resume a profile's active scheduling.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    db_profile.status = ProfileStatus.ACTIVE
    await db.commit()
    await db.refresh(db_profile)
    return db_profile


@router.post("/{profile_id}/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_profile_session(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Manually trigger an autonomous execution session for a profile.
    Spawns background task immediately and dispatches to Celery.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    # Spawn immediate async execution in background
    from xbot.tasks import _run_session_async
    asyncio.create_task(_run_session_async(str(profile_id)))

    return {
        "message": f"Autonomous AI session started for @{db_profile.x_handle.lstrip('@')}",
        "profile_id": str(profile_id),
        "task_id": "async-session",
    }


# === Profile Sub-resources ===
BASE_PROFILE_DIR = "/home/ubuntu/projects/xbot/data/profiles"


@router.get("/{profile_id}/analytics", response_model=list[dict[str, Any]])
async def get_profile_analytics_snapshots(
    profile_id: uuid.UUID,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Gets analytics snapshots history for a profile."""
    stmt = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    snaps = result.scalars().all()

    return [
        {
            "id": s.id,
            "profile_id": s.profile_id,
            "snapshot_date": s.snapshot_date,
            "followers": s.followers,
            "following": s.following,
            "total_tweets": s.total_tweets,
            "impressions_24h": s.impressions_24h,
            "engagements_24h": s.engagements_24h,
            "engagement_rate": s.engagement_rate,
            "top_tweets": s.top_tweets,
            "captured_at": s.captured_at,
        }
        for s in snaps
    ]


@router.get("/{profile_id}/monetization", response_model=dict[str, Any])
async def get_profile_monetization_status(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Gets calculated progress toward X's monetization thresholds."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    # 1. Fetch latest snapshot
    stmt_snap = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(1)
    )
    res_snap = await db.execute(stmt_snap)
    snap = res_snap.scalar_one_or_none()
    current_followers = snap.followers if snap else 0

    # 2. Get past 30 days snapshots for projections
    thirty_days_ago = datetime.date.today() - datetime.timedelta(days=30)
    stmt_snaps_30d = (
        select(AnalyticsSnapshot)
        .where(
            AnalyticsSnapshot.profile_id == profile_id,
            AnalyticsSnapshot.snapshot_date >= thirty_days_ago,
        )
        .order_by(AnalyticsSnapshot.snapshot_date.asc())
    )
    res_snaps_30d = await db.execute(stmt_snaps_30d)
    snaps_30d = res_snaps_30d.scalars().all()

    # Estimate 3-month impressions
    # Sum impressions over 30 days or extrapolate
    total_impressions_30d = sum(s.impressions_24h for s in snaps_30d)
    if len(snaps_30d) > 0:
        avg_daily_impressions = total_impressions_30d / len(snaps_30d)
        impressions_3mo = round(avg_daily_impressions * 90)
    else:
        impressions_3mo = snap.impressions_24h * 90 if snap else 0

    # Calculate growth rate
    growth_rate_per_day = 1.0  # default minimum
    if len(snaps_30d) >= 2:
        earliest_followers = snaps_30d[0].followers
        latest_followers = snaps_30d[-1].followers
        delta_days = (snaps_30d[-1].snapshot_date - snaps_30d[0].snapshot_date).days
        if delta_days > 0:
            growth_rate_per_day = max(
                0.1, (latest_followers - earliest_followers) / delta_days
            )

    # Project eligibility date
    days_until_eligible = max(0, (500 - current_followers) / growth_rate_per_day)
    projected_date = datetime.date.today() + datetime.timedelta(
        days=round(days_until_eligible)
    )

    # Pct calculations
    pct_followers_ads = min(100, round((current_followers / 500) * 100))
    pct_impressions_ads = min(100, round((impressions_3mo / 5000000) * 100))
    pct_followers_subs = min(100, round((current_followers / 2000) * 100))

    # Read active flags from profile config if available
    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    stripe_active = False
    premium_active = False
    if profile_dir.exists():
        try:
            config = load_config(profile_dir)
            premium_active = bool(config.credentials and config.credentials.password_encrypted)
        except Exception:
            pass

    return {
        "x_premium_active": premium_active,
        "stripe_connected": stripe_active,
        "ads_revenue_sharing": {
            "eligible": current_followers >= 500 and impressions_3mo >= 5000000,
            "progress": {
                "followers": {
                    "current": current_followers,
                    "required": 500,
                    "pct": pct_followers_ads,
                },
                "impressions_3mo": {
                    "current": impressions_3mo,
                    "required": 5000000,
                    "pct": pct_impressions_ads,
                },
            },
            "estimated_eligibility_date": projected_date.isoformat(),
        },
        "creator_subscriptions": {
            "eligible": current_followers >= 2000 and impressions_3mo >= 5000000,
            "progress": {
                "followers": {
                    "current": current_followers,
                    "required": 2000,
                    "pct": pct_followers_subs,
                },
                "impressions_3mo": {
                    "current": impressions_3mo,
                    "required": 5000000,
                    "pct": pct_impressions_ads,
                },
            },
        },
    }


@router.get("/{profile_id}/persona", response_model=dict[str, Any])
async def get_profile_persona(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Retrieves raw persona configuration yaml details."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    persona = load_persona(profile_dir)
    return persona.model_dump()


@router.put("/{profile_id}/persona", response_model=dict[str, Any])
async def update_profile_persona(
    profile_id: uuid.UUID,
    persona_in: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates persona.yaml configurations on disk."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    persona_file = profile_dir / "persona.yaml"
    with persona_file.open("w", encoding="utf-8") as f:
        yaml.dump(persona_in, f)

    return {"status": "success", "message": "Persona configuration updated successfully."}


class ImportCardRequest(BaseModel):
    content_or_path: str
    use_ai: bool = False


@router.post("/{profile_id}/import-card", response_model=dict[str, Any])
async def import_profile_character_card(
    profile_id: uuid.UUID,
    req: ImportCardRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Loads and parses a character card (JSON/YAML/file path) into our 7-Dimension Bedrock Persona,
    preserving the full raw card anchor to prevent hallucinations.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    try:
        raw_card = load_raw_card(req.content_or_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to load character card: {str(e)}"
        )

    persona_dict = map_card_to_persona(raw_card, existing_id=db_profile.profile_slug, existing_slug=db_profile.profile_slug)

    if req.use_ai:
        try:
            from xbot.ai.client import get_ai_client
            from xbot.config import settings
            import json as json_lib
            client = get_ai_client()
            prompt = (
                f"Enhance and refine this persona dictionary into a rich, high-fidelity 7-dimension persona:\n"
                f"{json_lib.dumps(persona_dict, indent=2)}\n\n"
                f"Original raw source:\n{req.content_or_path[:2000]}\n\n"
                f"Return ONLY valid JSON matching the persona schema with rich traits, values, writing rules, and background."
            )
            res = await client.chat.completions.create(
                model=settings.MODEL_POST_CREATION,
                messages=[
                    {"role": "system", "content": "You are an expert persona architect. Return ONLY JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            content_str = res.choices[0].message.content
            if content_str:
                ai_parsed = json_lib.loads(content_str)
                if isinstance(ai_parsed, dict) and "identity" in ai_parsed and "personality" in ai_parsed:
                    ai_parsed["id"] = db_profile.profile_slug
                    ai_parsed["raw_character_card"] = raw_card
                    persona_dict = ai_parsed
        except Exception as e:
            logger.warning(f"AI persona enhancement failed, using deterministic mapping: {e}")

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    persona_file = profile_dir / "persona.yaml"
    with persona_file.open("w", encoding="utf-8") as f:
        yaml.dump(persona_dict, f)

    return {
        "status": "success",
        "message": "Character card loaded and mapped successfully.",
        "persona": persona_dict
    }


@router.get("/{profile_id}/diary", response_model=list[dict[str, Any]])
async def get_profile_diary_logs(
    profile_id: uuid.UUID,
    limit: int = 15,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves recent daily inner-monologue diary entry summaries."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    diary_mgr = DiaryManager(profile_dir)
    return diary_mgr.get_recent_entries(limit=limit)


@router.get("/{profile_id}/memories", response_model=list[dict[str, Any]])
async def get_profile_memories(
    profile_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Gets extracted long-term memories for a profile."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    memory_mgr = MemoryManager(profile_dir)
    return memory_mgr.retrieve_memories(recency_limit=limit, min_importance=0.0)


@router.get("/{profile_id}/relationships", response_model=dict[str, Any])
async def get_profile_relationships(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves priority accounts and sentiment relationship tracking logs."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    relationships = load_relationships(profile_dir)
    return relationships.model_dump()


@router.get("/{profile_id}/strategy", response_model=dict[str, Any])
async def get_profile_strategy(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves current weekly strategy details."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    strategy = load_strategy(profile_dir)
    return strategy.model_dump()


@router.put("/{profile_id}/strategy", response_model=dict[str, Any])
async def update_profile_strategy(
    profile_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates strategy configuration (keywords, competitor accounts, topics) on disk."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    strategy = load_strategy(profile_dir)

    if "content_strategy" in payload and isinstance(payload["content_strategy"], dict):
        cs = payload["content_strategy"]
        if "top_performing_topics" in cs and isinstance(cs["top_performing_topics"], list):
            strategy.content_strategy.top_performing_topics = cs["top_performing_topics"]
        if "underperforming_topics" in cs and isinstance(cs["underperforming_topics"], list):
            strategy.content_strategy.underperforming_topics = cs["underperforming_topics"]
        if "posting_frequency" in cs:
            strategy.content_strategy.posting_frequency = str(cs["posting_frequency"])

    if "engagement_strategy" in payload and isinstance(payload["engagement_strategy"], dict):
        es = payload["engagement_strategy"]
        if "priority_accounts" in es and isinstance(es["priority_accounts"], list):
            strategy.engagement_strategy.priority_accounts = es["priority_accounts"]
        if "daily_targets" in es and isinstance(es["daily_targets"], dict):
            for k, v in es["daily_targets"].items():
                strategy.engagement_strategy.daily_targets[k] = str(v)

    if "current_focus" in payload and isinstance(payload["current_focus"], dict):
        cf = payload["current_focus"]
        if "primary" in cf:
            strategy.current_focus.primary = str(cf["primary"])
        if "secondary" in cf:
            strategy.current_focus.secondary = str(cf["secondary"])

    save_strategy(profile_dir, strategy)
    return {"status": "success", "message": "Strategy updated successfully.", "strategy": strategy.model_dump()}



@router.get("/{profile_id}/config", response_model=dict[str, Any])
async def get_profile_config(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves current automation limits and execution schedule configuration."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    config = load_config(profile_dir)
    return config.model_dump()


@router.put("/{profile_id}/config", response_model=dict[str, Any])
async def update_profile_config(
    profile_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates automation limits and execution schedule configuration on disk and clears Redis cache."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    config = load_config(profile_dir)

    if "mock_mode" in payload:
        config.mock_mode = bool(payload["mock_mode"])

    if "limits" in payload and isinstance(payload["limits"], dict):
        for k, v in payload["limits"].items():
            if hasattr(config.limits, k):
                try:
                    setattr(config.limits, k, int(v))
                except (ValueError, TypeError):
                    pass

    if "schedule" in payload and isinstance(payload["schedule"], dict):
        for k, v in payload["schedule"].items():
            if hasattr(config.schedule, k):
                if k in ("min_sessions_per_day", "max_sessions_per_day", "interval_minutes"):
                    try:
                        setattr(config.schedule, k, int(v))
                    except (ValueError, TypeError):
                        pass
                else:
                    setattr(config.schedule, k, str(v))

    save_config(profile_dir, config)

    try:
        import redis, datetime
        from xbot.config import settings
        r = redis.from_url(settings.REDIS_URL)
        today_str = datetime.date.today().isoformat()
        redis_key = f"schedule:{db_profile.profile_slug}:{today_str}"
        r.delete(redis_key)
    except Exception as e:
        logger.warning("Could not clear Redis schedule cache for %s: %s", db_profile.profile_slug, e)

    return {"status": "success", "message": "Automation limits and schedule updated successfully.", "config": config.model_dump()}



@router.post("/{profile_id}/login-session", response_model=dict[str, Any])
async def launch_login_session(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Launches a headed Playwright browser on the host display pointing to X.com login.
    Captures cookies/storage state upon browser window close and saves it for persistent session.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    from playwright.async_api import async_playwright
    import os

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    state_path = profile_dir / "storage_state.json"

    try:
        if not os.environ.get("DISPLAY"):
            os.environ["DISPLAY"] = ":0"

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )
            context = await browser.new_context(
                viewport=None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto("https://x.com/i/flow/login")
            
            closed_event = asyncio.Event()
            page.on("close", lambda: closed_event.set())
            
            try:
                await asyncio.wait_for(closed_event.wait(), timeout=300.0)
            except asyncio.TimeoutError:
                pass
            
            await context.storage_state(path=str(state_path))
            await browser.close()

        if state_path.exists() and state_path.stat().st_size > 100:
            return {"status": "success", "message": "Login session captured and stored successfully."}
        else:
            return {"status": "cancelled", "message": "Browser closed without logging in."}

    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run login browser session: {str(ex)}"
        )


@router.get("/{profile_id}/auth-status", response_model=dict[str, Any])
async def get_profile_auth_status(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Inspects storage_state.json cookies and returns session health and profile stats."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    await _populate_profile_metrics(db, db_profile)
    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    auth_status = inspect_profile_auth_status(profile_dir)
    auth_status["avatar_url"] = db_profile.avatar_url
    auth_status["followers_count"] = getattr(db_profile, "followers_count", 0)
    auth_status["following_count"] = getattr(db_profile, "following_count", 0)
    return auth_status


class ImportCookiesRequest(BaseModel):
    auth_token: str | None = None
    ct0: str | None = None
    raw_cookies: str | None = None
    twid: str | None = None


@router.post("/{profile_id}/import-cookies", response_model=dict[str, Any])
async def import_profile_cookies(
    profile_id: uuid.UUID,
    req: ImportCookiesRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Imports auth cookies directly or from a raw cookie header/JSON string."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    auth_token = req.auth_token
    ct0 = req.ct0
    twid = req.twid

    if req.raw_cookies:
        parsed = parse_cookie_string(req.raw_cookies)
        auth_token = auth_token or parsed.get("auth_token")
        ct0 = ct0 or parsed.get("ct0")
        twid = twid or parsed.get("twid")

    if not auth_token or not ct0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both auth_token and ct0 cookies are required to import session.",
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    storage_state = format_storage_state(
        auth_token=auth_token.strip(),
        ct0=ct0.strip(),
        twid=twid.strip() if twid else None,
    )
    state_file = profile_dir / "storage_state.json"
    if state_file.exists():
        try:
            state_file.unlink(missing_ok=True)
        except Exception as unlink_err:
            logger.warning("Could not unlink existing storage_state.json for %s: %s", db_profile.profile_slug, unlink_err)

    try:
        with state_file.open("w", encoding="utf-8") as f:
            json.dump(storage_state, f, indent=2)
    except Exception as io_err:
        logger.error("Failed to write storage_state.json for %s: %s", db_profile.profile_slug, io_err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write session file to disk: {str(io_err)}"
        )

    return {
        "status": "success",
        "message": "Cookies imported successfully.",
        "auth_status": inspect_profile_auth_status(profile_dir),
    }


@router.post("/{profile_id}/sync-from-x", response_model=dict[str, Any])
async def sync_profile_from_x_endpoint(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Launches headless browser session to sync follower/following counts, avatar,
    display name, and verify live auth state from X.com.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    manager = BrowserManager(base_profile_dir=str(BASE_PROFILE_DIR))
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=120):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile {db_profile.profile_slug} is currently locked or in use.",
        )

    context = None
    try:
        await manager.start()
        context = await manager.get_context(profile_slug=db_profile.profile_slug)
        page = await context.new_page()
        sync_action = SyncProfileFromX()
        sync_data = await sync_action.execute(page, db_profile.x_handle)
    except Exception as e:
        logger.error("Error during sync from X for profile %s: %s", db_profile.profile_slug, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync profile from X: {str(e)}",
        )
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        manager.release_lock(db_profile.profile_slug)
        await manager.stop()

    if sync_data.get("avatar_url"):
        db_profile.avatar_url = sync_data["avatar_url"]
    if sync_data.get("display_name"):
        db_profile.display_name = sync_data["display_name"]

    followers = sync_data.get("followers_count", 0)
    following = sync_data.get("following_count", 0)
    posts = sync_data.get("posts_count", 0)
    impressions = sync_data.get("impressions_24h", 0)
    engagements = sync_data.get("engagements_24h", 0)
    eng_rate = sync_data.get("engagement_rate", 0.0)
    likes = sync_data.get("likes_count", 0)
    retweets = sync_data.get("retweets_count", 0)
    recent_tw = sync_data.get("recent_tweets", [])

    snapshot = AnalyticsSnapshot(
        profile_id=db_profile.id,
        snapshot_date=datetime.date.today(),
        followers=followers,
        following=following,
        total_tweets=posts,
        impressions_24h=impressions,
        engagements_24h=engagements,
        engagement_rate=eng_rate,
        top_tweets={
            "likes_count": likes,
            "retweets_count": retweets,
            "recent_tweets": recent_tw,
        },
        captured_at=datetime.datetime.utcnow(),
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(db_profile)
    await _populate_profile_metrics(db, db_profile)

    return {
        "status": "success",
        "sync_data": sync_data,
        "profile": ProfileResponse.model_validate(db_profile).model_dump(mode="json"),
    }




@router.get("/{profile_id}/learned-state", response_model=dict[str, Any])
async def get_profile_learned_state(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Retrieves dynamic learned state configuration."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    learned = load_learned_state(profile_dir)
    return learned.model_dump()


@router.put("/{profile_id}/learned-state", response_model=dict[str, Any])
async def update_profile_learned_state(
    profile_id: uuid.UUID,
    state_in: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates learned_state.yaml on disk."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    learned = LearnedState.model_validate(state_in)
    save_learned_state(profile_dir, learned)
    return {"status": "success", "message": "Learned state updated successfully."}


@router.post("/{profile_id}/reflect", response_model=dict[str, Any])
async def trigger_profile_reflection(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually triggers the auto-learning reflection Celery task."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    from xbot.tasks import run_persona_reflection
    run_persona_reflection.delay(str(profile_id))
    return {"status": "accepted", "message": "Auto-learning reflection triggered in background."}


class LivePostRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=280)
    media_paths: list[str] | None = None
    gif_query: str | None = None


class LiveReplyRequest(BaseModel):
    tweet_url: str = Field(..., min_length=5)
    reply_text: str = Field(..., min_length=1, max_length=280)


class LivePollRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=200)
    options: list[str] = Field(..., min_length=2, max_length=4)
    duration_days: int = Field(default=1, ge=1, le=7)


class LiveThreadRequest(BaseModel):
    tweets: list[str] = Field(..., min_length=2, max_length=10)


class LiveFollowRequest(BaseModel):
    username: str = Field(..., min_length=1)


class LiveLikeRequest(BaseModel):
    tweet_url: str = Field(..., min_length=5)


@router.post("/{profile_id}/upload-media", response_model=dict[str, Any])
async def upload_profile_media(
    profile_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Uploads an image or media file to the profile's media library."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    media_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    clean_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    target_path = media_dir / clean_name

    contents = await file.read()
    with open(target_path, "wb") as f:
        f.write(contents)

    return {
        "status": "success",
        "filename": clean_name,
        "file_path": str(target_path),
        "size_bytes": len(contents),
    }


@router.get("/{profile_id}/media", response_model=list[dict[str, Any]])
async def list_profile_media(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists all available images/media files for this profile."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    media_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug / "media"
    if not media_dir.exists():
        return []

    files = []
    for p in media_dir.glob("*.*"):
        if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4"]:
            files.append({
                "filename": p.name,
                "file_path": str(p),
                "size_bytes": p.stat().st_size,
                "modified_at": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            })
    return sorted(files, key=lambda x: x["modified_at"], reverse=True)


@router.post("/{profile_id}/publish-post", response_model=dict[str, Any])
async def publish_live_post(
    profile_id: uuid.UUID,
    req: LivePostRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publishes a live post directly to the user's X timeline using Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ComposePost
    from xbot.models.content import Content, ContentStatus

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is currently busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = ComposePost()
        success = await action.execute(
            page,
            text=req.text,
            media_paths=req.media_paths,
            gif_query=req.gif_query,
        )
        
        # Record in DB
        content_row = Content(
            profile_id=db_profile.id,
            body=req.text,
            content_type="post",
            status=ContentStatus.POSTED if success else ContentStatus.FAILED,
            ai_metadata={
                "media_paths": req.media_paths,
                "gif_query": req.gif_query,
            }
        )
        db.add(content_row)
        await db.commit()

        return {
            "status": "success" if success else "failed",
            "message": "Post published to X timeline successfully!" if success else "Failed to publish post to X.",
            "post_text": req.text,
            "media_paths": req.media_paths,
        }
    except Exception as e:
        logger.error(f"Error publishing live post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


@router.post("/{profile_id}/publish-reply", response_model=dict[str, Any])
async def publish_live_reply(
    profile_id: uuid.UUID,
    req: LiveReplyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publishes a live reply directly to a target tweet on X using Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ReplyToTweet

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = ReplyToTweet()
        success = await action.execute(page, reply_text=req.reply_text, tweet_url=req.tweet_url)

        return {
            "status": "success" if success else "failed",
            "message": "Reply published to X thread successfully!" if success else "Failed to publish reply to X.",
            "reply_text": req.reply_text,
            "target_tweet": req.tweet_url,
        }
    except Exception as e:
        logger.error(f"Error publishing live reply: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


@router.post("/{profile_id}/publish-poll", response_model=dict[str, Any])
async def publish_live_poll(
    profile_id: uuid.UUID,
    req: LivePollRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publishes a live interactive poll directly to X using Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.poll_action import CreatePoll

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = CreatePoll()
        clean_opts = [opt[:25].strip() for opt in req.options if opt.strip()]
        success = await action.execute(
            page,
            question=req.question,
            options=clean_opts,
            duration_days=req.duration_days,
        )

        return {
            "status": "success" if success else "failed",
            "message": "Poll published to X successfully!" if success else "Failed to create poll on X.",
            "question": req.question,
            "options": clean_opts,
        }
    except Exception as e:
        logger.error(f"Error publishing live poll: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


@router.post("/{profile_id}/publish-thread", response_model=dict[str, Any])
async def publish_live_thread(
    profile_id: uuid.UUID,
    req: LiveThreadRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publishes a live multi-tweet thread directly to X using Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ComposeThread

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(35000)

        action = ComposeThread()
        res = await action.execute(page, tweets=req.tweets)
        success = res.get("status") == "success"

        return {
            "status": "success" if success else "failed",
            "message": "Thread published to X successfully!" if success else f"Failed to publish thread: {res.get('error')}",
            "total_tweets": len(req.tweets),
            "root_tweet_id": res.get("root_tweet_id"),
        }
    except Exception as e:
        logger.error(f"Error publishing live thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


@router.post("/{profile_id}/follow-user", response_model=dict[str, Any])
async def follow_user_live(
    profile_id: uuid.UUID,
    req: LiveFollowRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executes a live follow action on X for the target username."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import FollowUser

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = FollowUser()
        success = await action.execute(page, username=req.username)

        return {
            "status": "success" if success else "failed",
            "message": f"Successfully followed @{req.username.lstrip('@')}!" if success else f"Failed to follow @{req.username.lstrip('@')}.",
            "target_user": req.username,
        }
    except Exception as e:
        logger.error(f"Error following user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


@router.post("/{profile_id}/like-tweet", response_model=dict[str, Any])
async def like_tweet_live(
    profile_id: uuid.UUID,
    req: LiveLikeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executes a live like action on X for the target tweet URL."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import LikeTweet

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = LikeTweet()
        success = await action.execute(page, tweet_url=req.tweet_url)

        return {
            "status": "success" if success else "failed",
            "message": "Tweet liked on X successfully!" if success else "Failed to like tweet on X.",
            "target_tweet": req.tweet_url,
        }
    except Exception as e:
        logger.error(f"Error liking tweet: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


@router.get("/{profile_id}/drafts", response_model=list[dict[str, Any]])
async def get_pending_drafts(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves all pending drafts requiring user review/approval."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.models.content import Content, ContentStatus
    stmt = (
        select(Content)
        .where(Content.profile_id == profile_id)
        .where(Content.status == ContentStatus.DRAFT)
        .order_by(Content.created_at.desc())
    )
    res = await db.execute(stmt)
    drafts = res.scalars().all()
    return [
        {
            "id": str(d.id),
            "content_type": d.content_type.value if hasattr(d.content_type, "value") else str(d.content_type),
            "body": d.body,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "ai_metadata": d.ai_metadata,
            "thread_items": [
                {
                    "id": str(item.id),
                    "position": item.position,
                    "item_type": item.item_type,
                    "text": item.text,
                }
                for item in getattr(d, "thread_items", [])
            ],
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in drafts
    ]


@router.post("/{profile_id}/drafts/{content_id}/approve", response_model=dict[str, Any])
async def approve_and_publish_draft(
    profile_id: uuid.UUID,
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approves a staged draft post/poll/thread and publishes it to live X via Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.models.content import Content, ContentStatus, ContentType
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ComposePost, ComposeThread
    from xbot.browser.actions.poll_action import CreatePoll

    c_res = await db.execute(select(Content).where(Content.id == content_id).where(Content.profile_id == profile_id))
    draft = c_res.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft content not found")

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    success = False
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(35000)

        if draft.content_type == ContentType.POLL:
            meta_poll = draft.ai_metadata.get("poll", {}) if draft.ai_metadata else {}
            question = meta_poll.get("question") or draft.body.split("\n")[0]
            options = meta_poll.get("options") or ["Yes", "No"]
            duration_days = meta_poll.get("duration_days", 1)
            screenshot_dir = str(Path(BASE_PROFILE_DIR) / db_profile.profile_slug / "screenshots")
            action = CreatePoll(screenshot_dir=screenshot_dir)
            success = await action.execute(page, question=question, options=options, duration_days=duration_days)
        elif draft.content_type == ContentType.THREAD or draft.content_type == "thread":
            tweets = []
            if getattr(draft, "thread_items", None):
                tweets = [item.text for item in draft.thread_items]
            elif draft.ai_metadata and "tweets" in draft.ai_metadata:
                tweets = draft.ai_metadata["tweets"]
            else:
                tweets = [p.strip() for p in draft.body.split("\n\n") if p.strip()]
            action = ComposeThread()
            res = await action.execute(page, tweets=tweets)
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

        return {
            "status": "success" if success else "failed",
            "message": "Draft approved and published to X!" if success else "Browser returned failure.",
            "content_id": str(draft.id),
        }
    except Exception as e:
        logger.error(f"Error publishing draft: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


@router.delete("/{profile_id}/drafts/{content_id}", response_model=dict[str, Any])
async def dismiss_draft(
    profile_id: uuid.UUID,
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dismisses/deletes a single pending draft."""
    from xbot.models.content import Content
    c_res = await db.execute(select(Content).where(Content.id == content_id).where(Content.profile_id == profile_id))
    draft = c_res.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft content not found")

    await db.delete(draft)
    await db.commit()
    return {"status": "success", "message": "Draft dismissed."}


@router.delete("/{profile_id}/drafts", response_model=dict[str, Any])
async def dismiss_all_drafts(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dismisses/deletes ALL pending drafts for a profile in bulk."""
    from sqlalchemy import delete
    from xbot.models.content import Content, ContentStatus
    stmt = (
        delete(Content)
        .where(Content.profile_id == profile_id)
        .where(Content.status == ContentStatus.DRAFT)
    )
    res = await db.execute(stmt)
    await db.commit()
    return {
        "status": "success",
        "message": f"All {res.rowcount} pending drafts discarded.",
        "discarded_count": res.rowcount,
    }


@router.post("/{profile_id}/drafts/approve-all", response_model=dict[str, Any])
async def approve_all_pending_drafts(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approves all staged drafts for immediate autonomous sequential publishing."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.models.content import Content, ContentStatus
    c_res = await db.execute(
        select(Content)
        .where(Content.profile_id == profile_id)
        .where(Content.status == ContentStatus.DRAFT)
    )
    drafts = c_res.scalars().all()
    count = len(drafts)
    if count == 0:
        return {"status": "success", "message": "No pending drafts to approve.", "count": 0}

    # Mark all as APPROVED so autonomous publisher executes them sequentially
    for d in drafts:
        d.status = ContentStatus.APPROVED
    await db.commit()

    # Trigger immediate auto-publish task in background
    try:
        from xbot.tasks import auto_publish_pending_drafts
        auto_publish_pending_drafts.delay()
    except Exception as t_err:
        logger.warning("Could not dispatch auto_publish_pending_drafts Celery task: %s", t_err)

    return {
        "status": "success",
        "message": f"Successfully approved {count} drafts for autonomous publishing!",
        "count": count,
    }


# -------------------------------------------------------------
# Deep Analytics & Official Creator Studio Milestones Endpoints
# -------------------------------------------------------------

@router.get("/{profile_id}/deep-analytics", response_model=dict[str, Any])
async def get_deep_analytics(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns full deep analytics:
    - Official Creator Studio Milestones (500 Verified Followers & 500K 90d Verified Impressions)
    - 28-Day Rolling Impressions & Engagement Rate
    - Top Performing Posts Ranking
    - Historical Snapshots
    """
    from datetime import datetime, timedelta
    from xbot.models.content import Content, ContentStatus
    from xbot.models.analytics import AnalyticsSnapshot

    prof_res = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = prof_res.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Fetch latest analytics snapshot
    snap_res = await db.execute(
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(1)
    )
    latest_snap = snap_res.scalar_one_or_none()

    verified_followers = latest_snap.verified_followers if latest_snap else 16
    verified_imp_90d = latest_snap.verified_impressions_90d if latest_snap else 0

    # 28-day window aggregation
    cutoff_28d = datetime.utcnow() - timedelta(days=28)
    content_res = await db.execute(
        select(Content)
        .where(Content.profile_id == profile_id)
        .where(Content.status == ContentStatus.POSTED)
        .where(Content.created_at >= cutoff_28d)
        .order_by(Content.created_at.desc())
    )
    posts_28d = content_res.scalars().all()

    total_posts = len(posts_28d)
    total_impressions_28d = 0
    total_engagements_28d = 0
    top_posts_list = []

    for p in posts_28d:
        meta = p.ai_metadata or {}
        views = int(meta.get("views_count") or meta.get("views") or meta.get("impressions") or 0)
        likes = int(meta.get("likes_count") or meta.get("likes") or 0)
        retweets = int(meta.get("retweets_count") or meta.get("retweets") or 0)
        replies = int(meta.get("replies_count") or meta.get("replies") or 0)
        
        engagements = likes + retweets + replies
        total_impressions_28d += views
        total_engagements_28d += engagements

        top_posts_list.append({
            "id": str(p.id),
            "body": p.body,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "views": views,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "engagements": engagements,
            "media_paths": meta.get("media_paths", []),
            "visual_spec": meta.get("visual_spec"),
            "gif_query": meta.get("gif_query"),
        })

    # Sort top posts by views / engagements
    top_posts_list.sort(key=lambda x: (x["views"], x["engagements"]), reverse=True)

    engagement_rate_28d = (
        round((total_engagements_28d / total_impressions_28d) * 100, 2)
        if total_impressions_28d > 0
        else 0.0
    )

    # Fetch last 7 snapshots for sparklines
    hist_res = await db.execute(
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(7)
    )
    history_snaps = hist_res.scalars().all()
    history_data = [
        {
            "date": s.snapshot_date.isoformat() if s.snapshot_date else s.captured_at.strftime("%Y-%m-%d"),
            "followers": s.followers,
            "verified_followers": s.verified_followers,
            "impressions": s.impressions_24h,
            "engagement_rate": s.engagement_rate,
        }
        for s in reversed(history_snaps)
    ]

    return {
        "status": "success",
        "profile_id": str(profile_id),
        "handle": db_profile.x_handle,
        "monetization_milestones": {
            "verified_followers": {
                "current": verified_followers,
                "target": 500,
                "percentage": round(min(100.0, (verified_followers / 500.0) * 100.0), 1),
                "remaining": max(0, 500 - verified_followers),
            },
            "verified_impressions_90d": {
                "current": verified_imp_90d,
                "target": 500000,
                "percentage": round(min(100.0, (verified_imp_90d / 500000.0) * 100.0), 2),
                "remaining": max(0, 500000 - verified_imp_90d),
            },
        },
        "rolling_28d": {
            "total_posts": total_posts,
            "total_impressions": total_impressions_28d,
            "total_engagements": total_engagements_28d,
            "engagement_rate": engagement_rate_28d,
        },
        "top_performing_posts": top_posts_list[:5],
        "history": history_data,
        "last_synced_at": latest_snap.captured_at.isoformat() if latest_snap else None,
    }


@router.post("/{profile_id}/sync-analytics", response_model=dict[str, Any])
async def sync_live_analytics(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Triggers an instant live sync of official Creator Studio metrics and profile metrics via Playwright.
    """
    from datetime import date, datetime
    from xbot.models.analytics import AnalyticsSnapshot
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ScrapeCreatorStudioMetrics, ScrapeProfileTweets

    prof_res = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = prof_res.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()

        # 1. Scrape Creator Studio official numbers
        studio_action = ScrapeCreatorStudioMetrics()
        studio_res = await studio_action.execute(page)

        verified_followers = studio_res.get("verified_followers", 16)
        verified_imp_90d = studio_res.get("verified_impressions_90d", 0)

        # 2. Scrape Profile stats
        prof_action = ScrapeProfileTweets()
        prof_stats = await prof_action.execute(page, db_profile.x_handle.lstrip("@"), limit=10)

        followers = prof_stats.get("followers", 0)
        following = prof_stats.get("following", 0)

        # 3. Store snapshot
        snapshot = AnalyticsSnapshot(
            profile_id=profile_id,
            snapshot_date=date.today(),
            followers=followers,
            following=following,
            verified_followers=verified_followers,
            verified_impressions_90d=verified_imp_90d,
            captured_at=datetime.utcnow(),
        )
        db.add(snapshot)
        await db.commit()

        return {
            "status": "success",
            "message": "Live analytics and Creator Studio metrics synced successfully!",
            "verified_followers": verified_followers,
            "verified_impressions_90d": verified_imp_90d,
            "followers": followers,
            "following": following,
            "synced_at": datetime.utcnow().isoformat(),
        }
    except Exception as ex:
        logger.error("Error during live analytics sync: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


# -------------------------------------------------------------
# Follow-for-Follow (F4F) & 1,000 Blue Tick Milestone Endpoints
# -------------------------------------------------------------

class F4FFollowRequest(BaseModel):
    target_handle: str = Field(..., min_length=1)
    is_blue_tick: bool = Field(default=True)
    niche: str | None = Field(default="ai")


@router.get("/{profile_id}/f4f/candidates", response_model=list[dict[str, Any]])
async def get_f4f_candidates(
    profile_id: uuid.UUID,
    niche: str = "all",
    blue_tick_only: bool = True,
    limit: int = 25,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists high-reciprocity Blue Tick candidates across anime, movies, tech, and AI communities."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.models.follow_growth import FollowCandidate
    from xbot.growth.f4f_engine import populate_f4f_candidates

    query = select(FollowCandidate).where(FollowCandidate.profile_id == profile_id)
    if niche != "all":
        query = query.where(FollowCandidate.niche == niche)
    if blue_tick_only:
        query = query.where(FollowCandidate.is_blue_tick == True)
    
    query = query.order_by(FollowCandidate.reciprocity_score.desc()).limit(limit)
    res = await db.execute(query)
    candidates = res.scalars().all()

    if not candidates:
        candidates = await populate_f4f_candidates(profile_id=profile_id, db=db, niche=niche, limit=limit)

    return [
        {
            "id": str(c.id),
            "handle": c.handle,
            "display_name": c.display_name,
            "niche": c.niche,
            "is_blue_tick": c.is_blue_tick,
            "follower_count": c.follower_count,
            "following_count": c.following_count,
            "bio": c.bio,
            "source_discussion": c.source_discussion,
            "reciprocity_score": c.reciprocity_score,
            "status": c.status,
            "discovered_at": c.discovered_at.isoformat() if c.discovered_at else None,
        }
        for c in candidates
    ]


@router.post("/{profile_id}/f4f/scan", response_model=dict[str, Any])
async def trigger_f4f_scan(
    profile_id: uuid.UUID,
    niche: str = "all",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Scans community discussions and refreshes the candidate radar."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.growth.f4f_engine import populate_f4f_candidates
    candidates = await populate_f4f_candidates(profile_id=profile_id, db=db, niche=niche, limit=limit)
    return {
        "status": "success",
        "message": f"Harvested {len(candidates)} high-reciprocity Blue Tick candidates.",
        "count": len(candidates),
    }


@router.post("/{profile_id}/f4f/follow", response_model=dict[str, Any])
async def execute_f4f_follow(
    profile_id: uuid.UUID,
    req: F4FFollowRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executes a live follow of a candidate and starts the 4-day reciprocity grace period."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import FollowUser
    from xbot.growth.f4f_engine import record_follow_action

    clean_handle = req.target_handle.lstrip("@")
    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Browser is currently busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = FollowUser()
        success = await action.execute(page, username=clean_handle)
        
        if success:
            await record_follow_action(
                profile_id=profile_id,
                target_handle=clean_handle,
                db=db,
                is_blue_tick=req.is_blue_tick,
                niche=req.niche,
            )

        return {
            "status": "success" if success else "failed",
            "message": f"Successfully followed @{clean_handle} on X!" if success else f"Failed to follow @{clean_handle}.",
            "target_handle": clean_handle,
        }
    except Exception as e:
        logger.error(f"Error following candidate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass


@router.get("/{profile_id}/f4f/stats", response_model=dict[str, Any])
async def get_f4f_stats(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Returns analytics for the 1,000 Blue Tick Follower Milestone."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.growth.f4f_engine import get_f4f_milestone_analytics
    return await get_f4f_milestone_analytics(profile_id=profile_id, db=db)


@router.get("/{profile_id}/f4f/growth-posts", response_model=list[dict[str, Any]])
async def get_active_growth_posts(
    profile_id: uuid.UUID,
    niche: str = "all",
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Hunts active follow-for-follow and mutuals posts across Twitter/X."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.growth.community_harvester import discover_active_growth_posts
    posts = discover_active_growth_posts(niche=niche)
    return [p.model_dump() for p in posts]


@router.post("/{profile_id}/f4f/batch-follow", response_model=dict[str, Any])
async def execute_f4f_batch_follow(
    profile_id: uuid.UUID,
    count: int = 3,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executes sequential live follows for the top N high-reciprocity Blue Tick candidates."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.models.follow_growth import FollowCandidate
    from xbot.growth.f4f_engine import record_follow_action
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import FollowUser
    from xbot.browser.timing import sleep_with_jitter

    c_stmt = (
        select(FollowCandidate)
        .where(FollowCandidate.profile_id == profile_id)
        .where(FollowCandidate.status == "discovered")
        .order_by(FollowCandidate.reciprocity_score.desc())
        .limit(min(10, max(1, count)))
    )
    c_res = await db.execute(c_stmt)
    candidates = c_res.scalars().all()

    if not candidates:
        return {"status": "no_op", "message": "No un-followed candidates in queue.", "followed_count": 0}

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Browser is currently busy. Please retry.")

    context = None
    followed: list[str] = []
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = FollowUser()
        for cand in candidates:
            clean = cand.handle.lstrip("@")
            success = await action.execute(page, username=clean)
            if success:
                followed.append(clean)
                await record_follow_action(
                    profile_id=profile_id,
                    target_handle=clean,
                    db=db,
                    is_blue_tick=cand.is_blue_tick,
                    niche=cand.niche,
                )
                await sleep_with_jitter(2000)

        return {
            "status": "success",
            "message": f"Successfully followed {len(followed)} Blue Tick candidates live on X!",
            "followed_handles": followed,
            "followed_count": len(followed),
        }
    except Exception as e:
        logger.error(f"Error in batch follow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass











