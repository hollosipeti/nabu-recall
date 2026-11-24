"""Timestamp boundaries for explicitly time-scoped conversation recall.

Only timestamps on user journal turns count. Durable facts have no assertion
date and cannot prove what was said yesterday.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re

TZ = ZoneInfo("Europe/Budapest")
_YESTERDAY = re.compile(r"\b(?:tegnap|tegnapi)\b", re.I)


def journal_window(query, now=None):
    """Return yesterday's half-open UTC-epoch range, or None if not scoped."""
    if not isinstance(query, str) or not _YESTERDAY.search(query):
        return None
    clock = now or datetime.now(TZ)
    local = clock.astimezone(TZ)
    current_midnight = datetime(local.year, local.month, local.day,
                                tzinfo=TZ)
    yesterday = current_midnight - timedelta(days=1)
    return int(yesterday.timestamp()), int(current_midnight.timestamp())


def in_window(turn, window):
    try:
        return window[0] <= int(turn["created"]) < window[1]
    except (TypeError, ValueError, KeyError):
        return False
