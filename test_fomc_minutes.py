"""Regression tests for FOMC minutes sourced exclusively from Fed schedules."""
import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo
from icalendar import Calendar

from publisher_schedules import parse_official_minutes_month
from official_schedules import append_event
from event_descriptions import event_description

NOV = """
<html><body><h4>FOMC Meetings</h4><div>Time:</div><div>Release Date(s):</div>
<div>2:00 p.m.</div><div>FOMC Minutes</div>
<div>Meeting of October 27-28</div><div>18</div>
<h4>Beige Book</h4><div>25</div></body></html>
"""
DEC = """
<html><body><h4>FOMC Meetings</h4><div>2:00 p.m.</div>
<div>FOMC Minutes</div><div>Meeting of December 8-9</div><div>30</div>
<div>2:30 p.m. FOMC Press Conference 9</div>
<h4>Statistical Releases</h4></body></html>
"""

class FOMCMinutesTests(unittest.TestCase):
    def test_release_day_not_meeting_day(self):
        self.assertEqual(parse_official_minutes_month(NOV, 2026, 11), [date(2026, 11, 18)])
        self.assertEqual(parse_official_minutes_month(DEC, 2026, 12), [date(2026, 12, 30)])

    def test_no_inferred_date_without_minutes_entry(self):
        self.assertEqual(parse_official_minutes_month(
            "<html><body><h4>FOMC Meetings</h4><div>FOMC Meeting 27</div></body></html>",
            2027, 1), [])

    def test_minutes_alarm_and_market_impact(self):
        c = Calendar()
        now = datetime(2026, 11, 18, 12, tzinfo=ZoneInfo("UTC"))
        count = append_event(c, now, date(2026, 11, 18), datetime.strptime("14:00", "%H:%M").time(),
                             "FOMC Meeting Minutes", "fomc-minutes-2026-11-18", 
                             "https://www.federalreserve.gov/newsevents/2026-november.htm")
        self.assertEqual(count, 1)
        e = c.walk("VEVENT")[0]
        self.assertEqual(str(e["SUMMARY"]), "FOMC Meeting Minutes")
        self.assertEqual(e.decoded("dtstart").astimezone(ZoneInfo("Asia/Jerusalem")).hour, 21)
        self.assertEqual(e.walk("VALARM")[0].decoded("TRIGGER").total_seconds(), -1800)
        desc = event_description("FOMC Meeting Minutes", "Fed")
        self.assertIn("ולא החלטת ריבית חדשה", desc)
        self.assertIn("NQ", desc)

if __name__ == "__main__":
    unittest.main()
