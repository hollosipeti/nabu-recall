"""End-to-end read-only audit against a real encrypted SQLCipher fixture."""
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nabu_recall"))
from store import Store
from dashboard import render


class AuditFixtureTests(unittest.TestCase):
    def test_full_audit_never_changes_turns_memories_or_encryption_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recall.sqlite3"
            store = Store(path)
            try:
                linked = store.add_turn("user linked", "", "session")
                unlinked = store.add_turn("user unlinked", "  ", "session")
                pending = store.add_turn("user pending", "", "session")
                complete = store.add_turn("user complete", "assistant answer", "session")
                store.processed([linked, unlinked, complete])
                store.apply([{"action": "add", "fact": "Fact from incomplete source"}], linked)
                key_path = path.with_suffix(".key")
                key_before = hashlib.sha256(key_path.read_bytes()).hexdigest()
                rows_before = [
                    tuple(r) for r in store.db.execute(
                        "SELECT id, created, conversation_id, user_text, assistant_text, processed "
                        "FROM turns ORDER BY id"
                    )
                ]
                memories_before = [
                    tuple(r) for r in store.db.execute(
                        "SELECT id, created, updated, fact, source_turn "
                        "FROM memories ORDER BY id"
                    )
                ]
                counts_before = store.statistics()
                summary = store.journal_integrity_summary()
                preview = store.journal_cleanup_preview()
                page = render(store, {"version": "test"}, "audit")
                self.assertEqual(summary["missing"], 3)
                self.assertEqual(summary["referenced_turns"], 1)
                self.assertEqual(summary["referenced_memories"], 1)
                self.assertEqual(preview["pending"]["sample_ids"], [pending])
                self.assertEqual(preview["linked"]["sample_ids"], [linked])
                self.assertEqual(preview["unlinked"]["sample_ids"], [unlinked])
                self.assertEqual(
                    sum(x["count"] for x in preview.values()), summary["missing"]
                )
                self.assertIn("NINCS VÉGREHAJTÁS", page)
                for secret in ("user linked", "user unlinked", "user pending",
                               "user complete", "assistant answer",
                               "Fact from incomplete source"):
                    self.assertNotIn(secret, page)
                self.assertEqual(rows_before, [
                    tuple(r) for r in store.db.execute(
                        "SELECT id, created, conversation_id, user_text, assistant_text, processed "
                        "FROM turns ORDER BY id"
                    )
                ])
                self.assertEqual(memories_before, [
                    tuple(r) for r in store.db.execute(
                        "SELECT id, created, updated, fact, source_turn "
                        "FROM memories ORDER BY id"
                    )
                ])
                self.assertEqual(store.statistics(), counts_before)
                self.assertEqual(hashlib.sha256(key_path.read_bytes()).hexdigest(),
                                 key_before)
            finally:
                store.db.close()

    def test_database_is_still_encrypted_after_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recall.sqlite3"
            store = Store(path)
            store.add_turn("sensitive transcript", "", "conversation")
            store.journal_integrity_summary()
            store.journal_cleanup_preview()
            store.db.close()
            self.assertNotEqual(path.read_bytes()[:16], b"SQLite format 3\\x00")
            self.assertNotIn(b"sensitive transcript", path.read_bytes())
            again = Store(path)
            try:
                self.assertEqual(again.statistics()["turns"], 1)
            finally:
                again.db.close()
