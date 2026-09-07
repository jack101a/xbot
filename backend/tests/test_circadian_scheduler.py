import datetime
import pytest
from xbot.scheduler.circadian import (
    CircadianScheduleSlot,
    generate_daily_circadian_schedule,
    is_within_active_session,
)


def test_generate_daily_circadian_schedule_bounds():
    slots = generate_daily_circadian_schedule(
        wake_hour=8,
        sleep_hour=23,
        target_sessions=4,
        skip_probability=0.0,
        seed=42,
    )
    assert len(slots) == 4
    for slot in slots:
        assert 15 <= slot.duration_minutes <= 45
        assert slot.start_hour >= 8
        assert slot.start_hour < 23
        assert not slot.is_skipped


def test_sleep_block_preservation():
    slots = generate_daily_circadian_schedule(
        wake_hour=8,
        sleep_hour=23,
        target_sessions=5,
        skip_probability=0.0,
        seed=100,
    )
    # Ensure no slot starts during sleep hours (23:00 to 07:59)
    for slot in slots:
        assert not (slot.start_hour >= 23 or slot.start_hour < 8)


def test_is_within_active_session():
    slot1 = CircadianScheduleSlot(
        start_hour=14,
        start_minute=30,
        duration_minutes=30,
        target_wave="US_MORNING",
        is_skipped=False,
    )
    slots = [slot1]

    # Exactly during session (14:45)
    t_inside = datetime.time(14, 45)
    assert is_within_active_session(t_inside, slots) is True

    # Before session (14:15)
    t_before = datetime.time(14, 15)
    assert is_within_active_session(t_before, slots) is False

    # After session (15:05)
    t_after = datetime.time(15, 5)
    assert is_within_active_session(t_after, slots) is False
