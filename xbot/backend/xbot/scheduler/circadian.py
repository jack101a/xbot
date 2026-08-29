from __future__ import annotations

import datetime
import logging
import random
from typing import Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

WaveType = Literal["US_MORNING", "US_AFTERNOON", "APAC_ASIA", "EU_INDIA"]


class CircadianScheduleSlot(BaseModel):
    start_hour: int = Field(..., ge=0, le=23)
    start_minute: int = Field(..., ge=0, le=59)
    duration_minutes: int = Field(..., ge=10, le=60)
    target_wave: WaveType = Field(default="US_MORNING")
    is_skipped: bool = Field(default=False, description="Natural 10% human skip probability")


def generate_daily_circadian_schedule(
    wake_hour: int = 8,
    sleep_hour: int = 23,
    target_sessions: int = 4,
    skip_probability: float = 0.10,
    seed: int | None = None,
) -> list[CircadianScheduleSlot]:
    """
    Generates an organic episodic daily schedule with biological entropy,
    bounded jitter, and multi-timezone demographic wave alignment.
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    awake_minutes = (sleep_hour - wake_hour) * 60
    if awake_minutes <= 60 or target_sessions <= 0:
        return []

    window_size = awake_minutes // target_sessions
    slots: list[CircadianScheduleSlot] = []

    waves: list[WaveType] = ["EU_INDIA", "US_MORNING", "US_AFTERNOON", "APAC_ASIA"]

    for i in range(target_sessions):
        slot_start_min = wake_hour * 60 + i * window_size
        # Bounded randomized offset within window
        jitter = rng.randint(5, max(10, window_size - 40))
        actual_min_from_midnight = slot_start_min + jitter
        actual_min_from_midnight = min(sleep_hour * 60 - 30, max(wake_hour * 60, actual_min_from_midnight))

        start_h = actual_min_from_midnight // 60
        start_m = actual_min_from_midnight % 60
        duration = rng.randint(15, 45)

        is_skipped = rng.random() < skip_probability
        wave = waves[i % len(waves)]

        slots.append(
            CircadianScheduleSlot(
                start_hour=start_h,
                start_minute=start_m,
                duration_minutes=duration,
                target_wave=wave,
                is_skipped=is_skipped,
            )
        )

    return slots


def is_within_active_session(
    current_time: datetime.time,
    schedule_slots: list[CircadianScheduleSlot],
) -> bool:
    """
    Checks whether current_time falls inside any active non-skipped session window.
    """
    curr_min = current_time.hour * 60 + current_time.minute
    for slot in schedule_slots:
        if slot.is_skipped:
            continue
        start_min = slot.start_hour * 60 + slot.start_minute
        end_min = start_min + slot.duration_minutes
        if start_min <= curr_min <= end_min:
            return True
    return False
