from __future__ import annotations

import datetime
import io
import logging
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from ruamel.yaml import YAML
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.profile import Profile, RateLimit
from xbot.models.session import Action
from xbot.persona import (
    DiaryManager,
    MemoryManager,
    load_config,
    load_persona,
    load_relationships,
    load_strategy,
)
from xbot.persona.loader import Config, Persona, Strategy

logger = logging.getLogger(__name__)

# Configure ruamel.yaml for safe load/dump
yaml = YAML(typ="safe")
yaml.default_flow_style = False


class AssembledContext(BaseModel):
    # Persona & Profile Configs
    persona: Persona = Field(..., description="The loaded Persona configuration")
    strategy: Strategy = Field(..., description="The current strategy document")
    config: Config = Field(..., description="The loaded profile config")

    # Rendered Strings for Prompts
    persona_sheet: str = Field(
        ..., description="Formatted persona sheet for system prompt"
    )
    current_time: str = Field(
        ..., description="Formatted local current time (e.g. YYYY-MM-DD hh:mm AM/PM)"
    )
    account_age_days: int = Field(..., description="Age of the account in days")
    followers_count: int = Field(
        0, description="Follower count from latest analytics snapshot"
    )
    following_count: int = Field(
        0, description="Following count from latest analytics snapshot"
    )

    # State & Summaries
    today_actions_summary: str = Field(
        ..., description="Formatted summary of actions taken today so far"
    )
    rate_budget_remaining: str = Field(
        ..., description="Breakdown of remaining rate limits/budgets"
    )
    recent_diary_entries: str = Field(
        ..., description="Last 3 diary entries formatted as markdown"
    )
    active_memories: str = Field(
        ..., description="List of active memories filtered and budget-capped"
    )
    relationships_summary: str = Field(
        ..., description="Top 10 relationships sorted by interaction count"
    )
    analytics_summary: str = Field(
        ..., description="Performance summary of the last 7 days"
    )

    def render_user_prompt(self, feed_snapshot_str: str | None = None) -> str:
        """
        Renders the user prompt context following the structure defined in
        MASTER_PLAN.md Section 5.3.
        """
        feed_content = feed_snapshot_str or "No active feed snapshot available."
        return (
            f"## Your Current State\n"
            f"- Current time: {self.current_time}\n"
            f"- Account age: {self.account_age_days} days\n"
            f"- Followers: {self.followers_count} | Following: {self.following_count}\n"
            f"- Today's actions so far:\n{self.today_actions_summary}\n"
            f"- Rate budget remaining:\n{self.rate_budget_remaining}\n\n"
            f"## Your Recent Diary\n"
            f"{self.recent_diary_entries}\n\n"
            f"## Your Active Memories\n"
            f"{self.active_memories}\n\n"
            f"## Your Relationships\n"
            f"{self.relationships_summary}\n\n"
            f"## Your Strategy\n"
            f"```yaml\n"
            f"{self._render_strategy_yaml()}\n"
            f"```\n\n"
            f"## Your Performance (Last 7 Days)\n"
            f"{self.analytics_summary}\n\n"
            f"## Current Feed Snapshot\n"
            f"{feed_content}"
        )

    def _render_strategy_yaml(self) -> str:
        """Helper to dump Strategy model to YAML string."""
        buf = io.StringIO()
        yaml.dump(self.strategy.model_dump(), buf)
        return buf.getvalue().strip()


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

        # Convert naive now_utc to aware local
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
        stmt_snap = (
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.profile_id == profile.id)
            .order_by(AnalyticsSnapshot.captured_at.desc())
            .limit(1)
        )
        res_snap = await db.execute(stmt_snap)
        latest_snap = res_snap.scalar_one_or_none()
        followers_count = latest_snap.followers if latest_snap else 0
        following_count = latest_snap.following if latest_snap else 0

        # 7. Today's actions so far
        # Calculate midnight local in UTC timezone
        local_midnight = local_now.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        midnight_utc = local_midnight.astimezone(datetime.timezone.utc).replace(
            tzinfo=None
        )

        stmt_actions = (
            select(Action)
            .where(
                Action.profile_id == profile.id, Action.executed_at >= midnight_utc
            )
            .order_by(Action.executed_at.asc())
        )
        res_actions = await db.execute(stmt_actions)
        actions_today = res_actions.scalars().all()

        if not actions_today:
            actions_summary = "  None"
        else:
            action_lines = []
            for action in actions_today:
                assert action.executed_at is not None
                act_local = (
                    action.executed_at.replace(tzinfo=datetime.timezone.utc)
                    .astimezone(tz)
                    .strftime("%I:%M %p")
                )
                line = f"  - [{act_local}] {action.action_type.upper()}"
                if action.target_url:
                    line += f" target: {action.target_url}"
                if action.content:
                    snippet = (
                        action.content
                        if len(action.content) <= 60
                        else action.content[:57] + "..."
                    )
                    line += f" content: '{snippet}'"
                line += f" ({action.status})"
                action_lines.append(line)
            actions_summary = "\n".join(action_lines)

        # 8. Rate limits & budget remaining
        stmt_limits = select(RateLimit).where(RateLimit.profile_id == profile.id)
        res_limits = await db.execute(stmt_limits)
        limits_db = res_limits.scalars().all()
        counts_today = {lim.action_type: lim.count_today for lim in limits_db}

        limits_config = config.limits
        budget = {
            "like": {
                "limit": limits_config.max_likes_per_day,
                "used": counts_today.get("like", 0),
            },
            "reply": {
                "limit": limits_config.max_replies_per_day,
                "used": counts_today.get("reply", 0),
            },
            "post": {
                "limit": limits_config.max_posts_per_day,
                "used": counts_today.get("post", 0),
            },
            "follow": {
                "limit": limits_config.max_follows_per_day,
                "used": counts_today.get("follow", 0),
            },
        }

        budget_lines = []
        for action_name, info in budget.items():
            remaining = max(0, info["limit"] - info["used"])
            budget_lines.append(
                f"  - {action_name.upper()}: {remaining} remaining "
                f"({info['used']}/{info['limit']} used today)"
            )
        rate_budget_remaining = "\n".join(budget_lines)

        # 9. Recent diary entries
        diary_mgr = DiaryManager(profile_dir)
        diary_entries = diary_mgr.get_recent_entries(limit=3)
        if not diary_entries:
            recent_diary_entries = "No recent diary entries."
        else:
            diary_lines = []
            for entry in diary_entries:
                diary_lines.append(
                    f"### Date: {entry['date']}\n{entry['content']}"
                )
            recent_diary_entries = "\n\n".join(diary_lines).strip()

        # 10. Active memories
        memory_mgr = MemoryManager(profile_dir)
        memories = memory_mgr.retrieve_memories(
            mention_query=mention_query, token_budget=token_budget
        )
        if not memories:
            active_memories = "No active memories retrieved."
        else:
            memory_lines = []
            for m in memories:
                ts = m.get("ts", "unknown")
                m_type = m.get("type", "unknown")
                importance = m.get("importance", 0.0)

                if m_type == "episodic":
                    event = m.get("event", "")
                    content = m.get("content", "")
                    memory_lines.append(
                        f"[{ts}] (episodic, importance: {importance}) "
                        f"Event: {event} | Content: {content}"
                    )
                elif m_type == "semantic":
                    fact = m.get("fact", "")
                    source = m.get("source", "")
                    memory_lines.append(
                        f"[{ts}] (semantic, importance: {importance}) "
                        f"Fact: {fact} | Source: {source}"
                    )
                elif m_type == "important":
                    content = m.get("content", "")
                    evidence = m.get("evidence", "")
                    memory_lines.append(
                        f"[{ts}] (important, importance: {importance}) "
                        f"Content: {content} | Evidence: {evidence}"
                    )
            active_memories = "\n".join(memory_lines)

        # 11. Relationships
        sorted_accounts = sorted(
            relationships.accounts.items(),
            key=lambda x: x[1].interaction_count,
            reverse=True,
        )
        if not sorted_accounts:
            relationships_summary = "No registered relationships yet."
        else:
            rel_lines = []
            for username, rel in sorted_accounts[:10]:
                rel_lines.append(
                    f"- @{username} ({rel.display_name}): "
                    f"Relationship: {rel.relationship} | "
                    f"Sentiment: {rel.sentiment} | "
                    f"Interactions: {rel.interaction_count} | "
                    f"Last Interaction: {rel.last_interaction or 'Never'} | "
                    f"Notes: {rel.notes or 'None'}"
                )
            relationships_summary = "\n".join(rel_lines)

        # 12. Analytics snapshots last 7 days
        stmt_snaps_7d = (
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.profile_id == profile.id)
            .order_by(AnalyticsSnapshot.snapshot_date.desc())
            .limit(7)
        )
        res_snaps_7d = await db.execute(stmt_snaps_7d)
        snapshots_7d = res_snaps_7d.scalars().all()

        if not snapshots_7d:
            analytics_summary = "No recent analytics snapshots available."
        else:
            snapshots_sorted = sorted(snapshots_7d, key=lambda x: x.snapshot_date)
            analytics_lines = []
            for snap in snapshots_sorted:
                analytics_lines.append(
                    f"- [{snap.snapshot_date}] "
                    f"Followers: {snap.followers} | "
                    f"Following: {snap.following} | "
                    f"24h Impressions: {snap.impressions_24h} | "
                    f"24h Engagements: {snap.engagements_24h} | "
                    f"Engagement Rate: {snap.engagement_rate:.2%}"
                )
            analytics_summary = "\n".join(analytics_lines)

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
            analytics_summary=analytics_summary,
        )

    def _format_persona_sheet(self, persona: Persona) -> str:
        """Helper to format the Persona object into a markdown character sheet."""
        lines = [
            f"Display Name: {persona.display_name}",
            f"X Handle: {persona.x_handle}",
            "",
            "## Identity",
            f"- Age: {persona.identity.age or 'Unknown'}",
            f"- Location: {persona.identity.location or 'Unknown'}",
            f"- Occupation: {persona.identity.occupation or 'Unknown'}",
            f"- Education: {persona.identity.education or 'Unknown'}",
            f"- Background: {persona.identity.background}",
            "",
            "## Personality",
            f"- Traits: {', '.join(persona.personality.traits)}",
            f"- Values: {', '.join(persona.personality.values)}",
            f"- Communication Style: {persona.personality.communication_style}",
            "",
            "## Interests",
            f"- Primary Interests: {', '.join(persona.interests.primary)}",
            f"- Secondary Interests: {', '.join(persona.interests.secondary)}",
            f"- Will Not Discuss: {', '.join(persona.interests.will_not_discuss)}",
            "",
            "## Writing Style",
            f"- Tone: {persona.writing_style.tone}",
            f"- Typical Length: {persona.writing_style.typical_length}",
            "- Formatting Rules:",
        ]
        for fmt in persona.writing_style.formatting:
            lines.append(f"  * {fmt}")

        lines.append("- Writing Examples:")
        for ex in persona.writing_style.examples:
            lines.append(f"  * \"{ex}\"")

        lines.extend([
            "",
            "## Goals & Content Pillars",
            "- Short Term Goals:",
        ])
        for goal in persona.goals.short_term:
            lines.append(f"  * {goal}")
        lines.append("- Long Term Goals:")
        for goal in persona.goals.long_term:
            lines.append(f"  * {goal}")
        lines.append("- Content Pillars:")
        for pillar in persona.goals.content_pillars:
            lines.append(f"  * {pillar}")

        lines.extend([
            "",
            "## Rules of Engagement",
            "- Always Do:",
        ])
        for rule in persona.rules.always:
            lines.append(f"  * {rule}")
        lines.append("- Never Do:")
        for rule in persona.rules.never:
            lines.append(f"  * {rule}")

        return "\n".join(lines)
