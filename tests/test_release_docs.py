"""Release documentation, cleanup and source-of-truth contracts."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ReleaseDocsTests(unittest.TestCase):
    def test_no_legacy_manual_calendar_installation_files(self):
        self.assertFalse((ROOT/"examples").exists())
        self.assertFalse((ROOT/"tests/test_calendar_script.py").exists())
        self.assertFalse((ROOT/"tests/test_calendar_weekend.py").exists())
        llm = (ROOT/"custom_components/nabu_recall/llm.py").read_text()
        self.assertIn("nabu_recall__calendar_query", llm)
        self.assertIn("nabu_recall__calendar_create", llm)
        self.assertNotIn("calendar.delete_event", llm)

    def test_v2_single_version_and_release_notes(self):
        manifest=json.loads((ROOT/"custom_components/nabu_recall/manifest.json").read_text())
        config=(ROOT/"nabu_recall/config.yaml").read_text()
        server=(ROOT/"nabu_recall/server.py").read_text()
        self.assertEqual(manifest["version"],"2.0.6")
        self.assertIn('version: "2.0.6"', config)
        self.assertIn("'version': '2.0.6'",server)
        notes=(ROOT/"nabu_recall/CHANGELOG.md").read_text()
        self.assertEqual(re.findall(r"^## (\d+\.\d+\.\d+)", notes, re.M),["2.0.6","2.0.5","2.0.4","2.0.3","2.0.2","2.0.1","2.0.0"])

    def test_prompt_map_links_exact_live_sources(self):
        instructions = (ROOT/"NABU_RECALL_PROMPT.md").read_text()
        for source in ("custom_components/nabu_recall/repo_instructions.py",
                       "custom_components/nabu_recall/conversation.py",
                       "custom_components/nabu_recall/llm.py",
                       "nabu_recall/ai.py"):
            self.assertIn(source,instructions)
            self.assertTrue((ROOT/source).is_file())
        self.assertNotIn("## Archivált",instructions)
        self.assertIn("Instructions",instructions)
        self.assertIn("NABU_RULES",instructions)

    def test_cleanup_requires_backup_and_no_delete_endpoint(self):
        guide=(ROOT/"docs/SAFE_CLEANUP_HU.md").read_text()
        for required in ("recall.sqlite3","recall.key","WAL",
                         "visszaállítási","SELECT","source_turn"):
            with self.subTest(required=required):
                self.assertIn(required,guide)
        dashboard=(ROOT/"nabu_recall/dashboard.py").read_text()
        self.assertIn('tab == "audit"',dashboard)
        self.assertIn("journal_cleanup_preview()",dashboard)
        self.assertNotIn("journal_cleanup_execute(",dashboard)

if __name__ == "__main__":
    unittest.main()
