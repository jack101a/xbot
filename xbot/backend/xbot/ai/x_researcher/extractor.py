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
    Downloads the top high-res images from viral tweets to the local media folder
    `data/media/threads/{topic_slug}/` for dashboard preview and tweet attachment.
    """
    downloaded: list[DownloadedMedia] = []
    target_dir = MEDIA_STORAGE_DIR / topic_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    seen_urls: set[str] = set()

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for tw in tweets:
            if len(downloaded) >= max_images:
                break
            for img_url in tw.media_urls:
                if len(downloaded) >= max_images:
                    break
                if img_url in seen_urls:
                    continue
                seen_urls.add(img_url)

                try:
                    clean_url = img_url
                    if "name=" in clean_url:
                        clean_url = re.sub(r"name=\w+", "name=large", clean_url)

                    url_hash = hashlib.md5(clean_url.encode()).hexdigest()[:8]
                    ext = ".jpg"
                    if "format=png" in clean_url or ".png" in clean_url:
                        ext = ".png"
                    elif "format=webp" in clean_url or ".webp" in clean_url:
                        ext = ".webp"

                    file_name = f"{topic_slug}_{url_hash}{ext}"
                    local_file = target_dir / file_name

                    resp = await client.get(clean_url)
                    if resp.status_code == 200 and len(resp.content) > 1024:
                        with open(local_file, "wb") as f:
                            f.write(resp.content)

                        caption = tw.text[:120].replace("\n", " ")
                        downloaded.append(
                            DownloadedMedia(
                                local_path=str(local_file.resolve()),
                                source_url=clean_url,
                                caption=caption,
                                author_handle=tw.handle,
                            )
                        )
                        logger.info(
                            "Downloaded real viral media asset from X (@%s) to %s (%d bytes)",
                            tw.handle,
                            local_file,
                            len(resp.content),
                        )
                except Exception as dl_err:
                    logger.debug("Failed downloading image %s: %s", img_url, dl_err)

    return downloaded
