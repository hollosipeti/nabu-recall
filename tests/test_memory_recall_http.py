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
