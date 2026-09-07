from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.content import Content
from xbot.models.follow_growth import FollowCandidate
from xbot.models.profile import RateLimit
from xbot.models.session import Action
from xbot.persona import DiaryManager, MemoryManager, Relationships


async def get_latest_followers_and_following(
    db: AsyncSession, profile_id: int
) -> tuple[int, int]:
    stmt_snap = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(1)
    )
    res_snap = await db.execute(stmt_snap)
    latest_snap = res_snap.scalar_one_or_none()
    followers = latest_snap.followers if latest_snap else 0
    following = latest_snap.following if latest_snap else 0
    return followers, following


async def build_today_actions_summary(
    db: AsyncSession, profile_id: int, midnight_utc: datetime.datetime, tz: ZoneInfo
) -> str:
    stmt_actions = (
        select(Action)
        .where(Action.profile_id == profile_id, Action.executed_at >= midnight_utc)
        .order_by(Action.executed_at.desc())
    )
    res_actions = await db.execute(stmt_actions)
    actions_today = res_actions.scalars().all()

    if not actions_today:
        return "None"

    counts = {}
    for a in actions_today:
        atype = a.action_type.lower()
        counts[atype] = counts.get(atype, 0) + 1

    summary_part = ", ".join(f"{v} {k}s" for k, v in counts.items())
    recent_parts = []
    for a in actions_today[:3]:
        act_local = a.executed_at.replace(tzinfo=datetime.timezone.utc).astimezone(tz).strftime("%I:%M %p")
        raw_val = (a.content or a.target_url or "").strip()
        snippet = (raw_val[:40] + "...") if len(raw_val) > 40 else raw_val
        if snippet:
            recent_parts.append(f"[{act_local}] {a.action_type.upper()} ({snippet})")
        else:
            recent_parts.append(f"[{act_local}] {a.action_type.upper()}")

    return f"Completed today: {summary_part}. Recent: {'; '.join(recent_parts)}"


async def build_rate_budget_summary(
    db: AsyncSession, profile_id: int, limits_config: Any
) -> str:
    stmt_limits = select(RateLimit).where(RateLimit.profile_id == profile_id)
    res_limits = await db.execute(stmt_limits)
    limits_db = res_limits.scalars().all()
    counts_today = {lim.action_type: lim.count_today for lim in limits_db}

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
    return "\n".join(budget_lines)


def build_recent_diary_summary(profile_dir: Path) -> str:
    diary_mgr = DiaryManager(profile_dir)
    diary_entries = diary_mgr.get_recent_entries(limit=3)
    if not diary_entries:
        return "No recent diary entries."

    diary_lines = []
    for entry in diary_entries:
        diary_lines.append(f"### Date: {entry['date']}\n{entry['content']}")
    return "\n\n".join(diary_lines).strip()


def build_active_memories_summary(
    profile_dir: Path,
    mention_query: str | None = None,
    token_budget: int = 400,
) -> str:
    memory_mgr = MemoryManager(profile_dir)
    memories = memory_mgr.retrieve_memories(
        mention_query=mention_query, token_budget=token_budget
    )
    if not memories:
        return "No active memories."

    memory_lines = []
    for m in memories[:4]:
        m_type = m.get("type", "important")
        content = m.get("content") or m.get("fact") or m.get("event") or ""
        if content:
            memory_lines.append(f"- ({m_type}) {content}")
    return "\n".join(memory_lines) if memory_lines else "No active memories."


def build_relationships_summary(relationships: Relationships) -> str:
    sorted_accounts = sorted(
        relationships.accounts.items(),
        key=lambda x: x[1].interaction_count,
        reverse=True,
    )
    if not sorted_accounts:
        return "No registered relationships yet."

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
    return "\n".join(rel_lines)


async def build_blue_tick_candidates_summary(
    db: AsyncSession, profile_id: int
) -> str:
    stmt_cand = (
        select(FollowCandidate)
        .where(FollowCandidate.profile_id == profile_id)
        .where(FollowCandidate.status == "discovered")
        .order_by(FollowCandidate.reciprocity_score.desc())
        .limit(6)
    )
    res_cand = await db.execute(stmt_cand)
    cand_list = res_cand.scalars().all()
    if not cand_list:
        return "No queued candidates available."

    cand_lines = []
    for c in cand_list:
        cand_lines.append(
            f"- @{c.handle} ({c.display_name or 'Peer'}): Niche: {c.niche} | "
            f"Reciprocity Score: {c.reciprocity_score:.0f}% | "
            f"Followers: {c.follower_count} | Source: {c.source_discussion or 'Community'}"
        )
    return "\n".join(cand_lines)


async def build_analytics_summary(db: AsyncSession, profile_id: int) -> str:
    stmt_snaps_7d = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.snapshot_date.desc())
        .limit(7)
    )
    res_snaps_7d = await db.execute(stmt_snaps_7d)
    snapshots_7d = res_snaps_7d.scalars().all()

    if not snapshots_7d:
        return "No recent analytics snapshots available."

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
    return "\n".join(analytics_lines)


async def build_recent_content_summary(
    db: AsyncSession, profile_id: int
) -> str:
    stmt_content = (
        select(Content)
        .where(Content.profile_id == profile_id)
        .order_by(Content.created_at.desc())
        .limit(15)
    )
    res_content = await db.execute(stmt_content)
    recent_content_items = res_content.scalars().all()

    cutoff_recent = datetime.datetime.utcnow() - datetime.timedelta(days=3)
    stmt_recent_actions = (
        select(Action)
        .where(
            Action.profile_id == profile_id,
            Action.content.isnot(None),
            Action.executed_at >= cutoff_recent,
        )
        .order_by(Action.executed_at.desc())
        .limit(20)
    )
    res_recent_actions = await db.execute(stmt_recent_actions)
    recent_action_items = res_recent_actions.scalars().all()

    c_lines = []
    seen_bodies = set()

    for item in recent_content_items:
        dt_str = item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else "recent"
        c_body = " ".join(item.body.split()).strip()
        if c_body.lower() not in seen_bodies:
            seen_bodies.add(c_body.lower())
            snippet = c_body if len(c_body) <= 100 else c_body[:97] + "..."
            c_lines.append(f"- [{item.status.value.upper()} {dt_str} ({item.content_type.value})]: \"{snippet}\"")

    for act in recent_action_items:
        if act.content:
            c_body = " ".join(act.content.split()).strip()
            if c_body.lower() not in seen_bodies:
                seen_bodies.add(c_body.lower())
                dt_str = act.executed_at.strftime("%Y-%m-%d %H:%M") if act.executed_at else "today"
                snippet = c_body if len(c_body) <= 100 else c_body[:97] + "..."
                target_info = f" -> {act.target_url}" if act.target_url else ""
                c_lines.append(f"- [EXECUTED_{act.action_type.upper()} {dt_str}{target_info}]: \"{snippet}\"")

    return "\n".join(c_lines) if c_lines else "No recent posts or drafts recorded."
