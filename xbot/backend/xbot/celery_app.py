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
)

# Celery Beat Periodic Schedule
celery_app.conf.beat_schedule = {
    "check-schedules-every-60-seconds": {
        "task": "xbot.tasks.check_schedules",
        "schedule": 60.0,
    },
    "sniper-check-targets-every-120-seconds": {
        "task": "xbot.tasks.sniper_check_targets",
        "schedule": 120.0,
    },
    "fast-response-sentinel-every-90-seconds": {
        "task": "xbot.tasks.fast_response_sentinel",
        "schedule": 90.0,
    },
    "check-trend-radar-every-1800-seconds": {
        "task": "xbot.tasks.check_trend_radar",
        "schedule": 1800.0,
    },
    "auto-publish-pending-drafts-every-300-seconds": {
        "task": "xbot.tasks.auto_publish_pending_drafts",
        "schedule": 300.0,  # 5 minutes
    },
    "f4f-growth-and-autofollowback-every-600-seconds": {
        "task": "xbot.tasks.run_growth_and_autofollowback",
        "schedule": 600.0,  # 10 minutes
    },
    "sync-creator-studio-every-12-hours": {
        "task": "xbot.tasks.sync_all_profiles_creator_studio",
        "schedule": 43200.0,  # 12 hours
    },
}

# Auto-discover tasks in the xbot package
celery_app.autodiscover_tasks(["xbot"])
