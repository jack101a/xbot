from __future__ import annotations

import io
from pydantic import BaseModel, Field
from ruamel.yaml import YAML
from xbot.persona.loader import Config, Persona, Strategy

# Configure ruamel.yaml for safe load/dump
yaml = YAML(typ="safe")
yaml.default_flow_style = False


def format_persona_sheet(persona: Persona) -> str:
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

    lines.extend([
        "",
        "## 🚫 GLOBAL SYSTEM-WIDE SAFETY DIRECTIVE (MANDATORY ACROSS ALL PERSONAS & ACCOUNTS)",
        "- ABSOLUTE ZERO TOLERANCE FOR INDIAN POLITICS: You are STRICTLY FORBIDDEN from discussing, mentioning, debating, liking, quoting, or joking about ANY Indian political parties, politicians, elections, policies, or controversies (STRICTLY BANNED: BJP, Congress, AAP, Modi, Narendra Modi, Rahul Gandhi, Kejriwal, Amit Shah, Yogi, Hindutva, RSS, Lok Sabha, Indian government). This applies globally to all personas, tools, and actions without exception.",
    ])

    return "\n".join(lines)


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
    blue_tick_candidates_summary: str = Field(
        "No queued candidates.", description="High-reciprocity Blue Tick candidates queued for following"
    )
    recent_content_summary: str = Field(
        "No recent posts.", description="Recently created posts and drafts to prevent duplication"
    )
    analytics_summary: str = Field(
        ..., description="Performance summary of the last 7 days"
    )

    def render_user_prompt(self, feed_snapshot_str: str | None = None) -> str:
        """
        Renders the user prompt context for session planning.
        """
        feed_content = feed_snapshot_str or "No active feed snapshot available."
        return (
            f"## Your Current State\n"
            f"- Local Time: {self.current_time}\n"
            f"- Account age: {self.account_age_days} days\n"
            f"- Followers: {self.followers_count} | Following: {self.following_count}\n"
            f"- Today's actions so far:\n{self.today_actions_summary}\n\n"
            f"## 📜 Recently Created Posts & Drafts (DO NOT DUPLICATE)\n"
            f"{self.recent_content_summary}\n\n"
            f"## High-Reciprocity Blue Tick Follow Candidates (Queue)\n"
            f"{self.blue_tick_candidates_summary}\n\n"
            f"## Your Active Memories\n"
            f"{self.active_memories}\n\n"
            f"## Your Strategy\n"
            f"```yaml\n"
            f"{self._render_strategy_yaml()}\n"
            f"```\n\n"
            f"## Current Feed Snapshot\n"
            f"{feed_content}"
        )

    def _render_strategy_yaml(self) -> str:
        """Helper to dump Strategy model to YAML string."""
        buf = io.StringIO()
        yaml.dump(self.strategy.model_dump(), buf)
        return buf.getvalue().strip()
