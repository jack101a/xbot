from __future__ import annotations

import logging
from pathlib import Path

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

# Configure ruamel.yaml for safe load/dump
yaml = YAML(typ="safe")
yaml.default_flow_style = False


class Identity(BaseModel):
    age: int | None = None
    location: str | None = None
    occupation: str | None = None
    education: str | None = None
    background: str


class Personality(BaseModel):
    traits: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    communication_style: str


class Interests(BaseModel):
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)
    will_not_discuss: list[str] = Field(default_factory=list)


class WritingStyle(BaseModel):
    tone: str
    typical_length: str
    formatting: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class Goals(BaseModel):
    short_term: list[str] = Field(default_factory=list)
    long_term: list[str] = Field(default_factory=list)
    content_pillars: list[str] = Field(default_factory=list)


class Rules(BaseModel):
    always: list[str] = Field(default_factory=list)
    never: list[str] = Field(default_factory=list)


class TargetKOL(BaseModel):
    handle: str = Field(..., description="Target X handle without leading @")
    category: str = Field("general", description="Niche or industry category")
    priority: str = Field("medium", description="Priority tier: high, medium, low")
    preferred_angle: str = Field(
        "insight", description="Preferred response angle: contrarian, framework, witty, data, insight"
    )


class Persona(BaseModel):
    id: str
    display_name: str
    x_handle: str
    identity: Identity
    personality: Personality
    interests: Interests
    writing_style: WritingStyle
    goals: Goals
    rules: Rules
    target_kols: list[TargetKOL] = Field(default_factory=list)
    system_prompt: str | None = None
    tone_prompt: str | None = None
    raw_character_card: Any = None

    model_config = ConfigDict(extra="allow")


class ScheduleConfig(BaseModel):
    timezone: str = "America/New_York"
    active_hours: str = "08:00-22:00"
    min_sessions_per_day: int = 3
    max_sessions_per_day: int = 5
    interval_minutes: int = 45


class LimitsConfig(BaseModel):
    max_likes_per_day: int = 50
    max_replies_per_day: int = 15
    max_posts_per_day: int = 5
    max_follows_per_day: int = 10
    warmup_enabled: bool = False
    cooldown_seconds: int = 15
    safety_mode: str = "normal"

    model_config = ConfigDict(extra="allow")


class CredentialsConfig(BaseModel):
    password_encrypted: str | None = None
    email: str | None = None
    two_factor_secret_encrypted: str | None = None


class Config(BaseModel):
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    proxy_url: str | None = None
    credentials: CredentialsConfig | None = None
    mock_mode: bool = False

    model_config = ConfigDict(extra="ignore")


class FocusConfig(BaseModel):
    primary: str
    secondary: str | None = None


class ContentStrategyConfig(BaseModel):
    posting_frequency: str
    best_times: list[str] = Field(default_factory=list)
    top_performing_topics: list[str] = Field(default_factory=list)
    underperforming_topics: list[str] = Field(default_factory=list)


class EngagementTargets(BaseModel):
    likes: str
    replies: str
    follows: str


class EngagementStrategyConfig(BaseModel):
    daily_targets: EngagementTargets
    priority_accounts: list[str] = Field(default_factory=list)


class Strategy(BaseModel):
    last_updated: str
    review_period: str = "weekly"
    current_focus: FocusConfig
    content_strategy: ContentStrategyConfig
    engagement_strategy: EngagementStrategyConfig
    growth_observations: list[str] = Field(default_factory=list)
    adjustments: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class AccountRelationship(BaseModel):
    display_name: str
    first_seen: str
    relationship: str
    sentiment: str = "neutral"
    interaction_count: int = 0
    last_interaction: str | None = None
    notes: str | None = None


class Relationships(BaseModel):
    accounts: dict[str, AccountRelationship] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")



class LearnedCharacteristics(BaseModel):
    behavioral_adaptations: list[str] = Field(default_factory=list)


class LearnedPersonality(BaseModel):
    evolving_nuances: list[str] = Field(default_factory=list)


class LearnedHabits(BaseModel):
    learned_writing_patterns: list[str] = Field(default_factory=list)
    engagement_tactics: list[str] = Field(default_factory=list)


class LearnedInterests(BaseModel):
    emerging_topics: list[str] = Field(default_factory=list)
    decaying_topics: list[str] = Field(default_factory=list)


class LearnedLikes(BaseModel):
    content_preferences: list[str] = Field(default_factory=list)
    author_archetypes: list[str] = Field(default_factory=list)


class LearnedDislikes(BaseModel):
    learned_taboos: list[str] = Field(default_factory=list)


class LearnedState(BaseModel):
    last_reflected_at: str | None = None
    reflection_count: int = 0
    characteristics: LearnedCharacteristics = Field(default_factory=LearnedCharacteristics)
    personality: LearnedPersonality = Field(default_factory=LearnedPersonality)
    habits: LearnedHabits = Field(default_factory=LearnedHabits)
    interests: LearnedInterests = Field(default_factory=LearnedInterests)
    likes: LearnedLikes = Field(default_factory=LearnedLikes)
    dislikes: LearnedDislikes = Field(default_factory=LearnedDislikes)

    model_config = ConfigDict(extra="ignore")


def load_persona(profile_dir: Path) -> Persona:
    """Loads persona.yaml from the given profile directory or direct file path."""
    if profile_dir.is_file() or str(profile_dir).endswith(".yaml") or str(profile_dir).endswith(".yml"):
        path = profile_dir
    else:
        path = profile_dir / "persona.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    return Persona.model_validate(data)


def load_config(profile_dir: Path) -> Config:
    """Loads config.yaml from the given profile directory."""
    path = profile_dir / "config.yaml"
    if not path.exists():
        # Fall back to default config if it doesn't exist
        return Config()
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    return Config.model_validate(data)


def save_config(profile_dir: Path, config: Config) -> None:
    """Saves config.yaml to the given profile directory."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / "config.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f)


def load_strategy(profile_dir: Path) -> Strategy:
    """Loads strategy.yaml from the given profile directory."""
    path = profile_dir / "strategy.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    return Strategy.model_validate(data)


def load_relationships(profile_dir: Path) -> Relationships:
    """Loads known_accounts.yaml from the relationships subdirectory."""
    path = profile_dir / "relationships" / "known_accounts.yaml"
    if not path.exists():
        return Relationships()
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    if not data:
        return Relationships()
    return Relationships.model_validate(data)


def save_strategy(profile_dir: Path, strategy: Strategy) -> None:
    """Saves strategy.yaml to the given profile directory."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / "strategy.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(strategy.model_dump(), f)


def save_relationships(profile_dir: Path, relationships: Relationships) -> None:
    """Saves known_accounts.yaml to the relationships subdirectory."""
    rel_dir = profile_dir / "relationships"
    rel_dir.mkdir(parents=True, exist_ok=True)
    path = rel_dir / "known_accounts.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(relationships.model_dump(), f)


def load_learned_state(profile_dir: Path) -> LearnedState:
    """Loads learned_state.yaml from the given profile directory."""
    path = profile_dir / "learned_state.yaml"
    if not path.exists():
        return LearnedState()
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    if not data:
        return LearnedState()
    return LearnedState.model_validate(data)


def save_learned_state(profile_dir: Path, state: LearnedState) -> None:
    """Saves learned_state.yaml to the given profile directory."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / "learned_state.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(state.model_dump(), f)
