"""Simple dashboard tests; no HA installation or API credentials needed."""
import sys, os, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nabu_recall"))
from store import Store

class DashboardStorageTests(unittest.TestCase):
    def test_statistics_and_original_text(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(os.path.join(d, "db.sqlite3"))
            store.add_turn("a <test>", "válasz")
            stats = store.statistics()
            self.assertEqual(stats["turns"], 1)
            self.assertEqual(stats["pending"], 1)
            self.assertEqual(stats["retention_days"], 45)
            self.assertEqual(store.recent_turns()[0]["user_text"], "a <test>")
            store.processed([1])
            self.assertEqual(store.statistics()["pending"], 0)
            store.db.close()
