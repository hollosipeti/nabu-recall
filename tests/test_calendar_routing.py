"""Calendar instructions must reach upstream Home Assistant, not memory storage."""
import ast
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nabu_recall"))
from management import calendar_action, operation_kind

def get_agent_calendar_action():
    """Execute only the function definition from HA code without HA installed."""
    source=(ROOT / "custom_components/nabu_recall/conversation.py").read_text()
    tree=ast.parse(source)
    import re
    # The regex constant is assigned separately and the helper is AST-isolated.
    ns={"re":re}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id=="CALENDAR_DESTINATION"
                for t in statement.targets):
            exec(compile(ast.Module(body=[statement],type_ignores=[]),"<extract>","exec"),ns)
        if isinstance(statement, ast.FunctionDef) and statement.name=="calendar_action":
            exec(compile(ast.Module(body=[statement],type_ignores=[]),"<extract>","exec"),ns)
    return ns["calendar_action"]

class CalendarRoutingTests(unittest.TestCase):
    def test_upstream_and_server_agree(self):
        ha_calendar_action=get_agent_calendar_action()
        examples={
          "Mentsd el a naptárba holnap reggel nyolcra a próba eseményt":True,
          "mentsd el az alapértelmezett naptárba, holnap reggel 8-ra, hogy próba esemény":True,
          "De mentsd el a naptárba holnap reggel 8-ra.":True,
          "Töröld az eseményt a naptárból":True,
          "Hozz létre próba naptáreseményt":True,
          "Javítsd a naptárban a holnapi eseményt":True,
          "Jegyezd meg, hogy a kedvenc naptáram a Család":False,
          "Jegyezd meg, hogy a naptárba a Család nevűt használjuk":False,
          "Mentsd el, hogy Apa születésnapja májusban van":False,
          "Töröld a régi emléket":False,
          "Kapcsold fel a lámpát":False,
        }
        for phrase, expected in examples.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(calendar_action(phrase),expected)
                self.assertEqual(ha_calendar_action(phrase),expected)
                if expected: self.assertIsNone(operation_kind(phrase))
    def test_calendar_not_intercepted_by_ha_memory_branch(self):
        source=(ROOT/"custom_components/nabu_recall/conversation.py").read_text()
        self.assertIn("if memory_command and not calendar_action(user_input.text):",source)
    def test_not_reclassified_as_durable_learning(self):
        source=(ROOT/"nabu_recall/ai.py").read_text()
        self.assertIn("calendar event creation requests are not durable memories",source)
