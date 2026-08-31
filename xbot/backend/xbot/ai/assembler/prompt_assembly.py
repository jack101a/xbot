from __future__ import annotations

import io
from pydantic import BaseModel, Field
from ruamel.yaml import YAML
from xbot.persona.loader import Config, Persona, Strategy

# Configure ruamel.yaml for safe load/dump
yaml = YAML(typ="safe")
yaml.default_flow_style = False


def format_persona_sheet(persona: Persona) -> str:
    """Helper to format the Persona into a sharp, lean Creator Capsule (<120 words)."""
    traits = ", ".join(persona.personality.traits[:4]) if persona.personality.traits else "witty, tech-literate"
    pillars = ", ".join(persona.goals.content_pillars[:4]) if persona.goals.content_pillars else "Tech, Cinema, AI"
    examples = persona.writing_style.examples[:3] if persona.writing_style.examples else []

    lines = [
        f"You are {persona.display_name} (@{persona.x_handle.lstrip('@')}), an authentic creator on X.",
        f"VOICE & TONE: {persona.writing_style.tone or 'Sharp, self-aware wit, conversational, tech-literate'}.",
        f"CORE TRAITS: {traits}.",
        f"CONTENT PILLARS: {pillars}.",
        "",
        "REPRESENTATIVE VOICE EXAMPLES:",
    ]
    for ex in examples:
        lines.append(f"- \"{ex}\"")

    lines.extend([
        "",
        "CRITICAL RULES:",
        "- Double-spacing between lines (\\n\\n) for mobile pacing.",
        "- No corporate AI buzzwords (delve, tapestry, supercharge, beacon).",
        "- Strictly 0 hashtags in replies. Max 1-2 authentic hashtags in standalone posts.",
        "- Strictly 0 Indian political commentary.",
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
        Renders the concise user prompt context for session planning.
        """
        feed_content = feed_snapshot_str or "No active feed snapshot available."
        return (
            f"## Session Context ({self.current_time})\n"
            f"- Daily Activity: {self.today_actions_summary}\n\n"
            f"## 📜 Recent Posts (DO NOT REPEAT TOPICS):\n"
            f"{self.recent_content_summary}\n\n"
            f"## Active Creator Memories:\n"
            f"{self.active_memories}\n\n"
            f"## Live Feed Opportunities & Trends:\n"
            f"{feed_content}"
        )

    def _render_strategy_yaml(self) -> str:
        """Helper to dump Strategy model to YAML string."""
        buf = io.StringIO()
        yaml.dump(self.strategy.model_dump(), buf)
        return buf.getvalue().strip()
