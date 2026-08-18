import asyncio
import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
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
from pydantic import BaseModel
from xbot.persona.card_parser import load_raw_card, map_card_to_persona
from xbot.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate

logger = logging.getLogger(__name__)

yaml = YAML(typ="safe")
yaml.default_flow_style = False

router = APIRouter(prefix="/profiles", tags=["Profiles"])


async def _populate_profile_metrics(db: AsyncSession, p: Profile) -> Profile:
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
    Manually trigger an execution session for a profile.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    # Trigger Celery session task asynchronously
    from xbot.tasks import run_session

    task = run_session.delay(str(profile_id))

    return {
        "message": f"Session manually triggered for profile {db_profile.profile_slug}",
        "profile_id": str(profile_id),
        "task_id": str(task.id),
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
    with state_file.open("w", encoding="utf-8") as f:
        json.dump(storage_state, f, indent=2)

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

    snapshot = AnalyticsSnapshot(
        profile_id=db_profile.id,
        snapshot_date=datetime.date.today(),
        followers=followers,
        following=following,
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


@router.get("/{profile_id}/follower-snapshots", response_model=dict[str, Any])
async def get_follower_snapshots(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves the latest follower and following snapshots for a profile."""
    from xbot.models.analytics import FollowerSnapshot
    
    followers_stmt = (
        select(FollowerSnapshot)
        .where(FollowerSnapshot.profile_id == profile_id, FollowerSnapshot.snapshot_type == "follower")
        .order_by(FollowerSnapshot.captured_at.desc())
        .limit(1)
    )
    res = await db.execute(followers_stmt)
    followers_snap = res.scalar_one_or_none()

    following_stmt = (
        select(FollowerSnapshot)
        .where(FollowerSnapshot.profile_id == profile_id, FollowerSnapshot.snapshot_type == "following")
        .order_by(FollowerSnapshot.captured_at.desc())
        .limit(1)
    )
    res = await db.execute(following_stmt)
    following_snap = res.scalar_one_or_none()

    return {
        "followers": followers_snap.handles if followers_snap else [],
        "following": following_snap.handles if following_snap else [],
        "last_updated": followers_snap.captured_at if followers_snap else None
    }


@router.get("/{profile_id}/follower-changelogs", response_model=list[dict[str, Any]])
async def get_follower_changelogs(
    profile_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves follower and following change logs for a profile."""
    from xbot.models.analytics import FollowerChangeLog
    
    stmt = (
        select(FollowerChangeLog)
        .where(FollowerChangeLog.profile_id == profile_id)
        .order_by(FollowerChangeLog.detected_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    logs = res.scalars().all()
    
    return [
        {
            "id": str(log.id),
            "change_type": log.change_type,
            "handle": log.handle,
            "detected_at": log.detected_at
        }
        for log in logs
    ]


@router.post("/{profile_id}/follower-audit", response_model=dict[str, Any])
async def trigger_follower_audit_endpoint(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Triggers a follower tracking/diffing snapshot audit in the background."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    
    from xbot.tasks import run_follower_audit
    run_follower_audit.delay(str(profile_id))
    return {"status": "accepted", "message": "Follower tracking and diffing audit queued."}


@router.get("/{profile_id}/campaigns", response_model=list[dict[str, Any]])
async def get_campaigns(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves all campaigns for a profile."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    
    from xbot.campaign_manager import load_campaigns
    campaigns = load_campaigns(db_profile.profile_slug)
    return [c.model_dump() for c in campaigns]


@router.post("/{profile_id}/campaigns", response_model=dict[str, Any])
async def create_campaign(
    profile_id: uuid.UUID,
    campaign_in: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Creates a new campaign for a profile."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    
    from xbot.campaign_manager import load_campaigns, save_campaigns, Campaign
    campaigns = load_campaigns(db_profile.profile_slug)
    
    new_c = Campaign(
        name=campaign_in.get("name", "Unnamed Campaign"),
        steps=campaign_in.get("steps", [])
    )
    campaigns.append(new_c)
    save_campaigns(db_profile.profile_slug, campaigns)
    return new_c.model_dump()


@router.post("/{profile_id}/campaigns/{campaign_id}/run", response_model=dict[str, Any])
async def trigger_campaign_run(
    profile_id: uuid.UUID,
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually triggers a campaign Celery task run in the background."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    
    from xbot.tasks import run_campaign
    run_campaign.delay(str(profile_id), campaign_id)
    return {"status": "accepted", "message": "Campaign run queued in background."}


@router.delete("/{profile_id}/campaigns/{campaign_id}", response_model=dict[str, Any])
async def delete_campaign(
    profile_id: uuid.UUID,
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Deletes a campaign from disk."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    
    from xbot.campaign_manager import load_campaigns, save_campaigns
    campaigns = load_campaigns(db_profile.profile_slug)
    campaigns = [c for c in campaigns if c.id != campaign_id]
    save_campaigns(db_profile.profile_slug, campaigns)
    return {"status": "success", "message": "Campaign deleted."}


@router.get("/{profile_id}/reputation-history", response_model=list[dict[str, Any]])
async def get_reputation_history(
    profile_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves the reputation history logs for a profile."""
    from xbot.models.analytics import ReputationLog
    
    stmt = (
        select(ReputationLog)
        .where(ReputationLog.profile_id == profile_id)
        .order_by(ReputationLog.captured_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    logs = res.scalars().all()
    
    return [
        {
            "id": str(log.id),
            "sentiment_score": log.sentiment_score,
            "total_replies_analyzed": log.total_replies_analyzed,
            "positive_count": log.positive_count,
            "negative_count": log.negative_count,
            "neutral_count": log.neutral_count,
            "captured_at": log.captured_at
        }
        for log in logs
    ]


@router.post("/{profile_id}/reputation-analysis", response_model=dict[str, Any])
async def run_reputation_analysis_endpoint(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually triggers a reputation and sentiment analysis task."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
        
    from xbot.tasks import run_reputation_analysis
    run_reputation_analysis.delay(str(profile_id))
    return {"status": "accepted", "message": "Reputation and sentiment analysis queued."}


@router.get("/{profile_id}/social-graph", response_model=dict[str, Any])
async def get_social_graph(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves the pre-scraped social graph connections JSON from disk."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    
    import json
    from pathlib import Path
    graph_file = Path("/home/ubuntu/projects/xbot/data/profiles") / db_profile.profile_slug / "social_graph.json"
    if not graph_file.exists():
        return {"nodes": [], "links": [], "created_at": None, "seed": None}
        
    try:
        with open(graph_file, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read social graph: {e}"
        )


@router.post("/{profile_id}/social-graph/crawl", response_model=dict[str, Any])
async def trigger_social_graph_crawl(
    profile_id: uuid.UUID,
    seed_handle: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually triggers a background social graph crawler task starting from a seed handle."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
        
    from xbot.tasks import run_graph_crawler
    run_graph_crawler.delay(str(profile_id), seed_handle)
    return {"status": "accepted", "message": f"Social graph crawl triggered for seed @{seed_handle}."}


@router.post("/{profile_id}/autoreply-mentions", response_model=dict[str, Any])
async def trigger_autoreply_mentions(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Triggers an autonomous auto-reply to mentions task for this profile."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
        
    from xbot.tasks import run_autoreply_mentions
    run_autoreply_mentions.delay(str(profile_id))
    return {"status": "accepted", "message": "Autonomous auto-reply notifications scan task triggered."}




