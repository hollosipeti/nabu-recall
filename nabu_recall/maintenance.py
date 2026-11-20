"""Explicit, reversible maintenance on the existing encrypted SQLCipher database.

Never called by background workers, voice commands or the bridge.
All destructive operations have compare-and-swap preconditions and in-DB undo records.
"""
import hashlib
import json
import secrets
import time

CANDIDATE_SQL = (
    "SELECT t.id, t.created, t.conversation_id, t.user_text, "
    "t.assistant_text, t.processed FROM turns t "
    "WHERE t.processed=1 AND TRIM(t.assistant_text)='' "
    "AND NOT EXISTS (SELECT 1 FROM memories m WHERE m.source_turn=t.id) "
    "ORDER BY t.id"
)


class MaintenanceConflict(ValueError):
    pass


def _digest(data):
    return hashlib.sha256(json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def init_schema(store):
    store.db.executescript("""
    CREATE TABLE IF NOT EXISTS journal_archive (
        id INTEGER PRIMARY KEY, batch_id TEXT NOT NULL,
        created INTEGER NOT NULL, conversation_id TEXT,
        user_text TEXT NOT NULL, assistant_text TEXT NOT NULL,
        processed INTEGER NOT NULL, archived_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS journal_archive_batch ON journal_archive(batch_id);
    CREATE TABLE IF NOT EXISTS maintenance_history (
        id INTEGER PRIMARY KEY, kind TEXT NOT NULL,
        created INTEGER NOT NULL, payload TEXT NOT NULL,
        undone INTEGER NOT NULL DEFAULT 0
    );
    """)
    store.db.commit()


def cleanup_preview(store):
    rows = [dict(x) for x in store.db.execute(CANDIDATE_SQL)]
    return {"count": len(rows), "digest": _digest(rows),
            "sample_ids": [r["id"] for r in rows[-12:]]}


def cleanup_commit(store, expected_digest, expected_count):
    """Atomically archive and remove only unchanged, processed, unlinked blank replies."""
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise MaintenanceConflict("Invalid snapshot")
    if type(expected_count) is not int or expected_count <= 0:
        raise MaintenanceConflict("Empty or invalid cleanup")
    with store.db:
        rows = [dict(x) for x in store.db.execute(CANDIDATE_SQL)]
        if len(rows) != expected_count or _digest(rows) != expected_digest:
            raise MaintenanceConflict("Journal changed; regenerate preview")
        batch = secrets.token_hex(16)
        stamp = int(time.time())
        store.db.executemany(
            "INSERT INTO journal_archive "
            "(id,batch_id,created,conversation_id,user_text,assistant_text,"
            "processed,archived_at) VALUES (?,?,?,?,?,?,?,?)",
            [(r["id"], batch, r["created"], r["conversation_id"],
              r["user_text"], r["assistant_text"], r["processed"], stamp)
             for r in rows]
        )
        ids = [r["id"] for r in rows]
        store.db.executemany(
            "DELETE FROM turns WHERE id=? AND processed=1 "
            "AND TRIM(assistant_text)='' AND NOT EXISTS "
            "(SELECT 1 FROM memories m WHERE m.source_turn=turns.id)",
            [(id_,) for id_ in ids]
        )
        remaining = store.db.execute(
            "SELECT COUNT(*) FROM turns WHERE id IN (%s)" %
            ",".join("?" * len(ids)), ids
        ).fetchone()[0]
        if remaining:
            raise MaintenanceConflict("Protected record; transaction rolled back")
        store.db.execute(
            "INSERT INTO maintenance_history(kind,created,payload) VALUES(?,?,?)",
            ("cleanup", stamp, json.dumps({"batch": batch, "count": len(rows)}))
        )
    return {"batch": batch, "count": len(rows)}


def latest_cleanup(store):
    item = store.db.execute(
        "SELECT id,created,payload FROM maintenance_history "
        "WHERE kind='cleanup' AND undone=0 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not item:
        return None
    payload = json.loads(item["payload"])
    found = store.db.execute(
        "SELECT COUNT(*) FROM journal_archive WHERE batch_id=?",
        (payload["batch"],)
    ).fetchone()[0]
    if found != payload["count"]:
        return None
    return {"history_id": item["id"], "batch": payload["batch"],
            "count": payload["count"], "created": item["created"]}


def cleanup_restore(store, history_id):
    if type(history_id) is not int:
        raise MaintenanceConflict("Invalid history identifier")
    with store.db:
        history = store.db.execute(
            "SELECT kind,payload,undone,created FROM maintenance_history WHERE id=?",
            (history_id,)
        ).fetchone()
        if not history or history["kind"] != "cleanup" or history["undone"]:
            raise MaintenanceConflict("Cleanup history unavailable")
        info = json.loads(history["payload"])
        rows = [dict(r) for r in store.db.execute(
            "SELECT id,created,conversation_id,user_text,assistant_text,processed "
            "FROM journal_archive WHERE batch_id=? ORDER BY id",
            (info["batch"],)
        )]
        if not rows or len(rows) != info["count"]:
            raise MaintenanceConflict("Archive incomplete")
        for row in rows:
            if store.db.execute("SELECT 1 FROM turns WHERE id=?",
                                (row["id"],)).fetchone():
                raise MaintenanceConflict("Journal ID collision")
        store.db.executemany(
            "INSERT INTO turns(id,created,conversation_id,user_text,assistant_text,processed) "
            "VALUES(?,?,?,?,?,?)",
            [(r["id"], r["created"], r["conversation_id"], r["user_text"],
              r["assistant_text"], r["processed"]) for r in rows]
        )
        store.db.execute("DELETE FROM journal_archive WHERE batch_id=?",
                         (info["batch"],))
        store.db.execute("UPDATE maintenance_history SET undone=1 WHERE id=?",
                         (history_id,))
    return len(rows)


def memory_digest(store, ids):
    if not isinstance(ids, (tuple, list)) or not ids or len(ids) > 20:
        raise MaintenanceConflict("Invalid memory references")
    if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise MaintenanceConflict("Invalid memory IDs")
    rows = [dict(r) for r in store.db.execute(
        "SELECT id,created,updated,fact,source_turn FROM memories "
        "WHERE id IN (%s) ORDER BY id" % ",".join("?" * len(ids)),
        ids
    )]
    if len(rows) != len(ids):
        raise MaintenanceConflict("Memory was removed")
    return _digest(rows)


def validate_proposal(raw, store):
    """Model output is untrusted: require explicit keeper, removable IDs, and reasons."""
    if not isinstance(raw, dict) or raw.get("type") not in (
        "duplicate", "overlap", "conflict"
    ):
        return None
    keep = raw.get("keeper_id")
    remove = raw.get("remove_ids")
    fact = raw.get("new_fact")
    reason = raw.get("reason")
    if (type(keep) is not int or keep <= 0 or not isinstance(remove, list)
            or not 1 <= len(remove) <= 8 or any(type(x) is not int for x in remove)
            or keep in remove or len(set(remove)) != len(remove)
            or not isinstance(fact, str) or not 3 <= len(fact.strip()) <= 1500
            or not isinstance(reason, str) or not 5 <= len(reason.strip()) <= 500):
        return None
    ids = [keep] + remove
    try:
        digest = memory_digest(store, ids)
    except MaintenanceConflict:
        return None
    return {"type": raw["type"], "keeper_id": keep, "remove_ids": remove,
            "new_fact": fact.strip(), "reason": reason.strip(),
            "digest": digest}


def memory_apply(store, proposal):
    """Approve ONE individually reviewed proposal, atomically preserving undo."""
    keep = proposal["keeper_id"]
    remove = proposal["remove_ids"]
    ids = [keep] + remove
    with store.db:
        if memory_digest(store, ids) != proposal["digest"]:
            raise MaintenanceConflict("Memories changed; regenerate proposals")
        rows = [dict(r) for r in store.db.execute(
            "SELECT id,created,updated,fact,source_turn FROM memories "
            "WHERE id IN (%s) ORDER BY id" % ",".join("?" * len(ids)), ids
        )]
        if store.db.execute(
            "SELECT 1 FROM memories WHERE fact=? AND id NOT IN (%s)" %
            ",".join("?" * len(ids)),
            [proposal["new_fact"]] + ids
        ).fetchone():
            raise MaintenanceConflict("Resulting fact already exists")
        stamp = int(time.time())
        # Remove duplicates first, then update keeper; the new fact may
        # equal one of the removed facts (UNIQUE(fact) constraint).
        store.db.executemany("DELETE FROM memories WHERE id=?",
                             [(id_,) for id_ in remove])
        store.db.execute(
            "UPDATE memories SET fact=?, updated=? WHERE id=?",
            (proposal["new_fact"], stamp, keep)
        )
        payload = {"old": rows, "keep": keep,
                   "after": proposal["new_fact"], "removed": remove}
        return store.db.execute(
            "INSERT INTO maintenance_history(kind,created,payload) VALUES(?,?,?)",
            ("memory", stamp, json.dumps(payload, ensure_ascii=False))
        ).lastrowid


def memory_restore(store, history_id):
    if type(history_id) is not int:
        raise MaintenanceConflict("Invalid history identifier")
    with store.db:
        history = store.db.execute(
            "SELECT kind,payload,undone,created FROM maintenance_history WHERE id=?",
            (history_id,)
        ).fetchone()
        if not history or history["kind"] != "memory" or history["undone"]:
            raise MaintenanceConflict("Undo not available")
        if history["created"] < int(time.time()) - 7 * 86400:
            raise MaintenanceConflict("Undo window expired")
        data = json.loads(history["payload"])
        keeper = store.db.execute(
            "SELECT fact FROM memories WHERE id=?", (data["keep"],)
        ).fetchone()
        if not keeper or keeper["fact"] != data["after"]:
            raise MaintenanceConflict("Memory has changed since approval")
        for r in data["old"]:
            if r["id"] != data["keep"] and store.db.execute(
                "SELECT 1 FROM memories WHERE id=?", (r["id"],)
            ).fetchone():
                raise MaintenanceConflict("Memory ID collision")
            if store.db.execute(
                "SELECT 1 FROM memories WHERE fact=? AND id<>?",
                (r["fact"], data["keep"])
            ).fetchone():
                raise MaintenanceConflict("Memory fact conflict")
        store.db.execute(
            "DELETE FROM memories WHERE id=?", (data["keep"],)
        )
        store.db.executemany(
            "INSERT INTO memories(id,created,updated,fact,source_turn) "
            "VALUES(?,?,?,?,?)",
            [(r["id"], r["created"], r["updated"], r["fact"], r["source_turn"])
             for r in data["old"]]
        )
        store.db.execute(
            "UPDATE maintenance_history SET undone=1 WHERE id=?", (history_id,)
        )
    return len(data["old"])


def recent_memory_undo(store):
    row = store.db.execute(
        "SELECT id,created FROM maintenance_history "
        "WHERE kind='memory' AND undone=0 AND created>=? ORDER BY id DESC LIMIT 1"
        , (int(time.time()) - 7 * 86400,)
    ).fetchone()
    return dict(row) if row else None
