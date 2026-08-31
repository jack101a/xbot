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
    # 1. Central Browser Queue Worker (10s)
    "browser-queue-worker-every-10s": {
        "task": "xbot.pipelines.browser_queue.process_browser_queue",
        "schedule": 10.0,
    },
    # 2. Independent Like Pipeline (15 min)
    "like-pipeline-every-15m": {
        "task": "xbot.pipelines.like_pipeline.run_like_pipeline",
        "schedule": 900.0,
    },
    # 3. Unified Reply Pipeline (5 min)
    "reply-pipeline-every-5m": {
        "task": "xbot.pipelines.reply_pipeline.run_reply_pipeline",
        "schedule": 300.0,
    },
    # 4. Independent Quote Pipeline (15 min)
    "quote-pipeline-every-15m": {
        "task": "xbot.pipelines.quote_pipeline.run_quote_pipeline",
        "schedule": 900.0,
    },
    # 5. Independent Follow & Reciprocity Pipeline (1 hour)
    "follow-pipeline-every-1h": {
        "task": "xbot.pipelines.follow_pipeline.run_follow_pipeline",
        "schedule": 3600.0,
    },
    # 6. Trend Researcher Pipeline (25 min - 24/7)
    "trend-researcher-every-25m": {
        "task": "xbot.pipelines.trend_researcher_pipeline.run_trend_researcher",
        "schedule": 1500.0,
    },
    # 7. Trend Generator Pipeline (20 min - 24/7)
    "trend-generator-every-20m": {
        "task": "xbot.pipelines.trend_generator_pipeline.run_trend_generator",
        "schedule": 1200.0,
    },
    # 8. Auto-Publish Approved Drafts (5 min)
    "auto-publish-pending-drafts-every-300-seconds": {
        "task": "xbot.tasks.auto_publish_pending_drafts",
        "schedule": 300.0,
    },
    # 9. Sync Creator Studio Metrics (12 hours)
    "sync-creator-studio-every-12-hours": {
        "task": "xbot.tasks.sync_all_profiles_creator_studio",
        "schedule": 43200.0,
    },
    # 10. Follow Growth Milestone & Visual Promotion Pipeline (1 hour)
    "follow-growth-post-every-1h": {
        "task": "xbot.pipelines.follow_growth_post_pipeline.run_follow_growth_post",
        "schedule": 3600.0,
    },
    # 11. Autonomous Notification & Follow-Back Engagement Pipeline (30 min)
    "notification-engagement-every-30m": {
        "task": "xbot.pipelines.notification_engagement_pipeline.run_notification_engagement",
        "schedule": 1800.0,
    },
    # 12. Sniper Check Targets (120 seconds)
    "sniper-check-targets-every-120-seconds": {
        "task": "xbot.tasks.sniper_check_targets",
        "schedule": 120.0,
    },
    # 13. Check Trend Radar (1800 seconds)
    "check-trend-radar-every-1800-seconds": {
        "task": "xbot.tasks.check_trend_radar",
        "schedule": 1800.0,
    },
    # 14. Check Profile Circadian Schedules (60 seconds)
    "check-schedules-every-60-seconds": {
        "task": "xbot.tasks.check_schedules",
        "schedule": 60.0,
    },
}

# Auto-discover and import tasks across all xbot packages
celery_app.conf.imports = [
    "xbot.tasks.sniper_tasks",
    "xbot.tasks.publish_tasks",
    "xbot.tasks.trend_tasks",
    "xbot.tasks.creator_sync_tasks",
    "xbot.tasks.circadian_tasks",
    "xbot.tasks.sentinel_tasks",
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

