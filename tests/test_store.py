"""SQLite memory, retention, and text retrieval unit tests."""
import os
import sys
import tempfile
import time
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nabu_recall"))
from store import Store

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "test.sqlite3"))

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def test_verbatim(self):
        turn_id = self.store.add_turn("Jegyezd meg!", "Rendben.", "abc")
        row = self.store.pending()[0]
        self.assertEqual(row["id"], turn_id)
        self.assertEqual(row["user_text"], "Jegyezd meg!")
        self.assertEqual(row["assistant_text"], "Rendben.")

    def test_strict_45_days(self):
        now = 2_000_000_000
        self.store.add_turn("old", "answer", created=now - 46 * 86400)
        self.store.add_turn("recent", "answer", created=now - 44 * 86400)
        self.assertEqual(self.store.purge(now), 1)
        self.assertEqual(len(self.store.pending()), 1)

    def test_learning_and_update(self):
        fact = "Szeretem a gyömbérteát."
        self.store.apply([{"action": "add", "fact": fact}])
        self.store.apply([{"action": "add", "fact": fact}])
        self.assertEqual(len(self.store.memory_list()), 1)
        ident = self.store.memory_list()[0]["id"]
        self.store.apply([{"action": "update", "id": ident, "fact": "Most zöld teát iszom."}])
        self.assertEqual(self.store.memory_list()[0]["fact"], "Most zöld teát iszom.")
        self.store.remove_memory(ident)
        self.assertFalse(self.store.memory_list())

    def test_read_only_journal_audit(self):
        m1 = self.store.add_turn("első", "", "c1")
        self.store.add_turn("második", "  ", "c1")
        self.store.add_turn("harmadik", "válasz", "c2")
        self.store.processed([m1])
        self.store.apply([{"action": "add", "fact": "Megőrzendő emlék."}], m1)
        before = self.store.statistics()
        summary = self.store.journal_integrity_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["missing"], 2)
        self.assertEqual(summary["complete"], 1)
        self.assertEqual(summary["missing_processed"], 1)
        self.assertEqual(summary["missing_pending"], 1)
        self.assertEqual(len(summary["sample_missing_ids"]), 2)
        self.assertEqual(before, self.store.statistics())
        self.assertEqual(self.store.memory_list()[0]["source_turn"], m1)

    def test_empty_journal_audit(self):
        summary = self.store.journal_integrity_summary()
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["sample_missing_ids"], [])

    def test_processed(self):
        ident = self.store.add_turn("u", "a")
        self.store.processed([ident])
        self.assertFalse(self.store.pending())

    def test_search_old_turns(self):
        self.store.add_turn(
            "Villanyszerelő jön a garázshoz", "Rendben",
            created=int(time.time()) - 30 * 86400)
        for _ in range(130):
            self.store.add_turn("Világítás kapcsolása", "Megvan")
        rows = self.store.candidates(["villanyszerelő"])
        self.assertTrue(any("Villanyszerelő" in row["user_text"] for row in rows))

if __name__ == "__main__":
    unittest.main()
