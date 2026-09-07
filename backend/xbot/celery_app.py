from celery import Celery

from xbot.config import settings

# Initialize Celery app with Redis broker and backend
celery_app = Celery(
    "xbot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# General Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes max execution time
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

celery_app.conf.task_routes = {
    "xbot.pipelines.browser_queue.*": {"queue": "browser"},
    "xbot.tasks.auto_publish_pending_drafts": {"queue": "publish"},
    "xbot.tasks.publish_tasks.*": {"queue": "publish"},
}

# Celery Beat Periodic Schedule — Phase 0 Streamlined Core Cadence
celery_app.conf.beat_schedule = {
    # 1. Central Browser Queue Worker (10s)
    "browser-queue-worker-every-10s": {
        "task": "xbot.pipelines.browser_queue.process_browser_queue",
        "schedule": 10.0,
        "options": {"queue": "browser", "expires": 10.0},
    },
    # 2. Auto-Publish Approved/Pending Drafts (5 min)
    "auto-publish-pending-drafts-every-300-seconds": {
        "task": "xbot.tasks.auto_publish_pending_drafts",
        "schedule": 300.0,
        "options": {"queue": "publish", "expires": 300.0},
    },
    # 3. Sniper Check Targets (120/600 seconds)
    "sniper-check-targets-every-120-seconds": {
        "task": "xbot.tasks.sniper_check_targets",
        "schedule": 120.0,
        "options": {"expires": 120.0},
    },
    # 4. Check Trend Radar (1800 seconds)
    "check-trend-radar-every-1800-seconds": {
        "task": "xbot.tasks.check_trend_radar",
        "schedule": 1800.0,
        "options": {"expires": 1800.0},
    },
    # 5. Check Profile Circadian Schedules (60 seconds)
    "check-schedules-every-60-seconds": {
        "task": "xbot.tasks.check_schedules",
        "schedule": 60.0,
        "options": {"expires": 60.0},
    },
    # 6. Trend Researcher (25 min - SearXNG / Web grounding)
    "trend-researcher-every-25m": {
        "task": "xbot.pipelines.trend_researcher_pipeline.run_trend_researcher",
        "schedule": 1500.0,
        "options": {"expires": 1500.0},
    },
    # 7. Instant Trend Growth Pipeline (every 60s)
    "instant-trend-campaign-runner-every-60s": {
        "task": "xbot.tasks.process_active_instant_trend_campaigns",
        "schedule": 60.0,
        "options": {"expires": 60.0},
    },
    # 8. Follow-for-Follow & 500 Verified Follower Reciprocity Pipeline (every 10 min)
    "follow-reciprocity-pipeline-every-10m": {
        "task": "xbot.pipelines.follow_pipeline.run_follow_pipeline",
        "schedule": 600.0,
        "options": {"expires": 600.0},
    },
    # 9. Follow Growth Visual Promotion Pipeline (every 90 min)
    "follow-growth-post-pipeline-every-90m": {
        "task": "xbot.pipelines.follow_growth_post_pipeline.run_follow_growth_post",
        "schedule": 5400.0,
        "options": {"expires": 5400.0},
    },
}

# Auto-discover and import tasks across all xbot packages
celery_app.conf.imports = [
    "xbot.tasks.sniper_tasks",
    "xbot.tasks.publish_tasks",
    "xbot.tasks.trend_tasks",
    "xbot.tasks.instant_trend_tasks",
    "xbot.tasks.creator_sync_tasks",
    "xbot.tasks.circadian_tasks",
    "xbot.tasks.sentinel_tasks",
    "xbot.tasks.maintenance_tasks",
    "xbot.tasks.reflection_tasks",
    "xbot.pipelines.browser_queue",
    "xbot.pipelines.like_pipeline",
    "xbot.pipelines.reply_pipeline",
    "xbot.pipelines.quote_pipeline",
    "xbot.pipelines.follow_pipeline",
    "xbot.pipelines.trend_researcher_pipeline",
    "xbot.pipelines.trend_generator_pipeline",
    "xbot.pipelines.follow_growth_post_pipeline",
    "xbot.pipelines.notification_engagement_pipeline",
]
celery_app.autodiscover_tasks(["xbot", "xbot.tasks", "xbot.pipelines"])


from celery.signals import worker_process_init

@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Dispose of engine connections across fork boundaries to ensure zero loop pollution."""
    from xbot.database import engine
    try:
        engine.sync_engine.dispose()
    except Exception:
        pass

