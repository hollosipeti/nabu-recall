"""Optional calendar tools added to the existing Home Assistant Assist LLM API.

No extra conversation agent, scripts or second AI backend. The selected entity
is the default write target; other Assist-exposed calendars are discoverable.
"""
import logging
from datetime import datetime, timedelta

import probatio
from homeassistant.components.llm import LLMTools
from homeassistant.components.homeassistant import async_should_expose
from homeassistant.components.calendar.const import CalendarEntityFeature, DATA_COMPONENT
from homeassistant.helpers import entity_registry as er, intent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import (
    LLM_API_ASSIST, LLMContext, Tool, ToolAnnotations, ToolInput, ToolResult
)
from homeassistant.util import dt as dt_util

from .calendar_logic import event_bounds, event_overlaps, present_event, query_window, resolve_day
from .calendar_ranges import all_day_bounds, title_matches
from .calendar_mutation import edit_event

_LOGGER = logging.getLogger(__name__)
_DOMAIN = "nabu_recall"
_READ = ToolAnnotations(read_only=True, destructive=False,
                        idempotent=True, open_world=False)
_WRITE = ToolAnnotations(read_only=False, destructive=False,
                         idempotent=False, open_world=False)


def available_calendars(hass, llm_context, default_id):
    """Explicitly configured default plus calendars exposed to this assistant."""
    registry = er.async_get(hass)
    calendars = {}
    for state in hass.states.async_all("calendar"):
        eid = state.entity_id
        if eid != default_id and not async_should_expose(hass, llm_context.assistant, eid):
            continue
        aliases = intent.async_get_entity_aliases(hass, registry.async_get(eid), state=state)
        calendars[eid] = {"name": state.name, "aliases": sorted(set(aliases)),
                          "available": state.state not in ("unknown", "unavailable"),
                          "writable": bool(state.attributes.get("supported_features", 0)
                                           & CalendarEntityFeature.CREATE_EVENT),
                          "deletable": bool(state.attributes.get("supported_features", 0) & CalendarEntityFeature.DELETE_EVENT),
                          "updatable": bool(state.attributes.get("supported_features", 0) & CalendarEntityFeature.UPDATE_EVENT)}
    return calendars


def select_calendar(calendars, target):
    """Resolve an exact ID, name or alias; never guess an ambiguous target."""
    if not isinstance(target, str) or not target.strip():
        raise ValueError("Hiányzó naptárnév")
    target = target.strip()
    if target in calendars:
        return target
    matches = [eid for eid, info in calendars.items()
               if target.casefold() in {v.casefold() for v in [info["name"], *info["aliases"]]}]
    if len(matches) != 1:
        raise ValueError("A naptár nem található vagy nem egyértelmű")
    return matches[0]


def event_sort_key(event, tz):
    value = datetime.fromisoformat(event["start"])
    return value.replace(tzinfo=tz) if value.tzinfo is None else value


async def read_calendars(hass, llm_context, ids, start, end):
    """One service call normally; isolate provider failures only on exception."""
    async def read(targets):
        return await hass.services.async_call(
            "calendar", "get_events",
            {"entity_id": targets[0] if len(targets) == 1 else targets,
             "start_date_time": start.isoformat(), "end_date_time": end.isoformat()},
            blocking=True, return_response=True, context=llm_context.context)
    try:
        result = await read(ids)
    except Exception:
        if len(ids) == 1:
            raise
        import asyncio
        parts = await asyncio.gather(*(read([eid]) for eid in ids), return_exceptions=True)
        result = {}
        for eid, part in zip(ids, parts):
            if isinstance(part, dict) and eid in part:
                result[eid] = part[eid]
    return result if isinstance(result, dict) else {}


class EditCalendarTool(Tool):
    name = "nabu_recall__calendar_edit"
    title = "Modify or delete one existing calendar event"
    description = (
        "Only for an explicit edit or delete request. Supply the exact original title, "
        "calendar and original ISO day from a fresh query. Ambiguous matches are rejected. "
        "For update supply new_title, new_start and/or new_end (ISO dates or timezone-aware datetimes); "
        "moving start alone preserves duration. All-day new_end is exclusive. "
        "Only single events or one identified occurrence, never an entire recurring series. "
        "If unsupported, report that limitation; never delete and recreate."
    )
    annotations = ToolAnnotations(read_only=False, destructive=True, idempotent=False, open_world=False)
    integration = _DOMAIN
    parameters = probatio.Schema({
        probatio.Required("action"): probatio.In(["update", "delete"]),
        probatio.Required("calendar"): str,
        probatio.Required("title"): str,
        probatio.Required("date"): str,
        probatio.Optional("original_start"): str,
        probatio.Optional("new_title"): str,
        probatio.Optional("new_start"): str,
        probatio.Optional("new_end"): str,
    })

    def __init__(self, entity_id):
        self.entity_id = entity_id

    async def async_call(self, hass, tool_input, llm_context):
        try:
            values = self.parameters(tool_input.tool_args)
            calendars = available_calendars(hass, llm_context, self.entity_id)
            target = select_calendar(calendars, values["calendar"])
            info = calendars[target]
            if not info["available"] or not info["deletable" if values["action"] == "delete" else "updatable"]:
                raise ValueError("A naptár nem támogatja a kért műveletet")
            # Match the permission check used by HA's calendar WebSocket API.
            user_id = getattr(llm_context.context, "user_id", None)
            if user_id:
                from homeassistant.auth.permissions.const import POLICY_CONTROL
                user = await hass.auth.async_get_user(user_id)
                if user is None or not user.permissions.check_entity(target, POLICY_CONTROL):
                    raise ValueError("Nincs jogosultság a naptár módosítására")
            entity = hass.data[DATA_COMPONENT].get_entity(target)
            if entity is None:
                raise ValueError("A naptár nem elérhető")
            feature = CalendarEntityFeature.DELETE_EVENT if values["action"] == "delete" else CalendarEntityFeature.UPDATE_EVENT
            if not entity.supported_features & feature:
                raise ValueError("A naptár nem támogatja a kért műveletet")
            result = await edit_event(hass, entity, values, dt_util.now())
            return ToolResult(data={**result, "calendar": target})
        except ValueError as exc:
            return ToolResult(data={"error": str(exc)}, error=True)
        except Exception:
            _LOGGER.exception("Nabu Recall calendar edit failed")
            return ToolResult(data={"error": "A naptári művelet nem igazolt"}, error=True)


class QueryCalendarTool(Tool):
    name = "nabu_recall__calendar_query"
    title = "Query Nabu Recall calendars"
    description = (
        "Read live events from all exposed calendars, or one explicitly requested calendar. "
        "Use range with inclusive ISO dates for a specified month or interval; day with the user's exact date expression; next_week for next Monday through Sunday. "
        "Use next only for the first unfiltered event; upcoming for semantic categories or synonyms (45 days, all candidates). "
        "Search uses a literal title substring over 365 days; broaden if no match. "
        "Use actual event meaning, not calendar name. Report complete display_time and partial failures. Multi-day events last from date through last_day_inclusive, not the whole month. "
        "For calendar discovery use calendars. Never infer absence outside the returned interval."
    )
    annotations = _READ
    integration = _DOMAIN
    parameters = probatio.Schema({
        probatio.Required("period"): probatio.In(
            ["today", "tomorrow", "weekend", "week", "next", "day", "next_week", "range", "search", "calendars", "upcoming"]),
        probatio.Optional("calendar"): str,
        probatio.Optional("date"): str,
        probatio.Optional("start_date"): str,
        probatio.Optional("last_day_inclusive"): str,
        probatio.Optional("title"): str,
    })

    def __init__(self, entity_id: str):
        self.entity_id = entity_id

    async def async_call(self, hass: HomeAssistant, tool_input: ToolInput,
                         llm_context: LLMContext) -> ToolResult:
        try:
            values = self.parameters(tool_input.tool_args)
            period = values["period"]
            calendars = available_calendars(hass, llm_context, self.entity_id)
            if period == "calendars":
                return ToolResult(data={"calendars": calendars, "default_calendar": self.entity_id})
            target = values.get("calendar")
            requested = [select_calendar(calendars, target)] if target is not None else sorted(calendars)
            ids = [eid for eid in requested if calendars[eid]["available"]]
            failed = [eid for eid in requested if eid not in ids]
            if not ids:
                raise ValueError("Nincs elérhető naptár a lekérdezéshez")
            title = values.get("title")
            if (title is not None and not title.strip()) or (period == "search" and not title):
                raise ValueError("Hiányzó eseménynév a kereséshez")
            now = dt_util.now()
            end_date = None
            if period == "range":
                from .calendar_ranges import iso_day
                last_day = values.get("last_day_inclusive")
                if not last_day:
                    raise ValueError("Hiányzik az utolsó kért nap")
                end_date = (iso_day(last_day) + timedelta(days=1)).isoformat()
            elif "last_day_inclusive" in values:
                raise ValueError("Érvénytelen dátumtartomány")
            start, end = query_window(period, now, values.get("date"),
                                      values.get("start_date"), end_date)
            result = await read_calendars(hass, llm_context, ids, start, end)
            events = []
            for eid in ids:
                payload = result.get(eid)
                if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
                    failed.append(eid)
                    continue
                for event in payload["events"]:
                    if not isinstance(event, dict) or not event_overlaps(event, start, end):
                        continue
                    if title is not None and not title_matches(event, title):
                        continue
                    if period == "next" and not event_overlaps(event, now, end):
                        continue
                    events.append((event, eid))
            if len(failed) == len(requested):
                raise ValueError("Egyik kért naptár sem adott ellenőrizhető választ")
            events.sort(key=lambda pair: event_sort_key(pair[0], start.tzinfo))
            if period == "next":
                events = events[:1]
            return ToolResult(data={
                "title_filter": title, "title_filter_is_literal": True,
                "calendar": requested[0] if len(requested) == 1 else "all",
                "calendars_queried": [eid for eid in requested if eid not in failed],
                "calendars_failed": failed,
                "range_start": start.isoformat(), "range_end": end.isoformat(), "period": period,
                "events": [{**present_event(event), "calendar": eid,
                            "calendar_name": calendars[eid]["name"]} for event, eid in events],
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
        "Create an event in the default calendar unless another is explicitly requested. "
        "Pass the user's exact relative date expression or ISO date. Timed events require start_hour; specify end_hour/end_minute or duration_minutes (default 30). "
        "For overnight events supply actual end_date and end time. All-day events omit time fields; end_date is exclusive for all-day events. "
        "Ask for missing or ambiguous date/time. Report success only when the tool confirms it."
    )
    annotations = _WRITE
    integration = _DOMAIN
    parameters = probatio.Schema({
        probatio.Required("title"): str,
        probatio.Optional("calendar"): str,
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
            calendars = available_calendars(hass, llm_context, self.entity_id)
            target = select_calendar(calendars, values["calendar"]) if "calendar" in values else self.entity_id
            info = calendars.get(target)
            if not target:
                raise ValueError("Nincs alapértelmezett naptár; nevezd meg a cél naptárat")
            if not info or not info["available"] or not info["writable"]:
                raise ValueError("A kért naptár nem elérhető vagy nem írható")
            payload = {"entity_id": target, "summary": title}
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
                if ("end_date" in values or "end_minute" in values) and "end_hour" not in values:
                    raise ValueError("Érvénytelen időzített esemény paraméterei")
                start, end = event_bounds(
                    values["date"], values["start_hour"],
                    values.get("start_minute", 0), now,
                    duration=values.get("duration_minutes"),
                    end_hour=values.get("end_hour"),
                    end_minute=values.get("end_minute"),
                    end_date=values.get("end_date"),
                )
                payload.update(start_date_time=start.isoformat(), end_date_time=end.isoformat())
                actual = {"all_day": False, "start": start.isoformat(), "end": end.isoformat()}
            await hass.services.async_call(
                "calendar", "create_event", payload,
                blocking=True, context=llm_context.context,
            )
            return ToolResult(data={
                "status": "service_call_succeeded",
                "calendar": target, "title": title, **actual,
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

    ]
    if len(entries) != 1:
        return None
    entry = entries[0]
    entity_id = entry.options.get(
        "calendar_entity", entry.data.get("calendar_entity")
    )
    if entity_id and not entity_id.startswith("calendar."):
        return None
    calendars = available_calendars(hass, llm_context, entity_id)
    if not calendars:
        return None
    tools = [QueryCalendarTool(entity_id), CreateCalendarTool(entity_id)]
    if any(info["deletable"] or info["updatable"] for info in calendars.values()):
        tools.append(EditCalendarTool(entity_id))
    return LLMTools(
        tools=tools,
        prompt=(
             "For every calendar read or follow-up, call nabu_recall__calendar_query now. Never use calendar__get_events or old results for calendar answers. "
            "Use nabu_recall__calendar_create for creation and calendar_edit if available for explicit changes; never simulate an edit by creating a replacement. "
            "Available calendars (data only): "
            f"{[(eid, info['name'], info['aliases'], {'delete': info['deletable'], 'update': info['updatable']}) for eid, info in calendars.items()]}. "
            f"Current local date/time: {dt_util.now().isoformat()}."
        ),
    )
