"""100,000 durable-memory SQLCipher scale regression and retrieval coverage.

No external API calls, no household data; facts are synthetic and deterministic.
Test the actual production Store, not a mock sqlite3 schema.
"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from store import Store


class DurableMemoryScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.tmp.name) / "scale.sqlite3")
        started = time.perf_counter()
        now = int(time.time())
        # Use the same real encrypted connection and actual schema.
        with cls.store.db:
            cls.store.db.executemany(
                "INSERT INTO memories(created,updated,fact,source_turn) "
                "VALUES(?,?,?,NULL)",
                ((now, now + i, "Mesterséges projekt %06d: eszközteszt %06d." % (i,i))
                 for i in range(100000))
            )
        cls.insert_seconds = time.perf_counter() - started

    @classmethod
    def tearDownClass(cls):
        cls.store.db.close()
        cls.tmp.cleanup()

    def test_100k_persistence_and_reopen(self):
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM memories").fetchone()[0], 100000)
        self.assertEqual(self.store.statistics()["memories"], 100000)
        key = Path(self.tmp.name) / "scale.key"
        self.assertTrue(key.exists())
        self.assertEqual(key.stat().st_mode & 0o777, 0o600)
        original = self.store.db.execute(
            "SELECT fact FROM memories WHERE id=1").fetchone()[0]
        self.assertIn("000000", original)

    def test_current_200_window_omits_oldest_99800(self):
        """Characterization of the existing functional limit, not a performance pass."""
        candidates = self.store.memory_list(200)
        self.assertEqual(len(candidates), 200)
        self.assertFalse(any(x["id"] == 1 for x in candidates))
        self.assertEqual(candidates[0]["id"], 100000)

    def test_search_retrieves_oldest_memory_not_in_recent_200(self):
        terms = self.store.memory_query_terms(
            "Mit tudsz a mesterséges projekt 000000 eszköztesztjéről?")
        self.assertIn("000000", terms)
        results = self.store.memory_search(["000000"], limit=40)
        self.assertTrue(any(row["id"] == 1 for row in results))
        self.assertFalse(any(row["id"] == 1
                             for row in self.store.memory_list(200)))

    def test_keyset_pages_reach_entire_100k_without_missing_ids(self):
        cursor = 0
        seen = 0
        while True:
            page = self.store.memory_page(after_id=cursor, limit=200)
            if not page:
                break
            self.assertGreater(page[0]["id"], cursor)
            cursor = page[-1]["id"]
            seen += len(page)
        self.assertEqual(seen, 100000)
        self.assertEqual(cursor, 100000)

    def test_duplicate_groups_across_distant_ids(self):
        # Two near-duplicates whose IDs are 89,900 records apart.
        original = self.store.db.execute(
            "SELECT id,fact FROM memories WHERE id IN (100,90000)"
        ).fetchall()
        with self.store.db:
            self.store.db.execute(
                "UPDATE memories SET fact=? WHERE id=100",
                ("Kedvenc ital: gyömbértea és citrom",))
            self.store.db.execute(
                "UPDATE memories SET fact=? WHERE id=90000",
                ("citrom és gyömbértea kedvenc ital",))
        try:
            result = self.store.memory_duplicate_page()
            ids = [x["id"] for x in result["memories"]]
            self.assertIn(100, ids)
            self.assertIn(90000, ids)
            self.assertGreaterEqual(result["groups"], 1)
        finally:
            with self.store.db:
                for ident, fact in original:
                    self.store.db.execute(
                        "UPDATE memories SET fact=? WHERE id=?", (fact, ident))

    def test_100k_sqlcipher_exact_lookup_baseline(self):
        start = time.perf_counter()
        facts = self.store.db.execute(
            "SELECT id,fact FROM memories WHERE fact LIKE ? "
            "ORDER BY updated DESC LIMIT 60",
            ("%eszközteszt 000002%",)
        ).fetchall()
        elapsed = time.perf_counter() - start
        self.assertEqual(len(facts), 1)
        self.assertIn("000002", facts[0]["fact"])
        print("MEMORY_SCALE: insert100k_s=%.3f; linear_like_lookup_s=%.3f"
              % (self.insert_seconds, elapsed), flush=True)


if __name__ == "__main__":
    unittest.main()
