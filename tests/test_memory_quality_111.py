"""Memory quality and transaction safety regression tests (no live API)."""
import asyncio
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nabu_recall"))
from store import Store
from ai import AI


class AtomicLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "quality.sqlite3")

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_learning_commits_fact_and_ack_together(self):
        turn_id = self.store.add_turn("Apa autója most BYD.", "Rendben.")
        self.store.apply_learning_batch(
            [{"action": "add", "fact": "Apa autója BYD."}], [turn_id], turn_id)
        self.assertEqual(len(self.store.memory_list()), 1)
        self.assertEqual(self.store.pending(), [])
        self.assertEqual(self.store.memory_list()[0]["source_turn"], turn_id)

    def test_failed_ack_rolls_back_added_memory(self):
        turn_id = self.store.add_turn("Apa autója BYD.", "Rendben.")
        self.store.db.execute(
            "CREATE TRIGGER reject_ack BEFORE UPDATE OF processed ON turns "
            "BEGIN SELECT RAISE(ABORT, 'simulated disk error'); END;")
        with self.assertRaises(Exception):
            self.store.apply_learning_batch(
                [{"action": "add", "fact": "Apa autója BYD."}],
                [turn_id], turn_id)
        self.assertEqual(self.store.memory_list(), [])
        self.assertEqual(len(self.store.pending()), 1)

    def test_failed_ack_rolls_back_replacement(self):
        self.store.apply([
            {"action": "add", "fact": "Apa autója Suzuki."},
            {"action": "add", "fact": "Betti autója Toyota."}])
        old = {row["fact"]: row["id"] for row in self.store.memory_list()}
        turn_id = self.store.add_turn("Apa BYD-ra cserélte.", "Értem.")
        self.store.db.execute(
            "CREATE TRIGGER reject_ack BEFORE UPDATE OF processed ON turns "
            "BEGIN SELECT RAISE(ABORT, 'simulated disk error'); END;")
        with self.assertRaises(Exception):
            self.store.apply_learning_batch(
                [{"action": "update", "id": old["Apa autója Suzuki."],
                  "fact": "Apa autója BYD."}], [turn_id], turn_id)
        facts = {row["fact"] for row in self.store.memory_list()}
        self.assertEqual(facts, {"Apa autója Suzuki.", "Betti autója Toyota."})
        self.assertEqual(len(self.store.pending()), 1)

    def test_successful_correction_keeps_other_person(self):
        self.store.apply([
            {"action": "add", "fact": "Apa autója Suzuki."},
            {"action": "add", "fact": "Betti autója Toyota."}])
        old = {row["fact"]: row["id"] for row in self.store.memory_list()}
        turn_id = self.store.add_turn("Apa lecserélte az autót BYD-ra.", "Értem.")
        self.store.apply_learning_batch(
            [{"action": "update", "id": old["Apa autója Suzuki."],
              "fact": "Apa autója BYD."}], [turn_id], turn_id)
        facts = {row["fact"] for row in self.store.memory_list()}
        self.assertEqual(facts, {"Apa autója BYD.", "Betti autója Toyota."})


class ModelInstructionTests(unittest.IsolatedAsyncioTestCase):
    async def test_learning_guidance_includes_ownership_and_corrections(self):
        model = AI("dummy")
        prompts = []
        async def fake_answer(instruction, payload, timeout=25):
            prompts.append(instruction)
            return {"operations": []}
        model.json_answer = fake_answer
        await model.learn(
            [{"user_text": "Apa lecserélte a Suzukit BYD-ra."}],
            [{"id": 1, "fact": "Apa autója Suzuki."},
             {"id": 2, "fact": "Betti autója Toyota."}])
        self.assertIn("never Betti's Toyota", prompts[0])
        self.assertIn("update that record", prompts[0])
        self.assertIn("A new, additional item", prompts[0])

    async def test_recall_guidance_handles_multiple_items(self):
        model = AI("dummy")
        prompts = []
        async def fake_answer(instruction, payload, timeout=25):
            prompts.append(instruction)
            return {"memory_ids": [1, 2], "turn_ids": []}
        model.json_answer = fake_answer
        await model.recall(
            "Milyen eszközök vannak a műhelyben?", [],
            [{"id": 1, "fact": "Makita csavarbehajtó"},
             {"id": 2, "fact": "Bosch fúrógép"}])
        self.assertIn("select each relevant ID", prompts[0])
        self.assertIn("do not mix different people's objects", prompts[0])


if __name__ == "__main__":
    unittest.main()
