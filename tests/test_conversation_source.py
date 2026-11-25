import pathlib, re, ast, unittest
class ConversationSourceTests(unittest.TestCase):
    def test_regex(self):
        source = pathlib.Path("custom_components/nabu_recall/conversation.py").read_text()
        ast.parse(source)
        self.assertIn('r"\\b(?:töröld', source)
        self.assertNotIn('r"\\\\b(?:töröld', source)
        self.assertIn('mentsd\\s+el', source)

    def test_nested_text_suppression_restores_listener(self):
        import sys
        from contextlib import contextmanager
        from contextvars import ContextVar
        from types import SimpleNamespace, ModuleType
        from unittest.mock import patch
        source = pathlib.Path("custom_components/nabu_recall/conversation.py").read_text()
        node = next(n for n in ast.parse(source).body
                    if isinstance(n, ast.FunctionDef) and n.name == "suppress_nested_text")
        ns = {"contextmanager": contextmanager}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<helper>", "exec"), ns)
        seen = []
        def listener(log, delta):
            seen.append(delta)
        log = SimpleNamespace(delta_listener=listener)
        module = ModuleType("homeassistant.components.conversation.chat_log")
        module.current_chat_log = ContextVar("test_log", default=log)
        with patch.dict(sys.modules, {module.__name__: module}):
            with self.assertRaises(RuntimeError):
                with ns["suppress_nested_text"]():
                    log.delta_listener(log, {"role":"assistant", "content":"duplicate"})
                    log.delta_listener(log, {"content":"duplicate"})
                    log.delta_listener(log, {"role":"tool_result", "result":{"ok":True}})
                    raise RuntimeError("upstream failed")
            self.assertIs(log.delta_listener, listener)
        self.assertEqual(seen, [{"role":"tool_result", "result":{"ok":True}}])
