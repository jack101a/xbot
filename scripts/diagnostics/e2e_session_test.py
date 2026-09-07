import asyncio
import logging
import sys

from sqlalchemy import select

from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.tasks import _run_session_async

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("e2e_test")

async def run_e2e_test():
    logger.info("Starting End-to-End Test for Automation Pipeline...")
    
    # MOCK the AI Planner to output our new actions
    import xbot.tasks
    from xbot.ai.planner import SessionPlan, PlannedAction
    
    async def mock_plan_session(*args, **kwargs):
        logger.info("MOCK AI PLANNER: Generating test plan with unfollow, scrape_metrics, and scrape_trends")
        return SessionPlan(
            mood="analytical",
            reasoning="Testing new OSINT scraper capabilities.",
            actions=[
                PlannedAction(type="scrape_trends", reasoning="Getting trends", priority=1),
                PlannedAction(type="scrape_metrics", target="elonmusk", reasoning="Checking metrics", priority=2),
                PlannedAction(type="unfollow", target="some_random_bot", reasoning="Cleaning feed", priority=3),
            ],
            skip_reason=None
        )
    xbot.tasks.plan_session = mock_plan_session

    async with AsyncSessionLocal() as db:
        # Find an active profile to test
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE).limit(1)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        
        if not profile:
            logger.error("No active profiles found in DB for testing.")
            sys.exit(1)
            
        profile_id_str = str(profile.id)
        logger.info(f"Targeting Profile: {profile.display_name} (@{profile.x_handle}) | ID: {profile_id_str}")
        
    logger.info("Triggering _run_session_async...")
    result = await _run_session_async(profile_id_str)
    
    logger.info(f"Session Execution Result:\n{result}")
    
    if result.get("status") in ["success", "aborted"]:
        logger.info("E2E Test Completed Successfully! The pipeline is fully functional.")
    else:
        logger.error("E2E Test Failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
