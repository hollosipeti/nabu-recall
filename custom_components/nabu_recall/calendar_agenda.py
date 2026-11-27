"""Conservative local agenda fast path. Unrecognized speech goes to the AI."""
import re
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from .calendar_ranges import MONTHS

_PERIODS = {"ma":"today", "mára":"today", "holnap":"tomorrow", "holnapra":"tomorrow",
            "hétvégén":"weekend", "jövő héten":"next_week", "a jövő héten":"next_week"}
_MONTHS = dict(zip(("januárban","februárban","márciusban","áprilisban","májusban","júniusban","júliusban","augusztusban","szeptemberben","októberben","novemberben","decemberben"), range(1,13)))


def agenda_args(text, now):
    if not isinstance(text, str):
        return None
    text = " ".join(text.casefold().strip().rstrip("?! .").split())
    # No standalone 'mi lesz holnap': weather, news and other topics can be meant.
    # Require explicit agenda vocabulary or the established 'mi van mára' idiom.
    if text == "mi van mára":
        return {"period":"today"}
    m = re.fullmatch(r"(?:mi(?:lyen)? (?:program(?:jaim|om|ok)?|esemény(?:eim|em|ek)?) (?:van|vannak|lesz|lesznek)|(?:mi|mik) (?:van|vannak|lesz|lesznek) (?:a )?naptár(?:amban|ban)) (.+)", text)
    if not m:
        m = re.fullmatch(r"(?:mi|mik) (?:van|vannak|lesz|lesznek) (.+) (?:a )?naptár(?:amban|ban)", text)
    if not m:
        return None
    value = m.group(1)
    if value in _PERIODS:
        return {"period":_PERIODS[value]}
    if value in _MONTHS:
        month = _MONTHS[value]
        year = now.year + int(month < now.month)
        first = date(year,month,1)
        after = date(year + int(month == 12), month % 12 + 1, 1)
        return {"period":"range","start_date":first.isoformat(),"last_day_inclusive":(after-timedelta(days=1)).isoformat()}
    return None


def day_label(value):
    d = date.fromisoformat(value)
    return f"{d.year}. {MONTHS[d.month-1]} {d.day}."


def format_agenda(data, tz):
    lines = []
    for event in data["events"]:
        title = event["summary"]
        if event["all_day"]:
            first = day_label(event["date"])
            last = event.get("last_day_inclusive")
            when = first + (" – " + day_label(last) if last else "")
        else:
            start = datetime.fromisoformat(event["start"]).astimezone(tz)
            end = datetime.fromisoformat(event["end"]).astimezone(tz)
            when = f"{day_label(start.date().isoformat())} {start:%H:%M} – "
            if end.date() != start.date():
                when += day_label(end.date().isoformat()) + " "
            when += f"{end:%H:%M}"
        lines.append(f"{when}: {title}.")
    if data.get("calendars_failed"):
        lines.append("Nem minden naptár volt elérhető, ezért a lista hiányos lehet.")
    return " ".join(lines) if lines else "A lekérdezett időszakban nincs esemény."


async def direct_agenda(hass, entry, user_input):
    from homeassistant.util import dt as dt_util
    from .llm import QueryCalendarTool, available_calendars
    now = dt_util.now()
    args = agenda_args(user_input.text, now)
    if args is None:
        return None
    default = entry.options.get("calendar_entity", entry.data.get("calendar_entity"))
    ctx = SimpleNamespace(assistant="conversation", context=user_input.context)
    if not available_calendars(hass, ctx, default):
        return None
    result = await QueryCalendarTool(default).async_call(hass, SimpleNamespace(tool_args=args), ctx)
    if result.error:
        return "A naptárat most nem sikerült lekérdezni."
    return format_agenda(result.data, now.tzinfo)
