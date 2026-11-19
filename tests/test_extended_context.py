"""Data-driven routing and memory isolation: no real personal data, no API key."""
import os, sys, unittest, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..","nabu_recall"))
from management import operation_kind, context_needed, previous_context, validate_change
from store import Store

CASES = [["Jegyezd meg, hogy a tesztállatom neve Maszat.","add"],["Mentsd el!","add"],["Mentsük el.","add"],["Tárold el ezt","add"],["Anya a feleségem.",null],["Enikő születési dátuma: 2006. június 28.",null],["Javítsd a bevásárlólistás emléket","update"],["Ezt az emléket ki kell javítani","update"],["Írd át","update"],["Módosítsuk","update"],["Töröld az emléket","delete"],["Felejtsd el a gyömbérteát","delete"],["Töröld minden emlékemet","blocked"],["Töröld mindet","blocked"],["Töröld az összes emlékemet","blocked"],["Töröld teljesen a memóriát","blocked"],["Kapcsold le a lámpát",null],["Anya neve Betti.",null],["Kik laknak a házban?",null],["Töröld az Anna nevű emléket","delete"],["Mentsd el az összes emléket","add"],["Írd át a tesztállat nevét","update"]]

class ContextRoutingTests(unittest.TestCase):
    def test_hungarian_variations(self):
        for phrase, kind in CASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(operation_kind(phrase), kind)

    def test_context_isolation_and_age(self):
        now=2_000_000_000
        turns=[
            dict(user_text="Anya a feleségem.",assistant_text="Téves, Anna",
                 conversation_id="session-a",created=now-20),
            dict(user_text="Idegen: 12",assistant_text="Igen",conversation_id="session-b",created=now-5)]
        self.assertEqual(previous_context(turns,"session-a",now),"Anya a feleségem.")
        self.assertEqual(previous_context(turns,"session-b",now),"Idegen: 12")
        self.assertIsNone(previous_context(turns,"session-c",now))
        self.assertIsNone(previous_context(turns,"",now))
        self.assertIsNone(previous_context(turns,"session-a",now+600))

    def test_never_use_assistant_as_fact(self):
        turns=[dict(user_text="",assistant_text="Apa 1973",conversation_id="a",created=20)]
        self.assertIsNone(previous_context(turns,"a",25))

    def test_elliptical_context_only(self):
        self.assertTrue(context_needed("Mentsd el!"))
        self.assertFalse(context_needed("Mentsd el! Anya a feleségem."))
        self.assertFalse(context_needed("Anya a feleségem."))

    def test_db_update_preserves_id_and_other_people(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Store(os.path.join(folder,"test.sqlite3"))
            db.apply([{"action":"add","fact":"Anna bevásárlólistáján zöldség és gyümölcs szerepel."},
                      {"action":"add","fact":"Apa születési dátuma: 1973. október 23."}])
            original=next(m for m in db.memory_list() if "bevásárlólistáján" in m["fact"])
            op={"action":"update","id":original["id"],"fact":"A bevásárlólistán zöldség és gyümölcs szerepel."}
            self.assertEqual(validate_change("update",[op],db.memory_list()),op)
            self.assertTrue(db.apply_confirmed(op))
            result=db.memory_list()
            self.assertEqual(len(result),2)
            self.assertEqual(next(m for m in result if m["id"]==original["id"])["fact"],op["fact"])
            self.assertTrue(any("Apa születési dátuma" in m["fact"] for m in result))
            db.db.close()

    def test_no_bulk_delete_through_validation(self):
        memories=[{"id":i} for i in range(20)]
        ops=[{"action":"delete","id":i} for i in range(20)]
        self.assertIsNone(validate_change("delete",ops,memories))
