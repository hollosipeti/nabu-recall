"""SQLite journal and durable memories. Verbatim transcript retention: 45 days."""
import sqlcipher3 as sqlite3
from encryption import encrypted_connect
import time
import re
from pathlib import Path

RETENTION_DAYS = 45

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = encrypted_connect(path)
        self.db.row_factory = sqlite3.Row
        # SQLite LIKE does not case-fold Hungarian accented letters itself.
        self.db.create_function("unicode_fold", 1,
                                lambda value: value.casefold() if isinstance(value, str) else "",
                                deterministic=True)
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
            timestamp = int(time.time()) if created is None else int(created)
            # SQLite INTEGER PRIMARY KEY may reuse the last deleted ID.
            # Preserve exact-ID restoration of archived journal rows.
            highest_archive = self.db.execute(
                "SELECT MAX(id) FROM journal_archive"
            ).fetchone()[0]
            if highest_archive is not None:
                highest_active = self.db.execute(
                    "SELECT MAX(id) FROM turns"
                ).fetchone()[0] or 0
                next_id = max(highest_active, highest_archive) + 1
                return self.db.execute(
                    "INSERT INTO turns(id,created,conversation_id,user_text,assistant_text)"
                    " VALUES(?,?,?,?,?)",
                    (next_id, timestamp, conversation_id, user, assistant)
                ).lastrowid
            return self.db.execute(
                "INSERT INTO turns(created,conversation_id,user_text,assistant_text)"
                " VALUES(?,?,?,?)",
                (timestamp, conversation_id, user, assistant)).lastrowid

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
            "SELECT * FROM memories ORDER BY updated DESC, id DESC LIMIT ?", (limit,))]

    def memory_page(self, after_id=0, limit=200):
        """Stable keyset paging over every durable fact, not the latest 200."""
        if type(after_id) is not int or after_id < 0:
            raise ValueError("Invalid memory cursor")
        limit = min(max(int(limit), 1), 200)
        return [dict(r) for r in self.db.execute(
            "SELECT id, created, updated, fact, source_turn FROM memories "
            "WHERE id > ? ORDER BY id LIMIT ?", (after_id, limit)
        )]

    @staticmethod
    def memory_query_terms(text):
        """Extract useful Unicode tokens from natural-language user requests."""
        if not isinstance(text, str):
            return []
        stopwords = {
            "hogy", "mikor", "milyen", "miért", "miert", "van", "volt",
            "lesz", "egy", "ezt", "azt", "nekem", "meg", "kell",
            "tudod", "tudsz", "kérlek", "kerlek", "szeretném",
            "szia", "mondd", "mond", "kérdés", "kerdes", "jegyezd",
            "emlékszel", "emlekszel", "hozzá", "hozza",
        }
        words = re.findall(r"[^\W_]{3,}", text.casefold(), flags=re.UNICODE)
        return list(dict.fromkeys(w for w in words if w not in stopwords))[:12]

    def memory_search(self, terms, limit=160):
        """Rank matches across the FULL memory table; bounded output for AI.

        LIKE is deliberately used rather than relying on optional SQLCipher FTS5
        compile flags. Escaping treats all query text as data. No newest-first
        window is applied before matching.
        """
        if not isinstance(terms, (list, tuple)):
            return []
        clean = []
        for term in terms[:12]:
            if not isinstance(term, str):
                continue
            term = term.strip()
            if not 2 <= len(term) <= 80 or term in clean:
                continue
            clean.append(term)
        if not clean:
            return []
        limit = min(max(int(limit), 1), 200)
        # A single OR query includes matching old memories regardless of updated
        # time; score with all terms, then deterministic updated/id tie-breaks.
        conditions = [
            ("unicode_fold(fact)" if any(ord(ch) > 127 for ch in term)
             else "fact") + " LIKE ? ESCAPE '\\'" for term in clean
        ]
        patterns = ["%" + term.casefold().replace("\\", "\\\\")
                    .replace("%", "\\%").replace("_", "\\_") + "%"
                    for term in clean]
        rows = [dict(r) for r in self.db.execute(
            "SELECT id, created, updated, fact, source_turn FROM memories "
            "WHERE " + " OR ".join(conditions), patterns
        )]
        folded = [s.casefold() for s in clean]
        rows.sort(key=lambda r: (
            -sum(1 for s in folded if s in r["fact"].casefold()),
            -r["updated"], -r["id"]
        ))
        return rows[:limit]

    def memory_duplicate_page(self, after_id=0, max_memories=120):
        """Find exact or reordered-token duplicates across ALL durable memories.

        This conservative lexical prefilter is not semantic equivalence and does
        not authorize deletion. Keyset cursor follows the smallest group ID.
        """
        if type(after_id) is not int or after_id < 0:
            raise ValueError("Invalid cursor")
        max_memories = min(max(int(max_memories), 2), 160)
        excluded = {"a", "az", "egy", "és", "es", "van", "volt"}
        groups = {}
        for r in self.db.execute(
                "SELECT id,fact FROM memories ORDER BY id"):
            tokens = re.findall(r"[^\W_]+", r["fact"].casefold(),
                                flags=re.UNICODE)
            key = tuple(sorted(t for t in tokens if t not in excluded))
            if len(key) < 2:
                continue
            group = groups.setdefault(key, [])
            if len(group) < 8:
                group.append(int(r["id"]))
        distinct = sorted((g for g in groups.values()
                           if len(g) >= 2 and g[0] > after_id),
                          key=lambda g: g[0])
        selected = []
        capacity = 0
        last_group_start = after_id
        consumed_groups = 0
        for group in distinct:
            if capacity + len(group) > max_memories:
                break
            selected.extend(group)
            capacity += len(group)
            consumed_groups += 1
            last_group_start = group[0]
        rows = []
        if selected:
            values = ",".join("?" * len(selected))
            rows = [dict(r) for r in self.db.execute(
                "SELECT id,created,updated,fact,source_turn FROM memories "
                "WHERE id IN (%s) ORDER BY id" % values, selected
            )]
        return {"memories": rows, "groups": consumed_groups,
                "cursor": last_group_start,
                "more": len(distinct) > consumed_groups}

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
