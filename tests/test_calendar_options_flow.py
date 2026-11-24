"""Check optional calendar configuration without an installed HA runtime."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/nabu_recall"


class FakeFlowBase:
    _config_entry = None
    @property
    def config_entry(self):
        return self._config_entry
    async def async_set_unique_id(self, unique_id):
        self._unique_id = unique_id
    def _abort_if_unique_id_configured(self):
        pass
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}
    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}


class FakeVol:
    UNDEFINED = object()
    @staticmethod
    def Schema(shape):
        return shape
    @staticmethod
    def Optional(key, default=None):
        return key
    @staticmethod
    def Required(key, default=None):
        return key


class CalendarOptionsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = {}
        def mod(name, **kwargs):
            m = ModuleType(name)
            m.__dict__.update(kwargs)
            self.fake[name] = m
            return m

        mod("voluptuous", Schema=FakeVol.Schema,
            Optional=FakeVol.Optional, Required=FakeVol.Required,
            UNDEFINED=FakeVol.UNDEFINED)
        mod("homeassistant")
        mod("homeassistant.config_entries",
            ConfigFlow=FakeFlowBase, OptionsFlow=FakeFlowBase)
        self.fake["homeassistant"].config_entries = self.fake["homeassistant.config_entries"]
        mod("homeassistant.helpers")
        selector = mod("homeassistant.helpers.selector",
                       EntitySelector=lambda config: config,
                       EntitySelectorConfig=lambda domain: domain,
                       TextSelector=lambda config: config,
                       TextSelectorConfig=lambda type: type,
                       TextSelectorType=SimpleNamespace(PASSWORD="password"))
        self.fake["homeassistant.helpers"].selector = selector
        mod("homeassistant.helpers.aiohttp_client",
            async_get_clientsession=lambda hass: None)
        package = mod("_calendar_config_test")
        package.__path__ = [str(SOURCE)]
        class Bridge:
            def __init__(self, *args):
                pass
            async def ping(self):
                return True
        mod("_calendar_config_test.gateway", Bridge=Bridge)
        self.module_patch = patch.dict(sys.modules, self.fake)
        self.module_patch.start()
        spec = importlib.util.spec_from_file_location(
            "_calendar_config_test.config_flow", SOURCE / "config_flow.py")
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.module
        spec.loader.exec_module(self.module)

    async def asyncTearDown(self):
        sys.modules.pop("_calendar_config_test.config_flow", None)
        self.module_patch.stop()

    async def test_initial_flow_offers_calendar_and_keeps_selection(self):
        flow = self.module.ConfigFlow()
        flow.hass = object()
        form = await flow.async_step_user()
        self.assertIn("calendar_entity", form["data_schema"])
        answer = await flow.async_step_user({
            "upstream": "conversation.original",
            "url": "http://internal-addon:8765",
            "token": "x" * 32,
            "calendar_entity": "calendar.family",
        })
        self.assertEqual(answer["type"], "create_entry")
        self.assertEqual(answer["data"]["calendar_entity"], "calendar.family")

    async def test_choose_calendar_and_replace_it_without_reinstall(self):
        entry = SimpleNamespace(data={"calendar_entity": "calendar.first"},
                                options={})
        flow = self.module.CalendarOptionsFlow()
        flow._config_entry = entry
        form = await flow.async_step_init()
        self.assertEqual(form["type"], "form")
        self.assertIn("calendar_entity", form["data_schema"])
        answer = await flow.async_step_init({"calendar_entity": "calendar.other"})
        self.assertEqual(answer["data"], {"calendar_entity": "calendar.other"})
        self.assertEqual(answer["type"], "create_entry")

    async def test_calendar_is_optional_and_can_be_disabled(self):
        entry = SimpleNamespace(data={}, options={})
        flow = self.module.CalendarOptionsFlow()
        flow._config_entry = entry
        answer = await flow.async_step_init({})
        self.assertEqual(answer["type"], "create_entry")
        self.assertEqual(answer["data"], {"calendar_entity": ""})

    async def test_reject_non_calendar_domain(self):
        entry = SimpleNamespace(data={}, options={})
        flow = self.module.CalendarOptionsFlow()
        flow._config_entry = entry
        answer = await flow.async_step_init(
            {"calendar_entity": "light.kitchen"})
        self.assertEqual(answer["type"], "form")
        self.assertEqual(answer["errors"]["calendar_entity"],
                         "invalid_calendar")


if __name__ == "__main__":
    unittest.main()
