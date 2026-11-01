"""Create a conservative calendar from FRED's published release dates.

FRED provides release DATES, not intraday release times. Times below are
documented regular publication times and should be checked against source notices.
"""
import os
import logging
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from icalendar import Calendar, Event, Alarm

API = "https://api.stlouisfed.org/fred"
NY = ZoneInfo("America/New_York")
OUTPUT = Path("docs/calendar.ics")
# These are release names, not individual data series: headline and core share a release.
RELEASES = {
    "Consumer Price Index": ("CPI (headline + core)", time(8, 30)),
    "Producer Price Index": ("PPI (headline + core)", time(8, 30)),
    "Employment Situation": ("NFP + Unemployment", time(8, 30)),
    "Personal Income and Outlays": ("PCE + Core PCE", time(8, 30)),
    "Gross Domestic Product": ("GDP", time(8, 30)),
}

def request_json(session, path, key, **params):
    response = session.get(
        API + path,
        params={"api_key": key, "file_type": "json", **params},
        timeout=35,
    )
    response.raise_for_status()
    return response.json()

def main():
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing FRED_API_KEY GitHub Actions secret")
    session = requests.Session()
    session.headers["User-Agent"] = "PersonalEconomicCalendar/1.0"
    releases = request_json(session, "/releases", key, limit=1000)["releases"]
    matches = {}
    for release in releases:
        name = release["name"].strip()
        if name in RELEASES:
            matches[name] = int(release["id"])
    missing = set(RELEASES) - set(matches)
    if missing:
        raise RuntimeError(f"FRED release names not found: {sorted(missing)}")
    now = datetime.now(timezone.utc)
    today = now.astimezone(NY).date()
    calendar = Calendar()
    calendar.add("prodid", "-//Personal US Macro Calendar//EN")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", "US Macro Events")
    total = 0
    for name, release_id in matches.items():
        label, clock = RELEASES[name]
        data = request_json(
            session, "/release/dates", key, release_id=release_id,
            include_release_dates_with_no_data="true",
            sort_order="desc", limit=1000,
        )
        future = sorted({
            date.fromisoformat(item["date"])
            for item in data["release_dates"]
            if today - timedelta(days=7) <= date.fromisoformat(item["date"])
            <= today + timedelta(days=400)
        })
        logging.info("%s: %d upcoming/recent dates", name, len(future))
        if not future:
            raise RuntimeError(f"No upcoming/recent dates for {name}; preserving previous feed")
        for day in future:
            start = datetime.combine(day, clock, tzinfo=NY)
            event = Event()
            event.add("uid", f"fred-{release_id}-{day.isoformat()}@economic-calendar")
            event.add("summary", label)
            event.add("dtstart", start)
            event.add("dtend", start + timedelta(minutes=15))
            event.add("dtstamp", now)
            event.add("description",
                f"Scheduled date via FRED, release: {name}. "
                "Time is the standard agency release time, not supplied by FRED. "
                "Verify against the issuing agency for exceptional schedule changes.")
            event.add("url", f"https://fred.stlouisfed.org/releases?rid={release_id}")
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", f"{label} in 30 minutes")
            alarm.add("trigger", timedelta(minutes=-30))
            event.add_component(alarm)
            calendar.add_component(event)
            total += 1
    if total < len(RELEASES):
        raise RuntimeError("Insufficient release dates; refusing to publish")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(calendar.to_ical())
    logging.info("Wrote %d events", total)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
