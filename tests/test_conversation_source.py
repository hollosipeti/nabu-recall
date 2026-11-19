import pathlib, re, ast, unittest
class ConversationSourceTests(unittest.TestCase):
    def test_regex(self):
        source = pathlib.Path("custom_components/nabu_recall/conversation.py").read_text()
        ast.parse(source)
        self.assertIn('r"\\b(?:töröld', source)
        self.assertNotIn('r"\\\\b(?:töröld', source)
        self.assertIn('mentsd\\s+el', source)
