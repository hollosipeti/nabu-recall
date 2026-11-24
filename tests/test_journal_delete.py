"""Manual, irreversible SQLCipher journal deletion invariants."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from store import Store
from journal_delete import (
    JournalDeletionConflict, deletion_preview, deletion_commit, journal_page, MAX_SELECT,
)

class ManualJournalDeleteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "recall.sqlite3"))

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def turn(self, prompt, reply="answer", processed=True, created=None):
        ident = self.store.add_turn(prompt, reply, created=created)
        if processed:
            self.store.processed([ident])
        return ident

    def test_success_is_permanent_not_archive_and_does_not_touch_durable(self):
        first = self.turn("Synthetic test A", "First response")
        second = self.turn("Synthetic test B", "Second response")
        keeper = self.turn("Actual important statement")
        self.store.apply([{"action": "add", "fact": "A tartós emlék megmarad."}], keeper)
        archive_before = self.store.db.execute(
            "SELECT COUNT(*) FROM journal_archive").fetchone()[0]
        snapshot = deletion_preview(self.store, [first, second])
        self.assertEqual(self.store.statistics()["turns"], 3)
        self.assertEqual(deletion_commit(self.store, [first, second], snapshot["digest"]), 2)
        self.assertEqual(self.store.statistics()["turns"], 1)
        self.assertEqual(self.store.statistics()["memories"], 1)
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM journal_archive").fetchone()[0], archive_before)
        self.assertEqual([r["id"] for r in self.store.recent_turns()], [keeper])
        self.assertNotIn("Synthetic test", str(self.store.candidates(["Synthetic test"])))

    def test_pending_and_source_linked_are_protected_even_in_mixed_batch(self):
        deletable = self.turn("Test removable")
        pending = self.turn("Test pending", processed=False)
        linked = self.turn("Test linked")
        self.store.apply([{"action": "add", "fact": "Protected memory."}], linked)
        for group in ([deletable, pending], [deletable, linked]):
            with self.subTest(group=group), self.assertRaises(JournalDeletionConflict):
                deletion_preview(self.store, group)
        self.assertEqual(self.store.statistics()["turns"], 3)
        self.assertEqual(self.store.statistics()["memories"], 1)

    def test_race_guards_use_digest_and_transaction(self):
        first = self.turn("Original question")
        second = self.turn("Second question")
        snap = deletion_preview(self.store, [first, second])
        self.store.db.execute("UPDATE turns SET assistant_text='changed' WHERE id=?", (second,))
        self.store.db.commit()
        with self.assertRaises(JournalDeletionConflict):
            deletion_commit(self.store, [first, second], snap["digest"])
        self.assertEqual(self.store.statistics()["turns"], 2)
        snap = deletion_preview(self.store, [first, second])
        self.store.apply([{"action": "add", "fact": "Changed link"}], second)
        with self.assertRaises(JournalDeletionConflict):
            deletion_commit(self.store, [first, second], snap["digest"])
        self.assertEqual(self.store.statistics()["turns"], 2)

    def test_bad_ids_are_refused(self):
        valid = self.turn("Synthetic")
        for bad in ([], [valid, valid], [valid, True], [0], [3.5],
                    list(range(1, MAX_SELECT + 2))):
            with self.subTest(bad=bad), self.assertRaises(JournalDeletionConflict):
                deletion_preview(self.store, bad)
        self.assertEqual(self.store.statistics()["turns"], 1)

    def test_filters_use_local_calendar_day_not_utc_day(self):
        local = datetime(2026, 11, 24, 0, 15,
                         tzinfo=ZoneInfo("Europe/Budapest"))
        in_day = self.turn("Selected amber test", created=int(local.timestamp()))
        other = self.turn("Selected amber test", created=int(local.timestamp())-3600)
        data = journal_page(self.store, "amber", "2026-11-24")
        self.assertEqual([r["id"] for r in data["rows"]], [in_day])
        self.assertEqual(journal_page(self.store, "amber", "2026-11-23")["rows"][0]["id"], other)

    def test_pagination_over_426_records(self):
        for i in range(426):
            self.turn(f"Test transcript {i:04d}")
        first = journal_page(self.store)
        self.assertEqual(first["total"], 426)
        self.assertEqual(len(first["rows"]), 40)
        self.assertEqual(first["rows"][0]["user_text"], "Test transcript 0425")
        last = journal_page(self.store, page=10)
        self.assertEqual(len(last["rows"]), 26)

if __name__ == "__main__":
    unittest.main()
