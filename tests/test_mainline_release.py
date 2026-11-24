"""Release 2.0.0 keeps the existing HAOS app identity and stored data location."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class MainlineReleaseTests(unittest.TestCase):
    def test_same_stable_addon_slug(self):
        config=(ROOT/"nabu_recall"/"config.yaml").read_text(encoding="utf-8")
        self.assertIn("slug: nabu_recall\n",config)
        self.assertIn('version: "2.0.0"',config)
        self.assertIn("stage: stable",config)
        self.assertNotIn("slug: nabu_recall_beta",config)

    def test_same_database_and_integration(self):
        script=(ROOT/"nabu_recall"/"run.sh").read_text(encoding="utf-8")
        self.assertIn("DB_PATH=/data/recall.sqlite3",script)
        manifest=(ROOT/"custom_components"/"nabu_recall"/"manifest.json").read_text(encoding="utf-8")
        self.assertIn('"version":"2.0.0"',manifest)

    def test_server_version(self):
        server=(ROOT/"nabu_recall"/"server.py").read_text(encoding="utf-8")
        self.assertIn('2.0.0',server)

    def test_container_includes_every_local_server_import(self):
        """Catch imports that pass host tests but crash the packaged add-on."""
        import ast
        addon = ROOT / "nabu_recall"
        source = (addon / "server.py").read_text(encoding="utf-8")
        dockerfile = (addon / "Dockerfile").read_text(encoding="utf-8")
        copied = set()
        for line in dockerfile.splitlines():
            if line.startswith("COPY ") and line.rstrip().endswith(" /app/"):
                copied.update(line.split()[1:-1])
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                local_file = addon / (node.module + ".py")
                if local_file.is_file():
                    with self.subTest(module=node.module):
                        self.assertIn(local_file.name, copied)
        self.assertIn("structured_context.py", copied)
