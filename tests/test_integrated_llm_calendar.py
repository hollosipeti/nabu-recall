"""Exercise actual integrated LLM tool path without a running Home Assistant.

All calendar events and identities are fictional.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib.util
import sys
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1] / "custom_components/nabu_recall"
TZ = ZoneInfo("Europe/Budapest")


class Schema:
    def __init__(self, fields):
        self.fields = fields
    def __call__(self, values):
        return values


class ToolAnnotations:
    def __init__(self, **kwargs):
        self.values = kwargs


class ToolResult:
    def __init__(self, data, error=False):
        self.data, self.error = data, error


class LLMTools:
    def __init__(self, tools, prompt=None):
        self.tools, self.prompt = tools, prompt


@dataclass
class TestEntry:
    data: dict
    options: dict


class TestServices:
    def __init__(self):
        self.calls = []
        self.fail = False

    async def async_call(self, domain, service, data, **kwargs):
        self.calls.append((domain, service, data, kwargs))
        if self.fail:
            raise RuntimeError("Service unavailable")
        if service == "get_events":
            return {"calendar.test": {"events": [
                {"start": "2026-11-27", "end": "2026-11-28",
                 "summary": "Friday only"},
                {"start": "2026-11-28", "end": "2026-11-29",
                 "summary": "Saturday event"},
            ]}}
        return None


class CalendarPlatformTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.stub = {}
        def module(name, **attributes):
            value = ModuleType(name)
            value.__dict__.update(attributes)
            self.stub[name] = value
            return value
        probatio = module("probatio", Schema=Schema, Required=lambda s: s,
                         Optional=lambda s, default=None: s,
                         In=lambda values: values)
        module("homeassistant")
        module("homeassistant.components")
        module("homeassistant.components.llm", LLMTools=LLMTools)
        module("homeassistant.components.homeassistant", async_should_expose=lambda hass, assistant, eid: eid in hass.exposed)
        module("homeassistant.components.calendar.const", CalendarEntityFeature=SimpleNamespace(CREATE_EVENT=1))
        module("homeassistant.helpers.entity_registry", async_get=lambda hass: SimpleNamespace(async_get=lambda eid: None))
        module("homeassistant.helpers.intent", async_get_entity_aliases=lambda hass, entry, state: [state.name])
        module("homeassistant.core", HomeAssistant=object, callback=lambda fn: fn)
        module("homeassistant.helpers")
        module("homeassistant.helpers.llm", LLM_API_ASSIST="assist",
               LLMContext=object, Tool=object, ToolAnnotations=ToolAnnotations,
               ToolInput=object, ToolResult=ToolResult)
        module("homeassistant.util")
        module("homeassistant.util.dt",
               now=lambda: datetime(2026, 11, 23, 14, tzinfo=TZ))
        package = module("_nabu_test_package")
        package.__path__ = [str(ROOT)]
        self.patcher = patch.dict(sys.modules, self.stub)
        self.patcher.start()
        name = "_nabu_test_package.llm"
        spec = importlib.util.spec_from_file_location(name, ROOT / "llm.py")
        self.library = importlib.util.module_from_spec(spec)
        sys.modules[name] = self.library
        spec.loader.exec_module(self.library)

        self.services = TestServices()
        self.entry = TestEntry(
            data={"upstream": "conversation.original",
                  "calendar_entity": "calendar.test"}, options={})
        self.states = [SimpleNamespace(entity_id="calendar.test", name="Default", state="off", attributes={"supported_features": 1})]
        self.hass = SimpleNamespace(
            exposed=set(),
            config_entries=SimpleNamespace(async_entries=lambda domain: [self.entry]),
            states=SimpleNamespace(get=lambda eid: next((s for s in self.states if s.entity_id == eid), None), async_all=lambda domain: self.states),
            services=self.services,
        )
        self.ctx = SimpleNamespace(agent_id="conversation.original",
                                   context=None, assistant="conversation")

    async def asyncTearDown(self):
        sys.modules.pop("_nabu_test_package.llm", None)
        sys.modules.pop("_nabu_test_package.calendar_logic", None)
        self.patcher.stop()

    def get_tools(self):
        return self.library.async_get_tools(self.hass, self.ctx, "assist")

    def test_optional_and_scoped_to_upstream(self):
        self.assertEqual(len(self.get_tools().tools), 2)
        self.assertIsNone(self.library.async_get_tools(self.hass, self.ctx, "other"))
        self.ctx.agent_id = "conversation.other"
        self.assertIsNone(self.get_tools())
        self.ctx.agent_id = "conversation.original"
        self.entry.options = {"calendar_entity": ""}
        self.assertIsNone(self.get_tools())
        self.hass.exposed.add("calendar.test")
        self.assertEqual(len(self.get_tools().tools), 2)
        self.hass.exposed.clear()
        self.entry.options = {"calendar_entity": "calendar.test"}
        self.assertEqual(len(self.get_tools().tools), 2)

    async def test_weekend_read_filters_friday_all_day(self):
        tool = self.get_tools().tools[0]
        result = await tool.async_call(
            self.hass, SimpleNamespace(tool_args={"period": "weekend"}),
            self.ctx)
        self.assertFalse(result.error)
        self.assertEqual([e["summary"] for e in result.data["events"]],
                         ["Saturday event"])
        self.assertEqual(result.data["events"][0]["date"], "2026-11-28")
        self.assertNotIn("end", result.data["events"][0])
        self.assertNotIn("last_day_inclusive", result.data["events"][0])
        self.assertEqual(result.data["event_count"], 1)
        sent = self.services.calls[-1][2]
        self.assertEqual(sent["entity_id"], "calendar.test")
        self.assertTrue(sent["start_date_time"].startswith("2026-11-28T00:00"))
        self.assertTrue(sent["end_date_time"].startswith("2026-11-30T00:00"))

    async def test_next_event_is_fresh_and_uses_future_window(self):
        tool = self.get_tools().tools[0]
        result = await tool.async_call(
            self.hass, SimpleNamespace(tool_args={"period": "next"}),
            self.ctx,
        )
        self.assertFalse(result.error)
        self.assertEqual(result.data["period"], "next")
        sent = self.services.calls[-1][2]
        self.assertTrue(sent["start_date_time"].startswith("2026-11-23T14:00"))
        self.assertGreater(result.data["event_count"], 0)

    async def test_friday_query_returns_all_friday_events_not_saturday(self):
        self.services.async_call_original = self.services.async_call
        async def fake_call(domain, service, data, **kwargs):
            self.services.calls.append((domain, service, data, kwargs))
            return {"calendar.test": {"events": [
                {"start": "2026-11-27", "end": "2026-11-28",
                 "summary": "Friday concert"},
                {"start": "2026-11-27T17:00:00+01:00",
                 "end": "2026-11-27T17:30:00+01:00",
                 "summary": "Friday family"},
                {"start": "2026-11-28", "end": "2026-11-29",
                 "summary": "Saturday only"},
            ]}}
        self.services.async_call = fake_call
        tool = self.get_tools().tools[0]
        result = await tool.async_call(
            self.hass, SimpleNamespace(tool_args={
                "period": "day", "date": "pénteken"}), self.ctx)
        self.assertFalse(result.error)
        self.assertEqual([v["summary"] for v in result.data["events"]],
                         ["Friday concert", "Friday family"])
        self.assertEqual(result.data["event_count"], 2)
        self.assertTrue(self.services.calls[-1][2]["start_date_time"].startswith("2026-11-27T00:00"))

    async def test_create_correct_friday_interval(self):
        tool = self.get_tools().tools[1]
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={
            "title": "Synthetic event", "date": "pénteken",
            "start_hour": 10, "end_hour": 11,
        }), self.ctx)
        self.assertFalse(result.error)
        sent = self.services.calls[-1][2]
        self.assertEqual(self.services.calls[-1][1], "create_event")
        self.assertEqual(sent["entity_id"], "calendar.test")
        self.assertTrue(sent["start_date_time"].startswith("2026-11-27T10:00"))
        self.assertTrue(sent["end_date_time"].startswith("2026-11-27T11:00"))

    async def test_invalid_request_never_calls_write_service(self):
        tool = self.get_tools().tools[1]
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={
            "title": "Synthetic", "date": "ma", "start_hour": 9,
        }), self.ctx)
        self.assertTrue(result.error)
        self.assertFalse(self.services.calls)

    async def test_range_schema_has_only_inclusive_end(self):
        tool = self.get_tools().tools[0]
        self.assertIn("last_day_inclusive", tool.parameters.fields)
        self.assertNotIn("end_date", tool.parameters.fields)
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={
            "period": "range", "start_date": "2027-01-04", "last_day_inclusive": "2027-01-04"
        }), self.ctx)
        self.assertFalse(result.error)
        self.assertTrue(self.services.calls[-1][2]["end_date_time"].startswith("2027-01-05T00:00"))

    async def test_inclusive_year_boundary(self):
        tool = self.get_tools().tools[0]
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={
            "period": "range", "start_date": "2026-12-29", "last_day_inclusive": "2027-01-04"
        }), self.ctx)
        self.assertFalse(result.error)
        self.assertTrue(self.services.calls[-1][2]["end_date_time"].startswith("2027-01-05T00:00"))

    async def test_explicit_overnight_end_date_and_reversed_hours(self):
        tool = self.get_tools().tools[1]
        request = {"title": "Year boundary", "date": "2026-12-31",
                   "start_hour": 23, "end_hour": 2, "end_date": "2027-01-01"}
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args=request), self.ctx)
        self.assertFalse(result.error)
        self.assertTrue(self.services.calls[-1][2]["end_date_time"].startswith("2027-01-01T02:00"))
        self.services.calls.clear()
        request.pop("end_date")
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args=request), self.ctx)
        self.assertTrue(result.error)
        self.assertFalse(self.services.calls)

    async def test_service_error_never_reports_success(self):
        self.services.fail = True
        tool = self.get_tools().tools[1]
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={
            "title": "Synthetic", "date": "holnap", "start_hour": 9,
        }), self.ctx)
        self.assertTrue(result.error)
        self.assertNotIn("status", result.data)

    def add_calendar(self, eid, name, exposed=True, writable=True, state="off"):
        self.states.append(SimpleNamespace(entity_id=eid, name=name, state=state,
                           attributes={"supported_features": int(writable)}))
        if exposed:
            self.hass.exposed.add(eid)

    async def test_multi_calendar_merged_order_and_visibility(self):
        self.add_calendar("calendar.birthdays", "Születésnapok")
        self.add_calendar("calendar.hidden", "Private", exposed=False)
        async def fake_call(domain, service, data, **kwargs):
            self.services.calls.append((domain, service, data, kwargs))
            return {
                "calendar.test": {"events": [{"start":"2026-11-27T18:00:00+01:00","end":"2026-11-27T19:00:00+01:00","summary":"Koncert"}]},
                "calendar.birthdays": {"events": [{"start":"2026-11-27","end":"2026-11-28","summary":"Vivi névnap"}]},
                "calendar.hidden": {"events": [{"start":"2026-11-27","end":"2026-11-28","summary":"Private"}]},
            }
        self.services.async_call = fake_call
        tool = self.get_tools().tools[0]
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={"period":"week"}), self.ctx)
        self.assertFalse(result.error)
        self.assertEqual(len(self.services.calls),1)
        self.assertEqual(set(self.services.calls[0][2]["entity_id"]), {"calendar.test","calendar.birthdays"})
        self.assertEqual([e["summary"] for e in result.data["events"]], ["Vivi névnap","Koncert"])
        self.assertEqual(result.data["events"][0]["calendar"],"calendar.birthdays")
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={"period":"next"}), self.ctx)
        self.assertEqual(result.data["events"][0]["summary"],"Vivi névnap")
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={"period":"week","calendar":"Születésnapok"}), self.ctx)
        self.assertEqual(self.services.calls[-1][2]["entity_id"],"calendar.birthdays")
        self.assertEqual(result.data["event_count"],1)

    async def test_discovery_and_explicit_single_write(self):
        self.add_calendar("calendar.birthdays","Születésnapok")
        self.add_calendar("calendar.hidden","Private",exposed=False)
        self.add_calendar("calendar.readonly","Read only",writable=False)
        tools = self.get_tools().tools
        result = await tools[0].async_call(self.hass, SimpleNamespace(tool_args={"period":"calendars"}), self.ctx)
        self.assertNotIn("calendar.hidden",result.data["calendars"])
        self.assertFalse(self.services.calls)
        args={"title":"Vivi névnap","date":"holnap","all_day":True}
        for target in ("Private","Read only","missing"):
            result = await tools[1].async_call(self.hass, SimpleNamespace(tool_args={**args,"calendar":target}), self.ctx)
            self.assertTrue(result.error)
        self.assertFalse(self.services.calls)
        result = await tools[1].async_call(self.hass, SimpleNamespace(tool_args={**args,"calendar":"Születésnapok"}), self.ctx)
        self.assertFalse(result.error)
        self.assertEqual(len(self.services.calls),1)
        self.assertEqual(self.services.calls[0][2]["entity_id"],"calendar.birthdays")
        result = await tools[1].async_call(self.hass, SimpleNamespace(tool_args=args), self.ctx)
        self.assertEqual(self.services.calls[-1][2]["entity_id"],"calendar.test")

    async def test_partial_failure_does_not_hide_healthy_calendar(self):
        self.add_calendar("calendar.broken","Broken")
        self.add_calendar("calendar.offline","Offline",state="unavailable")
        original = self.services.async_call
        async def fake_call(domain, service, data, **kwargs):
            if isinstance(data["entity_id"],list) or data["entity_id"] == "calendar.broken":
                raise RuntimeError("Provider failed")
            return await original(domain,service,data,**kwargs)
        self.services.async_call = fake_call
        result = await self.get_tools().tools[0].async_call(self.hass, SimpleNamespace(tool_args={"period":"week"}), self.ctx)
        self.assertFalse(result.error)
        self.assertEqual(result.data["calendars_queried"],["calendar.test"])
        self.assertEqual(set(result.data["calendars_failed"]),{"calendar.broken","calendar.offline"})
        self.assertEqual(result.data["event_count"],2)

    async def test_month_range_excludes_adjacent_months_and_preserves_duration(self):
        async def fake_call(domain, service, data, **kwargs):
            self.services.calls.append((domain, service, data, kwargs))
            return {"calendar.test":{"events":[
                {"summary":"November","start":"2026-11-27","end":"2026-11-28"},
                {"summary":"Vízóra","start":"2026-12-10","end":"2026-12-14"},
                {"summary":"January","start":"2027-01-01","end":"2027-01-02"}]}}
        self.services.async_call = fake_call
        result = await self.get_tools().tools[0].async_call(self.hass, SimpleNamespace(tool_args={"period":"range","start_date":"2026-12-01","last_day_inclusive":"2026-12-31"}), self.ctx)
        self.assertFalse(result.error)
        self.assertEqual(result.data["event_count"],1)
        self.assertEqual(result.data["events"][0]["display_time"],"2026-12-10 – 2026-12-13 (inclusive)")
        self.assertTrue(self.services.calls[-1][2]["end_date_time"].startswith("2027-01-01T00:00"))

    async def test_upcoming_returns_candidates_without_truncating_to_first(self):
        tool = self.get_tools().tools[0]
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={"period":"upcoming"}), self.ctx)
        self.assertFalse(result.error)
        self.assertEqual(result.data["event_count"],2)
        self.assertIsNone(result.data["title_filter"])
        self.assertTrue(result.data["title_filter_is_literal"])

    async def test_no_default_read_and_explicit_write(self):
        self.entry.options = {"calendar_entity": ""}
        self.hass.exposed.add("calendar.test")
        tools = self.get_tools().tools
        result = await tools[0].async_call(self.hass, SimpleNamespace(tool_args={"period":"week"}), self.ctx)
        self.assertFalse(result.error)
        args={"title":"Test","date":"holnap","all_day":True}
        result = await tools[1].async_call(self.hass, SimpleNamespace(tool_args=args), self.ctx)
        self.assertTrue(result.error)
        self.assertEqual(len(self.services.calls),1)
        result = await tools[1].async_call(self.hass, SimpleNamespace(tool_args={**args,"calendar":"Default"}), self.ctx)
        self.assertFalse(result.error)

if __name__ == "__main__":
    unittest.main()
