"""Verified official schedules; never extrapolate unannounced release dates.

Update these lists when publishers announce new schedules.
Sources:
https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
https://www.federalreserve.gov/newsevents/pressreleases/monetary20250905a.htm
"""
from datetime import date, datetime, time, timedelta
from icalendar import Event, Alarm
from zoneinfo import ZoneInfo
from publisher_schedules import official_dates
from event_descriptions import event_description

NY = ZoneInfo("America/New_York")

# 2026 dates explicitly published by ISM. No unverified 2027 extrapolation.
ISM_2026 = {
    "ISM Manufacturing PMI": [1,2,3,4,5,6,7,8,9,10,11,12],
    "ISM Services PMI": [1,2,3,4,5,6,7,8,9,10,11,12],
}
ISM_DAYS_2026 = {
    "ISM Manufacturing PMI": [5,2,2,1,1,1,1,3,1,1,2,1],
    "ISM Services PMI": [7,4,4,6,5,3,6,5,3,5,4,3],
}
# End dates of regularly scheduled FOMC meetings, 2026-2027.
FOMC = [
    (2026,1,28),(2026,3,18),(2026,4,29),(2026,6,17),
    (2026,7,29),(2026,9,16),(2026,10,28),(2026,12,9),
    (2027,1,27),(2027,3,17),(2027,4,28),(2027,6,9),
    (2027,7,28),(2027,9,15),(2027,10,27),(2027,12,8),
]

def append_event(calendar, now, day, clock, label, uid, source):
    start = datetime.combine(day, clock, tzinfo=NY)
    if start < now.astimezone(NY) - timedelta(days=7):
        return 0
    event = Event()
    event.add("uid", uid + "@economic-calendar")
    event.add("summary", label)
    event.add("dtstart", start)
    event.add("dtend", start + timedelta(minutes=15))
    event.add("dtstamp", now)
    event.add("description", event_description(label, source,
        "המועד מבוסס על לוח פרסומים רשמי או על רשימת תאריכים מאומתת ששמורה במערכת. יש לאמת שינויים חריגים מול הגוף המפרסם."))
    event.add("url", source)
    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", label + " in 30 minutes")
    alarm.add("trigger", timedelta(minutes=-30))
    event.add_component(alarm)
    calendar.add_component(event)
    return 1

def add_official_schedules(calendar, now):
    count = 0
    ism_source = "https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/"
    fallback_ism = {label: [date(2026, month, day) for month, day in enumerate(days, 1)]
                    for label, days in ISM_DAYS_2026.items()}
    fomc_dates, ism_dates = official_dates([date(*d) for d in FOMC], fallback_ism)
    for label, dates in ism_dates.items():
        for d in dates:
            count += append_event(calendar, now, d, time(10, 0),
                label, "ism-" + label.lower().replace(" ", "-") + f"-{d}", ism_source)
    fomc_source = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    for d in fomc_dates:
        count += append_event(calendar, now, d, time(14, 0), "FOMC Rate Decision",
            f"fomc-decision-{d}", fomc_source)
        count += append_event(calendar, now, d, time(14, 30), "FOMC Chair Press Conference",
            f"fomc-press-{d}", fomc_source)
    return count
