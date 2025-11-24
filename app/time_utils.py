"""Utility helpers for working with timestamps.

All timestamps are represented as UNIX seconds in UTC to keep a unified format
across the application.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


def to_timestamp(dt: datetime | None) -> float:
    """Convert a datetime to a UTC UNIX timestamp.

    Naive datetimes are treated as UTC for backwards compatibility.
    """
    if dt is None:
        return 0.0

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.timestamp()


def from_timestamp(timestamp: float) -> datetime:
    """Convert a UNIX timestamp in seconds to a UTC datetime."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def current_timestamp() -> float:
    """Return the current UTC timestamp in seconds."""
    return to_timestamp(utc_now())


def seconds_since(timestamp: float, now: float | None = None) -> float:
    """Return the number of seconds since the given timestamp."""
    reference = now if now is not None else current_timestamp()
    return reference - timestamp
