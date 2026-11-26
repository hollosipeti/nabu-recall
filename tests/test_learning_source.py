"""Regressions for memory pollution from ordinary questions and AI replies."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from learning_source import assertion_turn, credible_extracted_fact, live_agenda_only, routine_control_only, simple_preference_query
from ai import AI


class LearningSourceTests(unittest.TestCase):
    def test_never_promote_question_or_followup_as_fact(self):
        for utterance in (
            "Mi Próba Elemér kedvenc itala?",
            "És most mit szeret inni?",
            "Emlékszel, mit szeretett inni korábban Próba Áron?",
            "Biztosan?",
            "Mi a kedvenc itala és milyen színű a doboz?",
            "Más?",
        ):
            with self.subTest(utterance=utterance):
                self.assertFalse(assertion_turn(utterance))

    def test_user_assertions_still_learnable(self):
        for utterance in (
            "Próba Áron kedvenc itala a körtejuice.",
            "A műhelyben van egy képzeletbeli narancssárga doboz.",
            "Apa lecserélte az autóját.",
            "Jegyezd meg, hogy a tesztkutyám Bodza.",
        ):
            with self.subTest(utterance=utterance):
                self.assertTrue(assertion_turn(utterance))

    def test_agenda_fast_path_preserves_ambiguous_and_mixed_requests(self):
        for q in ('Mi lesz holnap?', 'Milyen események lesznek decemberben?', 'Mi van mára a naptárban?'):
            self.assertTrue(live_agenda_only(q), q)
        for q in ('Mi lesz a projektemmel holnap?', 'Mi lesz holnap és mit beszéltünk tegnap?', 'Mikor lesz Vivi névnapja?', 'Mi volt tegnap?', 'Mi a kedvenc naptáram?'):
            self.assertFalse(live_agenda_only(q), q)

    def test_routine_control_fast_path_is_narrow(self):
        for q in ("Kapcsold fel a lámpát!", "Kapcsold le a nappali világítást", "Oltsd el a villanyt"):
            self.assertTrue(routine_control_only(q), q)
        for q in ("Kapcsold fel a lámpát, és mondd meg mit szerettem tegnap", "A kedvenc lámpám zöld.", "Kapcsold fel a kedvenc lámpámat", "Kapcsold le a lámpát este nyolckor", "Hol van a lámpa?"):
            self.assertFalse(routine_control_only(q), q)

    def test_simple_preference_does_not_skip_compound_requests(self):
        self.assertTrue(simple_preference_query('Mi Teszt Orion kedvenc gyümölcse?'))
        self.assertFalse(simple_preference_query('Mi Teszt Orion kedvenc gyümölcse, és milyen a lámpa?'))
        self.assertFalse(simple_preference_query('Mi volt Teszt Orion kedvenc gyümölcse?'))

    def test_absent_information_is_not_durable_fact(self):
        for fact in (
            "Próba Elemér kedvenc itala nincs megadva.",
            "Az adat ismeretlen.",
            "A pontos dátum nem ismert.",
        ):
            self.assertFalse(credible_extracted_fact(fact))
        self.assertTrue(credible_extracted_fact(
            "Próba Áron kedvenc itala az almalé."))


class ModelGuidanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_update_and_delete_are_requested_by_id(self):
        prompts = []
        ai = AI("synthetic")
        async def mocked(instruction, payload, timeout=25):
            prompts.append(instruction)
            return {"operations": []}
        ai.json_answer = mocked
        await ai.manage("Javítsd ki: Próba Áron kedvenc itala almalé.",
                        "update", [{"id": 1, "fact": "Próba Áron kedvenc itala körtejuice."}])
        self.assertIn("NOT add, NOT a history record", prompts[-1])
        await ai.manage("Töröld Próba Ágnes kedvenc italát.", "delete",
                        [{"id": 2, "fact": "Próba Ágnes kedvenc itala limonádé."}])
        self.assertIn("delete its ID", prompts[-1])


if __name__ == "__main__":
    unittest.main()
