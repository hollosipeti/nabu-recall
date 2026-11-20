"""Documentation/version contracts: no external credentials or live HA calls."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ReleaseDocsTests(unittest.TestCase):
    def test_current_manuals_and_history(self):
        docs=["README.md","TELEPITES_HU.md","MANUAL_EN.md",
              "nabu_recall/DOCS.md","HISTORY.md","examples/README.md",
              "examples/google_calendar_create_event.yaml",
              "AI utasítások. ki ne töröld"]
        for filename in docs:
            with self.subTest(filename=filename):
                self.assertTrue((ROOT/filename).exists())
                self.assertGreater((ROOT/filename).stat().st_size, 100)
        self.assertIn("SQLCipher",(ROOT/"TELEPITES_HU.md").read_text())
        self.assertIn("SQLCipher",(ROOT/"MANUAL_EN.md").read_text())
        self.assertIn("45",(ROOT/"nabu_recall/DOCS.md").read_text())
        self.assertIn("10 perc",(ROOT/"nabu_recall/DOCS.md").read_text())
        self.assertIn("10-minute",(ROOT/"MANUAL_EN.md").read_text())

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
        self.assertEqual(manifest["version"],"1.0.3")
        self.assertIn('version: "1.0.2"',config)
        changelog=(ROOT/"nabu_recall/CHANGELOG.md").read_text()
        # Only maintained releases in this file; the archive has older records.
        versions=re.findall(r"^##\s+(\d+\.\d+\.\d+)",changelog,re.M)
        self.assertEqual(versions,["1.0.2","1.0.1"])
