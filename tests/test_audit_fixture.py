"""End-to-end read-only audit against a real encrypted SQLCipher fixture."""
import hashlib
import random
import shutil
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

    def test_random_320_turn_database_and_cold_restore(self):
        """Synthetic fixture: 230 missing replies, provenance and cold backup."""
        rng = random.Random(20261120)
        classes = (["pending"] * 40 + ["linked"] * 60 +
                   ["unlinked"] * 130 + ["complete"] * 90)
        rng.shuffle(classes)
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "live" / "recall.sqlite3"
            primary.parent.mkdir()
            store = Store(primary)
            try:
                expected = {"pending": [], "linked": [], "unlinked": []}
                for index, kind in enumerate(classes):
                    user_text = "SYNTHETIC-%06d-%06d" % (
                        rng.randrange(1000000), index
                    )
                    assistant = ("OK-%06d" % rng.randrange(1000000)
                                 if kind == "complete" else
                                 (" " if index % 3 == 0 else ""))
                    turn_id = store.add_turn(
                        user_text, assistant,
                        "session-%d" % rng.randrange(7)
                    )
                    if kind != "pending":
                        store.processed([turn_id])
                    if kind == "linked":
                        store.apply([{"action": "add",
                                     "fact": "Synthetic fact %06d" % turn_id}],
                                    turn_id)
                    if kind != "complete":
                        expected[kind].append(turn_id)

                report = store.journal_integrity_summary()
                groups = store.journal_cleanup_preview()
                page = render(store, {"version": "test"}, "audit")
                self.assertEqual(report["total"], 320)
                self.assertEqual(report["missing"], 230)
                self.assertEqual(report["complete"], 90)
                self.assertEqual(report["missing_pending"], 40)
                self.assertEqual(report["referenced_turns"], 60)
                self.assertEqual(report["referenced_memories"], 60)
                self.assertEqual(report["unreferenced_processed"], 130)
                self.assertEqual(report["orphan_sources"], 0)
                for kind in expected:
                    self.assertEqual(groups[kind]["count"], len(expected[kind]))
                    self.assertEqual(groups[kind]["sample_ids"],
                                     sorted(expected[kind], reverse=True)[:10])
                self.assertEqual(sum(g["count"] for g in groups.values()), 230)
                self.assertIn("NINCS VÉGREHAJTÁS", page)
                self.assertNotIn("SYNTHETIC-", page)
                fingerprint = hashlib.sha256(
                    repr([(x["id"], x["user_text"], x["assistant_text"],
                           x["processed"]) for x in store.recent_turns(100)]
                         ).encode("utf-8")
                ).hexdigest()
            finally:
                # Cold backup simulation: close sole writer and flush WAL.
                store.db.close()

            archive = Path(tmp) / "backup"
            archive.mkdir()
            restored = archive / "recall.sqlite3"
            shutil.copy2(primary, restored)
            shutil.copy2(primary.with_suffix(".key"),
                         restored.with_suffix(".key"))
            self.assertNotEqual(restored.read_bytes()[:16],
                                b"SQLite format 3\\x00")
            cloned = Store(restored)
            try:
                self.assertEqual(cloned.statistics()["turns"], 320)
                self.assertEqual(cloned.statistics()["memories"], 60)
                self.assertEqual(cloned.journal_cleanup_preview(), groups)
                self.assertEqual(cloned.journal_integrity_summary(), report)
                self.assertEqual(hashlib.sha256(
                    repr([(x["id"], x["user_text"], x["assistant_text"],
                           x["processed"]) for x in cloned.recent_turns(100)]
                         ).encode("utf-8")
                ).hexdigest(), fingerprint)
            finally:
                cloned.db.close()

    def test_database_is_still_encrypted_after_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recall.sqlite3"
            store = Store(path)
            store.add_turn("sensitive transcript", "", "conversation")
            store.journal_integrity_summary()
            store.journal_cleanup_preview()
            store.db.close()
            self.assertNotEqual(path.read_bytes()[:16], b"SQLite format 3\x00")
            self.assertNotIn(b"sensitive transcript", path.read_bytes())
            again = Store(path)
            try:
                self.assertEqual(again.statistics()["turns"], 1)
            finally:
                again.db.close()
