"""Bridge recall chooses historic, relevant durable facts across the full table."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from store import Store

db_home = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = os.path.join(db_home.name, "server-import.sqlite3")
import server


class FakeRecallAI:
    async def search_terms(self, query):
        return ["Reolink"]

    async def recall(self, query, turns, memories):
        selected = next(
            (x["id"] for x in memories if "Reolink" in x["fact"]), None
        )
        return {"turn_ids": [], "memory_ids": [selected] if selected else []}


class HistoricalRecallTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = (server.store, server.ai, server.token)
        server.store = Store(Path(self.tmp.name) / "data.sqlite3")
        server.ai = FakeRecallAI()
        server.token = "test-bridge-token"
        app = web.Application(middlewares=[server.authorization])
        app.router.add_post("/bridge/recall", server.recall)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        server.store.db.close()
        server.store, server.ai, server.token = self.old
        self.tmp.cleanup()

    async def test_two_distinct_durable_identifier_facts_both_reach_context(self):
        """Even if AI picks one memory, structured recall includes the other."""
        class FirstOnlyAI:
            async def search_terms(self, query):
                return ["Apa", "taj", "személyi"]
            async def recall(self, query, turns, memories):
                picked = next(x for x in memories if "TAJ" in x["fact"])
                return {"turn_ids": [], "memory_ids": [picked["id"]]}

        server.ai = FirstOnlyAI()
        server.store.apply([
            {"action": "add", "fact": "Apa (Peti) TAJ száma 123456789."},
            {"action": "add", "fact": "Apa személyi igazolvány száma: 111222AB."},
            {"action": "add", "fact": "Anya (Betti) személyi igazolvány száma: 222333CD."},
        ])
        response = await self.client.post(
            "/bridge/recall",
            json={"query": "Mi apa TAJ-száma és személyi igazolvány száma?"},
            headers={"X-Recall-Token": "test-bridge-token"}
        )
        self.assertEqual(response.status, 200)
        data = (await response.json())["context"]
        self.assertIn("123456789", data)
        self.assertIn("111222AB", data)
        self.assertNotIn("222333CD", data)

    async def test_unrelated_multiword_identity_is_filtered_out(self):
        """An LLM shortlist selecting a shared surname must not leak another ID."""
        class WrongPickAI:
            async def search_terms(self, query):
                return ["Teszt", "TAJ"]
            async def recall(self, query, turns, memories):
                return {"turn_ids": [], "memory_ids": [m["id"] for m in memories]}

        server.ai = WrongPickAI()
        server.store.apply([
            {"action": "add", "fact": "Teszt Béla TAJ száma 123456789."},
            {"action": "add", "fact": "Teszt Gábor TAJ száma 987654321."},
        ])
        response = await self.client.post(
            "/bridge/recall", json={"query": "Mi Teszt Géza TAJ-száma?"},
            headers={"X-Recall-Token": "test-bridge-token"}
        )
        self.assertEqual(response.status, 200)
        context = (await response.json())["context"]
        self.assertNotIn("123456789", context)
        self.assertNotIn("987654321", context)

    async def test_yesterday_recall_excludes_today_and_timeless_facts(self):
        """The assistant may not turn today's conversation into yesterday's."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from unittest.mock import patch
        tz = ZoneInfo("Europe/Budapest")
        today = int(datetime(2026, 11, 24, 8, 0, tzinfo=tz).timestamp())
        yesterday = int(datetime(2026, 11, 23, 9, 0, tzinfo=tz).timestamp())
        yesterday_id = server.store.add_turn(
            "Tegnap a műhelyben piros doboz volt.", "Értem.",
            created=yesterday)
        server.store.add_turn(
            "A műhelyben narancssárga doboz van.", "Értem.",
            created=today)
        server.store.apply([
            {"action": "add", "fact": "A műhelyben narancssárga doboz van."}
        ])
        class AllSelectingAI:
            async def search_terms(self, query):
                return ["doboz"]
            async def recall(self, query, turns, memories):
                return {"turn_ids": [t["id"] for t in turns],
                        "memory_ids": [m["id"] for m in memories]}
        server.ai = AllSelectingAI()
        day_begin = int(datetime(2026, 11, 23, 0, 0, tzinfo=tz).timestamp())
        day_end = int(datetime(2026, 11, 24, 0, 0, tzinfo=tz).timestamp())
        with patch.object(server, "journal_window", return_value=(day_begin, day_end)):
            response = await self.client.post(
                "/bridge/recall",
                json={"query": "Mit mondtam tegnap a dobozról?"},
                headers={"X-Recall-Token": "test-bridge-token"})
        result = (await response.json())["context"]
        self.assertIn("Tegnap a műhelyben piros", result)
        self.assertNotIn("narancssárga", result)
        self.assertNotIn("Fact:", result)

    async def test_old_fact_is_recalled_beyond_latest_200(self):
        server.store.apply([{
            "action": "add",
            "fact": "A Reolink kamera a garázs fölött van."
        }])
        oldest = server.store.memory_list()[0]["id"]
        for i in range(500):
            server.store.apply([{
                "action": "add", "fact": "Egyedi villany mérőadat %06d" % i
            }])
        self.assertNotIn(oldest, [
            m["id"] for m in server.store.memory_list(200)
        ])
        response = await self.client.post(
            "/bridge/recall",
            json={"query": "Hol van a Reolink kamera?"},
            headers={"X-Recall-Token": "test-bridge-token"}
        )
        self.assertEqual(response.status, 200)
        payload = await response.json()
        self.assertIn("Reolink kamera a garázs fölött", payload["context"])


if __name__ == "__main__":
    unittest.main()
