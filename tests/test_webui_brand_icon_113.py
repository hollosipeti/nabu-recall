"""Regression: Ingress header uses the existing brand PNG, not an emoji."""
import base64
import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HeaderBrandTests(unittest.TestCase):
    def test_existing_brand_icon_is_embedded_without_changes(self):
        from sys import path
        path.insert(0, str(ROOT / "nabu_recall"))
        import dashboard
        icon = (ROOT / "custom_components/nabu_recall/brand/icon.png").read_bytes()
        embedded = dashboard.BRAND_ICON_DATA_URI
        self.assertTrue(embedded.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(embedded.split(",", 1)[1]), icon)
        self.assertEqual(icon[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", icon[16:24])
        self.assertEqual((width, height), (128, 128))

    def test_page_renders_img_instead_of_emoji(self):
        from sys import path
        path.insert(0, str(ROOT / "nabu_recall"))
        import dashboard
        page = dashboard._page("CONTENT", "1.1.3")
        self.assertIn("<img class='brain' src='data:image/png;base64,", page)
        self.assertIn("Nabu Recall — állapot", page)
        self.assertNotIn("🧠", page)
        self.assertIn("CONTENT", page)

    def test_security_policy_allows_only_inline_images(self):
        source = (ROOT / "nabu_recall/dashboard.py").read_text()
        self.assertIn("img-src data:;", source)
        self.assertIn("default-src 'none';", source)


if __name__ == "__main__":
    unittest.main()
