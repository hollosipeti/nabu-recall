"""Maintenance regression: SQLCipher archive, undo, stale approvals and AI trust boundaries."""
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from store import Store
from maintenance import (
    cleanup_preview, cleanup_commit, cleanup_restore, latest_cleanup,
    validate_proposal, memory_apply, memory_restore, recent_memory_undo,
    MaintenanceConflict, memory_apply_many, memory_restore_many,
)


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.dir.name) / "recall.sqlite3")

    def tearDown(self):
        self.store.db.close()
        self.dir.cleanup()

    def add(self, kind, text):
        i = self.store.add_turn(text, "answer" if kind == "complete" else "")
        if kind != "pending":
            self.store.processed([i])
        if kind == "linked":
            self.store.apply([{"action": "add", "fact": "Linked fact " + text}], i)
        return i

    def test_cleanup_211_restores_exact_rows_and_preserves_links(self):
        rng = random.Random(32)
        types = ["unlinked"] * 211 + ["linked"] * 27 + ["complete"] * 48
        rng.shuffle(types)
        linked_ids = []
        for index, category in enumerate(types):
            ident = self.add(category, "synthetic-%d" % index)
            if category == "linked":
                linked_ids.append(ident)
        original = [tuple(x) for x in self.store.db.execute(
            "SELECT * FROM turns ORDER BY id"
        )]
        memories = [tuple(x) for x in self.store.db.execute(
            "SELECT * FROM memories ORDER BY id"
        )]
        before = cleanup_preview(self.store)
        self.assertEqual(before["count"], 211)
        outcome = cleanup_commit(self.store, before["digest"], before["count"])
        self.assertEqual(outcome["count"], 211)
        self.assertEqual(self.store.statistics()["turns"], 75)
        self.assertEqual(self.store.statistics()["memories"], 27)
        self.assertEqual(cleanup_preview(self.store)["count"], 0)
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM journal_archive"
        ).fetchone()[0], 211)
        self.assertEqual(self.store.journal_integrity_summary()["orphan_sources"], 0)
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM turns WHERE id IN (%s)" %
            ",".join("?" * len(linked_ids)), linked_ids
        ).fetchone()[0], 27)
        restored = cleanup_restore(self.store, latest_cleanup(self.store)["history_id"])
        self.assertEqual(restored, 211)
        self.assertEqual(original, [tuple(x) for x in self.store.db.execute(
            "SELECT * FROM turns ORDER BY id"
        )])
        self.assertEqual(memories, [tuple(x) for x in self.store.db.execute(
            "SELECT * FROM memories ORDER BY id"
        )])
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM journal_archive"
        ).fetchone()[0], 0)

    def test_add_turn_never_reuses_archived_highest_id(self):
        a = self.add("complete", "keep")
        b = self.add("unlinked", "archive highest")
        self.assertGreater(b, a)
        preview = cleanup_preview(self.store)
        cleanup_commit(self.store, preview["digest"], preview["count"])
        new_id = self.store.add_turn("fresh", "response")
        self.assertGreater(new_id, b)
        history = latest_cleanup(self.store)
        self.assertEqual(cleanup_restore(self.store, history["history_id"]), 1)
        self.assertEqual(self.store.statistics()["turns"], 3)

    def test_rejects_stale_snapshot_and_pending(self):
        self.add("unlinked", "one")
        plan = cleanup_preview(self.store)
        self.add("unlinked", "two")
        with self.assertRaises(MaintenanceConflict):
            cleanup_commit(self.store, plan["digest"], plan["count"])
        self.assertEqual(self.store.statistics()["turns"], 2)
        self.add("pending", "wait")
        updated = cleanup_preview(self.store)
        self.assertEqual(updated["count"], 2)
        self.assertEqual(cleanup_commit(
            self.store, updated["digest"], updated["count"])["count"], 2)
        self.assertEqual(self.store.statistics()["turns"], 1)
        self.assertEqual(self.store.pending()[0]["user_text"], "wait")

    def test_rejects_source_link_added_since_preview(self):
        ident = self.add("unlinked", "will become protected")
        plan = cleanup_preview(self.store)
        self.store.apply([{"action": "add", "fact": "source protected"}], ident)
        with self.assertRaises(MaintenanceConflict):
            cleanup_commit(self.store, plan["digest"], plan["count"])
        self.assertEqual(self.store.statistics()["turns"], 1)

    def test_cleanup_restore_rejects_colliding_id(self):
        self.add("unlinked", "one")
        plan = cleanup_preview(self.store)
        cleanup_commit(self.store, plan["digest"], plan["count"])
        self.store.db.execute(
            "INSERT INTO turns(id,created,user_text,assistant_text,processed) "
            "VALUES(1,1,'new','answer',1)"
        )
        self.store.db.commit()
        with self.assertRaises(MaintenanceConflict):
            cleanup_restore(self.store, latest_cleanup(self.store)["history_id"])
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM journal_archive"
        ).fetchone()[0], 1)


    def _proposal_for(self, first, second, merged):
        return validate_proposal({
            "type": "duplicate", "keeper_id": first,
            "remove_ids": [second], "new_fact": merged,
            "reason": "Az egyező tények összevonhatók."
        }, self.store)

    def test_batch_commit_and_restore_are_atomic(self):
        for fact in ("Első tény egyik változata", "Első tény másik változata",
                     "Második tény egyik változata", "Második tény másik változata"):
            self.store.apply([{"action": "add", "fact": fact}])
        rows = [dict(r) for r in self.store.db.execute(
            "SELECT * FROM memories ORDER BY id")]
        a = self._proposal_for(rows[0]["id"], rows[1]["id"],
                               "Első tény összevont változata")
        b = self._proposal_for(rows[2]["id"], rows[3]["id"],
                               "Második tény összevont változata")
        history_ids = memory_apply_many(self.store, [a, b])
        self.assertEqual(len(history_ids), 2)
        self.assertEqual(self.store.statistics()["memories"], 2)
        self.assertEqual(memory_restore_many(self.store, history_ids), 4)
        self.assertEqual(rows, [dict(r) for r in self.store.db.execute(
            "SELECT * FROM memories ORDER BY id")])

    def test_conflicting_second_merge_rolls_back_all(self):
        for fact in ("Első tény egyik változata", "Első tény másik változata",
                     "Második tény egyik változata", "Második tény másik változata"):
            self.store.apply([{"action": "add", "fact": fact}])
        ids = [r["id"] for r in self.store.db.execute(
            "SELECT id FROM memories ORDER BY id")]
        a = self._proposal_for(ids[0], ids[1], "Közös végeredmény")
        b = self._proposal_for(ids[2], ids[3], "Közös végeredmény")
        before = [tuple(r) for r in self.store.db.execute(
            "SELECT * FROM memories ORDER BY id")]
        with self.assertRaises(Exception):
            memory_apply_many(self.store, [a, b])
        self.assertEqual(before, [tuple(r) for r in self.store.db.execute(
            "SELECT * FROM memories ORDER BY id")])
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM maintenance_history WHERE kind='memory'"
        ).fetchone()[0], 0)

    def test_overlapping_proposals_are_rejected(self):
        for fact in ("Tény egyik változata", "Tény másik változata",
                     "Tény harmadik változata"):
            self.store.apply([{"action": "add", "fact": fact}])
        ids = [r["id"] for r in self.store.db.execute(
            "SELECT id FROM memories ORDER BY id")]
        a = self._proposal_for(ids[0], ids[1], "Első összevont tény")
        b = self._proposal_for(ids[1], ids[2], "Második összevont tény")
        with self.assertRaises(MaintenanceConflict):
            memory_apply_many(self.store, [a, b])
        self.assertEqual(self.store.statistics()["memories"], 3)

    def test_memory_proposal_apply_and_undo(self):
        self.store.apply([{"action": "add", "fact": "A kedvenc ital gyömbértea."}])
        self.store.apply([{"action": "add", "fact": "Az illető szereti a gyömbérteát."}])
        records = self.store.memory_list()
        ids = [r["id"] for r in records]
        original = [tuple(r) for r in self.store.db.execute(
            "SELECT * FROM memories ORDER BY id"
        )]
        item = validate_proposal({
            "type": "overlap", "keeper_id": ids[0],
            "remove_ids": [ids[1]],
            "new_fact": "Az illető kedvenc itala a gyömbértea.",
            "reason": "Két összefüggő, egyértelmű tény."
        }, self.store)
        self.assertIsNotNone(item)
        history_id = memory_apply(self.store, item)
        self.assertEqual(self.store.statistics()["memories"], 1)
        self.assertEqual(recent_memory_undo(self.store)["id"], history_id)
        self.assertEqual(memory_restore(self.store, history_id), 2)
        self.assertEqual(original, [tuple(r) for r in self.store.db.execute(
            "SELECT * FROM memories ORDER BY id"
        )])

    def test_merge_when_new_fact_matches_removed_fact(self):
        self.store.apply([{"action": "add", "fact": "Uncertain preliminary preference"}])
        self.store.apply([{"action": "add", "fact": "Confirmed preferred tea is ginger"}])
        ids = [r["id"] for r in self.store.memory_list()]
        remove_text = self.store.db.execute(
            "SELECT fact FROM memories WHERE id=?", (ids[1],)
        ).fetchone()[0]
        proposal = validate_proposal({
            "type": "overlap", "keeper_id": ids[0],
            "remove_ids": [ids[1]], "new_fact": remove_text,
            "reason": "Replace less precise fact by confirmed fact"
        }, self.store)
        self.assertIsNotNone(proposal)
        history = memory_apply(self.store, proposal)
        self.assertEqual(self.store.statistics()["memories"], 1)
        self.assertEqual(memory_restore(self.store, history), 2)

    def test_memory_stale_proposal_rejected_without_mutation(self):
        self.store.apply([{"action": "add", "fact": "One original memory"}])
        self.store.apply([{"action": "add", "fact": "Another original memory"}])
        ids = [r["id"] for r in self.store.memory_list()]
        proposal = validate_proposal({
            "type": "duplicate", "keeper_id": ids[0], "remove_ids": [ids[1]],
            "new_fact": "Consolidated fact", "reason": "Same concrete fact"
        }, self.store)
        self.store.apply_confirmed({
            "action": "update", "id": ids[1], "fact": "Updated while preview active"
        })
        with self.assertRaises(MaintenanceConflict):
            memory_apply(self.store, proposal)
        self.assertEqual(self.store.statistics()["memories"], 2)

    def test_invalid_optimizer_output_is_rejected(self):
        self.store.apply([{"action": "add", "fact": "First"}])
        self.store.apply([{"action": "add", "fact": "Second"}])
        ids = [r["id"] for r in self.store.memory_list()]
        bad = [
            {"type": "duplicate", "keeper_id": ids[0], "remove_ids": [ids[0]],
             "new_fact": "bad", "reason": "duplicate keeper id"},
            {"type": "duplicate", "keeper_id": "1", "remove_ids": [ids[1]],
             "new_fact": "bad", "reason": "non-integer keeper"},
            {"type": "conflict", "keeper_id": ids[0], "remove_ids": [99999],
             "new_fact": "bad", "reason": "unknown referenced ID"},
            {"type": "add", "keeper_id": ids[0], "remove_ids": [ids[1]],
             "new_fact": "bad", "reason": "unknown action type"},
        ]
        self.assertTrue(all(validate_proposal(x, self.store) is None for x in bad))

    def test_archived_transcripts_still_expire_at_45_days(self):
        now = 2_000_000_000
        old = self.store.add_turn("old archive", "", created=now - 46 * 86400)
        self.store.processed([old])
        plan = cleanup_preview(self.store)
        cleanup_commit(self.store, plan["digest"], plan["count"])
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM journal_archive"
        ).fetchone()[0], 1)
        self.store.purge(now)
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM journal_archive"
        ).fetchone()[0], 0)

    def test_encrypted_history_not_plaintext(self):
        i = self.add("unlinked", "synthetic private sentence")
        plan = cleanup_preview(self.store)
        cleanup_commit(self.store, plan["digest"], plan["count"])
        path = Path(self.dir.name) / "recall.sqlite3"
        self.store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.assertNotIn(b"synthetic private sentence", path.read_bytes())
        self.assertNotEqual(path.read_bytes()[:16], b"SQLite format 3\x00")

if __name__ == "__main__":
    unittest.main()
