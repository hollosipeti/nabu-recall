"""Optional calendar tools added to the existing Home Assistant Assist LLM API.

No extra conversation agent, scripts or second AI backend. The selected entity
is the only calendar these tools can access.
"""
import logging
from datetime import timedelta

import probatio
from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import (
    LLM_API_ASSIST, LLMContext, Tool, ToolAnnotations, ToolInput, ToolResult
)
from homeassistant.util import dt as dt_util

from .calendar_logic import event_bounds, event_overlaps, present_event, query_window, resolve_day
from .calendar_ranges import all_day_bounds, title_matches

_LOGGER = logging.getLogger(__name__)
_DOMAIN = "nabu_recall"
_READ = ToolAnnotations(read_only=True, destructive=False,
                        idempotent=True, open_world=False)
_WRITE = ToolAnnotations(read_only=False, destructive=False,
                         idempotent=False, open_world=False)


class QueryCalendarTool(Tool):
    name = "nabu_recall__calendar_query"
    title = "Query selected Nabu Recall calendar"
    description = (
        "Read the configured calendar. For 'hétvégén' use period=weekend: "
        "Saturday 00:00 through Monday 00:00 in Europe/Budapest. "
        "For 'next event' use period=next; never search only today. "
        "IMPORTANT: Call this tool for EVERY new agenda question, even if "
        "the previous user turn asked about calendar events; never reuse a "
        "previous tool result. For 'mi a következő eseményem' use period=next "
        "and consult the freshly returned event, not the earlier weekend. "
        "Only report returned events, not remembered calendar events. "
        "For an explicitly named date/weekday, use period=day and pass "
        "date EXACTLY as the user said it (e.g. 'pénteken' or 'jövő hét kedden'); "
        "period=next returns only ONE event, so it must never be used for "
        "'mi van pénteken'. The supplied date controls the entire day. "
        "Calendar event deletion and modification are NOT supported by these tools. Do not search for an "
        "event as if deletion or modification were possible; explicitly say the requested operation "
        "is not available. All-day dates in the response are DISPLAY dates, "
        "not exclusive RFC5545 end dates. "
        "For 'jövő héten' use period=next_week. Legacy week means the next 7 days. "
        "For any other interval (including 'következő két hét', a month, or "
        "two named dates), use period=range with ISO start_date inclusive "
        "and end_date exclusive (the day AFTER the final requested day). "
        "For a named event, e.g. 'mikor megyek fogorvoshoz?', use period=search "
        "and title='fogorvos', or period=range plus title for a bounded search. "
        "Search covers 365 days from now; disclose the searched range if empty. "
        "Do not use next to search by name unless the user asks for the next "
        "matching event. Do not repeat identical failed or inadequate calls. "
        "Never claim coverage outside range_start/range_end."
    )
    annotations = _READ
    integration = _DOMAIN
    parameters = probatio.Schema({
        probatio.Required("period"): probatio.In(
            ["today", "tomorrow", "weekend", "week", "next", "day", "next_week", "range", "search"]),
        probatio.Optional("date"): str,
        probatio.Optional("start_date"): str,
        probatio.Optional("end_date"): str,
        probatio.Optional("title"): str,
    })

    def __init__(self, entity_id: str):
        self.entity_id = entity_id

    async def async_call(self, hass: HomeAssistant, tool_input: ToolInput,
                         llm_context: LLMContext) -> ToolResult:
        try:
            values = self.parameters(tool_input.tool_args)
            period = values["period"]
            title = values.get("title")
            if (title is not None and not title.strip()) or (period == "search" and not title):
                raise ValueError("Hiányzó eseménynév a kereséshez")
            now = dt_util.now()
            start, end = query_window(period, now, values.get("date"),
                                      values.get("start_date"), values.get("end_date"))
            result = await hass.services.async_call(
                "calendar", "get_events",
                {"entity_id": self.entity_id,
                 "start_date_time": start.isoformat(),
                 "end_date_time": end.isoformat()},
                blocking=True, return_response=True,
                context=llm_context.context,
            )
            if not isinstance(result, dict) or self.entity_id not in result:
                raise ValueError("A naptár nem adott ellenőrizhető választ")
            events = result[self.entity_id].get("events")
            if not isinstance(events, list):
                raise ValueError("Érvénytelen naptárválasz")
            events = [e for e in events if event_overlaps(e, start, end)]
            if title is not None:
                events = [e for e in events if title_matches(e, title)]
            if period == "next":
                events = [e for e in events if
                          # Include ongoing events, not old finished events.
                          event_overlaps(e, now, end)]
                events.sort(key=lambda e: e.get("start", ""))
                events = events[:1]
            return ToolResult(data={
                "calendar": self.entity_id, "range_start": start.isoformat(),
                "range_end": end.isoformat(), "period": period,
                "events": [present_event(event) for event in events],
                "event_count": len(events),
            })
        except ValueError as exc:
            return ToolResult(data={"error": str(exc)}, error=True)
        except Exception:
            _LOGGER.exception("Nabu Recall calendar read failed")
            return ToolResult(data={"error": "Naptárlekérdezés sikertelen"},
                              error=True)


class CreateCalendarTool(Tool):
    name = "nabu_recall__calendar_create"
    title = "Create event in selected Nabu Recall calendar"
    description = (
        "Create an event in the calendar configured for Nabu Recall. "
        "date may be YYYY-MM-DD, MM-DD, 'ma', 'holnap', 'holnapután', "
        "'pénteken', 'jövő hét kedden', etc. Preserve the user's "
        "relative date expression EXACTLY as written: 'pénteken' MUST be "
        "date='pénteken', NEVER 'jövő hét pénteken'. Only use 'jövő hét' "
        "when the user explicitly said 'jövő hét'. Required: title, date. "
        "For absolute dates use ISO YYYY-MM-DD, not a different relative date. "
        "For timed events start_hour is required. For 'fél tizenegy' use "
        "hour=10, minute=30; include ending minutes when specified. "
        "Use either end_hour/end_minute or duration_minutes, not conflicting values. "
        "For an all-day event set all_day=true, omit ALL hour/minute/duration fields. "
        "For multi-day all-day events set end_date to the day AFTER the final day. "
        "For a range such as 10–11, supply end_hour=11; "
        "never fall back to 30 minutes if a finishing time was given. "
        "Default duration is 30 minutes if no end/duration is specified. "
        "Do not invent a missing date or start time; ask the user. "
        "If a date or time is rejected, ask for clarification or correct only its "
        "format with the SAME intended date/time; never substitute another day. "
        "On success report the actual returned date/start/end, not the requested "
        "values. On failure do not claim creation. Do not repeat identical calls."
    )
    annotations = _WRITE
    integration = _DOMAIN
    parameters = probatio.Schema({
        probatio.Required("title"): str,
        probatio.Required("date"): str,
        probatio.Optional("start_hour"): int,
        probatio.Optional("start_minute"): int,
        probatio.Optional("all_day"): bool,
        probatio.Optional("end_date"): str,
        probatio.Optional("duration_minutes"): int,
        probatio.Optional("end_hour"): int,
        probatio.Optional("end_minute"): int,
    })

    def __init__(self, entity_id: str):
        self.entity_id = entity_id

    async def async_call(self, hass: HomeAssistant, tool_input: ToolInput,
                         llm_context: LLMContext) -> ToolResult:
        try:
            values = self.parameters(tool_input.tool_args)
            title = values["title"].strip()
            if not title:
                raise ValueError("Hiányzó eseménynév")
            now = dt_util.now()
            all_day = values.get("all_day", False)
            payload = {"entity_id": self.entity_id, "summary": title}
            if all_day:
                if any(k in values for k in ("start_hour", "start_minute", "end_hour", "end_minute", "duration_minutes")):
                    raise ValueError("Egész napos eseményhez ne adj meg időpontot vagy időtartamot")
                start, end = all_day_bounds(values["date"], values.get("end_date"), now, resolve_day)
                payload.update(start_date=start.isoformat(), end_date=end.isoformat())
                actual = {"all_day": True, "date": start.isoformat(),
                          "last_day_inclusive": (end - timedelta(days=1)).isoformat()}
            else:
                if "start_hour" not in values:
                    raise ValueError("Hiányzó kezdési időpont")
                if "end_date" in values or ("end_minute" in values and "end_hour" not in values):
                    raise ValueError("Érvénytelen időzített esemény paraméterei")
                start, end = event_bounds(
                    values["date"], values["start_hour"],
                    values.get("start_minute", 0), now,
                    duration=values.get("duration_minutes"),
                    end_hour=values.get("end_hour"),
                    end_minute=values.get("end_minute"),
                )
                payload.update(start_date_time=start.isoformat(), end_date_time=end.isoformat())
                actual = {"all_day": False, "start": start.isoformat(), "end": end.isoformat()}
            await hass.services.async_call(
                "calendar", "create_event", payload,
                blocking=True, context=llm_context.context,
            )
            return ToolResult(data={
                "status": "service_call_succeeded",
                "calendar": self.entity_id, "title": title, **actual,
            })
        except ValueError as exc:
            return ToolResult(data={"error": str(exc)}, error=True)
        except Exception:
            _LOGGER.exception("Nabu Recall calendar creation failed")
            return ToolResult(data={"error": "Naptáresemény létrehozása sikertelen"},
                              error=True)


@callback
def async_get_tools(hass: HomeAssistant, llm_context: LLMContext,
                    api_id: str) -> LLMTools | None:
    """Advertise calendar tools only for the selected upstream agent."""
    if api_id != LLM_API_ASSIST:
        return None
    entries = [
        entry for entry in hass.config_entries.async_entries(_DOMAIN)
        if entry.data.get("upstream") == llm_context.agent_id
        and (entry.options.get("calendar_entity",
                               entry.data.get("calendar_entity")) or "")
    ]
    if len(entries) != 1:
        return None
    entry = entries[0]
    entity_id = entry.options.get(
        "calendar_entity", entry.data.get("calendar_entity")
    )
    if not entity_id or not entity_id.startswith("calendar."):
        return None
    if hass.states.get(entity_id) is None:
        return None
    return LLMTools(
        tools=[QueryCalendarTool(entity_id), CreateCalendarTool(entity_id)],
        prompt=(
            "For questions about the configured Nabu Recall calendar, use "
            "nabu_recall__calendar_query instead of calendar__get_events. "
            "For calendar creation, use nabu_recall__calendar_create. "
            "These tools enforce the calendar entity selected in the "
            "Nabu Recall integration and correct relative date boundaries. "
            "You MUST call nabu_recall__calendar_query anew for each "
            "new calendar question, even consecutive follow-ups. "
            "For 'next event' ALWAYS use period=next, NEVER infer the next "
            "event from an earlier weekend or today query. "
            "For 'mi van pénteken' or another specific day, ALWAYS use "
            "period=day and date='pénteken' (or the user's exact day). "
            "The 'next' result is only one event, not the full day's agenda. "
            "No calendar deletion or modification tool exists: for such requests clearly "
            "explain the limitation without claiming to have searched, deleted or modified. "
            "For all-day events, use the date or date + last_day_inclusive "
            "provided in the tool result; do not add one day to the date. "
            "For creation preserve the user's weekday exactly: "
            "'pénteken' never becomes 'jövő hét pénteken'. "
            "Use returned actual times; do not invent event results. "
            f"Current local date/time: {dt_util.now().isoformat()}. "
            "Follow the query/create tool schemas: next_week, range, search, all_day. "
            "Never use period=next as a name lookup. Report only the actual "
            "tool result and covered interval; if a tool fails, do not invent "
            "an alternative date or claim success. Never repeat an identical failed call."
        ),
    )
