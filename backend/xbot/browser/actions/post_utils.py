from __future__ import annotations
import logging
import os
import random
from playwright.async_api import Page
from xbot.browser.timing import (
    human_click,
    human_type,
    sleep_think_time,
)

logger = logging.getLogger(__name__)

async def _attach_gif_if_requested(page: Page, gif_query: str | None) -> bool:
    """Helper to open X native Tenor GIF search, search for a query, and select a relevant GIF item."""
    if not gif_query:
        return False
    try:
        logger.info("Attempting to search and attach GIF for query: '%s'", gif_query)
        gif_btn_sel = (
            'button[aria-label="Add a GIF"], '
            'button[data-testid="gifSearchButton"], '
            '[data-testid="gifSearchButton"], '
            'button[aria-label*="GIF"], '
            'button[aria-label*="gif" i], '
            '[data-testid="fileInput"] + div button'
        )
        gif_btn = await page.query_selector(gif_btn_sel)
        if not gif_btn:
            logger.debug("GIF search button not found in composer, falling back to text-only.")
            return False

        await human_click(page, gif_btn, 200, 500)
        await sleep_think_time(800, 1500)

        # Search input in GIF modal
        search_input_sel = (
            'input[data-testid="searchBox"], '
            'input[data-testid="SearchBox_Search_Input"], '
            'input[placeholder*="Search GIFs"], '
            'input[placeholder*="Search for GIFs"], '
            'input[aria-label*="Search for GIFs"], '
            'input[aria-label*="Search GIFs"]'
        )
        try:
            search_input = await page.wait_for_selector(search_input_sel, timeout=6000)
        except Exception:
            search_input = None

        if not search_input:
            logger.warning("GIF search input not found, falling back to text-only.")
            return False

        await human_type(page, search_input_sel, gif_query)
        await sleep_think_time(1200, 2500)

        # Select top GIF result
        gif_result_sel = (
            '[data-testid="gifItem"], '
            '[data-testid="gifSearchResults"] img, '
            '[data-testid="gifSearchResults"] [role="button"], '
            '[data-testid="gifCategory"], '
            'div[role="button"][data-testid*="gif"], '
            '[data-testid="gifSearchResults"] div'
        )
        try:
            await page.wait_for_selector(gif_result_sel, timeout=6000)
        except Exception:
            pass

        gif_items = await page.query_selector_all(gif_result_sel)
        if gif_items:
            target_gif = gif_items[0] if len(gif_items) == 1 else random.choice(gif_items[:min(2, len(gif_items))])
            await human_click(page, target_gif, 300, 700)
            await sleep_think_time(1000, 2000)
            logger.info("Successfully attached GIF for query: '%s'", gif_query)
            return True
        else:
            logger.warning("No GIF items found for query '%s', falling back to text-only.", gif_query)
            return False
    except Exception as e:
        logger.warning("Could not attach GIF (falling back to text-only): %s", e)
        return False

async def _attach_media_files(page: Page, media_paths: list[str] | None) -> bool:
    """Helper to upload local image/video files into X composer using input[type=file]."""
    if not media_paths:
        return False
    valid_paths = [p for p in media_paths if os.path.exists(p)]
    if not valid_paths:
        logger.warning("No valid media files found in paths: %s", media_paths)
        return False

    try:
        logger.info("Uploading %d media files to X composer: %s", len(valid_paths), valid_paths)
        file_input_sel = (
            'input[data-testid="fileInput"], '
            'input[type="file"][accept*="image"], '
            'input[type="file"]'
        )
        file_input = await page.query_selector(file_input_sel)
        if not file_input:
            file_input = await page.wait_for_selector(file_input_sel, state="attached", timeout=6000)

        if file_input:
            await file_input.set_input_files(valid_paths)
            await sleep_think_time(1500, 3000)
            
            # Wait for upload thumbnail preview to appear
            attachment_sel = (
                '[data-testid="attachments"], '
                '[data-testid="tweetPhoto"], '
                'div[role="group"][aria-label*="Media"], '
                'img[alt*="Image"]'
            )
            try:
                await page.wait_for_selector(attachment_sel, timeout=10000)
                logger.info("Media attachment preview loaded successfully.")
            except Exception:
                logger.warning("Attachment thumbnail selector timed out, proceeding.")

            return True
    except Exception as e:
        logger.warning("Could not upload media files: %s", e)
    return False

def smart_truncate_tweet_text(text: str, max_chars: int = 260) -> str:
    """Truncates tweet text cleanly at natural punctuation or word boundaries without severing words."""
    if not text or len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_punc = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if last_punc > 120:
        return truncated[:last_punc + 1].strip()
    last_space = truncated.rfind(" ")
    if last_space > 100:
        return truncated[:last_space].strip() + "..."
    return truncated[:max_chars - 3].strip() + "..."

