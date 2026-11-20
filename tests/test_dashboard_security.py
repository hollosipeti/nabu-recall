"""Ingress dashboard independent-password tests; no changes to SQLite content."""
import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"nabu_recall"))
from dashboard import create_dashboard, render, storage_metrics, _signed_session, _valid_session, SESSION_AGE
from store import Store

class DashboardAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.folder.name, "db.sqlite3"))
        self.store.add_turn("private transcript", "private response")
        self.store.apply([{"action":"add", "fact":"confidential memory"}])
        self.state = {"version":"1.0.0"}
        self.clients=[]

    async def asyncTearDown(self):
        for client in self.clients:
            await client.close()
        self.store.db.close()
        self.folder.cleanup()

    async def client_for(self, password):
        app=create_dashboard(self.store,self.state,password)
        client=TestClient(TestServer(app), cookie_jar=None)
        await client.start_server()
        self.clients.append(client)
        return client

    async def test_missing_password_fails_closed(self):
        client=await self.client_for("")
        response=await client.get("/")
        page=await response.text()
        self.assertIn("zárolva",page)
        self.assertNotIn("confidential memory",page)
        self.assertNotIn("private transcript",page)
        response=await client.post("/login",data={"password":"x"})
        self.assertEqual(response.status,403)

    async def test_login_and_protected_tabs(self):
        client=await self.client_for("long test password 123")
        page=await (await client.get("/?tab=memories")).text()
        self.assertNotIn("confidential memory",page)
        bad=await client.post("/login",data={"password":"wrong"},allow_redirects=False)
        self.assertEqual(bad.status,401)
        ok=await client.post("/login",data={"password":"long test password 123"},allow_redirects=False)
        self.assertEqual(ok.status,303)
        cookie=ok.cookies["recall_ui"].value
        for tab, secret in [("memories","confidential memory"),("turns","private transcript"),("storage","Memória és tárhely")]:
            response=await client.get("/?tab="+tab, headers={"Cookie":"recall_ui="+cookie})
            self.assertEqual(response.status,200)
            self.assertIn(secret,await response.text())
        logout=await client.post("/logout",headers={"Cookie":"recall_ui="+cookie},allow_redirects=False)
        self.assertEqual(logout.status,303)

    async def test_tampered_cookie_rejected(self):
        client=await self.client_for("long test password 123")
        response=await client.get("/",headers={"Cookie":"recall_ui=12345.abcdef"})
        self.assertNotIn("confidential memory",await response.text())

    async def test_no_sensitive_state_mutation(self):
        before=self.store.statistics()
        page=render(self.store,self.state,"storage")
        self.assertIn("Memória és tárhely",page)
        self.assertIn("Szabad tárhely",page)
        self.assertIn("Adatbázis + WAL/SHM",page)
        self.assertEqual(before,self.store.statistics())
        self.assertGreater(storage_metrics(self.store)["database"],0)

    def test_expiry_and_signature(self):
        key=b"test secret"
        token=_signed_session(key,100)
        self.assertTrue(_valid_session(token,key,101))
        self.assertEqual(SESSION_AGE, 600)
        self.assertTrue(_valid_session(token,key,699))
        self.assertFalse(_valid_session(token,key,700))
        self.assertFalse(_valid_session(token,b"different key",101))
        self.assertFalse(_valid_session(token,key, 100 + SESSION_AGE))

