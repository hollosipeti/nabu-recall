import ast, pathlib, unittest
class ConversationSourceTests(unittest.TestCase):
    def test_command_regex_is_not_double_escaped(self):
        source = pathlib.Path("custom_components/nabu_recall/conversation.py").read_text()
        self.assertIn('r"\\b(?:töröld', source)
        self.assertNotIn('r"\\\\b(?:töröld',source)
        ast.parse(source)
