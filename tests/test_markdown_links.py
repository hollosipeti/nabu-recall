"""Prevent broken relative Markdown links in active release docs."""
from pathlib import Path
from urllib.parse import unquote
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class MarkdownLinksTests(unittest.TestCase):
    def test_local_links_point_to_existing_files(self):
        for page in ROOT.rglob("*.md"):
            if ".git" in page.parts:
                continue
            content = page.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
                if target.startswith(("http://","https://","mailto:","#")):
                    continue
                target_path = unquote(target.split("#",1)[0])
                if not target_path or target_path.startswith("/"):
                    continue
                destination = page.parent / target_path
                with self.subTest(page=str(page.relative_to(ROOT)), link=target):
                    self.assertTrue(destination.exists(),f"Broken Markdown link: {page}: {target}")

    def test_no_legacy_example_or_manual_prompt_copy_paths(self):
        self.assertFalse((ROOT/"examples").exists())
        guide = (ROOT/"NABU_RECALL_PROMPT.md").read_text(encoding="utf-8")
        self.assertNotIn("## Archivált memóriautasítás-minta",guide)
        self.assertIn("repo_instructions.py",guide)

if __name__ == "__main__":
    unittest.main()
