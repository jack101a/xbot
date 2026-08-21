from __future__ import annotations

import datetime
import io
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from ruamel.yaml import YAML
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.content import Content, ContentStatus
from xbot.models.profile import Profile
from xbot.models.session import Action, ActionStatus, ActionType
from xbot.persona import load_persona, load_relationships, load_strategy, save_strategy
from xbot.persona.loader import Strategy

logger = logging.getLogger(__name__)

# Configure ruamel.yaml for safe load/dump
yaml = YAML(typ="safe")
yaml.default_flow_style = False


class StrategyResponse(BaseModel):
    strategy: Strategy


class StrategyReviewer:
    """
    Implements Phase 2.6 Weekly Strategy Review Logic.
    Queries database performance metrics, content analytics, and engagement counts,
    and calls the primary LLM to formulate an updated Strategy model.
    Saves the updated strategy back to the profile's strategy.yaml file.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)

    async def review_strategy(
        self,
        db: AsyncSession,
        profile_slug: str,
        now_utc: datetime.datetime | None = None,
    ) -> Strategy:
        """Runs the weekly strategic analysis and updates strategy.yaml."""
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        # 1. Fetch Profile
        stmt_profile = select(Profile).where(Profile.profile_slug == profile_slug)
        res_profile = await db.execute(stmt_profile)
        profile = res_profile.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile with slug '{profile_slug}' not found.")

        profile_dir = self.base_profile_dir / profile_slug
        persona = load_persona(profile_dir)
        current_strategy = load_strategy(profile_dir)
        relationships = load_relationships(profile_dir)

        # 2. Gather Performance Data
        # A. Analytics snapshots (last 14 days)
        stmt_snaps = (
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.profile_id == profile.id)
            .order_by(AnalyticsSnapshot.snapshot_date.desc())
            .limit(14)
        )
        res_snaps = await db.execute(stmt_snaps)
        snaps = sorted(res_snaps.scalars().all(), key=lambda x: x.snapshot_date)
        snap_lines = []
        for s in snaps:
            snap_lines.append(
                f"- [{s.snapshot_date}] Followers: {s.followers} | Following: {s.following} | "
                f"Impressions 24h: {s.impressions_24h} | Engagements 24h: {s.engagements_24h} | "
                f"Engagement Rate: {s.engagement_rate:.2%}"
            )
        snaps_summary = "\n".join(snap_lines) if snap_lines else "No analytics snapshots available."

        # B. Last 50 Posts and Performance
        stmt_posts = (
            select(Content)
            .where(
                Content.profile_id == profile.id,
                Content.status == ContentStatus.POSTED,
            )
            .order_by(Content.posted_at.desc())
            .limit(50)
        )
        res_posts = await db.execute(stmt_posts)
        posts = res_posts.scalars().all()
        post_lines = []
        for p in posts:
            perf = p.performance or {}
            likes = perf.get("likes", 0)
            retweets = perf.get("retweets", 0)
            replies = perf.get("replies", 0)
            views = perf.get("views", 0)
            post_lines.append(
                f"- Post: \"{p.body}\" | Posted At: {p.posted_at}\n"
                f"  Metrics: {likes} Likes, {retweets} Retweets, {replies} Replies, {views} Views"
            )
        posts_summary = "\n".join(post_lines) if post_lines else "No posted content available."

        # C. Engagement actual counts in the last 7 days
        seven_days_ago = now_utc - datetime.timedelta(days=7)
        stmt_actions = select(Action).where(
            Action.profile_id == profile.id,
            Action.status == ActionStatus.COMPLETED,
            Action.executed_at >= seven_days_ago,
        )
        res_actions = await db.execute(stmt_actions)
        actions_7d = res_actions.scalars().all()

        action_counts = {"like": 0, "reply": 0, "follow": 0}
        for act in actions_7d:
            if act.action_type in ("like", "reply", "follow"):
                action_counts[act.action_type] += 1

        targets_comparison = (
            f"Actual Actions Completed in the Last 7 Days:\n"
            f"- Likes: {action_counts['like']} (vs Strategy Daily Target: {current_strategy.engagement_strategy.daily_targets.likes})\n"
            f"- Replies: {action_counts['reply']} (vs Strategy Daily Target: {current_strategy.engagement_strategy.daily_targets.replies})\n"
            f"- Follows: {action_counts['follow']} (vs Strategy Daily Target: {current_strategy.engagement_strategy.daily_targets.follows})"
        )

        # 3. Format inputs for LLM
        buf = io.StringIO()
        yaml.dump(current_strategy.model_dump(), buf)
        strategy_yaml_str = buf.getvalue().strip()

        # 4. Construct LLM prompts
        system_prompt = (
            f"You are the strategic advisor for {persona.display_name} (@{persona.x_handle}).\n"
            "Your job is to review the account performance, strategy execution, and content engagement of the past week, "
            "and adjust the growth strategy document strategy.yaml for the upcoming week.\n"
            "Remain completely aligned with the character's core identity, goals, and interests."
        )

        user_prompt = (
            f"=== CHARACTER PROFILE ===\n"
            f"Display Name: {persona.display_name} | Handle: @{persona.x_handle}\n"
            f"Background: {persona.identity.background}\n"
            f"Traits: {', '.join(persona.personality.traits)}\n"
            f"Primary Interests: {', '.join(persona.interests.primary)}\n"
            f"Content Pillars: {', '.join(persona.goals.content_pillars)}\n\n"
            f"=== CURRENT STRATEGY DOCUMENT ===\n"
            f"```yaml\n{strategy_yaml_str}\n```\n\n"
            f"=== PERFORMANCE LOGS (LAST 14 DAYS) ===\n"
            f"{snaps_summary}\n\n"
            f"=== POSTED CONTENT ANALYTICS ===\n"
            f"{posts_summary}\n\n"
            f"=== TARGETS EXECUTION (LAST 7 DAYS) ===\n"
            f"{targets_comparison}\n\n"
            f"=== INSTRUCTIONS ===\n"
            f"Analyze what topics and formats are performing best vs underperforming.\n"
            f"Update the strategy document. Set the 'last_updated' field to the current date: '{now_utc.strftime('%Y-%m-%d')}'.\n"
            "Return a JSON object conforming exactly to this schema:\n"
            "{\n"
            "  \"strategy\": {\n"
            "    \"last_updated\": \"YYYY-MM-DD\",\n"
            "    \"review_period\": \"weekly\",\n"
            "    \"current_focus\": {\n"
            "      \"primary\": \"updated primary focus message\",\n"
            "      \"secondary\": \"updated secondary focus message or null\"\n"
            "    },\n"
            "    \"content_strategy\": {\n"
            "      \"posting_frequency\": \"updated frequency description\",\n"
            "      \"best_times\": [\"HH:MM\", \"HH:MM\"],\n"
            "      \"top_performing_topics\": [\"topic1\", \"topic2\"],\n"
            "      \"underperforming_topics\": [\"topic1\", \"topic2\"]\n"
            "    },\n"
            "    \"engagement_strategy\": {\n"
            "      \"daily_targets\": {\n"
            "        \"likes\": \"number as string\",\n"
            "        \"replies\": \"number as string\",\n"
            "        \"follows\": \"number as string\"\n"
            "      },\n"
            "      \"priority_accounts\": [\"@user1\", \"@user2\"]\n"
            "    },\n"
            "    \"growth_observations\": [\"observation1\", \"observation2\"],\n"
            "    \"adjustments\": [\"adjustment1\", \"adjustment2\"]\n"
            "  }\n"
            "}\n"
            "Return ONLY the valid JSON object."
        )

        client = get_ai_client()
        updated_strategy = None

        try:
            try:
                completion = await client.beta.chat.completions.parse(
                    model=settings.MODEL_TREND_ANALYSIS,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=StrategyResponse,
                )
                res_parsed = completion.choices[0].message.parsed
                if res_parsed and res_parsed.strategy:
                    updated_strategy = res_parsed.strategy
            except Exception as e:
                logger.warning("Beta chat parse for strategy failed, falling back: %s", e)
                completion = await client.chat.completions.create(
                    model=settings.MODEL_TREND_ANALYSIS,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_text = completion.choices[0].message.content or ""
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                data = json.loads(cleaned.strip())
                parsed_obj = StrategyResponse.model_validate(data)
                updated_strategy = parsed_obj.strategy
        except Exception as e:
            logger.error("Failed to generate updated strategy: %s. Using current strategy.", e)
            updated_strategy = current_strategy
            # Update date at least
            updated_strategy.last_updated = now_utc.strftime("%Y-%m-%d")

        # 5. Save Strategy back to file
        save_strategy(profile_dir, updated_strategy)
        logger.info("Weekly strategy reviewed and updated for slug %s", profile_slug)
        return updated_strategy
