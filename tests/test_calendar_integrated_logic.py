"""Pure calendar logic regressions, including the actual user-reported failures."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "custom_components" / "nabu_recall"))
from calendar_logic import event_bounds, query_window, resolve_day, event_overlaps, present_event

TZ = ZoneInfo("Europe/Budapest")
NOW = datetime(2026, 11, 23, 14, 0, tzinfo=TZ)


class CalendarLogicTests(unittest.TestCase):
    def test_next_week_tuesday(self):
        self.assertEqual(str(resolve_day("jövő hét kedden", NOW)), "2026-12-01")
        self.assertEqual(str(resolve_day("jövő hét kedd", NOW)), "2026-12-01")
        self.assertEqual(str(resolve_day("pénteken", NOW)), "2026-11-27")
        self.assertEqual(str(resolve_day("jövő hét pénteken", NOW)), "2026-12-04")

    def test_explicit_time_range_and_default(self):
        a, b = event_bounds("pénteken", 10, 0, NOW, end_hour=11)
        self.assertEqual(a.isoformat(), "2026-11-27T10:00:00+01:00")
        self.assertEqual(b-a, timedelta(hours=1))
        a, b = event_bounds("holnap", 10, 0, NOW)
        self.assertEqual(b-a, timedelta(minutes=30))
        a, b = event_bounds("holnap", 10, 30, NOW, duration=75)
        self.assertEqual(b-a, timedelta(minutes=75))

    def test_reject_bad_dates_times_and_conflicts(self):
        cases = [
            ("ma", 9, 0, {}),
            ("tegnap", 9, 0, {}),
            ("holnap", 24, 0, {}),
            ("holnap", 10, 60, {}),
            ("holnap", 10, 0, {"end_hour": 9}),
            ("holnap", 10, 0, {"end_hour": 11, "duration": 30}),
            ("2020-01-01", 10, 0, {}),
            ("2026-11-32", 10, 0, {}),
        ]
        for day, hour, minute, args in cases:
            with self.subTest(day=day, hour=hour, args=args):
                with self.assertRaises(ValueError):
                    event_bounds(day, hour, minute, NOW, **args)

    def test_year_selection_and_leap_days(self):
        self.assertEqual(str(resolve_day("12-01", NOW)), "2026-12-01")
        self.assertEqual(str(resolve_day("01-02", NOW)), "2027-01-02")
        self.assertEqual(str(resolve_day("02-29", NOW)), "2028-02-29")
        self.assertEqual(str(resolve_day("2027-03-01", NOW)), "2027-03-01")

    def test_weekend_whole_window_all_week(self):
        for day in range(23, 30):
            with self.subTest(day=day):
                t = datetime(2026, 11, day, 14, tzinfo=TZ)
                start, end = query_window("weekend", t)
                self.assertEqual(start.isoformat(), "2026-11-28T00:00:00+01:00")
                self.assertEqual(end.isoformat(), "2026-11-30T00:00:00+01:00")

    def test_after_weekend_moves_forward(self):
        start, end = query_window("weekend", datetime(2026, 11, 30, tzinfo=TZ))
        self.assertEqual(str(start.date()), "2026-12-05")
        self.assertEqual(str(end.date()), "2026-12-07")

    def test_all_day_friday_excluded(self):
        start, end = query_window("weekend", NOW)
        cases = [
            ({"start": "2026-11-27", "end": "2026-11-28"}, False),
            ({"start": "2026-11-28", "end": "2026-11-29"}, True),
            ({"start": "2026-11-29", "end": "2026-11-30"}, True),
            ({"start": "2026-11-30", "end": "2026-12-01"}, False),
            ({"start": "2026-11-27", "end": "2026-11-29"}, True),
            ({"start": "2026-11-27T20:00:00+01:00",
              "end": "2026-11-28T00:00:00+01:00"}, False),
        ]
        for event, expected in cases:
            with self.subTest(event=event):
                self.assertEqual(event_overlaps(event, start, end), expected)

    def test_empty_or_malformed_events(self):
        a, b = query_window("weekend", NOW)
        for bad in ({}, {"start": "bad", "end": "2026-11-29"},
                    {"start": "2026-11-28"}):
            self.assertFalse(event_overlaps(bad, a, b))

    def test_dst_window_local_midnight(self):
        start, end = query_window(
            "weekend", datetime(2027, 3, 26, 10, tzinfo=TZ))
        self.assertEqual(start.isoformat(), "2027-03-27T00:00:00+01:00")
        self.assertEqual(end.isoformat(), "2027-03-29T00:00:00+02:00")

    def test_dst_ambiguous_or_missing_time_rejected(self):
        for day, hour, minute in [
            ("2027-03-28", 2, 30),
            ("2027-10-31", 2, 30),
        ]:
            with self.subTest(day=day):
                now = datetime(2027, 3, 1, 12, tzinfo=TZ)
                with self.assertRaises(ValueError):
                    event_bounds(day, hour, minute, now)
        start, end = event_bounds("2027-03-28", 3, 30,
                                  datetime(2027, 3, 1, tzinfo=TZ))
        self.assertEqual(start.utcoffset(), timedelta(hours=2))
        self.assertGreater(end, start)

    def test_all_day_dates_are_inclusive_for_assistant_display(self):
        single = present_event({
            "summary": "Synthetic Saturday",
            "start": "2026-11-28",
            "end": "2026-11-29",
            "status": "confirmed",
        })
        self.assertEqual(single["date"], "2026-11-28")
        self.assertNotIn("last_day_inclusive", single)
        self.assertNotIn("end", single)
        self.assertTrue(single["all_day"])
        spanning = present_event({
            "summary": "Synthetic weekend",
            "start": "2026-11-28",
            "end": "2026-11-30",
        })
        self.assertEqual(spanning["last_day_inclusive"], "2026-11-29")
        timed = present_event({
            "summary": "Synthetic appointment",
            "start": "2026-11-27T17:00:00+01:00",
            "end": "2026-11-27T17:30:00+01:00",
        })
        self.assertFalse(timed["all_day"])
        self.assertEqual(timed["end"], "2026-11-27T17:30:00+01:00")

    def test_specific_day_is_full_day_and_rejects_missing_date(self):
        start, end = query_window("day", NOW, "pénteken")
        self.assertEqual(start.isoformat(), "2026-11-27T00:00:00+01:00")
        self.assertEqual(end.isoformat(), "2026-11-28T00:00:00+01:00")
        self.assertTrue(event_overlaps({
            "start": "2026-11-27T17:00:00+01:00",
            "end": "2026-11-27T17:30:00+01:00",
        }, start, end))
        self.assertFalse(event_overlaps({
            "start": "2026-11-28",
            "end": "2026-11-29",
        }, start, end))
        with self.assertRaises(ValueError):
            query_window("day", NOW)

    def test_next_event_range_not_just_today(self):
        a, b = query_window("next", NOW)
        self.assertEqual(a, NOW)
        self.assertGreaterEqual((b - a).days, 45)


if __name__ == "__main__":
    unittest.main()
