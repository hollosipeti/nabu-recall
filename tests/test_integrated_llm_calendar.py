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
        self.hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_entries=lambda domain: [self.entry]),
            states=SimpleNamespace(get=lambda eid: SimpleNamespace(entity_id=eid)),
            services=self.services,
        )
        self.ctx = SimpleNamespace(agent_id="conversation.original",
                                   context=None)

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

    async def test_service_error_never_reports_success(self):
        self.services.fail = True
        tool = self.get_tools().tools[1]
        result = await tool.async_call(self.hass, SimpleNamespace(tool_args={
            "title": "Synthetic", "date": "holnap", "start_hour": 9,
        }), self.ctx)
        self.assertTrue(result.error)
        self.assertNotIn("status", result.data)


if __name__ == "__main__":
    unittest.main()
