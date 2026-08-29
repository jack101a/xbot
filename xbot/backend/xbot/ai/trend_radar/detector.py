from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import email.utils
import hashlib
import logging
import re
from typing import Any
import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TrendItem(BaseModel):
    id: str = Field(..., description="Unique ID / hash of the trend item")
    title: str = Field(..., description="Headline of the story or topic")
    summary: str = Field(default="", description="Snippet or article summary")
    source_url: str = Field(..., description="URL to the source article")
    source_name: str = Field(default="RSS", description="Name of the news source")
    published_at: str | None = Field(default=None, description="ISO or raw timestamp")


def _clean_text(raw_text: str | None) -> str:
    if not raw_text:
        return ""
    clean = re.sub(r"<[^>]+>", "", raw_text)
    return re.sub(r"\s+", " ", clean).strip()


def _is_recent_timestamp(pub_str: str | None, max_age_days: int = 7) -> bool:
    """Checks if a published timestamp string is within the last `max_age_days` (default 7)."""
    if not pub_str:
        return True

    clean_dt = pub_str.strip()
    now_utc = datetime.now(timezone.utc)

    # 1. Try RFC 2822 format (e.g. "Wed, 27 Aug 2026 14:32:00 GMT")
    try:
        dt = email.utils.parsedate_to_datetime(clean_dt)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_days = (now_utc - dt).total_seconds() / 86400.0
            return age_days <= max_age_days
    except Exception:
        pass

    # 2. Try ISO format (e.g. "2026-08-27T14:32:00Z" or "2026-08-27")
    try:
        iso_clean = clean_dt.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_days = (now_utc - dt).total_seconds() / 86400.0
        return age_days <= max_age_days
    except Exception:
        pass

    return True


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _find_child_by_tags(elem: ET.Element, candidate_tags: set[str]) -> ET.Element | None:
    for child in elem:
        if _strip_ns(child.tag).lower() in candidate_tags:
            return child
    return None


def _get_child_text(elem: ET.Element, candidate_tags: set[str]) -> str:
    child = _find_child_by_tags(elem, candidate_tags)
    if child is not None and child.text:
        return _clean_text(child.text)
    return ""


def _parse_rss_item(
    item_elem: ET.Element,
    feed_title: str,
    keywords: list[str] | None = None,
    max_age_days: int = 7,
) -> TrendItem | None:
    title = _get_child_text(item_elem, {"title"})
    link = _get_child_text(item_elem, {"link"})
    if not link:
        guid_elem = _find_child_by_tags(item_elem, {"guid"})
        if guid_elem is not None and guid_elem.text and (
            guid_elem.attrib.get("isPermaLink", "true").lower() == "true"
            or guid_elem.text.startswith("http")
        ):
            link = guid_elem.text.strip()

    summary = _get_child_text(item_elem, {"description", "summary", "encoded"})
    published_at = _get_child_text(item_elem, {"pubdate", "published", "date"}) or None

    if published_at and not _is_recent_timestamp(published_at, max_age_days=max_age_days):
        logger.debug("Dropping RSS item older than %d days: %s (pub: %s)", max_age_days, title, published_at)
        return None

    if not title and not link:
        return None

    if keywords:
        clean_kw = [k.strip().lower() for k in keywords if k.strip()]
        if clean_kw:
            searchable = f"{title} {summary}".lower()
            if not any(kw in searchable for kw in clean_kw):
                return None

    raw_id = link or title
    item_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]

    return TrendItem(
        id=item_id,
        title=title or "Untitled",
        summary=summary,
        source_url=link or "",
        source_name=feed_title or "RSS",
        published_at=published_at,
    )


def _parse_atom_entry(
    entry_elem: ET.Element,
    feed_title: str,
    keywords: list[str] | None = None,
    max_age_days: int = 7,
) -> TrendItem | None:
    title = _get_child_text(entry_elem, {"title"})

    link = ""
    for child in entry_elem:
        if _strip_ns(child.tag).lower() == "link":
            href = child.attrib.get("href", "").strip()
            rel = child.attrib.get("rel", "alternate").strip()
            if href:
                if rel == "alternate" or not link:
                    link = href
            elif child.text and not link:
                link = child.text.strip()

    if not link:
        id_elem = _find_child_by_tags(entry_elem, {"id"})
        if id_elem is not None and id_elem.text and id_elem.text.startswith("http"):
            link = id_elem.text.strip()

    summary = _get_child_text(entry_elem, {"summary", "content"})
    published_at = _get_child_text(entry_elem, {"published", "updated", "date"}) or None

    if published_at and not _is_recent_timestamp(published_at, max_age_days=max_age_days):
        logger.debug("Dropping Atom item older than %d days: %s (pub: %s)", max_age_days, title, published_at)
        return None

    if not title and not link:
        return None

    if keywords:
        clean_kw = [k.strip().lower() for k in keywords if k.strip()]
        if clean_kw:
            searchable = f"{title} {summary}".lower()
            if not any(kw in searchable for kw in clean_kw):
                return None

    raw_id = link or title
    item_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]

    return TrendItem(
        id=item_id,
        title=title or "Untitled",
        summary=summary,
        source_url=link or "",
        source_name=feed_title or "RSS",
        published_at=published_at,
    )


def parse_feed_xml(
    xml_content: str,
    keywords: list[str] | None = None,
    max_items: int = 10,
    max_age_days: int = 7,
) -> list[TrendItem]:
    """Parses XML string from RSS 2.0 or Atom feeds into a list of TrendItem within max_age_days."""
    if not xml_content or not xml_content.strip():
        return []

    try:
        root = ET.fromstring(xml_content.strip())
    except ET.ParseError as e:
        logger.warning("XML parse error in RSS feed: %s", e)
        return []

    items: list[TrendItem] = []
    root_tag = _strip_ns(root.tag).lower()

    if root_tag == "feed":
        feed_title = _get_child_text(root, {"title"}) or "Atom Feed"
        for child in root:
            if _strip_ns(child.tag).lower() == "entry":
                item = _parse_atom_entry(child, feed_title, keywords, max_age_days=max_age_days)
                if item:
                    items.append(item)
                    if len(items) >= max_items:
                        break
    else:
        channel = _find_child_by_tags(root, {"channel"})
        search_root = channel if channel is not None else root
        feed_title = "RSS Feed"
        if channel is not None:
            feed_title = _get_child_text(channel, {"title"}) or "RSS"

        for child in search_root:
            if _strip_ns(child.tag).lower() == "item":
                item = _parse_rss_item(child, feed_title, keywords, max_age_days=max_age_days)
                if item:
                    items.append(item)
                    if len(items) >= max_items:
                        break

    return items


async def _fetch_single_feed(
    url: str,
    keywords: list[str] | None,
    max_items_per_feed: int,
    client: Any | None,
) -> list[TrendItem]:
    try:
        if client is not None:
            resp = await client.get(url, timeout=10.0)
            if hasattr(resp, "raise_for_status"):
                resp.raise_for_status()
            text = resp.text
        else:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as new_client:
                resp = await new_client.get(url)
                resp.raise_for_status()
                text = resp.text
        return parse_feed_xml(text, keywords=keywords, max_items=max_items_per_feed)
    except Exception as e:
        logger.warning("Failed to fetch or parse RSS feed %s: %s", url, e)
        return []


async def fetch_rss_trends(
    feed_urls: list[str],
    keywords: list[str] | None = None,
    max_items_per_feed: int = 5,
    client: Any | None = None,
) -> list[TrendItem]:
    if not feed_urls:
        return []

    tasks = [
        _fetch_single_feed(url, keywords, max_items_per_feed, client)
        for url in feed_urls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: list[TrendItem] = []
    for res in results:
        if isinstance(res, list):
            all_items.extend(res)
    return all_items
