"""Documentation/version contracts: no external credentials or live HA calls."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ReleaseDocsTests(unittest.TestCase):

    def test_examples_do_not_modify_memory_or_delete_events(self):
        example=(ROOT/"examples/google_calendar_create_event.yaml").read_text()
        self.assertIn("calendar.create_event",example)
        self.assertIn("calendar.esemenyek",example)
        self.assertIn("default(30, true)",example)
        self.assertIn("h: \"{{ ora | default(-1) | int(-1) }}\"",example)
        self.assertNotIn("todo.",example)
        self.assertNotIn("calendar.delete_event",example)

    def test_current_app_and_integration_release_numbers(self):
        import json
        manifest=json.loads((ROOT/"custom_components/nabu_recall/manifest.json").read_text())
        config=(ROOT/"nabu_recall/config.yaml").read_text()
        self.assertEqual(manifest["version"],"1.0.11")
        self.assertIn('version: "1.1.9"',config)
        changelog=(ROOT/"nabu_recall/CHANGELOG.md").read_text()
        # Only maintained releases in this file; the archive has older records.
        versions=re.findall(r"^##\s+(\d+\.\d+\.\d+)",changelog,re.M)
        self.assertEqual(versions,["1.1.9","1.1.8","1.1.7","1.1.6","1.1.5","1.1.4","1.1.3","1.1.2","1.1.1","1.1.0","1.0.6","1.0.5","1.0.4","1.0.3","1.0.4","1.0.3"])

    def test_cleanup_requires_backup_and_no_delete_endpoint(self):
        guide=(ROOT/"docs/SAFE_CLEANUP_HU.md").read_text()
        for required in ("recall.sqlite3", "recall.key", "WAL",
                         "visszaállítási", "SELECT", "source_turn"):
            with self.subTest(required=required):
                self.assertIn(required, guide)
        dashboard=(ROOT/"nabu_recall/dashboard.py").read_text()
        self.assertIn('tab == "audit"',dashboard)
        self.assertIn("journal_cleanup_preview()",dashboard)
        self.assertNotIn("journal_cleanup_execute(",dashboard)
