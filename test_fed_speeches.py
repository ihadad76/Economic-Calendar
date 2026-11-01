"""Live regression check against the Fed's published October 2026 calendar."""
from datetime import datetime, timezone
import requests
from fed_speeches import parse_month

URL = "https://www.federalreserve.gov/newsevents/2026-october.htm"
response = requests.get(URL, timeout=25, headers={"User-Agent": "EconomicCalendar/1.0"})
response.raise_for_status()
# Test as of the start of the historical month so the event isn't filtered out.
as_of = datetime(2026, 10, 1, tzinfo=timezone.utc)
events = parse_month(response.text, 2026, 10, as_of, URL)
assert any(day.isoformat() == "2026-10-15" and clock.strftime("%H:%M") == "23:30"
           for day, clock, _ in events), f"Chair event not detected: {events!r}"
assert len(events) == 1, f"Unexpected additional chair speeches (possibly Vice Chair): {events!r}"
print("PASS: October 15 chair discussion at 23:30 ET; vice-chair events excluded.")
