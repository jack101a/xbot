from __future__ import annotations

import datetime
import logging
import random
from pathlib import Path
from zoneinfo import ZoneInfo

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Session, SessionStatus
from xbot.models.analytics import AnalyticsSnapshot
from xbot.persona import load_config

logger = logging.getLogger(__name__)


def generate_daily_schedule(
    timezone_str: str,
    wake_hour: int,
    sleep_hour: int,
    sessions_per_day: int,
    min_gap_minutes: int,
    day_weights: dict[int | str, float],
    target_date: datetime.date | None = None,
) -> list[datetime.datetime]:
    """
    Generates N session times for the day within the wake/sleep local hours,
    distributing them in windows with ±15m jitter.
    """
    if target_date is None:
        target_date = datetime.datetime.now(ZoneInfo(timezone_str)).date()

    day_of_week = target_date.weekday()
    weight = day_weights.get(day_of_week, day_weights.get(str(day_of_week), 1.0))

    n = round(sessions_per_day * weight)
    if n <= 0:
        return []

    awake_duration_hours = (sleep_hour - wake_hour + 1) if sleep_hour >= wake_hour else (24 - wake_hour + sleep_hour + 1)
    if awake_duration_hours <= 0 or awake_duration_hours > 24:
        wake_hour, sleep_hour = 8, 22
        awake_duration_hours = 15

    awake_duration_minutes = awake_duration_hours * 60
    window_size_minutes = max(15, awake_duration_minutes // n)

    schedule_times: list[datetime.datetime] = []

    for i in range(n):
        window_start = wake_hour * 60 + i * window_size_minutes
        window_end = window_start + window_size_minutes

        random_minute = random.randint(window_start, window_end)
        jitter = random.randint(-15, 15)
        minute_today = random_minute + jitter

        # Clamp between wake_hour and sleep_hour
        minute_today = max(wake_hour * 60, min(sleep_hour * 60, minute_today))

        hour = minute_today // 60
        minute = minute_today % 60

        try:
            local_dt = datetime.datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                hour,
                minute,
                0,
                tzinfo=ZoneInfo(timezone_str),
            )
            # Convert to UTC datetime
            utc_dt = local_dt.astimezone(datetime.timezone.utc)
            schedule_times.append(utc_dt)
        except Exception as e:
            logger.error("Failed to build datetime for schedule slot %d: %s", i, e)

    schedule_times.sort()

    # Enforce minimum gap
    filtered_times: list[datetime.datetime] = []
    for t in schedule_times:
        if not filtered_times:
            filtered_times.append(t)
        else:
            gap = (t - filtered_times[-1]).total_seconds() / 60
            if gap >= min_gap_minutes:
                filtered_times.append(t)
            else:
                adjusted = filtered_times[-1] + datetime.timedelta(
                    minutes=min_gap_minutes
                )
                local_adjusted = adjusted.astimezone(ZoneInfo(timezone_str))
                if local_adjusted.hour < sleep_hour or (
                    local_adjusted.hour == sleep_hour and local_adjusted.minute == 0
                ):
                    filtered_times.append(adjusted)

    return filtered_times


def save_daily_schedule_to_redis(
    profile_slug: str, date_str: str, schedule_times: list[datetime.datetime]
) -> None:
    """Saves generated schedule datetimes as sorted set in Redis."""
    r = redis.from_url(settings.REDIS_URL)
    key = f"schedule:{profile_slug}:{date_str}"
    r.delete(key)

    for t in schedule_times:
        val = t.isoformat() + "Z"
        score = t.timestamp()
        r.zadd(key, {val: score})
    logger.info("Saved daily schedule with %d sessions to Redis key %s", len(schedule_times), key)


async def check_and_trigger_schedules(
    db: AsyncSession,
    now_utc: datetime.datetime | None = None,
    base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles",
) -> None:
    """
    Called every 60s by Celery Beat:
    1. Checks if active profiles are due for a session.
    2. Enforces min_gap and handles 10% natural skips.
    3. Triggers worker runs.
    """
    if now_utc is None:
        now_utc = datetime.datetime.utcnow()

    r = redis.from_url(settings.REDIS_URL)
    if r.get("system:paused") == b"1":
        logger.info("System-wide pause is active. Skipping scheduler check.")
        return

    # 1. Fetch active profiles
    stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
    res = await db.execute(stmt)
    active_profiles = res.scalars().all()

    for profile in active_profiles:
        profile_dir = Path(base_profile_dir) / profile.profile_slug
        if not profile_dir.exists():
            continue

        # Load config to get timezone & natural parameters
        config = load_config(profile_dir)
        timezone_str = config.schedule.timezone or "America/New_York"
        try:
            tz = ZoneInfo(timezone_str)
        except Exception:
            tz = ZoneInfo("America/New_York")

        min_gap_minutes = getattr(config.schedule, "interval_minutes", 20) or 20
        min_sessions = getattr(config.schedule, "min_sessions_per_day", 12) or 12
        max_sessions = getattr(config.schedule, "max_sessions_per_day", 48) or 48

        # Extract wake/sleep details (e.g. from active_hours "00:00-23:59" or "08:00-22:00")
        wake_hour, sleep_hour = 8, 22
        active_hours = config.schedule.active_hours or "08:00-22:00"
        parts = active_hours.split("-")
        if len(parts) == 2:
            try:
                wake_hour = int(parts[0].split(":")[0])
                sleep_hour = int(parts[1].split(":")[0])
            except ValueError:
                pass

        awake_duration_hours = (sleep_hour - wake_hour + 1) if sleep_hour >= wake_hour else (24 - wake_hour + sleep_hour + 1)
        if awake_duration_hours <= 0 or awake_duration_hours > 24:
            awake_duration_hours = 24
        awake_duration_minutes = awake_duration_hours * 60

        # Dynamically scale sessions_per_day based on available awake duration and interval
        target_sessions = int(awake_duration_minutes / max(min_gap_minutes + 5, 20))
        sessions_per_day = max(min_sessions, min(max_sessions, target_sessions))

        # Get current date in profile local timezone
        now_aware_utc = now_utc.replace(tzinfo=datetime.timezone.utc)
        local_now = now_aware_utc.astimezone(tz)
        local_date_str = local_now.strftime("%Y-%m-%d")

        # Trigger daily analytics snapshot scrape if not done today
        redis_lock_key = f"lock:analytics_trigger:{profile.profile_slug}:{local_date_str}"
        if not r.exists(redis_lock_key):
            stmt_snap = (
                select(AnalyticsSnapshot)
                .where(
                    AnalyticsSnapshot.profile_id == profile.id,
                    AnalyticsSnapshot.snapshot_date == local_now.date(),
                )
                .limit(1)
            )
            res_snap = await db.execute(stmt_snap)
            snap_today = res_snap.scalar_one_or_none()

            if not snap_today:
                # Set a Redis lock key for 24h to avoid duplicate triggering
                r.set(redis_lock_key, "1", ex=86400)
                from xbot.tasks import collect_analytics_snapshot
                collect_analytics_snapshot.delay(str(profile.id))
                logger.info("Triggered daily analytics collection Celery task for profile %s", profile.profile_slug)

        # Trigger daily evergreen recycling with 20% probability
        redis_evergreen_key = f"lock:evergreen_trigger:{profile.profile_slug}:{local_date_str}"
        if not r.exists(redis_evergreen_key):
            if random.random() < 0.2:
                r.set(redis_evergreen_key, "1", ex=86400)
                from xbot.tasks import run_evergreen_recycling
                run_evergreen_recycling.delay(str(profile.id))
                logger.info("Triggered evergreen recycling Celery task for profile %s", profile.profile_slug)
            else:
                # Set lock so we only roll the dice once per day
                r.set(redis_evergreen_key, "1", ex=86400)

        redis_key = f"schedule:{profile.profile_slug}:{local_date_str}"

        # 2. Self-healing: if Redis key does not exist, generate today's schedule
        if not r.exists(redis_key):
            # Parse day weights
            day_weights = {
                0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.2, 5: 0.7, 6: 0.5
            }

            times = generate_daily_schedule(
                timezone_str=timezone_str,
                wake_hour=wake_hour,
                sleep_hour=sleep_hour,
                sessions_per_day=sessions_per_day,
                min_gap_minutes=min_gap_minutes,
                day_weights=day_weights,
                target_date=local_now.date(),
            )
            save_daily_schedule_to_redis(profile.profile_slug, local_date_str, times)

        # Check daily completed session count against max_sessions
        today_start_utc = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(datetime.timezone.utc)
        stmt_count = (
            select(Session)
            .where(
                Session.profile_id == profile.id,
                Session.started_at >= today_start_utc.replace(tzinfo=None),
                Session.status == SessionStatus.COMPLETED,
            )
        )
        res_count = await db.execute(stmt_count)
        completed_today_count = len(res_count.scalars().all())
        if completed_today_count >= max_sessions:
            logger.info(
                "Profile %s has reached max sessions for today (%d/%d).",
                profile.profile_slug,
                completed_today_count,
                max_sessions,
            )
            continue

        # Check last session status and idle time
        stmt_last = (
            select(Session)
            .where(Session.profile_id == profile.id)
            .order_by(Session.started_at.desc())
            .limit(1)
        )
        res_last = await db.execute(stmt_last)
        last_session = res_last.scalar_one_or_none()

        if last_session and last_session.status == SessionStatus.RUNNING:
            logger.info(
                "Skipping schedule check for profile %s: previous session %s is still running.",
                profile.profile_slug,
                last_session.id,
            )
            continue

        idle_minutes = 999999.0
        if last_session:
            end_time = last_session.ended_at or last_session.started_at
            idle_minutes = (now_utc - end_time).total_seconds() / 60

        now_ts = now_utc.timestamp()
        due_sessions = r.zrangebyscore(redis_key, min=0, max=now_ts)

        is_due = False
        if due_sessions:
            earliest_due_str = due_sessions[0].decode("utf-8") if isinstance(due_sessions[0], bytes) else due_sessions[0]
            if idle_minutes < min_gap_minutes:
                logger.info(
                    "Postponing due session for profile %s: min gap limit active (%.1f < %d min).",
                    profile.profile_slug,
                    idle_minutes,
                    min_gap_minutes,
                )
                continue
            logger.info("Session due for profile %s: Scheduled at %s (Now is %s)", profile.profile_slug, earliest_due_str, now_utc.isoformat())
            r.zrem(redis_key, earliest_due_str)
            is_due = True
        else:
            # Continuous Autonomy Catch-Up:
            # If current time is within active hours and profile has been idle for >= min_gap_minutes:
            is_active_hour = (wake_hour <= local_now.hour <= sleep_hour) if sleep_hour >= wake_hour else (local_now.hour >= wake_hour or local_now.hour <= sleep_hour)
            if is_active_hour and idle_minutes >= min_gap_minutes:
                logger.info(
                    "Continuous autonomy catch-up triggered for profile %s: idle for %.1f min (min interval: %d min).",
                    profile.profile_slug,
                    idle_minutes,
                    min_gap_minutes,
                )
                is_due = True

        if not is_due:
            continue

        # 5. Natural Activity Gaps: 10% chance to skip
        if random.random() < 0.1:
            logger.info("Natural activity gap skip (10%% check) triggered for profile %s", profile.profile_slug)
            skipped_session = Session(
                profile_id=profile.id,
                status=SessionStatus.ABORTED,
                started_at=now_utc,
                ended_at=now_utc,
                summary={"reason": "natural_skip"},
            )
            db.add(skipped_session)
            await db.commit()
            continue

        # 6. Trigger session worker task
        from xbot.tasks import run_session
        task = run_session.delay(str(profile.id))
        logger.info("Triggered Celery task %s for profile %s", task.id, profile.profile_slug)
