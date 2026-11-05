"""US DOL weekly claims release schedule. Official exceptions maintained explicitly."""
import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from icalendar import Event, Alarm
from event_descriptions import event_description

NY = ZoneInfo("America/New_York")
SOURCE = "https://oui.doleta.gov/unemploy/archive.asp"
EXCEPTIONS = {
    date(2026, 11, 26): date(2026, 11, 25),
    date(2027, 11, 11): date(2027, 11, 10),
    date(2027, 11, 25): date(2027, 11, 24),
}
LABEL = "Weekly Jobless Claims (Initial + Continuing)"

def add_jobless_claims(calendar, now):
    today = now.astimezone(NY).date()
    start_day = today - timedelta(days=7)
    end_day = today + timedelta(days=400)
    day = start_day
    added = 0
    while day <= end_day:
        if day.weekday() == 3:
            actual = EXCEPTIONS.get(day, day)
            if start_day <= actual <= end_day:
                start = datetime.combine(actual, time(8, 30), tzinfo=NY)
                event = Event()
                event.add("uid", f"dol-weekly-claims-{day.isoformat()}@economic-calendar")
                event.add("summary", LABEL)
                event.add("dtstart", start)
                event.add("dtend", start + timedelta(minutes=15))
                event.add("dtstamp", now)
                event.add("description", event_description(LABEL, SOURCE,
                    "מועד קבוע: חמישי 08:30 שעון ניו יורק; חריגי חג לפי לוח DOL הרשמי. שינוי בלתי צפוי מחייב עדכון."))
                event.add("url", SOURCE)
                alarm = Alarm()
                alarm.add("action", "DISPLAY")
                alarm.add("description", LABEL + " in 30 minutes")
                alarm.add("trigger", timedelta(minutes=-30))
                event.add_component(alarm)
                calendar.add_component(event)
                added += 1
        day += timedelta(days=1)
    logging.info("DOL Weekly Jobless Claims: %d scheduled events added", added)
    return added
