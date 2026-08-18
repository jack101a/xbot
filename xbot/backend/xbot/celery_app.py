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
}

# Auto-discover tasks in the xbot package
celery_app.autodiscover_tasks(["xbot"])
