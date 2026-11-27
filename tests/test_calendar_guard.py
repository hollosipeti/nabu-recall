import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec=importlib.util.spec_from_file_location("calendar_guard",Path(__file__).resolve().parents[1]/"custom_components/nabu_recall/calendar_guard.py")
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class CalendarGuardTests(unittest.IsolatedAsyncioTestCase):
    def test_questions(self):
        for text in ("Mikor lesz a következő körmös?", "Mikor kell leolvasni a vízórát?", "Benne van még a próba a naptárban?"):
            self.assertTrue(guard.calendar_read_question(text))
        for text in ("Mikor lesz a következő napfogyatkozás?", "Töröld a naptárból a próbát", "Mikor született Petőfi?", "Kapcsold fel a lámpát"):
            self.assertFalse(guard.calendar_read_question(text))
    def test_fresh_results(self):
        result=lambda name,error: SimpleNamespace(role="tool_result",tool_name=name,result=SimpleNamespace(error=error))
        self.assertFalse(guard.fresh_calendar_result([]))
        self.assertFalse(guard.fresh_calendar_result([result("calendar__get_events",False)]))
        self.assertFalse(guard.fresh_calendar_result([result("nabu_recall__calendar_query",True)]))
        self.assertTrue(guard.fresh_calendar_result([result("nabu_recall__calendar_query",False)]))
        self.assertTrue(guard.has_write([result("nabu_recall__calendar_edit",False)]))
    async def test_tool_scope_restores_and_preserves_devices(self):
        original=[SimpleNamespace(name=n) for n in ("calendar__get_events","nabu_recall__calendar_query","HassTurnOn","nabu_recall__calendar_create")]
        api=SimpleNamespace(tools=original)
        class Chat:
            llm_api=api
            async def async_provide_llm_data(self,*args,**kwargs): pass
        chat=Chat()
        with self.assertRaises(RuntimeError):
            with guard.calendar_tool_scope(chat):
                await chat.async_provide_llm_data()
                self.assertEqual([t.name for t in api.tools],["nabu_recall__calendar_query","HassTurnOn","nabu_recall__calendar_create"])
                raise RuntimeError("test")
        self.assertIs(api.tools,original)
        self.assertNotIn("async_provide_llm_data",chat.__dict__)
    async def test_no_nabu_tool_keeps_native(self):
        api=SimpleNamespace(tools=[SimpleNamespace(name="calendar__get_events")])
        class Chat:
            llm_api=api
            async def async_provide_llm_data(self,*args,**kwargs): pass
        with guard.calendar_tool_scope(Chat()):
            self.assertEqual(len(api.tools),1)
