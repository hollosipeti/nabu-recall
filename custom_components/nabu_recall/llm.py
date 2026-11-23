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

from .calendar_logic import event_bounds, event_overlaps, query_window

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
        "Do not mix results with prior conversation memories. "
        "The query interval's end is exclusive."
    )
    annotations = _READ
    integration = _DOMAIN
    parameters = probatio.Schema({
        probatio.Required("period"): probatio.In(
            ["today", "tomorrow", "weekend", "week", "next"]),
    })

    def __init__(self, entity_id: str):
        self.entity_id = entity_id

    async def async_call(self, hass: HomeAssistant, tool_input: ToolInput,
                         llm_context: LLMContext) -> ToolResult:
        try:
            period = self.parameters(tool_input.tool_args)["period"]
            now = dt_util.now()
            start, end = query_window(period, now)
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
                "range_end": end.isoformat(), "events": events,
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
        "relative date expression as written. Required: title, date, "
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
            "Use returned actual times; do not invent event results."
        ),
    )
