"""SQLite journal and durable memories. Verbatim transcript retention: 45 days."""
import sqlite3
import time
from pathlib import Path

RETENTION_DAYS = 45

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS turns(
            id INTEGER PRIMARY KEY, created INTEGER NOT NULL,
            conversation_id TEXT, user_text TEXT NOT NULL,
            assistant_text TEXT NOT NULL, processed INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS turns_created ON turns(created);
        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY, created INTEGER NOT NULL,
            updated INTEGER NOT NULL, fact TEXT NOT NULL,
            source_turn INTEGER, UNIQUE(fact));
        """)
        self.db.commit()

    def add_turn(self, user, assistant, conversation_id="", created=None):
        with self.db:
            return self.db.execute(
                "INSERT INTO turns(created,conversation_id,user_text,assistant_text) VALUES(?,?,?,?)",
                (int(time.time()) if created is None else int(created),
                 conversation_id, user, assistant)).lastrowid

    def pending(self, limit=20):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM turns WHERE processed=0 ORDER BY id LIMIT ?", (limit,))]

    def processed(self, ids):
        if ids:
            with self.db:
                self.db.executemany("UPDATE turns SET processed=1 WHERE id=?", [(i,) for i in ids])

    def purge(self, now=None):
        cutoff = (int(time.time()) if now is None else int(now)) - RETENTION_DAYS * 86400
        with self.db:
            return self.db.execute("DELETE FROM turns WHERE created < ?", (cutoff,)).rowcount

    def candidates(self, terms, recent=12, max_matches=45):
        cutoff = int(time.time()) - RETENTION_DAYS * 86400
        rows = [dict(r) for r in self.db.execute(
            "SELECT id,created,user_text,assistant_text FROM turns WHERE created>=? ORDER BY id DESC LIMIT ?",
            (cutoff, recent))]
        seen = {r["id"] for r in rows}
        for term in terms[:12]:
            if not isinstance(term, str) or not 2 <= len(term) <= 80:
                continue
            term = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            sql = ("SELECT id,created,user_text,assistant_text FROM turns WHERE created>=? "
                   "AND (user_text LIKE ? ESCAPE '\\' OR assistant_text LIKE ? ESCAPE '\\') "
                   "ORDER BY id DESC LIMIT ?")
            for r in self.db.execute(sql, (cutoff, "%" + term + "%", "%" + term + "%", max_matches)):
                if r["id"] not in seen:
                    rows.append(dict(r))
                    seen.add(r["id"])
                    if len(seen) >= recent + max_matches:
                        return rows
        return rows

    def memory_list(self, limit=200):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM memories ORDER BY updated DESC LIMIT ?", (limit,))]

    def apply(self, operations, source_turn=None):
        now = int(time.time())
        with self.db:
            for op in operations:
                if not isinstance(op, dict):
                    continue
                action = op.get("action")
                fact = str(op.get("fact", "")).strip()[:1500]
                if action == "add" and fact:
                    self.db.execute(
                        "INSERT OR IGNORE INTO memories(created,updated,fact,source_turn) VALUES(?,?,?,?)",
                        (now, now, fact, source_turn))
                elif action == "update" and fact and type(op.get("id")) is int:
                    self.db.execute(
                        "UPDATE memories SET fact=?,updated=?,source_turn=? WHERE id=?",
                        (fact, now, source_turn, op["id"]))
                elif action == "delete" and type(op.get("id")) is int:
                    self.db.execute("DELETE FROM memories WHERE id=?", (op["id"],))

    def remove_memory(self, id):
        with self.db:
            return self.db.execute("DELETE FROM memories WHERE id=?", (id,)).rowcount
