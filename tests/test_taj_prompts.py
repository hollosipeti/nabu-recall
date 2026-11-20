"""Static regression guards: safe identifier handling and current encryption description."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
class TajPromptTests(unittest.TestCase):
    def test_agent_prompt_supports_requested_taj(self):
        source=(ROOT / "custom_components/nabu_recall/conversation.py").read_text()
        ast.parse(source)
        for phrase in ("Ordinary personal and family facts", "identification numbers",
                       "names, birthdays, relationships", "health facts",
                       "Do not automatically refuse", "Do not invent missing facts",
                       "without a relevant user request", "identity-card number", "not reliably available"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, source)
    def test_learning_prompt_does_not_claim_plaintext_sqlite(self):
        source=(ROOT / "nabu_recall/ai.py").read_text()
        ast.parse(source)
        self.assertIn("SQLCipher",source)
        self.assertNotIn("currently unencrypted",source)
        self.assertIn("do not promote it automatically",source)
