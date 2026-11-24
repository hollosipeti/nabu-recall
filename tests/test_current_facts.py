"""Regression: current factual preferences override journal without deleting it."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nabu_recall"))
from current_facts import authoritative_preferences, current_preference_subject

QUERY = "Mi Teszt Orion kedvenc gyümölcse?"
OLD = {"id": 1, "fact": "Teszt Orion kedvenc gyümölcse az alma."}
CURRENT = {"id": 1, "fact": "Teszt Orion kedvenc gyümölcse a barack."}
DRINK = {"id": 2, "fact": "Teszt Orion kedvenc itala a víz."}
OTHER = {"id": 3, "fact": "Teszt Nova kedvenc gyümölcse a körte."}


class CurrentPreferenceTests(unittest.TestCase):
    def test_named_current_preference_is_recognized(self):
        self.assertEqual(current_preference_subject(QUERY), "teszt orion")
        self.assertEqual(authoritative_preferences(QUERY, [CURRENT, DRINK, OTHER]),
                         [CURRENT])

    def test_deleted_durable_fact_cannot_resurface_from_journal(self):
        self.assertEqual(authoritative_preferences(QUERY, []), [])

    def test_attribute_and_person_are_not_confused(self):
        self.assertEqual(authoritative_preferences(QUERY, [DRINK, OTHER]), [])
        self.assertEqual(authoritative_preferences(
            "Mi Teszt Orion kedvenc itala?", [CURRENT, DRINK, OTHER]), [DRINK])
        self.assertEqual(authoritative_preferences(
            "Mi Teszt Nova kedvenc gyümölcse?", [CURRENT, DRINK, OTHER]), [OTHER])

    def test_history_queries_keep_normal_journal_retrieval(self):
        for question in (
            "Mi volt korábban Teszt Orion kedvenc gyümölcse?",
            "Mit mondtam tegnap Teszt Orion kedvenc gyümölcséről?",
            "Emlékszel, mi volt Teszt Orion kedvenc gyümölcse?",
            "Mit beszéltünk Teszt Orion kedvenc gyümölcséről?",
        ):
            with self.subTest(question=question):
                self.assertIsNone(authoritative_preferences(question, [CURRENT]))
        self.assertIsNone(authoritative_preferences(
            "Mit tudsz a műhelyről?", [CURRENT]))

    def test_missing_person_does_not_copy_other_preference(self):
        self.assertEqual(authoritative_preferences(
            "Mi Teszt Géza kedvenc gyümölcse?", [CURRENT, OTHER]), [])


if __name__ == "__main__":
    unittest.main()
