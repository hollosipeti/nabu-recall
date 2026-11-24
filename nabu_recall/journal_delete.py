"""Strictly manual, irreversible deletion of selected conversation turns.

Unlike maintenance.cleanup_commit this never writes transcripts to an archive.
Only the authenticated Ingress UI may call these functions. No bridge/voice API.
"""
import hashlib
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MAX_SELECT = 40
PAGE_SIZE = 40
TZ = ZoneInfo("Europe/Budapest")


class JournalDeletionConflict(ValueError):
    pass


def _ids(ids):
    if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_SELECT:
        raise JournalDeletionConflict("Select 1–40 journal rows")
    if any(type(n) is not int or n <= 0 for n in ids) or len(set(ids)) != len(ids):
        raise JournalDeletionConflict("Invalid or repeated journal IDs")
    return sorted(ids)


def _selected(store, ids):
    args = ",".join("?" for _ in ids)
    return [dict(row) for row in store.db.execute(
        "SELECT t.id,t.created,t.conversation_id,t.user_text,t.assistant_text,"
        "t.processed,EXISTS(SELECT 1 FROM memories m WHERE m.source_turn=t.id) AS linked "
        f"FROM turns t WHERE t.id IN ({args}) ORDER BY t.id", ids
    )]


def _digest(rows):
    return hashlib.sha256(json.dumps(
        rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def deletion_preview(store, ids):
    """Read-only, all-or-nothing eligibility and content snapshot."""
    ids = _ids(ids)
    rows = _selected(store, ids)
    if len(rows) != len(ids):
        raise JournalDeletionConflict("A selected conversation is missing")
    if any(not row["processed"] or row["linked"] for row in rows):
        raise JournalDeletionConflict("Pending or durable-memory source is protected")
    return {"count": len(rows), "ids": ids, "digest": _digest(rows),
            "rows": rows}


def deletion_commit(store, ids, expected_digest):
    """Delete exactly selected, unchanged and unlinked rows in one SQL transaction."""
    ids = _ids(ids)
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise JournalDeletionConflict("Invalid confirmation")
    # Overwrite freed SQLite cells; reclaim the WAL after commit so erased
    # conversation bodies are not left in a still-active journal segment.
    store.db.execute("PRAGMA secure_delete=ON")
    store.db.execute("BEGIN IMMEDIATE")
    try:
        current = deletion_preview(store, ids)
        if current["digest"] != expected_digest:
            raise JournalDeletionConflict("Journal changed since confirmation")
        placeholders = ",".join("?" for _ in ids)
        count = store.db.execute(
            f"DELETE FROM turns WHERE id IN ({placeholders})", ids
        ).rowcount
        if count != len(ids):
            raise JournalDeletionConflict("Deletion count changed")
        store.db.commit()
        store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return count
    except BaseException:
        store.db.rollback()
        raise


def journal_page(store, text="", day="", page=0):
    """User-directed search only; never infer which rows are test data."""
    if not isinstance(text, str) or len(text) > 120:
        raise ValueError("Invalid search")
    if not isinstance(day, str) or len(day) > 10:
        raise ValueError("Invalid date")
    if type(page) is not int or not 0 <= page <= 100000:
        raise ValueError("Invalid page")
    conditions = []
    args = []
    if text.strip():
        escaped = (text.strip().replace("\\", "\\\\")
                   .replace("%", "\\%").replace("_", "\\_"))
        conditions.append("(t.user_text LIKE ? ESCAPE '\\' OR "
                          "t.assistant_text LIKE ? ESCAPE '\\')")
        args += ["%" + escaped + "%"] * 2
    if day:
        try:
            selected_day = date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError("Invalid date") from exc
        start = int(datetime(selected_day.year, selected_day.month,
                             selected_day.day, tzinfo=TZ).timestamp())
        next_day = selected_day + timedelta(days=1)
        end = int(datetime(next_day.year, next_day.month,
                           next_day.day, tzinfo=TZ).timestamp())
        conditions.append("t.created >= ? AND t.created < ?")
        args += [start, end]
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    total = store.db.execute("SELECT COUNT(*) FROM turns t" + where, args).fetchone()[0]
    rows = [dict(row) for row in store.db.execute(
        "SELECT t.id,t.created,t.user_text,t.assistant_text,t.processed,"
        "EXISTS(SELECT 1 FROM memories m WHERE m.source_turn=t.id) AS linked "
        "FROM turns t" + where + " ORDER BY t.id DESC LIMIT ? OFFSET ?",
        args + [PAGE_SIZE, page * PAGE_SIZE]
    )]
    return {"rows": rows, "total": total, "page": page,
            "size": PAGE_SIZE, "search": text, "day": day}
