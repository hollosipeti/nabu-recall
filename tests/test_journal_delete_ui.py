"""Protected web flow: checkbox selection -> preview -> irreversible deletion."""
import asyncio
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

from aiohttp.test_utils import TestClient, TestServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from store import Store
from dashboard import create_dashboard


class JournalDeletionUiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.temp.name, "recall.sqlite3"))
        self.app = create_dashboard(self.store, {"version": "2.0.1"},
                                    "test-secret", None, asyncio.Lock())
        self.client = TestClient(TestServer(self.app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.store.db.close()
        self.temp.cleanup()

    async def login(self):
        response = await self.client.post("/login",
                                          data={"password": "test-secret"},
                                          allow_redirects=False)
        self.assertEqual(response.status, 303)
        return {"Cookie": "recall_ui=" + response.cookies["recall_ui"].value}

    async def csrf(self, headers):
        response = await self.client.get("/maintenance/journal", headers=headers)
        self.assertEqual(response.status, 200)
        html = await response.text()
        match = re.search(r'name="csrf" value="([0-9a-f]{64})"', html)
        self.assertIsNotNone(match)
        return match.group(1), html

    def add(self, question, processed=True, linked=False):
        ident = self.store.add_turn(question, "A synthetic reply.")
        if processed:
            self.store.processed([ident])
        if linked:
            self.store.apply([{"action": "add",
                               "fact": f"Source for test {ident}."}], ident)
        return ident

    async def test_select_confirm_and_permanent_no_archive(self):
        ident = self.add("A user question <script>alert(1)</script>")
        untouched = self.add("Real durable source", linked=True)
        headers = await self.login()
        csrf, html = await self.csrf(headers)
        self.assertIn("végleges törlés", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn(f'name="journal_id" value="{ident}"', html)
        self.assertIn("disabled", html)

        preview = await self.client.post(
            "/maintenance/journal/select", headers=headers,
            data=[("csrf", csrf), ("journal_id", str(ident))],
            allow_redirects=False)
        self.assertEqual(preview.status, 303)
        self.assertEqual(self.store.statistics()["turns"], 2)
        csrf, html = await self.csrf(headers)
        self.assertIn("Végső ellenőrzés", html)
        token = re.search(r'name="confirm" value="([0-9a-f]{32})"', html)
        self.assertIsNotNone(token)
        delete = await self.client.post(
            "/maintenance/journal/confirm", headers=headers,
            data={"csrf": csrf, "confirm": token.group(1), "ack": "yes"},
            allow_redirects=False)
        self.assertEqual(delete.status, 303)
        self.assertEqual(self.store.statistics()["turns"], 1)
        self.assertEqual(self.store.statistics()["memories"], 1)
        self.assertEqual(self.store.recent_turns()[0]["id"], untouched)
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM journal_archive").fetchone()[0], 0)
        repeat = await self.client.post(
            "/maintenance/journal/confirm", headers=headers,
            data={"csrf": csrf, "confirm": token.group(1), "ack": "yes"},
            allow_redirects=False)
        self.assertEqual(repeat.status, 303)
        self.assertEqual(self.store.statistics()["turns"], 1)

    async def test_auth_csrf_and_bypassed_approval_blocked(self):
        ident = self.add("Do not delete silently")
        unauth = await self.client.post(
            "/maintenance/journal/select", data={"journal_id": str(ident)},
            allow_redirects=False)
        self.assertEqual(unauth.status, 403)
        headers = await self.login()
        no_csrf = await self.client.post(
            "/maintenance/journal/select", headers=headers,
            data={"journal_id": str(ident)}, allow_redirects=False)
        self.assertEqual(no_csrf.status, 403)
        csrf, _ = await self.csrf(headers)
        without_preview = await self.client.post(
            "/maintenance/journal/confirm", headers=headers,
            data={"csrf": csrf, "confirm": "0"*32, "ack": "yes"},
            allow_redirects=False)
        self.assertEqual(without_preview.status, 303)
        self.assertEqual(self.store.statistics()["turns"], 1)

    async def test_protected_row_and_mixed_selection_fail_closed(self):
        safe = self.add("Safe")
        protected = self.add("Protected", linked=True)
        pending = self.add("Pending", processed=False)
        headers = await self.login()
        csrf, _ = await self.csrf(headers)
        for ids in ([safe, protected], [safe, pending]):
            with self.subTest(ids=ids):
                response = await self.client.post(
                    "/maintenance/journal/select", headers=headers,
                    data=[("csrf", csrf)] +
                         [("journal_id", str(i)) for i in ids],
                    allow_redirects=False)
                self.assertEqual(response.status, 303)
                self.assertEqual(self.store.statistics()["turns"], 3)
        _, html = await self.csrf(headers)
        self.assertNotIn("Végső ellenőrzés", html)

    async def test_select_page_without_inline_javascript_and_protect_sources(self):
        first = self.add("Disposable first")
        second = self.add("Disposable second")
        protected = self.add("Referenced source", linked=True)
        headers = await self.login()
        csrf, html = await self.csrf(headers)
        self.assertNotIn("onclick=", html)
        self.assertIn('name="mode" value="page"', html)
        self.assertIn('name="visible_id" value="%d"' % first, html)
        self.assertIn('name="visible_id" value="%d"' % second, html)
        self.assertNotIn('name="visible_id" value="%d"' % protected, html)
        response = await self.client.post(
            "/maintenance/journal/select", headers=headers,
            data=[("csrf", csrf), ("mode", "page"),
                  ("visible_id", str(first)),
                  ("visible_id", str(second))], allow_redirects=False)
        self.assertEqual(response.status, 303)
        self.assertEqual(self.store.statistics()["turns"], 3)
        _, html = await self.csrf(headers)
        self.assertIn("2 kijelölt párbeszéd", html)
        self.assertIn("Disposable first", html)
        self.assertNotIn("Végleges törlés sikeres", html)

    async def test_filter_and_page(self):
        for i in range(45):
            self.add("Synthetic sequence %03d" % i)
        headers = await self.login()
        response = await self.client.get(
            "/maintenance/journal?search=sequence&page=1", headers=headers)
        self.assertEqual(response.status, 200)
        html = await response.text()
        self.assertIn("Találatok: 45", html)
        self.assertIn('action="./journal" method="get"', html)
        self.assertIn('href="./journal?search=sequence"', html)
        self.assertIn("Synthetic sequence 000", html)
        self.assertNotIn("Synthetic sequence 044", html)

if __name__ == "__main__":
    unittest.main()
