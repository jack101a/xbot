from __future__ import annotations
import logging
import random
import re
from typing import Any
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_mouse_move,
    human_scroll,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet)

def _parse_metric_number(text: str | None) -> int:
    if not text:
        return 0
    try:
        clean = text.replace(",", "").strip()
        match = re.search(r"([\d\.]+)\s*([KkMmBb])?", clean)
        if not match:
            return 0
        val = float(match.group(1))
        suffix = (match.group(2) or "").upper()
        if suffix == "K":
            return int(val * 1_000)
        elif suffix == "M":
            return int(val * 1_000_000)
        elif suffix == "B":
            return int(val * 1_000_000_000)
        return int(val)
    except Exception:
        return 0


class BrowseFeed(BaseAction):
    """
    Browses the X home feed or search results by scrolling incrementally with inertia,
    mimicking natural reading pauses and occasional back-scrolls.
    """

    async def execute(
        self,
        page: Page,
        max_scrolls: int = 5,
        navigate_home: bool = True,
        min_results: int = 0,
        require_media: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            if navigate_home:
                await _navigate_home_if_needed(page)
            logger.info(
                "Starting feed browsing session (navigate_home=%s, max_scrolls=%d, min_results=%d, require_media=%s, current_url=%s).",
                navigate_home,
                max_scrolls,
                min_results,
                require_media,
                page.url,
            )
            tweets: list[dict[str, Any]] = []

            # Random initial idle — as if just opening the app
            await sleep_think_time(500, 2000)

            for scroll_idx in range(max_scrolls):
                # Inertia-based scroll (400–800 px)
                scroll_px = random.randint(400, 800)
                await human_scroll(page, scroll_px, "down")
                await sleep_think_time(1200, 2500)  # Read pause

                # 20% chance of a back-scroll (scanning up after reading)
                if random.random() < 0.2:
                    back_px = random.randint(100, 250)
                    await human_scroll(page, back_px, "up")
                    await sleep_with_jitter(1000)

                # 10% chance to hover over a random tweet as if reading more carefully
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                if tweet_elements and random.random() < 0.1:
                    hover_target = random.choice(tweet_elements[:5])
                    box = await hover_target.bounding_box()
                    if box:
                        await human_mouse_move(
                            page,
                            box["x"] + box["width"] * 0.4,
                            box["y"] + box["height"] * 0.4,
                        )
                        await sleep_think_time(600, 1800)

                # Extract visible tweets
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                for el in tweet_elements:
                    text_el = await el.query_selector(SELECTORS["tweet_text"])
                    if text_el:
                        text = (await text_el.inner_text()).strip()
                        if not text:
                            continue

                        # Global Political Safety Filter
                        from xbot.ai.sniper import BANNED_POLITICS_REGEX
                        if BANNED_POLITICS_REGEX.search(text):
                            continue

                        # Extract author handle & name
                        author = ""
                        display_name = ""
                        is_blue_tick = False
                        user_el = await el.query_selector('[data-testid="User-Name"]')
                        if user_el:
                            user_text = await user_el.inner_text()
                            match = re.search(r"@([A-Za-z0-9_]+)", user_text)
                            if match:
                                author = match.group(1)
                            # Blue tick detection
                            verified_icon = await user_el.query_selector(
                                'svg[data-testid="icon-verified"], svg[aria-label*="Verified"]'
                            )
                            if verified_icon:
                                is_blue_tick = True

                        tweet_data: dict[str, Any] = {
                            "text": text,
                            "author": author or "creator",
                            "is_blue_tick": is_blue_tick,
                        }

                        # Extract hashtags from text and links
                        hashtags = list(dict.fromkeys(re.findall(r"#[A-Za-z0-9_]+", text)))
                        try:
                            ht_els = await el.query_selector_all('a[href*="/hashtag/"]')
                            for h_el in ht_els:
                                h_text = (await h_el.inner_text()).strip()
                                if h_text.startswith("#") and h_text not in hashtags:
                                    hashtags.append(h_text)
                        except Exception:
                            pass
                        tweet_data["hashtags"] = hashtags

                        # Scrape attached images & video media (high-resolution official / tweet media)
                        try:
                            img_els = await el.query_selector_all(
                                '[data-testid="tweetPhoto"] img, div[aria-label="Image"] img, img[src*="pbs.twimg.com/media/"]'
                            )
                            for img_el in img_els:
                                img_src = await img_el.get_attribute("src")
                                img_alt = await img_el.get_attribute("alt")
                                if img_src and img_src.startswith("http") and "profile_images" not in img_src and "emoji" not in img_src:
                                    # Upgrade twimg thumbnails to pristine studio resolution
                                    high_res_url = img_src
                                    if "pbs.twimg.com/media/" in high_res_url:
                                        if "name=" in high_res_url:
                                            high_res_url = re.sub(r"name=[a-zA-Z0-9_]+", "name=large", high_res_url)
                                        else:
                                            separator = "&" if "?" in high_res_url else "?"
                                            high_res_url = f"{high_res_url}{separator}name=large"

                                    media_list = tweet_data.setdefault("media_urls", [])
                                    if high_res_url not in media_list:
                                        media_list.append(high_res_url)

                                if img_alt and img_alt.strip() and img_alt != "Image":
                                    tweet_data.setdefault("media_alts", []).append(img_alt.strip())

                            # Detect videos, trailers, and clips
                            video_el = await el.query_selector(
                                '[data-testid="videoComponent"], [data-testid="videoPlayer"], video, div[aria-label*="video" i]'
                            )
                            if video_el:
                                tweet_data["has_video"] = True
                                vid_tag = await el.query_selector("video")
                                if vid_tag:
                                    poster = await vid_tag.get_attribute("poster")
                                    if poster and poster.startswith("http"):
                                        media_list = tweet_data.setdefault("media_urls", [])
                                        if poster not in media_list:
                                            media_list.append(poster)
                        except Exception:
                            pass

                        # Engagement metrics (likes, retweets, replies)
                        replies_count, retweets_count, likes_count = 0, 0, 0
                        try:
                            reply_el = await el.query_selector('[data-testid="reply"]')
                            if reply_el:
                                reply_text = (await reply_el.get_attribute("aria-label")) or (await reply_el.inner_text()) or ""
                                replies_count = _parse_metric_number(reply_text)

                            rt_el = await el.query_selector('[data-testid="retweet"], [data-testid="unretweet"]')
                            if rt_el:
                                rt_text = (await rt_el.get_attribute("aria-label")) or (await rt_el.inner_text()) or ""
                                retweets_count = _parse_metric_number(rt_text)

                            like_el = await el.query_selector('[data-testid="like"], [data-testid="unlike"]')
                            if like_el:
                                like_text = (await like_el.get_attribute("aria-label")) or (await like_el.inner_text()) or ""
                                likes_count = _parse_metric_number(like_text)
                        except Exception:
                            pass

                        tweet_data["likes"] = likes_count
                        tweet_data["retweets"] = retweets_count
                        tweet_data["replies"] = replies_count
                        tweet_data["metrics"] = {
                            "likes": likes_count,
                            "retweets": retweets_count,
                            "replies": replies_count,
                        }

                        # Check if this is an active growth or follow-back thread
                        if re.search(r"(follow\s*back|drop\s*your\s*handle|mutuals|f4f|verified\s*mutuals|connect)", text, re.IGNORECASE):
                            tweet_data["is_growth_thread"] = True

                        try:
                            link_el = await el.query_selector("a[href*='/status/']")
                            if link_el:
                                href = await link_el.get_attribute("href")
                                if href:
                                    tweet_data["url"] = f"https://x.com{href}" if href.startswith("/") else href
                                    tweet_data["tweet_id"] = _extract_tweet_id_from_url(tweet_data["url"])
                        except Exception:
                            pass

                        # Enforce media requirement if requested
                        if require_media and not tweet_data.get("media_urls"):
                            continue

                        # Deduplicate by URL or text
                        is_duplicate = False
                        for t in tweets:
                            if tweet_data.get("url") and t.get("url") and t.get("url") == tweet_data.get("url"):
                                is_duplicate = True
                                break
                            if tweet_data.get("text") and t.get("text") and t.get("text") == tweet_data.get("text"):
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            tweets.append(tweet_data)

                # Check if target min_results reached
                if min_results > 0 and len(tweets) >= min_results:
                    logger.info(
                        "BrowseFeed: Target count reached (%d/%d items) on scroll %d/%d.",
                        len(tweets),
                        min_results,
                        scroll_idx + 1,
                        max_scrolls,
                    )
                    break

            logger.info("Browsed %d scrolls, gathered %d tweets", max_scrolls, len(tweets))
            return tweets
        except Exception as e:
            await self.capture_failure(page, "browse_feed")
            logger.error("Failed browsing feed: %s", e)
            raise e

class SearchQuery(BaseAction):
    """Performs a search query on X and browses results with adaptive operator relaxation."""

    async def execute(
        self,
        page: Page,
        query: str,
        search_filter: str = "top",
        auto_relax: bool = True,
        max_scrolls: int = 8,
        min_results: int = 0,
        require_media: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            from urllib.parse import quote_plus

            # Map category name and media filters
            cat_param = ""
            effective_query = query
            if search_filter in ("live", "latest"):
                cat_param = "&f=live"
            elif search_filter == "media":
                if "filter:media" not in effective_query and "filter:images" not in effective_query:
                    effective_query = f"{effective_query} filter:media"
                cat_param = ""
            elif search_filter in ("user", "people"):
                cat_param = "&f=user"

            if require_media and "filter:media" not in effective_query and "filter:images" not in effective_query:
                effective_query = f"{effective_query} filter:media"

            # 1. Execute initial query
            search_url = f"https://x.com/search?q={quote_plus(effective_query)}{cat_param}"
            logger.info("Executing X search: %s (url=%s)", effective_query, search_url)
            await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            try:
                await page.wait_for_selector(SELECTORS["tweet"], timeout=9000)
            except Exception:
                pass
            await sleep_with_jitter(1800)

            browser = BrowseFeed(str(self.screenshot_dir))
            results = await browser.execute(
                page,
                max_scrolls=max_scrolls,
                navigate_home=False,
                min_results=min_results,
                require_media=require_media or (search_filter == "media"),
            )

            # 2. Adaptive Relaxation Fallback if initial query returned 0 results
            if not results and auto_relax:
                logger.info("Search returned 0 results for '%s'. Attempting adaptive operator relaxation...", query)
                relaxed_candidates: list[tuple[str, str]] = []

                # Relaxation A: If min_faves was present, try lowering or removing it
                if "min_faves:" in query:
                    lower_faves = re.sub(r"min_faves:\d+", "min_faves:50", query)
                    if lower_faves != query:
                        relaxed_candidates.append((lower_faves, cat_param))
                    no_faves = re.sub(r"min_faves:\d+", "", query).strip()
                    relaxed_candidates.append((no_faves, cat_param))

                # Relaxation B: If filter:media was present, try without it
                if "filter:media" in query:
                    no_media = query.replace("filter:media", "").strip()
                    relaxed_candidates.append((no_media, cat_param))

                # Relaxation C: Switch to real-time live feed (&f=live)
                clean_base_topic = re.sub(r"(min_faves:\d+|filter:\w+|-filter:\w+|since:\S+)", "", query).strip()
                if clean_base_topic:
                    relaxed_candidates.append((f"{clean_base_topic} -filter:retweets", "&f=live"))
                    relaxed_candidates.append((clean_base_topic, "&f=live"))

                for rel_q, rel_cat in relaxed_candidates:
                    if not rel_q.strip():
                        continue
                    rel_url = f"https://x.com/search?q={quote_plus(rel_q)}{rel_cat}"
                    logger.info("Trying relaxed search fallback: %s", rel_url)
                    await page.goto(rel_url, wait_until="domcontentloaded", timeout=20000)
                    try:
                        await page.wait_for_selector(SELECTORS["tweet"], timeout=7000)
                    except Exception:
                        pass
                    results = await browser.execute(
                        page,
                        max_scrolls=min(max_scrolls, 4),
                        navigate_home=False,
                        min_results=min_results,
                        require_media=require_media or (rel_cat == "&f=media"),
                    )
                    if results:
                        logger.info("Relaxed fallback '%s' succeeded! Recovered %d tweets.", rel_q, len(results))
                        break

            logger.info("Gathered %d total search results for query '%s'.", len(results), query)
            return results
        except Exception as e:
            await self.capture_failure(page, "search")
            logger.error("Failed to perform search: %s", e)
            raise e


