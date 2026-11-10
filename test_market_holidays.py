"""Regression tests for US market holiday calendar feed."""
import unittest
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from icalendar import Calendar
from market_holidays import add_market_holidays

class MarketHolidayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calendar = Calendar()
        cls.total = add_market_holidays(cls.calendar, datetime(2026, 11, 10, 12, tzinfo=timezone.utc))
        cls.events = [part for part in cls.calendar.walk() if part.name == "VEVENT"]

    def event(self, prefix):
        matches = [e for e in self.events if str(e.get("uid")).startswith(prefix)]
        self.assertEqual(len(matches), 1, (prefix, len(matches)))
        return matches[0]

    def test_veterans_day_bond_market_closed(self):
        e = self.event("sifma-bond-closed-2026-11-11@")
        self.assertIn("Bond Market CLOSED", str(e.get("summary")))
        self.assertEqual(e.decoded("dtstart").date(), date(2026, 11, 11))
        self.assertEqual(e.decoded("dtstart").astimezone(ZoneInfo("Asia/Jerusalem")).hour, 16)
        alarms = [x for x in e.subcomponents if x.name == "VALARM"]
        self.assertEqual(len(alarms), 1)
        self.assertEqual(alarms[0].decoded("trigger"), timedelta(days=-1))

    def test_no_equity_holiday_on_veterans_day(self):
        self.assertFalse(any(str(e.get("uid")).startswith("equity-closed-2026-11-11@") for e in self.events))

    def test_bond_early_close_distinct_from_equities(self):
        e = self.event("sifma-bond-early-2026-11-27@")
        self.assertEqual(e.decoded("dtstart").hour, 14)
        self.assertIsNotNone(self.event("equity-early-2026-11-27@"))

    def test_uid_uniqueness(self):
        uids = [str(e.get("uid")) for e in self.events]
        self.assertEqual(len(uids), len(set(uids)))
        self.assertGreater(self.total, 5)

if __name__ == "__main__":
    unittest.main()
