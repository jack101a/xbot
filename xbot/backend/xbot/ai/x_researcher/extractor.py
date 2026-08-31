from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MEDIA_STORAGE_DIR = Path("/home/ubuntu/projects/xbot/data/media/threads")
MEDIA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class ViralTweet(BaseModel):
    author: str = ""
    handle: str = ""
    verified: bool = False
    text: str = ""
    views: int = 0
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    media_urls: list[str] = Field(default_factory=list)
    media_alts: list[str] = Field(default_factory=list)
    tweet_url: str = ""
    is_thread: bool = False
    created_at: str | None = None


class DownloadedMedia(BaseModel):
    local_path: str
    source_url: str
    caption: str
    author_handle: str = ""


class TopicResearchReport(BaseModel):
    topic: str
    search_queries: list[str] = Field(default_factory=list)
    viral_tweets: list[ViralTweet] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    community_sentiment: dict[str, Any] = Field(default_factory=dict)
    top_hashtags: list[str] = Field(default_factory=list)
    top_media_urls: list[str] = Field(default_factory=list)
    downloaded_media: list[DownloadedMedia] = Field(default_factory=list)
    summary: str = ""


def _parse_engagement_number(text: str) -> int:
    """Parses raw engagement text (e.g. '12.4K', '1.2M', '534') to an integer."""
    if not text:
        return 0
    clean = text.replace(",", "").strip().upper()
    match = re.search(r"([\d\.]+)\s*([KM]?)", clean)
    if not match:
        return 0
    num_str, mult = match.groups()
    try:
        val = float(num_str)
        if mult == "K":
            return int(val * 1000)
        elif mult == "M":
            return int(val * 1000000)
        return int(val)
    except Exception:
        return 0


async def download_viral_media(
    tweets: list[ViralTweet],
    topic_slug: str,
    max_images: int = 4,
) -> list[DownloadedMedia]:
    """
    Disabled: Returns empty list to prevent downloading external images.
    """
    return []
