"""Fresh, exact single-event targeting; no destructive fallback."""
from datetime import date, datetime, time, timedelta, timezone
from .calendar_ranges import iso_day, normalize_title


def parse_bound(value):
    if not isinstance(value, str):
        raise ValueError("ISO dátum vagy időpont szükséges")
    if len(value) == 10:
        return iso_day(value)
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("Időzóna szükséges")
    return dt


async def edit_event(hass, entity, values, now):
    day = iso_day(values["date"])
    start = datetime.combine(day, time.min, now.tzinfo)
    end = start + timedelta(days=1)
    title = normalize_title(values["title"])
    if not title:
        raise ValueError("Hiányzó eseménynév")
    events = await entity.async_get_events(hass, start, end)
    matches = [event for event in events
               if normalize_title(event.summary) == title
               and (event.start.astimezone(now.tzinfo).date()
                    if isinstance(event.start, datetime) else event.start) == day
               and ("original_start" not in values
                    or event.start == parse_bound(values["original_start"]))]
    if len(matches) != 1:
        raise ValueError("Az esemény nem található vagy nem egyértelmű; pontosíts")
    event = matches[0]
    if not event.uid or not event.uid.strip():
        raise ValueError("Az eseménynek nincs használható azonosítója")
    if event.rrule and not event.recurrence_id:
        raise ValueError("Ismétlődő sorozat módosítása vagy törlése nem támogatott")
    if values["action"] == "delete":
        if any(k in values for k in ("new_title", "new_start", "new_end")):
            raise ValueError("Törléshez nem adható új érték")
        await entity.async_delete_event(event.uid, recurrence_id=event.recurrence_id)
        return {"status": "deleted", "title": event.summary, "start": event.start.isoformat()}
    if values["action"] != "update":
        raise ValueError("Ismeretlen művelet")
    if not any(k in values for k in ("new_title", "new_start", "new_end")):
        raise ValueError("Hiányzik az új érték")
    new_start = parse_bound(values["new_start"]) if "new_start" in values else event.start
    if isinstance(new_start, datetime) != isinstance(event.start, datetime):
        raise ValueError("Az egész napos és időzített típus közötti átalakítás nem támogatott")
    if "new_end" in values:
        new_end = parse_bound(values["new_end"])
    elif isinstance(new_start, datetime):
        duration = event.end.astimezone(timezone.utc) - event.start.astimezone(timezone.utc)
        new_end = (new_start.astimezone(timezone.utc) + duration).astimezone(new_start.tzinfo)
    else:
        new_end = new_start + (event.end - event.start)
    if isinstance(new_start, datetime) != isinstance(new_end, datetime) or new_end <= new_start:
        raise ValueError("Érvénytelen időtartam")
    summary = values.get("new_title", event.summary).strip()
    if not summary:
        raise ValueError("Üres eseménynév")
    # Use the same validation schema as HA's calendar editor.
    from homeassistant.components.calendar import WEBSOCKET_EVENT_SCHEMA
    payload = {"dtstart": new_start, "dtend": new_end, "summary": summary}
    for key in ("description", "location"):
        value = getattr(event, key, None)
        if value is not None:
            payload[key] = value
    payload = WEBSOCKET_EVENT_SCHEMA(payload)
    await entity.async_update_event(event.uid, payload, recurrence_id=event.recurrence_id)
    return {"status": "updated", "title": summary, "start": new_start.isoformat(), "end": new_end.isoformat()}
