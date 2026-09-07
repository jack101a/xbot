from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class TrendCandidateTweet(BaseModel):
    """Represents a tweet discovered via X search for the trending topic."""
    tweet_id: str
    text: str
    url: str
    author: str = "creator"
    is_blue_tick: bool = False
    media_urls: list[str] = Field(default_factory=list)
    media_alts: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    has_video: bool = False
    is_growth_thread: bool = False


class InstantTrendCycleResult(BaseModel):
    """Summary of one execution cycle of an instant trend campaign."""
    status: str  # "success", "skipped", "completed", "error"
    campaign_id: str
    topic: str
    action_type: str = "none"  # "quote", "post", "none"
    tweet_id: str | None = None
    target_tweet_url: str | None = None
    content_posted: str | None = None
    error: str | None = None
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class CampaignCreateRequest(BaseModel):
    """API payload to initiate an instant trend growth campaign."""
    topic: str = Field(..., description="Trending keyword or event (e.g. 'Harry Potter series trailer')")
    profile_slug: str = Field(default="test_profile1", description="Profile slug executing the campaign")
    duration_hours: int = Field(default=48, ge=1, le=192, description="Active lifespan (up to 192h / 8 days)")
    interval_minutes: int = Field(default=20, ge=5, le=180, description="Minutes between cycles")
    quote_percentage: int = Field(default=70, ge=0, le=100, description="Percentage of actions that quote-tweet")
    sentiment_tone: str = Field(default="balanced", description="Tone: 'balanced', 'positive', 'negative', or 'ragebait'")
    ragebait_percentage: int = Field(default=0, ge=0, le=100, description="Percentage of takes taking spicy/ragebait angles")
