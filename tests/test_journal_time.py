"""Journal date filters and idempotent confirmed memory commands."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nabu_recall"))
from journal_time import journal_window, in_window
from management import identical_existing_fact

TZ = ZoneInfo("Europe/Budapest")


class TimeScopedMemoryTests(unittest.TestCase):
    def test_yesterday_is_local_midnight_to_midnight(self):
        now = datetime(2026, 11, 24, 8, 23, tzinfo=TZ)
        window = journal_window("Mit mondtam tegnap a tesztdobozról?", now)
        self.assertEqual(datetime.fromtimestamp(window[0], TZ).date().isoformat(),
                         "2026-11-23")
        self.assertEqual(datetime.fromtimestamp(window[1], TZ).date().isoformat(),
                         "2026-11-24")
        self.assertTrue(in_window({"created": window[0]}, window))
        self.assertTrue(in_window({"created": window[1] - 1}, window))
        self.assertFalse(in_window({"created": window[1]}, window))
        self.assertIsNone(journal_window("Mi a doboz színe?", now))

    def test_dst_yesterday_is_local_calendar_day(self):
        now = datetime(2027, 3, 29, 10, tzinfo=TZ)
        start, end = journal_window("Mit beszéltünk tegnap?", now)
        self.assertEqual(end - start, 23 * 3600)

    def test_exact_duplicate_only(self):
        records = [{"id": 1, "fact": "A műhelyben van egy képzeletbeli narancssárga doboz."}]
        self.assertTrue(identical_existing_fact(
            "A műhelyben van egy képzeletbeli narancssárga doboz!", records))
        self.assertFalse(identical_existing_fact(
            "A műhelyben van egy kék doboz.", records))
        self.assertFalse(identical_existing_fact(
            "A műhelyben egy narancssárga doboz van.", records))


if __name__ == "__main__":
    unittest.main()
