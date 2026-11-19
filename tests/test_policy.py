"""Deletion safety tests. Never mutate a persistent user database."""
import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nabu_recall"))
from policy import filter_memory_operations

class SafetyTests(unittest.TestCase):
    def test_single_explicit_delete(self):
        ops = [{"action":"delete","id":7}]
        self.assertEqual(filter_memory_operations(ops, ["Töröld a régi tesztital-emlékemet."]), ops)

    def test_bulk_delete_rejected(self):
        ops = [{"action":"delete","id":1},{"action":"delete","id":2}]
        self.assertEqual(filter_memory_operations(ops, ["Törölj minden emléket!"]), [])

    def test_bulk_even_one_id_rejected(self):
        self.assertEqual(filter_memory_operations(
            [{"action":"delete","id":1}], ["Felejts el mindent"]), [])

    def test_no_explicit_delete_rejected(self):
        self.assertEqual(filter_memory_operations(
            [{"action":"delete","id":3}], ["Mennyi az idő?"]), [])

    def test_ai_cannot_delete_from_assistant_text(self):
        self.assertEqual(filter_memory_operations(
            [{"action":"delete","id":3}], ["Köszi"]), [])

    def test_update_kept_but_bulk_delete_dropped(self):
        self.assertEqual(filter_memory_operations(
            [{"action":"delete","id":3},{"action":"update","id":4,"fact":"új"}],
            ["Töröld az összes emlékemet!"]),
            [{"action":"update","id":4,"fact":"új"}])

    def test_delete_needs_integer_id(self):
        self.assertEqual(filter_memory_operations(
            [{"action":"delete","id":"5"}], ["Töröld a kedvenc tesztitalomat"]), [])

if __name__ == "__main__":
    unittest.main()
