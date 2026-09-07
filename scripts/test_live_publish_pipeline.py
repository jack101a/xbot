import asyncio
import logging
import uuid
from sqlalchemy import select
from xbot.database import AsyncSessionLocal
from xbot.models.content import Content, ContentStatus
from xbot.tasks.publish_tasks import _auto_publish_pending_drafts_async
from xbot.infra.browser.queue.worker import _process_browser_queue_async

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("test_publish")

async def drain_queue_loop(stop_event: asyncio.Event):
    """Polls and drains browser queue every 2 seconds until stop_event is set."""
    logger.info("Starting background browser queue drain loop...")
    while not stop_event.is_set():
        try:
            count = await _process_browser_queue_async(max_jobs=2)
            if count > 0:
                logger.info("Drained %d browser job(s)", count)
        except Exception as e:
            logger.error("Queue drain error: %s", e)
        await asyncio.sleep(2.0)

async def main():
    target_draft_id = uuid.UUID("14c5099d-30f6-479e-baeb-afc3fbc23d86")
    
    # 1. Reset draft status to APPROVED
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Content).where(Content.id == target_draft_id))
        draft = res.scalar_one_or_none()
        if not draft:
            logger.error("Draft not found!")
            return
        
        meta = dict(draft.ai_metadata or {})
        meta["publish_attempts"] = 0
        draft.status = ContentStatus.APPROVED
        draft.ai_metadata = meta
        await db.commit()
        logger.info("Reset draft %s to APPROVED: '%s'", draft.id, draft.body[:50])

    # 2. Run publish and drainer concurrently
    stop_event = asyncio.Event()
    drainer_task = asyncio.create_task(drain_queue_loop(stop_event))

    try:
        logger.info("Invoking _auto_publish_pending_drafts_async()...")
        publish_result = await _auto_publish_pending_drafts_async()
        logger.info("Publish result: %s", publish_result)
    finally:
        stop_event.set()
        await drainer_task

    # 3. Verify final DB status
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Content).where(Content.id == target_draft_id))
        draft = res.scalar_one()
        logger.info("Final Draft Status: %s | Tweet ID: %s | Posted At: %s", draft.status, draft.tweet_id, draft.posted_at)

if __name__ == "__main__":
    asyncio.run(main())
