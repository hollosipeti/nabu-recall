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
        self.assertEqual(summary["referenced_memories"], 1)
        self.assertEqual(summary["referenced_turns"], 1)
        self.assertEqual(summary["unreferenced_processed"], 0)
        self.assertEqual(summary["orphan_sources"], 0)
        self.assertEqual(summary["sample_referenced_ids"], [m1])
        self.assertEqual(before, self.store.statistics())
        self.assertEqual(self.store.memory_list()[0]["source_turn"], m1)

    def test_empty_journal_audit(self):
        summary = self.store.journal_integrity_summary()
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["sample_missing_ids"], [])

    def test_audit_orphan_sources_and_unreferenced_turns(self):
        old = self.store.add_turn("old", "")
        pending = self.store.add_turn("pending", "")
        self.store.processed([old])
        self.store.apply([{"action":"add","fact":"unlinked"}], 99999)
        report = self.store.journal_integrity_summary()
        self.assertEqual(report["missing"], 2)
        self.assertEqual(report["unreferenced_processed"], 1)
        self.assertEqual(report["missing_pending"], 1)
        self.assertEqual(report["orphan_sources"], 1)
        self.assertEqual(report["referenced_memories"], 0)
        self.assertEqual(self.store.pending()[0]["id"], pending)

    def test_audit_multiple_memories_same_source(self):
        ident = self.store.add_turn("q", "")
        self.store.processed([ident])
        self.store.apply([{"action":"add","fact":"A"}, {"action":"add","fact":"B"}], ident)
        report = self.store.journal_integrity_summary()
        self.assertEqual(report["referenced_memories"], 2)
        self.assertEqual(report["referenced_turns"], 1)
        self.assertEqual(report["sample_referenced_ids"], [ident])

    def test_cleanup_preview_groups_are_disjoint(self):
        p = self.store.add_turn("pending", "")
        linked = self.store.add_turn("linked", "")
        unlinked = self.store.add_turn("unlinked", " ")
        self.store.add_turn("complete", "assistant")
        self.store.processed([linked, unlinked])
        self.store.apply([{"action":"add","fact":"linked fact"}], linked)
        before = self.store.statistics()
        groups = self.store.journal_cleanup_preview()
        self.assertEqual([groups[n]["count"] for n in
                          ("pending", "linked", "unlinked")], [1, 1, 1])
        self.assertEqual(groups["pending"]["sample_ids"], [p])
        self.assertEqual(groups["linked"]["sample_ids"], [linked])
        self.assertEqual(groups["unlinked"]["sample_ids"], [unlinked])
        self.assertEqual(sum(g["count"] for g in groups.values()),
                         self.store.journal_integrity_summary()["missing"])
        self.assertEqual(before, self.store.statistics())
        self.assertEqual(len(self.store.memory_list()), 1)

    def test_cleanup_preview_empty(self):
        result = self.store.journal_cleanup_preview()
        self.assertTrue(all(x["count"] == 0 and not x["sample_ids"]
                            for x in result.values()))

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
