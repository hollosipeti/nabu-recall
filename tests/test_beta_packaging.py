"""Beta packaging contract: never install over the stable Nabu Recall app."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BetaPackagingTests(unittest.TestCase):
    def test_isolated_addon_identity_and_version(self):
        config = (ROOT / "nabu_recall" / "config.yaml").read_text(encoding="utf-8")
        self.assertRegex(config, r'(?m)^name: Nabu Recall \\(Beta\\)$'.replace('\\\\','\\'))
        self.assertIn('version: "1.1.0b1"', config)
        self.assertIn("slug: nabu_recall_beta", config)
        self.assertIn("stage: experimental", config)
        self.assertIn("ingress: true", config)

    def test_bridge_reports_beta_version(self):
        server = (ROOT / "nabu_recall" / "server.py").read_text(encoding="utf-8")
        self.assertIn("1.1.0b1", server)
        self.assertNotIn("1.0.6", server)

    def test_stable_integration_untouched(self):
        manifest = (ROOT / "custom_components" / "nabu_recall" / "manifest.json").read_text(encoding="utf-8")
        self.assertIn('"version":"1.0.4"', manifest)

    def test_install_and_rollback_guide_present(self):
        guide = (ROOT / "BETA_TELEPITES_HU.md").read_text(encoding="utf-8")
        self.assertIn("#beta-1.1.0b1", guide)
        self.assertIn("Visszaállás", guide)
        self.assertIn("recall.key", guide)


if __name__ == "__main__":
    unittest.main()
