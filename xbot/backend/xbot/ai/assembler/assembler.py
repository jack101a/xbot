from __future__ import annotations

import datetime
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.models.profile import Profile
from xbot.persona import (
    load_config,
    load_persona,
    load_relationships,
    load_strategy,
)
from xbot.persona.loader import Persona

from .context_builder import (
    build_active_memories_summary,
    build_analytics_summary,
    build_blue_tick_candidates_summary,
    build_rate_budget_summary,
    build_recent_content_summary,
    build_recent_diary_summary,
    build_relationships_summary,
    build_today_actions_summary,
    get_latest_followers_and_following,
)
from .prompt_assembly import AssembledContext, format_persona_sheet

logger = logging.getLogger(__name__)


class ContextAssembler:
    """
    Compiles persona profiles, configs, database rate limits, actions,
    and performance snapshots into an unified context structure for AI decisions.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)

    async def assemble(
        self,
        db: AsyncSession,
        profile_slug: str,
        now_utc: datetime.datetime | None = None,
        mention_query: str | None = None,
        token_budget: int = 4000,
    ) -> AssembledContext:
        """
        Gathers files and database records to construct an AssembledContext
        for the given profile slug.
        """
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        # 1. Fetch Profile database record
        stmt = select(Profile).where(Profile.profile_slug == profile_slug)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile with slug '{profile_slug}' not found.")

        # 2. Compute profile directories and load persona configs
        profile_dir = self.base_profile_dir / profile_slug
        if not profile_dir.exists():
            raise FileNotFoundError(
                f"Profile directory not found: {profile_dir}"
            )

        persona = load_persona(profile_dir)
        config = load_config(profile_dir)
        strategy = load_strategy(profile_dir)
        relationships = load_relationships(profile_dir)

        # 3. Format persona sheet
        persona_sheet = self._format_persona_sheet(persona)

        # 4. Form timezone and local time strings
        timezone_str = config.schedule.timezone or "America/New_York"
        try:
            tz = ZoneInfo(timezone_str)
        except Exception:
            tz = ZoneInfo("America/New_York")

        now_aware_utc = now_utc.replace(tzinfo=datetime.timezone.utc)
        local_now = now_aware_utc.astimezone(tz)
        current_time_str = local_now.strftime("%Y-%m-%d %I:%M %p")

        # 5. Account age
        created_at_naive = profile.created_at
        if created_at_naive.tzinfo is not None:
            created_at_naive = created_at_naive.replace(tzinfo=None)
        now_naive_utc = now_utc.replace(tzinfo=None)
        account_age_days = (now_naive_utc - created_at_naive).days
        if account_age_days < 0:
            account_age_days = 0

        # 6. Fetch latest follower / following counts
        followers_count, following_count = await get_latest_followers_and_following(
            db, profile.id
        )

        # 7. Today's actions so far
        local_midnight = local_now.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        midnight_utc = local_midnight.astimezone(datetime.timezone.utc).replace(
            tzinfo=None
        )
        actions_summary = await build_today_actions_summary(
            db, profile.id, midnight_utc, tz
        )

        # 8. Rate limits & budget remaining
        rate_budget_remaining = await build_rate_budget_summary(
            db, profile.id, config.limits
        )

        # 9. Recent diary entries
        recent_diary_entries = build_recent_diary_summary(profile_dir)

        # 10. Active memories
        active_memories = build_active_memories_summary(
            profile_dir, mention_query=mention_query, token_budget=token_budget
        )

        # 11. Relationships
        relationships_summary = build_relationships_summary(relationships)

        # 11b. High-Reciprocity Blue Tick Candidates Queue
        blue_tick_candidates_summary = await build_blue_tick_candidates_summary(
            db, profile.id
        )

        # 12. Analytics snapshots last 7 days
        analytics_summary = await build_analytics_summary(db, profile.id)

        # 11c. Recent Content for Anti-Duplication
        recent_content_summary = await build_recent_content_summary(
            db, profile.id
        )

        return AssembledContext(
            persona=persona,
            strategy=strategy,
            config=config,
            persona_sheet=persona_sheet,
            current_time=current_time_str,
            account_age_days=account_age_days,
            followers_count=followers_count,
            following_count=following_count,
            today_actions_summary=actions_summary,
            rate_budget_remaining=rate_budget_remaining,
            recent_diary_entries=recent_diary_entries,
            active_memories=active_memories,
            relationships_summary=relationships_summary,
            blue_tick_candidates_summary=blue_tick_candidates_summary,
            recent_content_summary=recent_content_summary,
            analytics_summary=analytics_summary,
        )

    def _format_persona_sheet(self, persona: Persona) -> str:
        """Helper to format the Persona object into a markdown character sheet."""
        return format_persona_sheet(persona)
