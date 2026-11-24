"""Strict source-level and pure-python regression for repository-owned rules."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "nabu_recall"
sys.path.insert(0, str(ROOT))
from current_preference_reply import extract_current_preference
from repo_instructions import NABU_RULES, compose_instructions

class RepositoryPromptTests(unittest.TestCase):
    def test_prompts_are_versioned_and_compose_without_dropping_context(self):
        prompt = compose_instructions("Satellite context.", "Fact: test")
        self.assertTrue(prompt.startswith(NABU_RULES))
        self.assertIn("Satellite context.", prompt)
        self.assertIn("Fact: test", prompt)
        self.assertIn("45-day journal", prompt)

    def test_current_value_without_old_history(self):
        context = ("CURRENT CONFIRMED DURABLE FACTS ONLY.\n"
                   "Fact: Bodor Zalán kedvenc gyümölcse a mangó.")
        self.assertEqual(extract_current_preference(
            "Mi Bodor Zalán kedvenc gyümölcse?", context),
            "Bodor Zalán kedvenc gyümölcse a mangó.")

    def test_empty_current_snapshot_does_not_fall_back_to_old_history(self):
        context = ("CURRENT CONFIRMED DURABLE FACTS ONLY.\n"
                   "NO CURRENT FACT STORED FOR REQUESTED PERSON AND PREFERENCE.")
        self.assertEqual(extract_current_preference(
            "Mi Bodor Zalán kedvenc gyümölcse?", context),
            "Ezt az adatot most nem találom a memóriámban.")

    def test_compound_and_historical_questions_keep_original_agent_path(self):
        context = ("CURRENT CONFIRMED DURABLE FACTS ONLY.\n"
                   "Fact: Bodor Zalán kedvenc gyümölcse a mangó.")
        for q in ("Mit mondtam korábban Bodor Zalán kedvenc gyümölcséről?",
                  "Mi Bodor Zalán kedvenc gyümölcse, és kapcsold fel a lámpát?",
                  "Mi Váradi Emília kedvenc gyümölcse?"):
            with self.subTest(query=q):
                self.assertIsNone(extract_current_preference(q, context))

    def test_two_current_values_never_guess(self):
        context = ("CURRENT CONFIRMED DURABLE FACTS ONLY.\n"
                   "Fact: Bodor Zalán kedvenc gyümölcse a mangó.\n"
                   "Fact: Bodor Zalán kedvenc gyümölcse a szilva.")
        self.assertIsNone(extract_current_preference(
            "Mi Bodor Zalán kedvenc gyümölcse?", context))

if __name__ == "__main__":
    unittest.main()
