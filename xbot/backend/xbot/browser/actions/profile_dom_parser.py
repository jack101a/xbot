"""
DOM parsing utilities and extractor helpers for X profile pages.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from playwright.async_api import Page

logger = logging.getLogger(__name__)


def parse_count(text: str) -> int:
    """Parses abbreviation numbers (e.g. 1.2M, 15.4K, 1,234) into integers."""
    if not text:
        return 0
    clean = text.strip().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*([KkMmBb])?", clean)
    if not match:
        return 0
    num_str, suffix = match.groups()
    try:
        val = float(num_str)
        if suffix:
            s = suffix.upper()
            if s == "K":
                val *= 1_000
            elif s == "M":
                val *= 1_000_000
            elif s == "B":
                val *= 1_000_000_000
        return int(val)
    except Exception:
        return 0


def upgrade_avatar_url(url: str) -> str:
    """Upgrades X avatar thumbnail URL to high-resolution 400x400."""
    if not url:
        return ""
    return re.sub(
        r"_(normal|200x200|bigger|mini|x96|reasonably_small)(?=\.[a-zA-Z0-9]+(?:\?|$))",
        "_400x400",
        url,
    )


async def extract_count_from_selector(page: Page, selector: str) -> int:
    """Helper to find and parse count numbers from matching elements or child spans."""
    try:
        el = await page.query_selector(selector)
        if not el:
            return 0
        spans = await el.query_selector_all("span")
        for span in spans:
            text = (await span.inner_text()).strip()
            if not text:
                continue
            count = parse_count(text)
            if count > 0 or text == "0":
                return count
        full_text = (await el.inner_text()).strip()
        return parse_count(full_text)
    except Exception:
        return 0
