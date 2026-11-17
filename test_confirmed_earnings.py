"""Guard against estimated earnings and missing reminders."""
import unittest
from datetime import datetime, timezone
from icalendar import Calendar
from confirmed_earnings import add_confirmed_earnings

class ConfirmedEarningsTests(unittest.TestCase):
    def test_nvidia_confirmed_release_and_reminder(self):
        c = Calendar()
        n = add_confirmed_earnings(c, datetime(2026, 11, 17, 12, tzinfo=timezone.utc))
        self.assertEqual(n, 1)
        events = c.walk("VEVENT")
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIn("NVDA", str(event["SUMMARY"]))
        self.assertEqual(event["DTSTART"].dt.astimezone(timezone.utc).hour, 21)
        self.assertEqual(event["DTSTART"].dt.astimezone(timezone.utc).minute, 20)
        self.assertEqual(event.walk("VALARM")[0]["TRIGGER"].dt.total_seconds(), -1800)

    def test_no_unconfirmed_future_quarters(self):
        c = Calendar()
        self.assertEqual(add_confirmed_earnings(c, datetime(2027, 1, 1, tzinfo=timezone.utc)), 0)

if __name__ == "__main__":
    unittest.main()
