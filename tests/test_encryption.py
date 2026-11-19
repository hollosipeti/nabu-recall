"""Real SQLCipher migrations, key persistence, and failure-mode regression tests."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from encryption import encrypted_connect
from store import Store

HEADER = b"SQLite format 3\x00"

class EncryptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "recall.sqlite3"
    def tearDown(self):
        self.tmp.cleanup()
    def test_new_database_encrypted_and_persistent(self):
        s = Store(self.path)
        s.add_turn("Titkos mondat", "Titkos válasz", "session")
        s.apply([{"action":"add","fact":"A kedvenc szín zöld."}])
        s.db.close()
        contents = self.path.read_bytes()
        self.assertNotEqual(contents[:16], HEADER)
        self.assertNotIn(b"Titkos mondat", contents)
        self.assertNotIn(b"A kedvenc sz", contents)
        key = self.path.with_suffix(".key")
        self.assertEqual(key.stat().st_mode & 0o777, 0o600)
        s=Store(self.path)
        self.assertEqual(s.memory_list()[0]["fact"],"A kedvenc szín zöld.")
        self.assertEqual(s.recent_turns()[0]["user_text"],"Titkos mondat")
        s.db.close()
    def test_plaintext_migration_preserves_rows(self):
        legacy=sqlite3.connect(self.path)
        legacy.executescript("""
            CREATE TABLE turns(id INTEGER PRIMARY KEY,created INTEGER NOT NULL,
                conversation_id TEXT,user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL,processed INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE memories(id INTEGER PRIMARY KEY,created INTEGER NOT NULL,
                updated INTEGER NOT NULL,fact TEXT NOT NULL,
                source_turn INTEGER, UNIQUE(fact));
        """)
        legacy.execute("INSERT INTO turns VALUES(1,?,? ,?, ?,0)",
                       (1234,"abc","Régi napló","Válasz"))
        legacy.execute("INSERT INTO memories VALUES(1,?,?,?,?)",
                       (1234,1234,"Apa születési dátuma: 1973. október 23.",1))
        legacy.commit()
        legacy.close()
        self.assertEqual(self.path.read_bytes()[:16],HEADER)
        store=Store(self.path)
        self.assertEqual(store.memory_list()[0]["id"],1)
        self.assertEqual(store.memory_list()[0]["fact"],"Apa születési dátuma: 1973. október 23.")
        self.assertEqual(store.recent_turns()[0]["user_text"],"Régi napló")
        store.db.close()
        self.assertNotEqual(self.path.read_bytes()[:16],HEADER)
        with self.assertRaises(sqlite3.DatabaseError):
            plain=sqlite3.connect(self.path)
            try:
                plain.execute("SELECT * FROM memories").fetchall()
            finally:
                plain.close()
    def test_missing_key_does_not_reset_memories(self):
        s=Store(self.path)
        s.apply([{"action":"add","fact":"Megmarad"}])
        s.db.close()
        self.path.with_suffix(".key").unlink()
        with self.assertRaises(RuntimeError):
            Store(self.path)
        self.assertNotEqual(self.path.read_bytes()[:16],HEADER)
    def test_wrong_key_does_not_overwrite(self):
        s=Store(self.path)
        s.apply([{"action":"add","fact":"Megmarad"}])
        s.db.close()
        before=self.path.read_bytes()
        self.path.with_suffix(".key").write_text("0"*64+"\n")
        with self.assertRaises(Exception):
            Store(self.path)
        self.assertEqual(self.path.read_bytes(),before)
    def test_encrypted_operations_unchanged(self):
        s=Store(self.path)
        id=s.add_turn("Mentsd el","Rendben","a")
        s.apply([{"action":"add","fact":"Anna bevásárlólistája"}])
        memory=s.memory_list()[0]
        self.assertTrue(s.apply_confirmed({"action":"update","id":memory["id"],
                      "fact":"A bevásárlólistán zöldség és gyümölcs szerepel."}))
        self.assertEqual(s.memory_list()[0]["fact"],"A bevásárlólistán zöldség és gyümölcs szerepel.")
        self.assertTrue(s.apply_confirmed({"action":"delete","id":memory["id"]}))
        self.assertEqual(s.memory_list(),[])
        self.assertEqual(s.pending()[0]["id"],id)
        s.db.close()

    def test_legacy_wal_pending_transactions(self):
        """A live old DB may have committed entries only in its WAL file."""
        legacy=sqlite3.connect(self.path)
        legacy.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE turns(id INTEGER PRIMARY KEY,created INTEGER NOT NULL,
                conversation_id TEXT,user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL,processed INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE memories(id INTEGER PRIMARY KEY,created INTEGER NOT NULL,
                updated INTEGER NOT NULL,fact TEXT NOT NULL,
                source_turn INTEGER, UNIQUE(fact));
        """)
        legacy.execute("INSERT INTO turns VALUES(3,?,?,?,?,0)",
                       (2026,"sess","Uncheckpointed memory","Acknowledged"))
        legacy.execute("INSERT INTO memories VALUES(7,?,?,?,?)",
                       (2026,2026,"WAL-teszt tartós emlék",3))
        legacy.commit()
        # Checkpoint occurs while migration opens a second connection.
        legacy.close()
        s=Store(self.path)
        self.assertEqual(s.memory_list()[0]["id"],7)
        self.assertEqual(s.recent_turns()[0]["user_text"],"Uncheckpointed memory")
        s.db.close()

    def test_corrupted_legacy_stays_unmodified(self):
        self.path.write_bytes(HEADER + b"not-a-valid-sqlite-db")
        before=self.path.read_bytes()
        with self.assertRaises(Exception):
            Store(self.path)
        self.assertEqual(self.path.read_bytes(),before)
