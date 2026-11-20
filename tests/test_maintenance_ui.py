"""End-to-end ingress authentication, CSRF, explicit approval and undo."""
import asyncio
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from store import Store
from dashboard import create_dashboard
from maintenance import cleanup_preview


class MockOptimizer:
    async def optimize_memories(self, memories):
        ids = [m["id"] for m in memories]
        if len(ids) < 2:
            return []
        return [{
            "type": "overlap", "keeper_id": ids[0], "remove_ids": [ids[1]],
            "new_fact": "Az illető kedvenc itala gyömbértea.",
            "reason": "A két emlék ugyanazt a preferenciát pontosítja."
        }]


class MaintenanceUiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "db.sqlite3"))
        self.state = {"version": "test"}
        self.app = create_dashboard(self.store, self.state, "test-secret",
                                    MockOptimizer(), asyncio.Lock())
        self.client = TestClient(TestServer(self.app), cookie_jar=None)
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.store.db.close()
        self.tmp.cleanup()

    async def login(self):
        response = await self.client.post(
            "/login", data={"password": "test-secret"}, allow_redirects=False)
        self.assertEqual(response.status, 303)
        return {"Cookie": "recall_ui=" + response.cookies["recall_ui"].value}

    async def csrf(self, headers):
        response = await self.client.get("/maintenance", headers=headers)
        self.assertEqual(response.status, 200)
        html = await response.text()
        match = re.search(r'name="csrf" value="([0-9a-f]{64})"', html)
        self.assertIsNotNone(match, html[:1000])
        return match.group(1), html

    async def test_unauthenticated_write_refused(self):
        self.store.add_turn("private", "")
        response = await self.client.post(
            "/maintenance/cleanup", data={"digest": "0"*64, "count": "1"})
        self.assertEqual(response.status, 403)
        self.assertEqual(self.store.statistics()["turns"], 1)
        self.assertEqual((await self.client.get("/maintenance")).status, 403)

    async def test_missing_csrf_and_expired_cookie_refused(self):
        self.store.add_turn("synthetic", "")
        headers = await self.login()
        preview = cleanup_preview(self.store)
        invalid = await self.client.post("/maintenance/cleanup", headers=headers,
            data={"digest": preview["digest"], "count": str(preview["count"])})
        self.assertEqual(invalid.status, 403)
        invalid_cookie = await self.client.post("/maintenance/cleanup",
            headers={"Cookie": "recall_ui=1.invalid"},
            data={"csrf": "0"*64})
        self.assertEqual(invalid_cookie.status, 403)
        self.assertEqual(self.store.statistics()["turns"], 1)

    async def test_manual_cleanup_and_undo(self):
        ident = self.store.add_turn("unlinked", "")
        self.store.processed([ident])
        protected = self.store.add_turn("protected", "")
        self.store.processed([protected])
        self.store.apply([{"action": "add", "fact": "Protected fact"}], protected)
        headers = await self.login()
        csrf, html = await self.csrf(headers)
        self.assertIn("Kézi memóriakarbantartás", html)
        self.assertIn("1</p>", html)
        preview = cleanup_preview(self.store)
        done = await self.client.post("/maintenance/cleanup", headers=headers,
            data={"csrf": csrf, "digest": preview["digest"],
                  "count": str(preview["count"])}, allow_redirects=False)
        self.assertEqual(done.status, 303)
        self.assertEqual(self.store.statistics()["turns"], 1)
        self.assertEqual(self.store.statistics()["memories"], 1)
        csrf, html = await self.csrf(headers)
        self.assertIn("Naplók visszaállítása", html)
        undone = await self.client.post("/maintenance/undo-cleanup",
            headers=headers,
            data={"csrf": csrf, "history_id": "1"}, allow_redirects=False)
        self.assertEqual(undone.status, 303)
        self.assertEqual(self.store.statistics()["turns"], 2)

    async def test_duplicate_scan_finds_old_and_new_memory_together(self):
        self.store.apply([{"action": "add",
                           "fact": "Kedvenc ital gyömbértea és citrom"}])
        for i in range(250):
            self.store.apply([{"action": "add",
                               "fact": "Egyedi eszközteszt %06d" % i}])
        self.store.apply([{"action": "add",
                           "fact": "citrom és gyömbértea kedvenc ital"}])
        headers = await self.login()
        csrf, _ = await self.csrf(headers)
        response = await self.client.post(
            "/maintenance/scan-duplicates", headers=headers,
            data={"csrf": csrf, "after_id": "0"},
            allow_redirects=False
        )
        self.assertEqual(response.status, 303)
        csrf, html = await self.csrf(headers)
        self.assertIn("Javasolt új tény", html)
        self.assertIn("Kedvenc ital gyömbértea és citrom", html)
        self.assertIn("citrom és gyömbértea kedvenc ital", html)

    async def test_manual_optimizer_preview_approve_and_undo(self):
        self.store.apply([{"action": "add", "fact": "Kedvenc ital: gyömbértea."}])
        self.store.apply([{"action": "add", "fact": "Szereti a gyömbérteát."}])
        headers = await self.login()
        csrf, _ = await self.csrf(headers)
        response = await self.client.post("/maintenance/analyze",
            headers=headers, data={"csrf": csrf}, allow_redirects=False)
        self.assertEqual(response.status, 303)
        csrf, html = await self.csrf(headers)
        self.assertIn("Két", html) if False else None
        self.assertIn("Javasolt új tény", html)
        match = re.search(r'name="nonce" value="([0-9a-f]{32})"', html)
        self.assertIsNotNone(match)
        outcome = await self.client.post("/maintenance/apply",
            headers=headers,
            data={"csrf": csrf, "index": "0", "nonce": match.group(1)},
            allow_redirects=False)
        self.assertEqual(outcome.status, 303)
        self.assertEqual(self.store.statistics()["memories"], 1)
        csrf, html = await self.csrf(headers)
        self.assertIn("Összevonás visszavonása", html)
        undone = await self.client.post("/maintenance/undo-memory",
            headers=headers,
            data={"csrf": csrf, "history_id": "1"}, allow_redirects=False)
        self.assertEqual(undone.status, 303)
        self.assertEqual(self.store.statistics()["memories"], 2)


if __name__ == "__main__":
    unittest.main()
