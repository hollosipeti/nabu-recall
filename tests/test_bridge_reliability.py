"""Run the real bridge functions with an isolated encrypted database and fake AI.

No OpenAI network access and no live Home Assistant instance are needed.
"""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nabu_recall"))

# Server constructs its Store on import; never use /data during tests.
_BOOT = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(_BOOT.name) / "boot.sqlite3")
import server
from ai import OpenAIRequestError
from store import Store


class FakeAI:
    def __init__(self, fail=False):
        self.fail = fail
        self.learn_calls = 0

    async def search_terms(self, query):
        return ["műhelyben"]

    async def learn(self, turns, memories):
        self.learn_calls += 1
        if self.fail:
            raise OpenAIRequestError(503, "service_unavailable")
        return [{"action": "add", "fact": "A műhelyben kék Makita csavarbehajtó van."}]

    async def recall(self, query, turns, memories):
        if self.fail:
            raise OpenAIRequestError(503, "service_unavailable")
        return {"memory_ids": [m["id"] for m in memories], "turn_ids": []}


class BridgeReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_store = server.store
        self.old_ai = server.ai
        self.old_token = server.token
        self.old_lock = server.lock
        self.old_task = server._learning_task
        server.store = Store(str(Path(self.temp.name) / "isolated.sqlite3"))
        server.ai = None
        server.token = "test-bridge-token"
        server.lock = asyncio.Lock()
        server._learning_task = None
        app = web.Application(middlewares=[server.authorization])
        app.router.add_post("/bridge/ping", server.ping)
        app.router.add_post("/bridge/turn", server.log_turn)
        app.router.add_post("/bridge/recall", server.recall)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()
        self.headers = {"X-Recall-Token": "test-bridge-token"}

    async def asyncTearDown(self):
        task = server._learning_task
        if task is not None and not task.done():
            await task
        await self.client.close()
        server.store.db.close()
        server.store = self.old_store
        server.ai = self.old_ai
        server.token = self.old_token
        server.lock = self.old_lock
        server._learning_task = self.old_task
        self.temp.cleanup()

    async def test_authentication_rejects_missing_and_wrong_token(self):
        for headers in ({}, {"X-Recall-Token": "incorrect"}):
            response = await self.client.post("/bridge/ping", json={}, headers=headers)
            self.assertEqual(response.status, 401)
        response = await self.client.post("/bridge/ping", json={}, headers=self.headers)
        self.assertEqual(response.status, 200)
        self.assertTrue((await response.json())["ok"])

    async def test_missing_ai_never_blocks_verbatim_logging(self):
        data = {"user": "Szeretem a gyömbérteát.",
                "assistant": "Megértettem.", "conversation_id": "qa"}
        response = await self.client.post("/bridge/turn", json=data, headers=self.headers)
        self.assertEqual(response.status, 200)
        await server._learning_task
        row = server.store.pending()[0]
        self.assertEqual(row["user_text"], data["user"])
        self.assertEqual(row["assistant_text"], data["assistant"])
        response = await self.client.post("/bridge/recall",
                                          json={"query": "gyömbértea"},
                                          headers=self.headers)
        self.assertEqual((await response.json())["context"], "")

    async def test_outage_retains_pending_then_recovers_once(self):
        ident = server.store.add_turn("A műhelyben kék Makita csavarbehajtó van.",
                                      "Rendben.", "c")
        fake = FakeAI(fail=True)
        server.ai = fake
        await server.process_pending()
        self.assertEqual([row["id"] for row in server.store.pending()], [ident])
        self.assertEqual(server.store.memory_list(), [])
        fake.fail = False
        await server.process_pending()
        self.assertEqual(server.store.pending(), [])
        self.assertEqual(len(server.store.memory_list()), 1)
        await server.process_pending()
        self.assertEqual(len(server.store.memory_list()), 1)
        self.assertEqual(fake.learn_calls, 2)

    async def test_busy_memory_lock_does_not_drop_learning(self):
        ident = server.store.add_turn(
            "A műhelyben kék Makita csavarbehajtó van.", "Rendben.", "busy")
        fake = FakeAI()
        server.ai = fake
        await server.lock.acquire()
        try:
            task = asyncio.create_task(server.process_pending())
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertEqual([r["id"] for r in server.store.pending()], [ident])
        finally:
            server.lock.release()
        await asyncio.wait_for(task, timeout=3)
        self.assertEqual(server.store.pending(), [])
        self.assertEqual(fake.learn_calls, 1)
        self.assertEqual(len(server.store.memory_list()), 1)

    async def test_invalid_api_payload_does_not_create_journal(self):
        for data in ({"user": "", "assistant": "ok"},
                     {"user": "hello", "assistant": 12},
                     {"user": "x" * 12001, "assistant": "ok"}):
            response = await self.client.post(
                "/bridge/turn", json=data, headers=self.headers)
            self.assertEqual(response.status, 400)
        self.assertEqual(server.store.statistics()["turns"], 0)

    async def test_recall_outage_is_nonfatal(self):
        server.store.apply([{"action": "add", "fact": "A műhelyben van egy szerszám."}])
        server.ai = FakeAI(fail=True)
        response = await self.client.post("/bridge/recall",
                                          json={"query": "Milyen szerszámom van?"},
                                          headers=self.headers)
        self.assertEqual(response.status, 200)
        data = await response.json()
        self.assertEqual(data["context"], "")
        self.assertEqual(data["warning"], "AI unavailable")
        server.ai.fail = False
        response = await self.client.post("/bridge/recall",
                                          json={"query": "Milyen szerszámom van?"},
                                          headers=self.headers)
        self.assertEqual(response.status, 200)
        self.assertIn("A műhelyben van egy szerszám.", (await response.json())["context"])


if __name__ == "__main__":
    unittest.main()
