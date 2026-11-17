"""Company-announced Magnificent Seven earnings only; never estimated dates.

Entries are deliberately curated from official investor-relations announcements.
Add new quarters only after the issuer confirms the date and timing.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from icalendar import Event, Alarm

NY = ZoneInfo("America/New_York")
# UTC is not hard-coded; NY timezone handles DST correctly.
CONFIRMED = [
    {
        "ticker": "NVDA",
        "company": "NVIDIA",
        "quarter": "Q3 FY2027",
        "day": "2026-11-17",
        "time": "16:20",  # Company-confirmed approximate results time, NY local
        "call": "17:00",
        "official": "https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Sets-Conference-Call-for-Third-Quarter-Financial-Results/",
        "announced": "2026-10-28",
    },
]
MAG7 = {"NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"}

def add_confirmed_earnings(calendar, now):
    count = 0
    today = now.astimezone(NY).date()
    for item in CONFIRMED:
        if item["ticker"] not in MAG7:
            raise ValueError("Unexpected earnings ticker")
        day = datetime.fromisoformat(item["day"]).date()
        if day < today - timedelta(days=7) or day > today + timedelta(days=400):
            continue
        announced = datetime.fromisoformat(item["announced"]).date()
        if announced > day or announced > today:
            continue
        hour, minute = map(int, item["time"].split(":"))
        start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=NY)
        summary = f"EARNINGS: {item['company']} ({item['ticker']}) — {item['quarter']}"
        event = Event()
        event.add("uid", f"confirmed-earnings-{item['ticker']}-{item['day']}@economic-calendar")
        event.add("summary", summary)
        event.add("dtstart", start)
        event.add("dtend", start + timedelta(minutes=15))
        event.add("dtstamp", now)
        event.add("description", "\n".join([
            "דוח רבעוני מאומת — לא אומדן מלוח דוחות.",
            f"חברה: {item['company']} ({item['ticker']})",
            f"תקופה: {item['quarter']}",
            "שעת פרסום: בקירוב, לפי הודעת החברה; השעה עשויה להשתנות.",
            f"שיחת משקיעים: {item['call']} שעון ניו יורק.",
            "חשיבות למסחר: עשויה להשפיע על NQ ו-ES, במיוחד מחוץ לשעות המסחר.",
            f"אישור רשמי פורסם: {item['announced']}",
            f"מקור רשמי: {item['official']}",
        ]))
        event.add("url", item["official"])
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"{item['ticker']} earnings in 30 minutes")
        alarm.add("trigger", timedelta(minutes=-30))
        event.add_component(alarm)
        calendar.add_component(event)
        count += 1
    return count
