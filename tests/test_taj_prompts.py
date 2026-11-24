"""Prompt ownership regression: repository controls Nabu-specific behavior."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PromptOwnershipTests(unittest.TestCase):
    def test_nabu_response_rules_are_loaded_from_repository(self):
        source = (ROOT / "custom_components/nabu_recall/conversation.py").read_text()
        ast.parse(source)
        self.assertNotIn("        instructions = (", source)
        self.assertNotIn("TAJ number", source)
        self.assertNotIn("Ordinary personal and family facts", source)
        self.assertIn("compose_instructions(user_input.extra_system_prompt, memory)", source)
        self.assertIn("from .repo_instructions import compose_instructions", source)
        self.assertIn("agent_id=upstream", source)
        self.assertIn("extra_system_prompt=extra", source)
        self.assertIn("calendar_action(user_input.text)", source)
        self.assertIn("bridge.manage(", source)
        self.assertIn("bridge.recall(", source)
        self.assertIn("bridge.log(", source)

    def test_compound_queries_do_not_rewrite_question_or_duplicate_stream(self):
        source = (ROOT / "custom_components/nabu_recall/conversation.py").read_text()
        ast.parse(source)
        self.assertIn("exact_answer = extract_precise(user_input.text, memory)", source)
        self.assertIn("extract_current_preference(user_input.text, memory)", source)
        self.assertIn("self.hass, text=user_input.text", source)
        self.assertEqual(source.count("result = await conversation.async_converse("), 1)
        self.assertNotIn("upstream_text", source)
        self.assertNotIn("complementary_question", source)
        self.assertNotIn("result.response.async_set_speech(answer)", source)

    def test_repo_owned_prompt_document_has_only_current_sources(self):
        guide = (ROOT / "NABU_RECALL_PROMPT.md").read_text()
        for phrase in (
            "Home Assistant", "Instructions", "repo_instructions.py",
            "nabu_recall/ai.py", "nabu_recall/llm.py", "NABU_RULES",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase,guide)
        self.assertNotIn("## Archivált memóriautasítás-minta",guide)

    def test_learning_prompt_does_not_claim_plaintext_sqlite(self):
        source = (ROOT / "nabu_recall/ai.py").read_text()
        ast.parse(source)
        self.assertIn("SQLCipher", source)
        self.assertNotIn("currently unencrypted", source)
        self.assertIn("do not promote it automatically", source)


if __name__ == "__main__":
    unittest.main()
