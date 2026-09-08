"""Time and timezone utility functions for xbot.

Indian Standard Time (IST - Asia/Kolkata, UTC+5:30) is the standard system timezone.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

# Indian Standard Time (Asia/Kolkata: UTC+5:30)
IST = ZoneInfo("Asia/Kolkata")
DEFAULT_TIMEZONE = "Asia/Kolkata"


def now_ist() -> datetime.datetime:
    """Return the current naive datetime in Indian Standard Time (Asia/Kolkata).

    Ideal for storing in SQLite / SQLAlchemy DateTime columns.
    """
    return datetime.datetime.now(IST).replace(tzinfo=None)


def now_ist_aware() -> datetime.datetime:
    """Return the current timezone-aware datetime in Indian Standard Time (Asia/Kolkata)."""
    return datetime.datetime.now(IST)


def now_ist_iso() -> str:
    """Return the current datetime as an ISO-8601 string with IST offset (+05:30)."""
    return datetime.datetime.now(IST).isoformat()


def to_ist(dt: datetime.datetime | None) -> datetime.datetime | None:
    """Convert any datetime (naive UTC or aware) to naive IST datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime was UTC
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(IST).replace(tzinfo=None)


def to_ist_iso(dt: datetime.datetime | None) -> str | None:
    """Format any datetime as an ISO string in IST."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive, treat as IST
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)
    return dt.isoformat()
