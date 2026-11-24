"""Optional calendar tools added to the existing Home Assistant Assist LLM API.

No extra conversation agent, scripts or second AI backend. The selected entity
is the only calendar these tools can access.
"""
import logging

import probatio
from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import (
    LLM_API_ASSIST, LLMContext, Tool, ToolAnnotations, ToolInput, ToolResult
)
from homeassistant.util import dt as dt_util

from .calendar_logic import event_bounds, event_overlaps, present_event, query_window

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
        "Calendar event deletion is NOT supported. Do not search for an "
        "event as if a deletion were possible; explicitly say deletion "
        "is not available. All-day dates in the response are DISPLAY dates, "
        "not exclusive RFC5545 end dates."
    )
    annotations = _READ
    integration = _DOMAIN
    parameters = probatio.Schema({
        probatio.Required("period"): probatio.In(
            ["today", "tomorrow", "weekend", "week", "next", "day"]),
        probatio.Optional("date"): str,
    })

    def __init__(self, entity_id: str):
        self.entity_id = entity_id

    async def async_call(self, hass: HomeAssistant, tool_input: ToolInput,
                         llm_context: LLMContext) -> ToolResult:
        try:
            period = self.parameters(tool_input.tool_args)["period"]
            now = dt_util.now()
            start, end = query_window(period, now, tool_input.tool_args.get("date"))
            result = await hass.services.async_call(
                "calendar", "get_events",
                {"entity_id": self.entity_id,
                 "start_date_time": start.isoformat(),
                 "end_date_time": end.isoformat()},
                blocking=True, return_response=True,
                context=llm_context.context,
            )
            events = (result or {}).get(self.entity_id, {}).get("events", [])
            events = [e for e in events if event_overlaps(e, start, end)]
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
        "when the user explicitly said 'jövő hét'. Required: title, date, "
        "start_hour. For a range such as 10–11, supply end_hour=11; "
        "never fall back to 30 minutes if a finishing time was given. "
        "Default duration is 30 minutes if no end/duration is specified. "
        "Do not invent a missing date or start time; ask the user."
    )
    annotations = _WRITE
    integration = _DOMAIN
    parameters = probatio.Schema({
        probatio.Required("title"): str,
        probatio.Required("date"): str,
        probatio.Required("start_hour"): int,
        probatio.Optional("start_minute", default=0): int,
        probatio.Optional("duration_minutes"): int,
        probatio.Optional("end_hour"): int,
        probatio.Optional("end_minute", default=0): int,
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
            start, end = event_bounds(
                values["date"], values["start_hour"],
                values.get("start_minute", 0), dt_util.now(),
                duration=values.get("duration_minutes"),
                end_hour=values.get("end_hour"),
                end_minute=values.get("end_minute", 0),
            )
            await hass.services.async_call(
                "calendar", "create_event",
                {"entity_id": self.entity_id, "summary": title,
                 "start_date_time": start.isoformat(),
                 "end_date_time": end.isoformat()},
                blocking=True, context=llm_context.context,
            )
            return ToolResult(data={
                "status": "service_call_succeeded",
                "calendar": self.entity_id, "title": title,
                "start": start.isoformat(), "end": end.isoformat(),
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
            "No calendar deletion tool exists: for deletion requests clearly "
            "explain the limitation without claiming to have searched or deleted. "
            "For all-day events, use the date or date + last_day_inclusive "
            "provided in the tool result; do not add one day to the date. "
            "For creation preserve the user's weekday exactly: "
            "'pénteken' never becomes 'jövő hét pénteken'. "
            "Use returned actual times; do not invent event results."
        ),
    )
