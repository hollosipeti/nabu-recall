"""SQLite journal and durable memories. Verbatim transcript retention: 45 days."""
import sqlcipher3 as sqlite3
from encryption import encrypted_connect
import time
from pathlib import Path

RETENTION_DAYS = 45

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = encrypted_connect(path)
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
        from maintenance import init_schema
        init_schema(self)

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
            deleted = self.db.execute("DELETE FROM turns WHERE created < ?", (cutoff,)).rowcount
            # Archived transcripts have exactly the same 45-day retention.
            self.db.execute("DELETE FROM journal_archive WHERE created < ?", (cutoff,))
            # Reversible old memory edits expire after seven days, so deleted facts
            # cannot be retained indefinitely in maintenance history.
            self.db.execute(
                "DELETE FROM maintenance_history WHERE kind='memory' AND created < ?",
                ((int(time.time()) if now is None else int(now)) - 7 * 86400,)
            )
            return deleted

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

    def apply_confirmed(self, op):
        """Apply one checked operation and confirm a real database change."""
        action = op["action"]
        with self.db:
            if action == "delete":
                cursor = self.db.execute("DELETE FROM memories WHERE id=?", (op["id"],))
                return cursor.rowcount == 1
            if action == "update":
                cursor = self.db.execute(
                    "UPDATE memories SET fact=?,updated=? WHERE id=?",
                    (op["fact"].strip(), int(time.time()), op["id"]))
                return cursor.rowcount == 1
            if action == "add":
                cursor = self.db.execute(
                    "INSERT OR IGNORE INTO memories(created,updated,fact) VALUES(?,?,?)",
                    (int(time.time()), int(time.time()), op["fact"].strip()))
                return cursor.rowcount == 1
        return False

    def remove_memory(self, id):
        with self.db:
            return self.db.execute("DELETE FROM memories WHERE id=?", (id,)).rowcount

    def statistics(self):
        row = self.db.execute(
            "SELECT COUNT(*) AS turns, COALESCE(SUM(CASE WHEN processed=0 THEN 1 ELSE 0 END),0) AS pending, "
            "MIN(created) AS oldest, MAX(created) AS newest FROM turns"
        ).fetchone()
        memories = self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        return {"turns": row["turns"], "pending": row["pending"],
                "memories": memories, "oldest": row["oldest"], "newest": row["newest"],
                "retention_days": RETENTION_DAYS}

    def journal_integrity_summary(self):
        """Read-only audit; no user or assistant text in the report."""
        row = self.db.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(CASE WHEN TRIM(assistant_text) = '' THEN 1 ELSE 0 END),0) AS missing, "
            "COALESCE(SUM(CASE WHEN TRIM(assistant_text) = '' AND processed = 1 THEN 1 ELSE 0 END),0) AS missing_processed, "
            "COALESCE(SUM(CASE WHEN TRIM(assistant_text) = '' AND processed = 0 THEN 1 ELSE 0 END),0) AS missing_pending, "
            "COALESCE(SUM(CASE WHEN TRIM(assistant_text) <> '' THEN 1 ELSE 0 END),0) AS complete "
            "FROM turns"
        ).fetchone()
        sample_ids = [int(item[0]) for item in self.db.execute(
            "SELECT id FROM turns WHERE TRIM(assistant_text) = '' "
            "ORDER BY id DESC LIMIT 20"
        )]
        # Provenance statistics are read-only; never interpret as deletion approval.
        refs = self.db.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM memories m WHERE m.source_turn IN "
            "(SELECT t.id FROM turns t WHERE TRIM(t.assistant_text) = '')) AS referenced_memories, "
            "(SELECT COUNT(*) FROM turns t WHERE TRIM(t.assistant_text) = '' "
            "AND EXISTS (SELECT 1 FROM memories m WHERE m.source_turn=t.id)) AS referenced_turns, "
            "(SELECT COUNT(*) FROM turns t WHERE TRIM(t.assistant_text) = '' AND t.processed=1 "
            "AND NOT EXISTS (SELECT 1 FROM memories m WHERE m.source_turn=t.id)) AS unreferenced_processed, "
            "(SELECT COUNT(*) FROM memories m WHERE m.source_turn IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM turns t WHERE t.id=m.source_turn)) AS orphan_sources"
        ).fetchone()
        referenced_ids = [int(x[0]) for x in self.db.execute(
            "SELECT t.id FROM turns t WHERE TRIM(t.assistant_text) = '' "
            "AND EXISTS (SELECT 1 FROM memories m WHERE m.source_turn=t.id) "
            "ORDER BY t.id DESC LIMIT 20"
        )]
        return {
            "total": int(row["total"]),
            "missing": int(row["missing"]),
            "missing_processed": int(row["missing_processed"]),
            "missing_pending": int(row["missing_pending"]),
            "complete": int(row["complete"]),
            "sample_missing_ids": sample_ids,
            "referenced_memories": int(refs["referenced_memories"]),
            "referenced_turns": int(refs["referenced_turns"]),
            "unreferenced_processed": int(refs["unreferenced_processed"]),
            "orphan_sources": int(refs["orphan_sources"]),
            "sample_referenced_ids": referenced_ids,
        }

    def journal_cleanup_preview(self):
        """Read-only classification of incomplete journal rows, no deletion approval.

        Classes are disjoint and total exactly the count of blank assistant replies.
        A source_turn link is provenance, not an authorization to delete anything.
        """
        cases = (
            ("pending", "t.processed = 0"),
            ("linked", "t.processed = 1 AND EXISTS "
             "(SELECT 1 FROM memories m WHERE m.source_turn = t.id)"),
            ("unlinked", "t.processed = 1 AND NOT EXISTS "
             "(SELECT 1 FROM memories m WHERE m.source_turn = t.id)"),
        )
        result = {}
        for name, condition in cases:
            where = "TRIM(t.assistant_text) = '' AND " + condition
            result[name] = {
                "count": int(self.db.execute(
                    "SELECT COUNT(*) FROM turns t WHERE " + where
                ).fetchone()[0]),
                "sample_ids": [int(r[0]) for r in self.db.execute(
                    "SELECT t.id FROM turns t WHERE " + where +
                    " ORDER BY t.id DESC LIMIT 10"
                )],
            }
        return result

    def recent_turns(self, limit=35):
        return [dict(r) for r in self.db.execute(
            "SELECT id,created,conversation_id,user_text,assistant_text,processed "
            "FROM turns ORDER BY id DESC LIMIT ?", (min(int(limit), 100),))]
