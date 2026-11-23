"""Offline weekend calendar query checks (synthetic events, no HA instance)."""
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import unittest
import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = yaml.safe_load((ROOT / "examples/google_calendar_weekend_events.yaml").read_text())
TZ = ZoneInfo("Europe/Budapest")


def window(instant):
    context = {
        "now": lambda: instant,
        "today_at": lambda time: datetime.combine(instant.date(),
                                                  datetime.strptime(time, "%H:%M").time(),
                                                  tzinfo=TZ),
        "timedelta": timedelta,
    }
    env = jinja2.Environment()
    variables = DOC["sequence"][0]["variables"]
    a = datetime.fromisoformat(env.from_string(
        variables["hetvege_kezdete"]).render(**context).strip())
    b = datetime.fromisoformat(env.from_string(
        variables["hetvege_vege"]).render(**context).strip())
    return a, b


def overlaps(event_start, event_end, start, end):
    """Same half-open overlap contract implemented by HA calendar integrations."""
    def aware(v):
        if isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time(), tzinfo=TZ)
        return v
    return aware(event_start) < end and aware(event_end) > start


class WeekendWindowTests(unittest.TestCase):
    def test_schema_is_read_only_and_has_response(self):
        self.assertEqual(DOC["mode"], "parallel")
        steps = DOC["sequence"]
        self.assertEqual(steps[1]["action"], "calendar.get_events")
        self.assertEqual(steps[1]["target"]["entity_id"], "calendar.esemenyek")
        self.assertIn("start_date_time", steps[1]["data"])
        self.assertIn("end_date_time", steps[1]["data"])
        self.assertEqual(steps[1]["response_variable"], "agenda")
        self.assertEqual(steps[-1]["response_variable"], "eredmeny")
        self.assertNotIn("calendar.create_event", str(DOC))
        self.assertNotIn("calendar.delete_event", str(DOC))

    def test_every_day_in_test_week(self):
        expected_start = date(2026, 11, 28)
        expected_end = date(2026, 11, 30)
        for day in range(23, 30):
            with self.subTest(day=day):
                start, end = window(datetime(2026, 11, day, 14, tzinfo=TZ))
                self.assertEqual(start.date(), expected_start)
                self.assertEqual(end.date(), expected_end)
                self.assertEqual((start.hour, end.hour), (0, 0))

    def test_sunday_keeps_current_weekend_and_monday_moves(self):
        sunday = window(datetime(2026, 11, 29, 23, 59, tzinfo=TZ))
        monday = window(datetime(2026, 11, 30, 0, 0, tzinfo=TZ))
        self.assertEqual(sunday[0].date(), date(2026, 11, 28))
        self.assertEqual(monday[0].date(), date(2026, 12, 5))
        self.assertEqual(monday[1].date(), date(2026, 12, 7))

    def test_cross_year_weekend(self):
        start, end = window(datetime(2026, 12, 31, 20, tzinfo=TZ))
        self.assertEqual(start.date(), date(2027, 1, 2))
        self.assertEqual(end.date(), date(2027, 1, 4))

    def test_dst_has_local_midnight_boundaries(self):
        start, end = window(datetime(2027, 3, 26, 12, tzinfo=TZ))
        self.assertEqual(start.date(), date(2027, 3, 27))
        self.assertEqual(end.date(), date(2027, 3, 29))
        self.assertEqual(start.utcoffset(), timedelta(hours=1))
        self.assertEqual(end.utcoffset(), timedelta(hours=2))

    def test_friday_all_day_excluded_saturday_included(self):
        a, b = window(datetime(2026, 11, 23, 14, tzinfo=TZ))
        cases = [
            ("Friday all day", date(2026, 11, 27), date(2026, 11, 28), False),
            ("Friday appointment", datetime(2026, 11, 27, 17, tzinfo=TZ),
             datetime(2026, 11, 27, 18, tzinfo=TZ), False),
            ("Saturday all day", date(2026, 11, 28), date(2026, 11, 29), True),
            ("Sunday all day", date(2026, 11, 29), date(2026, 11, 30), True),
            ("Monday all day", date(2026, 11, 30), date(2026, 12, 1), False),
            ("Spans Friday and Saturday", date(2026, 11, 27),
             date(2026, 11, 29), True),
            ("Ends Saturday midnight", datetime(2026, 11, 27, 20, tzinfo=TZ),
             datetime(2026, 11, 28, 0, tzinfo=TZ), False)
        ]
        for label, start, end, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(overlaps(start, end, a, b), expected)


if __name__ == "__main__":
    unittest.main()
