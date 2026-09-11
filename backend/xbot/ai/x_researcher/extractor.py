from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from xbot.config import settings

logger = logging.getLogger(__name__)

MEDIA_STORAGE_DIR = Path(settings.BASE_PROFILE_DIR).parent / "media" / "threads"
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
    Downloads authentic images attached to high-engagement tweets on X.
    Upgrades twimg URLs to large resolution and validates image dimensions.
    """
    downloaded: list[DownloadedMedia] = []
    seen_urls: set[str] = set()

    clean_slug = re.sub(r"[^\w]+", "_", topic_slug.lower()).strip("_")[:25] or "x_media"
    MEDIA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for tw in tweets:
            if len(downloaded) >= max_images:
                break
            for raw_url in tw.media_urls:
                if not raw_url or raw_url in seen_urls:
                    continue
                seen_urls.add(raw_url)

                # Upgrade twimg URL to large format
                img_url = raw_url
                if "pbs.twimg.com" in img_url:
                    if "name=" in img_url:
                        img_url = re.sub(r"name=[a-zA-Z0-9_]+", "name=large", img_url)
                    else:
                        img_url = f"{img_url}&name=large" if "?" in img_url else f"{img_url}?name=large"

                try:
                    resp = await client.get(
                        img_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                    )
                    if resp.status_code == 200 and len(resp.content) >= 15000:
                        url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                        ext = ".png" if ".png" in img_url.lower() else ".jpg"
                        target_path = MEDIA_STORAGE_DIR / f"{clean_slug}_{url_hash}{ext}"
                        target_path.write_bytes(resp.content)

                        # Optional PIL dimension verification
                        try:
                            from PIL import Image
                            import io
                            with Image.open(io.BytesIO(resp.content)) as im:
                                w, h = im.size
                                if w < 300 or h < 300:
                                    if target_path.exists():
                                        target_path.unlink()
                                    continue
                        except Exception:
                            pass

                        downloaded.append(
                            DownloadedMedia(
                                local_path=str(target_path),
                                source_url=img_url,
                                caption=tw.text[:120],
                                author_handle=tw.handle,
                            )
                        )
                        logger.info("Successfully downloaded authentic X media: %s from @%s", target_path.name, tw.handle)
                        if len(downloaded) >= max_images:
                            break
                except Exception as dl_err:
                    logger.debug("Failed downloading X media %s: %s", img_url, dl_err)

    return downloaded
