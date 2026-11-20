"""HTTP bridge integration tests with fake AI. No network to OpenAI, no user data."""
import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from store import Store
import tempfile as _tmpmod
_GLOBAL_DB = _tmpmod.TemporaryDirectory()
os.environ['DB_PATH'] = os.path.join(_GLOBAL_DB.name, 'server-import.sqlite3')
import server

class FakeAI:
    def __init__(self, operations=None, error=None):
        self.operations=operations or []
        self.error=error
        self.calls=[]
    async def manage(self, utterance, kind, memories, recent_user_statement=None):
        self.calls.append((utterance,kind,recent_user_statement))
        if self.error:
            raise self.error
        return self.operations
    async def learn(self, turns, memories):
        self.calls.append(("learn",len(turns)))
        return self.operations

class HttpMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.previous=(server.store,server.ai,server.token)
        server.store=Store(os.path.join(self.temp.name,"test.sqlite3"))
        server.token="unit-test-token"
        server.ai=FakeAI()
        # Only test bridge endpoints, no ingress port and no worker.
        app=web.Application(middlewares=[server.authorization])
        app.router.add_post("/bridge/turn",server.log_turn)
        app.router.add_post("/bridge/manage",server.manage)
        self.client=TestClient(TestServer(app))
        await self.client.start_server()
    async def asyncTearDown(self):
        await self.client.close()
        server.store.db.close()
        server.store,server.ai,server.token=self.previous
        self.temp.cleanup()
    async def post(self,path,body,token=True):
        headers={"X-Recall-Token":"unit-test-token"} if token else {}
        response=await self.client.post("/bridge/"+path,json=body,headers=headers)
        return response.status, await response.json() if response.content_type=="application/json" else {}
    async def test_auth(self):
        status,_=await self.post("manage",{"utterance":"Töröld mindet"},False)
        self.assertEqual(status,401)
    async def test_insert_and_confirm(self):
        server.ai=FakeAI([{"action":"add","fact":"A tesztállatom neve Maszat."}])
        status,body=await self.post("manage",{"utterance":"Jegyezd meg, hogy a tesztállatom neve Maszat."})
        self.assertEqual(status,200)
        self.assertEqual(body["status"],"confirmed")
        self.assertEqual(server.store.memory_list()[0]["fact"],"A tesztállatom neve Maszat.")
    async def test_update_same_id_without_affecting_other_memories(self):
        server.store.apply([{"action":"add","fact":"Anna bevásárlólistáján zöldség és gyümölcs szerepel."},
                            {"action":"add","fact":"Apa születési dátuma 1973. október 23."}])
        original=next(m for m in server.store.memory_list() if "Anna" in m["fact"])
        server.ai=FakeAI([{"action":"update","id":original["id"],
                           "fact":"A bevásárlólistán zöldség és gyümölcs szerepel."}])
        _,body=await self.post("manage",{"utterance":"Javítsd az emléket, név nélkül maradjon a bevásárlólista."})
        self.assertEqual(body["status"],"confirmed")
        self.assertEqual(len(server.store.memory_list()),2)
        revised=next(m for m in server.store.memory_list() if m["id"]==original["id"])
        self.assertNotIn("Anna",revised["fact"])
    async def test_historical_memory_outside_latest_200_can_be_managed(self):
        server.store.apply([{"action": "add",
                            "fact": "Régi beállítás: műhelylámpa színe kék."}])
        oldest = server.store.memory_list()[0]
        for i in range(300):
            server.store.apply([{"action": "add",
                                "fact": "Független mesterséges naplóérték %d" % i}])
        self.assertFalse(any(x["id"] == oldest["id"]
                             for x in server.store.memory_list(200)))
        server.ai = FakeAI([{
            "action": "update", "id": oldest["id"],
            "fact": "Régi beállítás: műhelylámpa színe zöld."
        }])
        _, body = await self.post(
            "manage", {"utterance": "Javítsd a műhelylámpa színét zöldre"})
        self.assertEqual(body["status"], "confirmed")
        self.assertEqual(server.store.db.execute(
            "SELECT fact FROM memories WHERE id=?", (oldest["id"],)
        ).fetchone()[0], "Régi beállítás: műhelylámpa színe zöld.")

    async def test_unknown_id_not_confirmed(self):
        server.ai=FakeAI([{"action":"update","id":999,"fact":"Apa"}])
        _,body=await self.post("manage",{"utterance":"Javítsd az emléket"})
        self.assertEqual(body["status"],"not_found")
    async def test_bulk_delete_never_calls_ai(self):
        server.store.apply([{"action":"add","fact":"Faktum A"},{"action":"add","fact":"Faktum B"}])
        server.ai=FakeAI([{"action":"delete","id":1}])
        _,body=await self.post("manage",{"utterance":"Töröld minden emlékemet"})
        self.assertEqual(body["status"],"blocked")
        self.assertFalse(server.ai.calls)
        self.assertEqual(len(server.store.memory_list()),2)
    async def test_model_returns_two_deletes_blocked(self):
        server.store.apply([{"action":"add","fact":"Faktum A"},{"action":"add","fact":"Faktum B"}])
        server.ai=FakeAI([{"action":"delete","id":1},{"action":"delete","id":2}])
        _,body=await self.post("manage",{"utterance":"Töröld a Faktum A emléket"})
        self.assertEqual(body["status"],"not_found")
        self.assertEqual(len(server.store.memory_list()),2)
    async def test_model_error_is_not_success(self):
        server.ai=FakeAI(error=RuntimeError("synthetic"))
        _,body=await self.post("manage",{"utterance":"Jegyezd meg, hogy a tesztállatom neve Maszat"})
        self.assertEqual(body["status"],"error")
        self.assertEqual(server.store.memory_list(),[])
    async def test_elliptical_save_from_same_conversation(self):
        server.store.add_turn("Anya a feleségem.","Értem.","abc")
        server.ai=FakeAI([{"action":"add","fact":"Anya a felhasználó felesége."}])
        _,body=await self.post("manage",{"utterance":"Mentsd el!","conversation_id":"abc"})
        self.assertEqual(body["status"],"confirmed")
        self.assertEqual(server.ai.calls[-1][2],"Anya a feleségem.")
    async def test_elliptical_save_missing_context(self):
        server.store.add_turn("Anya a feleségem.","Értem.","someone-else")
        server.ai=FakeAI([{"action":"add","fact":"Anya a felhasználó felesége."}])
        _,body=await self.post("manage",{"utterance":"Mentsd el!","conversation_id":"abc"})
        self.assertEqual(body["status"],"not_found")
        self.assertFalse(server.ai.calls)
    async def test_no_false_success_on_duplicate(self):
        server.store.apply([{"action":"add","fact":"Maszat"}])
        server.ai=FakeAI([{"action":"add","fact":"Maszat"}])
        _,body=await self.post("manage",{"utterance":"Jegyezd meg, hogy a tesztállatom Maszat"})
        self.assertEqual(body["status"],"not_found")
    async def test_explicit_commands_not_relearned_on_log(self):
        _,body=await self.post("turn",{"user":"Mentsd el!","assistant":"Tényleg.","conversation_id":"abc"})
        self.assertTrue(body["ok"])
        self.assertFalse(server.store.pending())
