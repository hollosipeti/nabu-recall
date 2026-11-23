"""Offline execution of calendar-script Jinja templates with HA-like functions.

No actual calendar events are created. No personal data or network access.
"""
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import unittest

import jinja2
import yaml

SOURCE = Path(__file__).resolve().parents[1] / "examples/google_calendar_create_event.yaml"
SCRIPT = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
TZ = ZoneInfo("Europe/Budapest")


def simulate(inputs, now_time=None):
    current = now_time or datetime(2026, 11, 23, 10, 0, tzinfo=TZ)

    def as_datetime(value, default=None):
        if value is None:
            return default
        try:
            return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        except ValueError:
            return default

    def as_local(value):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=TZ)
        return value.astimezone(TZ)

    def as_timestamp(value, default=0):
        value = as_datetime(value)
        return as_local(value).timestamp() if value is not None else default

    env = jinja2.Environment()
    env.filters["regex_match"] = lambda value, pattern: bool(re.match(pattern, str(value)))
    context = dict(inputs, now=lambda: current,
                   as_datetime=as_datetime, as_local=as_local,
                   as_timestamp=as_timestamp, timedelta=timedelta)
    for step in SCRIPT["sequence"]:
        if "variables" in step:
            for key, template in step["variables"].items():
                if isinstance(template, dict):
                    context[key] = {
                        k: env.from_string(v).render(**context).strip()
                        if isinstance(v, str) else v
                        for k, v in template.items()
                    }
                    continue
                rendered = env.from_string(str(template)).render(**context).strip()
                # Home Assistant returns native bool for templated variables.
                if rendered in ("True", "False"):
                    context[key] = rendered == "True"
                else:
                    context[key] = rendered
        elif "if" in step:
            expression = step["if"][0]["condition"] == "template"
            assert expression
            failed = env.from_string(
                step["if"][0]["value_template"]).render(**context).strip()
            if failed == "True":
                return None
        elif step.get("action") == "calendar.create_event":
            fields = step["data"]
            context["written"] = {
                key: env.from_string(v).render(**context).strip()
                for key, v in fields.items()
            }
        elif "stop" in step and "response_variable" in step:
            context["returned"] = context[step["response_variable"]]
    return context


class CalendarScriptTests(unittest.TestCase):
    def test_yaml_and_metadata(self):
        self.assertEqual(SCRIPT["mode"], "parallel")
        self.assertEqual(SCRIPT["sequence"][-1]["response_variable"], "eredmeny")
        self.assertEqual(SCRIPT["sequence"][-2]["variables"]["eredmeny"]["calendar"],
                         "calendar.esemenyek")

    def test_next_week_tuesday_not_previous_saturday(self):
        result = simulate(dict(esemeny="Próba", nap="jövő hét kedden", ora=14))
        self.assertEqual(result["datum_nap"], "2026-12-01")
        self.assertTrue(result["written"]["start_date_time"].startswith("2026-12-01T14:00"))
        self.assertEqual(result["returned"]["start"], result["written"]["start_date_time"])

    def test_friday_ten_to_eleven_is_one_hour(self):
        result = simulate(dict(esemeny="Próba", nap="pénteken", ora=10,
                               vege_ora=11))
        self.assertEqual(result["datum_nap"], "2026-11-27")
        start = datetime.fromisoformat(result["written"]["start_date_time"])
        end = datetime.fromisoformat(result["written"]["end_date_time"])
        self.assertEqual(end - start, timedelta(hours=1))

    def test_weekend_and_next_week_boundaries(self):
        cases = [
            ("jövő hét hétfő", "2026-11-30"),
            ("jövő hét péntek", "2026-12-04"),
            ("kedd", "2026-11-24"),
            ("holnap", "2026-11-24"),
            ("holnapután", "2026-11-25"),
            ("12-01", "2026-12-01"),
            ("2026-12-03", "2026-12-03"),
        ]
        for day, expected in cases:
            with self.subTest(day=day):
                self.assertEqual(simulate(dict(
                    esemeny="Próba", nap=day, ora=14))["datum_nap"], expected)

    def test_default_30_minutes_and_explicit_duration(self):
        for duration, expected in ((None, 30), (45, 45)):
            with self.subTest(duration=duration):
                values = dict(esemeny="Próba", nap="holnap", ora=14)
                if duration is not None:
                    values["idotartam"] = duration
                result = simulate(values)
                start = datetime.fromisoformat(result["written"]["start_date_time"])
                end = datetime.fromisoformat(result["written"]["end_date_time"])
                self.assertEqual(end - start, timedelta(minutes=expected))

    def test_invalid_and_inconsistent_times_rejected(self):
        cases = [
            dict(esemeny="Próba", nap="ma", ora=9),
            dict(esemeny="Próba", nap="jövő hét szombat", ora=25),
            dict(esemeny="Próba", nap="holnap", ora=10, vege_ora=9),
            dict(esemeny="Próba", nap="holnap", ora=10, vege_ora=11,
                 idotartam=30),
            dict(esemeny="Próba", nap="tegnap", ora=10),
            dict(esemeny="Próba", nap="holnap", ora=-1),
        ]
        for values in cases:
            with self.subTest(values=values):
                self.assertIsNone(simulate(values))

    def test_same_day_past_time_is_rejected(self):
        self.assertIsNone(simulate(dict(esemeny="Próba", nap="ma", ora=8)))
        self.assertIsNotNone(simulate(dict(esemeny="Próba", nap="ma", ora=14)))


if __name__ == "__main__":
    unittest.main()
