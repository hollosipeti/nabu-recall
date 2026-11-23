"""Small, deterministic Hungarian calendar date/window helpers.

No HA imports, no persistence, no guessing missing event times.
"""
from datetime import date, datetime, time, timedelta, timezone
import re

WEEKDAYS = {
    "hétfő": 0, "hétfőn": 0, "kedd": 1, "kedden": 1,
    "szerda": 2, "szerdán": 2, "csütörtök": 3, "csütörtökön": 3,
    "péntek": 4, "pénteken": 4, "szombat": 5, "szombaton": 5,
    "vasárnap": 6, "vasárnapon": 6,
}


def resolve_day(value: str, now: datetime, hour: int = 0, minute: int = 0) -> date:
    """Resolve a supported calendar date without inferring a missing year."""
    key = value.casefold().strip()
    today = now.date()
    if key == "ma":
        return today
    if key == "holnap":
        return today + timedelta(days=1)
    if key == "holnapután":
        return today + timedelta(days=2)
    if key.startswith("jövő hét "):
        weekday = WEEKDAYS.get(key[len("jövő hét "):])
        if weekday is None:
            raise ValueError("Ismeretlen hétköznap")
        return today + timedelta(days=7 - today.weekday() + weekday)
    if key in WEEKDAYS:
        delta = (WEEKDAYS[key] - today.weekday()) % 7
        candidate = today + timedelta(days=delta)
        if candidate == today and datetime.combine(candidate, time(hour, minute), now.tzinfo) <= now:
            candidate += timedelta(days=7)
        return candidate
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", key):
        return date.fromisoformat(key)
    if re.fullmatch(r"\d{2}-\d{2}", key):
        month, day = (int(part) for part in key.split("-"))
        for year in range(now.year, now.year + 9):
            try:
                candidate = date(year, month, day)
            except ValueError:
                continue
            if datetime.combine(candidate, time(hour, minute), now.tzinfo) > now:
                return candidate
        raise ValueError("Nincs érvényes jövőbeli dátum")
    raise ValueError("Ismeretlen dátum; kérj pontosítást")



def _valid_local_time(value: datetime) -> bool:
    """Reject ambiguous or nonexistent local times around DST transitions."""
    if value.utcoffset() != value.replace(fold=1).utcoffset():
        return False
    roundtrip = value.astimezone(timezone.utc).astimezone(value.tzinfo)
    return roundtrip.replace(tzinfo=None) == value.replace(tzinfo=None)


def event_bounds(day: str, hour: int, minute: int, now: datetime,
                 duration: int | None = None, end_hour: int | None = None,
                 end_minute: int = 0) -> tuple[datetime, datetime]:
    """Convert request to a validated pair of local datetimes."""
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= end_minute <= 59):
        raise ValueError("Érvénytelen időpont")
    if duration is not None and not (1 <= duration <= 1440):
        raise ValueError("Érvénytelen időtartam")
    if end_hour is not None and not 0 <= end_hour <= 23:
        raise ValueError("Érvénytelen befejezési óra")
    resolved = resolve_day(day, now, hour, minute)
    start = datetime.combine(resolved, time(hour, minute), now.tzinfo)
    if not _valid_local_time(start):
        raise ValueError("Nem egyértelmű vagy nem létező helyi időpont")
    if start <= now:
        raise ValueError("A múltba nem hozható létre esemény")
    if end_hour is not None:
        end = datetime.combine(resolved, time(end_hour, end_minute), now.tzinfo)
        if not _valid_local_time(end):
            raise ValueError("Nem egyértelmű vagy nem létező befejezési időpont")
        if end <= start:
            raise ValueError("A befejezésnek a kezdés után kell lennie")
        if duration is not None and (end - start) != timedelta(minutes=duration):
            raise ValueError("A megadott időtartam és a befejezés eltér")
    else:
        end = start + timedelta(minutes=duration if duration is not None else 30)
    return start, end


def query_window(period: str, now: datetime) -> tuple[datetime, datetime]:
    """Return half-open range in local HA timezone."""
    midnight = datetime.combine(now.date(), time.min, now.tzinfo)
    if period == "today":
        return midnight, midnight + timedelta(days=1)
    if period == "tomorrow":
        start = midnight + timedelta(days=1)
        return start, start + timedelta(days=1)
    if period == "weekend":
        saturday = midnight + timedelta(days=(5 - now.weekday()) if now.weekday() <= 5 else -1)
        return saturday, saturday + timedelta(days=2)
    if period == "week":
        return midnight, midnight + timedelta(days=7)
    if period == "next":
        return now, now + timedelta(days=45)
    raise ValueError("Ismeretlen naptári időszak")


def event_overlaps(event: dict, start: datetime, end: datetime) -> bool:
    """Reject provider spillover; RFC5545 all-day end dates are exclusive."""
    def parse(value):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=start.tzinfo)
        return parsed
    try:
        first = parse(event["start"])
        last = parse(event["end"])
        return first < end and last > start
    except (ValueError, TypeError, KeyError):
        return False
