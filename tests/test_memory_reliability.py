"""Focused regression checks for memory recall and coalesced background jobs."""
import ast
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nabu_recall"))
from store import Store


class SearchReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.temp.name, "test.sqlite3"))

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_old_fact_is_recalled_among_many(self):
        self.store.apply([{"action": "add", "fact": "A műhelyben egy kék Makita csavarbehajtó van."}])
        original = self.store.memory_list()[0]["id"]
        for index in range(350):
            self.store.apply([{"action": "add", "fact": f"Külön tény {index}: nappali világítás."}])
        rows = self.store.memory_search(["muhelyben", "csavarbehajto"])
        self.assertEqual([row["id"] for row in rows], [original])

    def test_no_accidental_wildcard_search(self):
        self.store.apply([{"action": "add", "fact": "A műhelyben van egy fúró."}])
        self.assertEqual(self.store.memory_search(["%"]), [])
        self.assertEqual(self.store.memory_search(["_"]), [])
        self.assertEqual(len(self.store.memory_search(["FURÓ"])), 1)

    def test_whitespace_and_unicode_cases(self):
        self.store.apply([{"action": "add", "fact": "Ősszel a fűtés beindul."}])
        self.assertEqual(len(self.store.memory_search(["OSSZEL"])), 1)
        self.assertEqual(len(self.store.memory_search(["futes"])), 1)
        self.assertEqual(self.store.memory_search([]), [])


class CoalescedLearningTests(unittest.IsolatedAsyncioTestCase):
    async def test_burst_schedules_one_worker_then_allows_new_worker(self):
        # Load the actual function without initializing the live SQLCipher
        # server, OpenAI client or web listener.
        tree = ast.parse((ROOT / "nabu_recall" / "server.py").read_text(encoding="utf-8"))
        function = next(x for x in tree.body
                        if isinstance(x, ast.FunctionDef) and x.name == "schedule_learning")
        runs = []
        started = asyncio.Event()
        release = asyncio.Event()

        async def simulated_pending_worker():
            runs.append(1)
            started.set()
            await release.wait()

        namespace = {
            "asyncio": asyncio,
            "_learning_task": None,
            "process_pending": simulated_pending_worker,
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]),
                     "server.py", "exec"), namespace)
        schedule = namespace["schedule_learning"]
        for _ in range(100):
            schedule()
        await asyncio.wait_for(started.wait(), timeout=2)
        self.assertEqual(len(runs), 1)
        for _ in range(100):
            schedule()
        self.assertEqual(len(runs), 1)
        release.set()
        await namespace["_learning_task"]
        schedule()
        await namespace["_learning_task"]
        self.assertEqual(len(runs), 2)


if __name__ == "__main__":
    unittest.main()
