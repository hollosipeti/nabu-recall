"""Single-instance staging and rollback installer safety checks."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class InstallerStagingTests(unittest.TestCase):
    def test_sh_syntax(self):
        subprocess.run(["sh", "-n", str(ROOT / "install_integration.sh")],
                       check=True)

    def test_only_explicit_staging_and_stable_branches(self):
        script = (ROOT / "install_integration.sh").read_text(encoding="utf-8")
        self.assertIn('main|stable-2026-11-24-before-v2)', script)
        self.assertIn('BRANCH="${1:-main}"', script)
        self.assertIn('refs/heads/${BRANCH}.zip', script)
        self.assertIn('nabu-recall-${BRANCH}/custom_components/nabu_recall', script)
        self.assertIn('BACKUP_ROOT="/config/nabu_recall_backups"', script)
        self.assertNotIn('addon_config', script)
        self.assertNotIn('nabu_recall/run.sh', script)

    def test_staging_version_distinct_from_stable(self):
        staging = (ROOT / "custom_components/nabu_recall/manifest.json").read_text()
        self.assertIn('"version":"2.0.2"', staging)
        self.assertIn('"domain":"nabu_recall"', staging)

if __name__ == "__main__":
    unittest.main()
