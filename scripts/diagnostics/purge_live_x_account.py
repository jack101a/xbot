"""
Live X Account Cleaner & Purger

Purges all published tweets, replies, retweets, and likes on the live X account (@jackds1234)
using BrowserManager with test_profile1. Also cleans local memory files and SQLite records.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sqlite3
import sys
from pathlib import Path

# Ensure backend in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("purge_live_x")

PROFILE_SLUG = "test_profile1"
PROFILE_ID_HYPHEN = "c0fb031e-d884-4706-a9ff-fe84e4a7d014"
PROFILE_ID_HEX = "c0fb031ed8844706a9fffe84e4a7d014"
BASE_PROFILE_DIR = Path(__file__).resolve().parent.parent / "data" / "profiles"
DB_PATH = Path(__file__).resolve().parent.parent / "xbot.db"
OUT_DIR = Path(__file__).parent / "purge_screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def delete_all_tweets_on_url(page, url: str, label: str = "Posts") -> int:
    """
    Navigates to the given profile URL and repeatedly deletes/unretweets all tweets until 0 remain.
    """
    logger.info(f"Navigating to {url} to purge {label}...")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)
    await page.screenshot(path=str(OUT_DIR / f"before_purge_{label.lower()}.png"))

    deleted_count = 0
    consecutive_no_action = 0
    max_loops = 50

    for loop_idx in range(max_loops):
        # Check for tweets
        tweets = await page.query_selector_all('[data-testid="tweet"]')
        logger.info(f"[{label}] Loop {loop_idx + 1}: Found {len(tweets)} tweets in DOM.")

        if not tweets or len(tweets) == 0:
            consecutive_no_action += 1
            if consecutive_no_action >= 2:
                logger.info(f"[{label}] No more tweets found. Purge complete for {label}.")
                break
            await asyncio.sleep(2)
            # Try a slight scroll to ensure nothing is lazy loading
            await page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(2)
            continue

        action_taken = False

        for i, tweet in enumerate(tweets):
            try:
                # 1. Check for Unretweet first (if this was a retweet)
                unrt_btn = await tweet.query_selector('[data-testid="unretweet"]')
                if unrt_btn and await unrt_btn.is_visible():
                    logger.info(f"[{label}] Found Retweet at index {i}. Clicking Unretweet...")
                    await unrt_btn.click()
                    await asyncio.sleep(1)
                    confirm_unrt = await page.wait_for_selector(
                        '[data-testid="unretweetConfirm"]', timeout=3000
                    )
                    if confirm_unrt:
                        await confirm_unrt.click()
                        logger.info(f"[{label}] Confirmed Unretweet.")
                        deleted_count += 1
                        action_taken = True
                        await asyncio.sleep(2)
                        break

                # 2. Check for Caret / More menu
                caret = await tweet.query_selector(
                    '[data-testid="caret"], button[aria-label="More"], button[aria-label="More actions"]'
                )
                if not caret:
                    continue

                # Scroll caret into view
                await caret.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await caret.click()
                logger.info(f"[{label}] Clicked caret menu for tweet {i + 1}.")

                # Wait for dropdown menu
                menu = await page.wait_for_selector(
                    '[data-testid="Dropdown"], [role="menu"]', timeout=4000
                )
                if not menu:
                    logger.warning(f"[{label}] Dropdown menu not displayed.")
                    await page.keyboard.press("Escape")
                    continue

                # Look for "Delete" menuitem
                delete_item = await page.query_selector(
                    '[data-testid="Dropdown"] [role="menuitem"]:has-text("Delete"), '
                    '[role="menu"] [role="menuitem"]:has-text("Delete"), '
                    'div[role="menuitem"]:has-text("Delete")'
                )

                if not delete_item:
                    logger.info(f"[{label}] No 'Delete' option in menu (not our tweet). Closing menu.")
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(1)
                    continue

                logger.info(f"[{label}] Found Delete button in dropdown. Clicking...")
                await delete_item.click()
                await asyncio.sleep(1)

                # Wait for confirmation sheet
                confirm_btn = await page.wait_for_selector(
                    '[data-testid="confirmationSheetConfirm"], button[data-testid="confirmationSheetConfirm"]',
                    timeout=5000,
                )
                if confirm_btn:
                    await confirm_btn.click()
                    logger.info(f"[{label}] Confirmed tweet deletion ({deleted_count + 1} deleted so far).")
                    deleted_count += 1
                    action_taken = True
                    await asyncio.sleep(2.5)
                    break
                else:
                    logger.warning(f"[{label}] Confirmation modal did not appear.")
                    await page.keyboard.press("Escape")

            except Exception as e:
                logger.warning(f"[{label}] Exception while processing tweet {i}: {e}")
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass
                await asyncio.sleep(1)

        if action_taken:
            consecutive_no_action = 0
            # Refresh page or wait for DOM update
            await page.reload(wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)
        else:
            consecutive_no_action += 1
            if consecutive_no_action >= 2:
                logger.info(f"[{label}] No actionable tweets remaining after {consecutive_no_action} attempts.")
                break
            await page.reload(wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)

    await page.screenshot(path=str(OUT_DIR / f"after_purge_{label.lower()}.png"))
    logger.info(f"[{label}] Finished purging {label}. Total removed: {deleted_count}")
    return deleted_count


async def unlike_all_tweets(page) -> int:
    """
    Navigates to https://x.com/jackds1234/likes and unlikes all liked tweets.
    """
    likes_url = "https://x.com/jackds1234/likes"
    logger.info(f"Navigating to {likes_url} to unlike all tweets...")
    await page.goto(likes_url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)
    await page.screenshot(path=str(OUT_DIR / "before_purge_likes.png"))

    unliked_count = 0
    consecutive_no_action = 0
    max_loops = 30

    for loop_idx in range(max_loops):
        unlike_buttons = await page.query_selector_all('[data-testid="unlike"]')
        logger.info(f"[Likes] Loop {loop_idx + 1}: Found {len(unlike_buttons)} unlike buttons.")

        if not unlike_buttons:
            consecutive_no_action += 1
            if consecutive_no_action >= 2:
                logger.info("[Likes] No liked tweets found. Unliking complete.")
                break
            await asyncio.sleep(2)
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(2)
            continue

        for btn in unlike_buttons:
            try:
                if await btn.is_visible():
                    await btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    await btn.click()
                    unliked_count += 1
                    logger.info(f"[Likes] Unliked tweet #{unliked_count}")
                    await asyncio.sleep(0.8)
            except Exception as e:
                logger.warning(f"[Likes] Error unliking tweet: {e}")

        consecutive_no_action = 0
        await page.evaluate("window.scrollBy(0, 600)")
        await asyncio.sleep(2)

    await page.screenshot(path=str(OUT_DIR / "after_purge_likes.png"))
    logger.info(f"[Likes] Finished unliking. Total unliked: {unliked_count}")
    return unliked_count


def clean_local_memory():
    """
    Cleans local diary files and resets JSONL memory files for test_profile1.
    """
    logger.info("\n--- Cleaning Local Filesystem Memory for test_profile1 ---")
    profile_dir = BASE_PROFILE_DIR / PROFILE_SLUG
    diary_dir = profile_dir / "diary"
    memories_dir = profile_dir / "memories"

    # 1. Remove legacy diary files
    if diary_dir.exists():
        diary_files = list(diary_dir.glob("*.md"))
        logger.info(f"Found {len(diary_files)} diary files to remove in {diary_dir}")
        for df in diary_files:
            try:
                df.unlink()
                logger.info(f"Deleted diary file: {df.name}")
            except Exception as e:
                logger.error(f"Failed to delete {df}: {e}")
    else:
        logger.info(f"Diary directory {diary_dir} does not exist.")

    # 2. Empty JSONL memory files
    memory_files = ["episodic.jsonl", "semantic.jsonl", "important.jsonl"]
    if memories_dir.exists():
        for mf in memory_files:
            file_path = memories_dir / mf
            try:
                with open(file_path, "w") as f:
                    pass  # truncate to 0 bytes
                logger.info(f"Emptied memory file: {file_path} (size: {file_path.stat().st_size} bytes)")
            except Exception as e:
                logger.error(f"Failed to empty {file_path}: {e}")
    else:
        logger.info(f"Memories directory {memories_dir} does not exist.")


def clean_sqlite_db():
    """
    Cleans legacy SQLite records in xbot.db for profile c0fb031e-d884-4706-a9ff-fe84e4a7d014.
    """
    logger.info(f"\n--- Cleaning SQLite DB records for profile {PROFILE_ID_HYPHEN} ---")
    if not DB_PATH.exists():
        logger.error(f"Database {DB_PATH} not found!")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    tables = ["sessions", "actions", "content", "analytics_snapshots", "rate_limits"]
    for table in tables:
        try:
            cursor.execute(
                f"DELETE FROM {table} WHERE profile_id IN (?, ?)",
                (PROFILE_ID_HEX, PROFILE_ID_HYPHEN),
            )
            deleted_rows = cursor.rowcount
            logger.info(f"Deleted {deleted_rows} rows from table '{table}'")
        except Exception as e:
            logger.error(f"Error deleting from '{table}': {e}")

    conn.commit()

    # Verification
    logger.info("Verifying record counts after cleanup:")
    for table in tables:
        cursor.execute(
            f"SELECT count(*) FROM {table} WHERE profile_id IN (?, ?)",
            (PROFILE_ID_HEX, PROFILE_ID_HYPHEN),
        )
        count = cursor.fetchone()[0]
        logger.info(f"Remaining records in '{table}': {count}")

    conn.close()


async def main():
    logger.info("==================================================================")
    logger.info("STARTING FULL LIVE X ACCOUNT PURGE & CLEANUP")
    logger.info(f"Profile: {PROFILE_SLUG} (@jackds1234)")
    logger.info("==================================================================")

    # 1. Playwright Browser Purge
    manager = BrowserManager(base_profile_dir=str(BASE_PROFILE_DIR))
    if not manager.acquire_lock(PROFILE_SLUG, timeout_seconds=1800):
        logger.error(f"Could not acquire profile lock for {PROFILE_SLUG}. Exiting.")
        return

    context = None
    try:
        await manager.start()
        context = await manager.get_context(PROFILE_SLUG)
        page = await context.new_page()

        # Purge main profile posts
        posts_deleted = await delete_all_tweets_on_url(
            page, "https://x.com/jackds1234", label="Posts"
        )

        # Purge profile replies tab
        replies_deleted = await delete_all_tweets_on_url(
            page, "https://x.com/jackds1234/with_replies", label="Replies"
        )

        # Purge likes
        likes_unliked = await unlike_all_tweets(page)

        logger.info("\n================ PURGE SUMMARY ================")
        logger.info(f"Posts deleted:   {posts_deleted}")
        logger.info(f"Replies deleted: {replies_deleted}")
        logger.info(f"Likes unliked:   {likes_unliked}")
        logger.info("===============================================")

    except Exception as e:
        logger.error(f"Error during browser purge: {e}", exc_info=True)
    finally:
        if context:
            await context.close()
        await manager.stop()
        manager.release_lock(PROFILE_SLUG)

    # 2. Local Filesystem Cleanup
    clean_local_memory()

    # 3. Database Cleanup
    clean_sqlite_db()

    logger.info("\nALL PURGE & CLEANUP OPERATIONS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
