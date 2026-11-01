"""Build a US economic calendar from official iCalendar release feeds."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
import requests
from icalendar import Calendar, Event, Alarm

SOURCES = {
    "BLS": "https://www.bls.gov/schedule/news_release/bls.ics",
    "BEA": "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics",
}
OUTPUT = Path("docs/calendar.ics")

def classify(source, title):
    name = title.lower()
    if source == "BLS":
        if "consumer price index" in name: return "CPI"
        if "producer price index" in name: return "PPI"
        if "employment situation" in name: return "NFP + Unemployment"
    if source == "BEA":
        if "personal income and outlays" in name: return "PCE"
        if "gross domestic product" in name and "by state" not in name: return "GDP"
    return None

def main():
    output = Calendar()
    output.add("prodid", "-//US Economic Calendar//EN")
    output.add("version", "2.0")
    output.add("calscale", "GREGORIAN")
    output.add("x-wr-calname", "US Economic Calendar")
    now = datetime.now(timezone.utc)
    counts = {}
    for source, url in SOURCES.items():
        response = requests.get(url, timeout=30, headers={"User-Agent": "EconomicCalendar/1.0"})
        response.raise_for_status()
        upstream = Calendar.from_ical(response.content)
        count = 0
        for original in upstream.walk("VEVENT"):
            title = str(original.get("summary", ""))
            label = classify(source, title)
            if not label or "dtstart" not in original: continue
            start = original.decoded("dtstart")
            if not isinstance(start, datetime) or start.tzinfo is None: continue
            start = start.astimezone(timezone.utc)
            if start < now - timedelta(days=7): continue
            event = Event()
            event.add("uid", f"{source}-{label}-{start:%Y%m%dT%H%M%S}@economic-calendar")
            event.add("summary", label)
            event.add("dtstart", start)
            event.add("dtend", start + timedelta(minutes=15))
            event.add("dtstamp", now)
            event.add("description", f"Official release: {title}\nSource: {url}")
            event.add("url", url)
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", f"{label} in 30 minutes")
            alarm.add("trigger", timedelta(minutes=-30))
            event.add_component(alarm)
            output.add_component(event)
            count += 1
        counts[source] = count
    if not all(counts.values()):
        raise RuntimeError(f"Refusing to replace calendar: missing source events: {counts}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(output.to_ical())
    logging.info("Calendar updated: %s", counts)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
