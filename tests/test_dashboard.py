"""Simple dashboard tests; no HA installation or API credentials needed."""
import sys, os, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nabu_recall"))
from store import Store
from dashboard import render

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
            page=render(store, {"version":"1.0.1"}, "turns")
            self.assertIn("v1.0.1 · HAOS ingress",page)
            self.assertNotIn("v0.2.0 · HAOS ingress",page)
            audit=render(store, {"version":"1.0.1"}, "audit")
            self.assertIn("Naplóellenőrzés",audit)
            self.assertIn("Hiányzó válasz",audit)
            self.assertIn("NINCS VÉGREHAJTÁS",audit)
            self.assertIn("Előzetes tisztítási besorolás",audit)
            self.assertIn("Feldolgozatlan",audit)
            self.assertNotIn("a <test>",audit)
            self.assertEqual(stats["turns"],store.statistics()["turns"])
            store.db.close()
