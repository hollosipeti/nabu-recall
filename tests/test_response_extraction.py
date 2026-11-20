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
