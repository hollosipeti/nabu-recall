"""Offline regression tests for HA IntentResponse structure; no HA imports."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/nabu_recall/conversation.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
FUNC = next(node for node in TREE.body if isinstance(node, ast.FunctionDef)
            and node.name == "extract_spoken_answer")
NAMESPACE = {}
exec(compile(ast.Module(body=[FUNC], type_ignores=[]), str(SOURCE), "exec"), NAMESPACE)
extract_spoken_answer = NAMESPACE["extract_spoken_answer"]


class ResponseExtractionTests(unittest.TestCase):
    def test_home_assistant_actual_dict_response(self):
        result = SimpleNamespace(response=SimpleNamespace(
            speech={"plain": {"speech": "A kocsid egy Suzuki."}}))
        self.assertEqual(extract_spoken_answer(result), "A kocsid egy Suzuki.")

    def test_legacy_attribute_response(self):
        result = SimpleNamespace(response=SimpleNamespace(
            speech=SimpleNamespace(plain=SimpleNamespace(speech="Rendben."))))
        self.assertEqual(extract_spoken_answer(result), "Rendben.")

    def test_empty_or_missing(self):
        for result in (
            SimpleNamespace(), SimpleNamespace(response=None),
            SimpleNamespace(response=SimpleNamespace(speech={})),
            SimpleNamespace(response=SimpleNamespace(speech={"plain": {}})),
            SimpleNamespace(response=SimpleNamespace(speech={"plain": {"speech": None}})),
            SimpleNamespace(response=SimpleNamespace(speech={"plain": {"speech": 123}}))
        ):
            with self.subTest(result=result):
                self.assertEqual(extract_spoken_answer(result), "")


class RealAgentRoutingTests(unittest.IsolatedAsyncioTestCase):
    """Run the actual wrapper async_process with fake HA and fake bridge."""

    async def asyncSetUp(self):
        import asyncio
        import re
        import sys
        from types import ModuleType
        from unittest.mock import patch
        sys.path.insert(0, str(SOURCE.parents[0]))
        from exact_recall import extract_precise
        from current_preference_reply import extract_current_preference
        from repo_instructions import compose_instructions
        from calendar_guard import calendar_read_question, fresh_calendar_result, has_write, calendar_tool_scope
        from contextlib import nullcontext
        from contextvars import ContextVar
        self.chat_context = ContextVar('test_chat', default=None)
        self.fresh = False

        self.calls = []
        self.logged = []
        self.tasks = []
        self.context = (
            "Fact: Apa (Peti) születési dátuma 1980. január 2., "
            "TAJ száma 123456789.\n"
            "Fact: Apa személyi igazolvány száma: 111222AB.\n"
        )
        self.fail = False
        parent = self

        class IntentResponse:
            def __init__(self, language=None):
                self.speech = {"plain": {"speech": ""}}
            def async_set_speech(self, value):
                self.speech["plain"]["speech"] = value

        class Result:
            def __init__(self, response, conversation_id):
                self.response = response
                self.conversation_id = conversation_id

        class FakeConversation:
            ConversationResult = Result
            async def async_converse(self, hass, **kwargs):
                parent.calls.append(kwargs)
                chat = parent.chat_context.get()
                if chat is not None:
                    await chat.async_provide_llm_data()
                    if parent.fresh:
                        chat.content.append(SimpleNamespace(role='tool_result', tool_name='nabu_recall__calendar_query', result=SimpleNamespace(error=False)))
                r = IntentResponse()
                r.async_set_speech("Az eredeti asszisztens válasza.")
                return Result(r, kwargs["conversation_id"])

        class FakeBridge:
            def __init__(self, *args):
                pass
            async def recall(self, text):
                if parent.fail:
                    raise ConnectionError("simulated outage")
                return parent.context
            async def manage(self, utterance, conversation_id):
                return {"status": "confirmed", "message": "Rendben."}
            async def log(self, user, assistant, cid):
                parent.logged.append((user, assistant, cid))

        class Hass:
            def async_create_background_task(self, task, name):
                parent.tasks.append(asyncio.create_task(task))

        class Agent:
            def __init__(self):
                self.entry = SimpleNamespace(data={
                    "upstream": "conversation.original", "url": "http://fake",
                    "token": "synthetic"})
                self.entity_id = "conversation.nabu_recall_memoria"
                self.hass = Hass()
            async def _log(self, bridge, user, assistant, cid):
                await bridge.log(user, assistant, cid)

        cls = next(node for node in TREE.body
                   if isinstance(node, ast.ClassDef) and node.name == "RecallAgent")
        method = next(node for node in cls.body
                      if isinstance(node, ast.AsyncFunctionDef)
                      and node.name == "async_process")
        namespace = {
            "re": re, "Bridge": FakeBridge,
            "async_get_clientsession": lambda hass: None,
            "conversation": FakeConversation(),
            "calendar_action": lambda text: False,
            "extract_precise": extract_precise,
            "extract_current_preference": extract_current_preference,
            "compose_instructions": compose_instructions,
            "extract_spoken_answer": extract_spoken_answer,
            "_LOGGER": SimpleNamespace(warning=lambda *args: None),
            "calendar_read_question": calendar_read_question,
            "fresh_calendar_result": fresh_calendar_result,
            "has_write": has_write,
            "calendar_tool_scope": calendar_tool_scope,
            "suppress_nested_text": nullcontext,
            "_passthrough": nullcontext,
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]),
                     str(SOURCE), "exec"), namespace)
        self.agent = Agent()
        self.process = namespace["async_process"]
        ha = ModuleType("homeassistant")
        helpers = ModuleType("homeassistant.helpers")
        helpers.intent = SimpleNamespace(IntentResponse=IntentResponse)
        chat_module = ModuleType("homeassistant.components.conversation.chat_log")
        chat_module.current_chat_log = self.chat_context
        self.patch = patch.dict(sys.modules, {
            "homeassistant": ha, "homeassistant.helpers": helpers,
            "homeassistant.components.conversation.chat_log": chat_module})
        self.patch.start()

    async def asyncTearDown(self):
        import asyncio
        if self.tasks:
            await asyncio.gather(*self.tasks)
        self.patch.stop()

    async def ask(self, text):
        user = SimpleNamespace(
            text=text, agent_id="conversation.nabu_recall_memoria",
            conversation_id="same-conversation", context=None,
            language="hu-HU", device_id=None, satellite_id=None,
            extra_system_prompt=None)
        return await self.process(self.agent, user)

    async def test_compound_exact_answer_only_once_no_upstream(self):
        result = await self.ask("Mi apa TAJ száma és személyi igazolvány száma?")
        self.assertEqual(self.calls, [])
        reply = extract_spoken_answer(result)
        self.assertIn("1, 2, 3", reply)
        self.assertIn("111222AB", reply)
        self.assertEqual(reply.count("TAJ-száma"), 1)
        self.assertEqual(reply.count("igazolvány száma"), 1)
        self.assertEqual(result.conversation_id, "same-conversation")

    async def test_open_question_unchanged_no_result_mutation(self):
        question = "Mi apa TAJ száma és mit tudsz róla?"
        result = await self.ask(question)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["text"], question)
        self.assertEqual(extract_spoken_answer(result),
                         "Az eredeti asszisztens válasza.")

    async def test_device_control_and_memory_commands_untouched(self):
        result = await self.ask("Kapcsold fel a nappali lámpát!")
        self.assertEqual(len(self.calls), 1)
        self.assertIn("Kapcsold", self.calls[0]["text"])
        self.calls.clear()
        result = await self.ask("Jegyezd meg ezt a próbaadatot!")
        self.assertEqual(len(self.calls), 0)
        self.assertEqual(extract_spoken_answer(result), "Rendben.")

    async def test_repo_owned_instruction_is_passed_to_upstream(self):
        result = await self.ask("Kapcsold fel a nappali lámpát!")
        self.assertEqual(len(self.calls), 1)
        prompt = self.calls[0]["extra_system_prompt"]
        self.assertIn("REPOSITORY-MANAGED RULES", prompt)
        self.assertIn("Durable memories are the authoritative", prompt)

    async def test_current_preference_does_not_ask_stale_upstream(self):
        self.context = ("CURRENT CONFIRMED DURABLE FACTS ONLY. Historical "
                        "conversation text is not evidence of current preferences.\\n"
                        "Fact: Bodor Zalán kedvenc gyümölcse a mangó.")
        result = await self.ask("Mi Bodor Zalán kedvenc gyümölcse?")
        self.assertIn("mangó", extract_spoken_answer(result))
        self.assertEqual(self.calls, [])

    async def test_bridge_error_preserves_original_agent(self):
        self.fail = True
        result = await self.ask("Mi apa TAJ száma?")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(extract_spoken_answer(result),
                         "Az eredeti asszisztens válasza.")

    async def test_explicit_calendar_requires_fresh_result(self):
        class Chat:
            content = []
            llm_api = None
            async def async_provide_llm_data(self): pass
        chat = Chat()
        self.chat_context.set(chat)
        result = await self.ask("Mikor lesz a következő körmös?")
        self.assertIn("nem kaptam ellenőrzött", extract_spoken_answer(result))
        self.fresh = True
        result = await self.ask("Mikor lesz a következő körmös?")
        self.assertEqual(extract_spoken_answer(result), "Az eredeti asszisztens válasza.")
        self.fresh = False
        result = await self.ask("Mikor lesz a következő körmös?")
        self.assertIn("nem kaptam ellenőrzött", extract_spoken_answer(result))
        self.assertEqual(len(self.calls),3)
