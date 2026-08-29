from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


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


class KOLChannel(BaseModel):
    name: str = Field(..., description="Channel slug e.g. anime_manga, movies_cinema, consumer_tech, ai_ecosystem, growth_f4f")
    display_title: str = Field(..., description="User-facing channel title")
    description: str = Field("", description="Channel focus description")
    is_active: bool = Field(True, description="Whether this channel is actively sniped")
    priority_weight: float = Field(1.0, description="Priority multiplier for queueing")
    preferred_angle: str = Field("insight", description="Default angle: contrarian, framework, witty, data, insight, debate_catalyst")


class TargetKOL(BaseModel):
    handle: str = Field(..., description="Target X handle without leading @")
    category: str = Field("general", description="Channel category: anime_manga, movies_cinema, consumer_tech, ai_ecosystem, growth_f4f, general")
    priority: str = Field("medium", description="Priority tier: high, medium, low")
    preferred_angle: str = Field(
        "insight", description="Preferred response angle: contrarian, framework, witty, data, insight, debate_catalyst"
    )
    is_active: bool = Field(True, description="Whether this target is actively monitored")


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
    kol_channels: list[KOLChannel] = Field(default_factory=list)
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
    require_post_approval: bool = False

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
