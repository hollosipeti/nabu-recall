"""Regressions: shopping list actions never become durable memories."""
import asyncio
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nabu_recall"))

from shopping_filter import is_shopping_list_action
from store import Store
import server


class ShoppingGuardTests(unittest.TestCase):
    def test_actual_user_reports_are_skipped(self):
        cases = [
            ("Tedd a bevásárlólistára a vécépapírt.",
             "A bevásárlólistához hozzáadva: vécé."),
            ("Adj hozzá egy CG golyót a bevásárlólistához.",
             "A bevásárlólistához hozzáadva: Cg golyó."),
            ("Hozzáadnál tejet a bevásárlólistához?",
             "Hozzáadva a bevásárlólistához: tej."),
            ("Végy le kenyeret a bevásárlólistáról.",
             "A bevásárlólistáról törölve: kenyér."),
            ("Vegyél fel vajat a bevásárlólistára.", "Kész."),
            ("Tedd a bevásárló listára a cukrot.", "Kész."),
            ("Add milk to shopping list.", "Added to shopping list."),
        ]
        for user, assistant in cases:
            with self.subTest(user=user):
                self.assertTrue(is_shopping_list_action(user, assistant))

    def test_preferences_and_explicit_memory_remain_eligible(self):
        cases = [
            ("Jegyezd meg, hogy a bevásárlólistát Anna vezeti.", "Rendben."),
            ("A bevásárlólistához általában egy liter tejet írunk.", "Értem."),
            ("Mindig laktózmentes tejet veszünk.", "Rendben."),
            ("A boltban a kedvenc teám gyömbértea.", "Értem."),
            ("Mit tettünk tegnap a bevásárlólistára?", "Nem tudom."),
            ("Jegyezd meg, hogy a heti bevásárlás kedden van.",
             "Megjegyeztem."),
            ("Milyen listát használunk a bevásárláshoz?", "A közös listát."),
        ]
        for user, assistant in cases:
            with self.subTest(user=user):
                self.assertFalse(is_shopping_list_action(user, assistant))


class ShoppingBatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_store, self.old_ai, self.old_lock = server.store, server.ai, server.lock
        self.store = Store(Path(self.temp.name) / "shopping.sqlite3")
        server.store, server.lock = self.store, asyncio.Lock()
        self.fake = self.FakeAI()
        server.ai = self.fake

    async def asyncTearDown(self):
        self.store.db.close()
        self.temp.cleanup()
        server.store, server.ai, server.lock = (
            self.old_store, self.old_ai, self.old_lock)

    class FakeAI:
        def __init__(self):
            self.learn_batches = []
            self.search_calls = 0

        async def search_terms(self, query):
            self.search_calls += 1
            return ["tevékenység"]

        async def learn(self, turns, memories):
            self.learn_batches.append(turns)
            return [{"action": "add", "fact": row["user_text"]}
                    for row in turns]

    async def test_only_shopping_turns_do_not_call_ai(self):
        self.store.add_turn("Hozzáadnál cukrot a bevásárlólistához?",
                            "A bevásárlólistához hozzáadva: cukor.")
        self.store.add_turn("Tedd a bevásárlólistára a kávét.",
                            "A bevásárlólistához hozzáadva: kávé.")
        await server.process_pending()
        self.assertEqual(self.fake.search_calls, 0)
        self.assertEqual(self.fake.learn_batches, [])
        self.assertEqual(self.store.memory_list(), [])
        self.assertEqual(self.store.pending(), [])
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM turns").fetchone()[0], 2)

    async def test_mixed_batch_learns_only_real_fact(self):
        self.store.add_turn("Tedd a bevásárlólistára a kávét.",
                            "A bevásárlólistához hozzáadva: kávé.")
        self.store.add_turn("A kedvenc kávém arabica.", "Értem.")
        self.store.add_turn("Rakj tejet a bevásárlólistára.",
                            "A bevásárlólistához hozzáadva: tej.")
        await server.process_pending()
        self.assertEqual(len(self.fake.learn_batches), 1)
        self.assertEqual(len(self.fake.learn_batches[0]), 1)
        self.assertIn("arabica", self.fake.learn_batches[0][0]["user_text"])
        self.assertEqual(len(self.store.memory_list()), 1)
        self.assertEqual(self.store.pending(), [])
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM turns").fetchone()[0], 3)

    async def test_explicit_memory_request_kept(self):
        self.store.add_turn(
            "Jegyezd meg, hogy a bevásárlólistát Anna kezeli.", "Rendben.")
        await server.process_pending()
        self.assertEqual(len(self.fake.learn_batches), 1)
        self.assertEqual(len(self.store.memory_list()), 1)


if __name__ == "__main__":
    unittest.main()
