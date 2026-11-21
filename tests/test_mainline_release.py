"""Release 1.1.2 keeps the existing HAOS app identity and stored data location."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class MainlineReleaseTests(unittest.TestCase):
    def test_same_stable_addon_slug(self):
        config=(ROOT/"nabu_recall"/"config.yaml").read_text(encoding="utf-8")
        self.assertIn("slug: nabu_recall\n",config)
        self.assertIn('version: "1.1.2"',config)
        self.assertIn("stage: stable",config)
        self.assertNotIn("slug: nabu_recall_beta",config)

    def test_same_database_and_integration(self):
        script=(ROOT/"nabu_recall"/"run.sh").read_text(encoding="utf-8")
        self.assertIn("DB_PATH=/data/recall.sqlite3",script)
        manifest=(ROOT/"custom_components"/"nabu_recall"/"manifest.json").read_text(encoding="utf-8")
        self.assertIn('"version":"1.0.4"',manifest)

    def test_server_version(self):
        server=(ROOT/"nabu_recall"/"server.py").read_text(encoding="utf-8")
        self.assertIn('1.1.2',server)
