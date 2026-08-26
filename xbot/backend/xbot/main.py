import asyncio
import datetime
import logging
import random
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from xbot.api import api_router
from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import load_config
from xbot.tasks import _run_session_async

logger = logging.getLogger("xbot.main")


async def _background_growth_scheduler_loop() -> None:
    """
    Continuous autonomous growth loop:
    Periodically checks active profiles every 15-20 minutes, validates active operating hours,
    and runs full research & engagement sessions automatically.
    """
    logger.info("Starting XBot Autonomous Growth Interval Scheduler...")
    # Initial startup delay (5s) to allow servers to stabilize
    await asyncio.sleep(5)

    base_profiles_dir = Path(__file__).resolve().parent.parent.parent / "data" / "profiles"

    while True:
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
                res = await db.execute(stmt)
                active_profiles = res.scalars().all()

                for prof in active_profiles:
                    try:
                        profile_path = base_profiles_dir / prof.profile_slug
                        if not profile_path.exists() or not (profile_path / "config.yaml").exists():
                            continue

                        cfg = load_config(profile_path)
                        tz_str = cfg.schedule.timezone or "Asia/Kolkata"
                        active_hours = cfg.schedule.active_hours or "00:00-23:59"

                        # Parse active hours
                        start_str, end_str = active_hours.split("-")
                        start_h, start_m = map(int, start_str.split(":"))
                        end_h, end_m = map(int, end_str.split(":"))

                        now_local = datetime.datetime.now(ZoneInfo(tz_str))
                        current_min = now_local.hour * 60 + now_local.minute
                        start_min = start_h * 60 + start_m
                        end_min = end_h * 60 + end_m

                        if start_min <= current_min <= end_min:
                            logger.info(
                                "Autonomous Scheduler: Triggering scheduled growth session for %s (@%s) at local time %s",
                                prof.display_name,
                                prof.x_handle,
                                now_local.strftime("%H:%M"),
                            )
                            # Launch session in background
                            asyncio.create_task(_run_session_async(str(prof.id)))
                        else:
                            logger.debug(
                                "Autonomous Scheduler: Skipping %s - outside active hours (%s vs %s)",
                                prof.x_handle,
                                now_local.strftime("%H:%M"),
                                active_hours,
                            )
                    except Exception as p_err:
                        logger.warning("Error checking profile %s for scheduled session: %s", prof.profile_slug, p_err)

        except Exception as e:
            logger.error("Error in background growth scheduler loop: %s", e)

        # Wait 15 minutes (with random jitter ± 2 minutes)
        interval_secs = random.randint(13 * 60, 17 * 60)
        logger.debug("Autonomous Scheduler: Sleeping for %d seconds until next scan cycle", interval_secs)
        await asyncio.sleep(interval_secs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup cleanup: purge stale locks & dangling sessions
    try:
        import redis
        from xbot.models.session import Session, SessionStatus
        r = redis.from_url(settings.REDIS_URL)
        for k in r.keys("lock:browser:*"):
            r.delete(k)
        async with AsyncSessionLocal() as db:
            stuck_stmt = select(Session).where(Session.status == SessionStatus.RUNNING)
            stuck_res = await db.execute(stuck_stmt)
            for s in stuck_res.scalars().all():
                s.status = SessionStatus.ABORTED
                s.error_log = "Cleaned up on server restart."
                s.ended_at = datetime.datetime.utcnow()
            await db.commit()
    except Exception as cl_err:
        logger.warning("Startup cleanup error: %s", cl_err)

    # Start background scheduler
    scheduler_task = asyncio.create_task(_background_growth_scheduler_loop())
    yield
    # Cancel scheduler on shutdown
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="XBot API Server",
    description="Backend API services for XBot Twitter Automation System",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint returning system status.
    """
    return {
        "status": "healthy",
        "service": "xbot-api",
        "version": "0.1.0",
        "database_configured": bool(settings.DATABASE_URL),
        "redis_configured": bool(settings.REDIS_URL),
    }


# Mount data directory for serving generated & downloaded media
data_dir = Path(__file__).resolve().parent.parent.parent / "data"
data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=str(data_dir)), name="data_static")

# Mount lightweight static dashboard SPA directly
static_dashboard_dir = Path(__file__).resolve().parent.parent.parent / "dashboard" / "out"
if static_dashboard_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dashboard_dir), html=True), name="static_dashboard")
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Welcome to XBot API Server"}
