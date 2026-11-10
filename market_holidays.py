"""Official US equity closures and CME Globex holiday-schedule notices.

CME holiday hours are PRODUCT-SPECIFIC. Never infer an exact NQ/ES/GC close
from a generic exchange holiday. Verify exact hours on CME's live page.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from icalendar import Event, Alarm

NY = ZoneInfo("America/New_York")
NYSE_URL = "https://www.nyse.com/trade/hours-calendars"
NASDAQ_URL = "https://www.nasdaqtrader.com/Trader.aspx?id=Calendar"
CME_URL = "https://www.cmegroup.com/trading-hours.html"

# Official NYSE 2026-2028 calendar; Nasdaq 2026 independently checked.
EQUITY_CLOSED = {
    2026: ["01-01","01-19","02-16","04-03","05-25","06-19","07-03","09-07","11-26","12-25"],
    2027: ["01-01","01-18","02-15","03-26","05-31","06-18","07-05","09-06","11-25","12-24"],
    2028: ["01-17","02-21","04-14","05-29","06-19","07-04","09-04","11-23","12-25"],
}
EQUITY_EARLY = {
    2026: ["11-27","12-24"],
    2027: ["11-26"],
    2028: ["07-03","11-24"],
}
# CME official 2026 Globex holiday-schedule windows. This is NOT a list
# of full exchange closures or a claim about specific product hours.
CME_SPECIAL_2026 = [
    ("2026-11-26", "Thanksgiving"),
    ("2026-11-27", "Thanksgiving"),
    ("2026-12-24", "Christmas"),
    ("2026-12-25", "Christmas"),
    ("2026-12-31", "New Year's"),
    ("2027-01-01", "New Year's"),
]

# US dollar fixed-income MARKET recommendations from SIFMA.
# Source: https://www.sifma.org/resources/general/holiday-schedule
# These are recommended CASH bond-market holidays, NOT CME futures closings.
# 2027 values reflect the SIFMA 2026-2027 announcement; verify revisions
# against the source calendar before trading.
SIFMA_URL = "https://www.sifma.org/resources/general/holiday-schedule"
BOND_CLOSED = {
    "2026-10-12": "Columbus Day",
    "2026-11-11": "Veterans Day",
    "2026-11-26": "Thanksgiving",
    "2026-12-25": "Christmas",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King Jr. Day",
    "2027-02-15": "Presidents Day",
    "2027-03-26": "Good Friday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-10-11": "Columbus Day",
    "2027-11-11": "Veterans Day",
    "2027-11-25": "Thanksgiving",
    "2027-12-24": "Christmas (observed)",
}
# Date -> (holiday name, recommended close time in US Eastern).
BOND_EARLY = {
    "2026-11-27": ("Day after Thanksgiving", time(14, 0)),
    "2026-12-24": ("Christmas Eve", time(14, 0)),
    "2026-12-31": ("New Year's Eve", time(14, 0)),
    "2027-03-25": ("Before Good Friday", time(14, 0)),
    "2027-05-28": ("Before Memorial Day", time(14, 0)),
    "2027-07-02": ("Before Independence Day", time(14, 0)),
    "2027-11-26": ("Day after Thanksgiving", time(14, 0)),
    "2027-12-23": ("Christmas Eve (observed)", time(14, 0)),
    "2027-12-31": ("New Year's Eve", time(14, 0)),
}

def add_market_holidays(cal, now):
    count = 0
    def emit(day, clock, duration, uid, title, description, url):
        nonlocal count
        start = datetime.combine(day, clock, tzinfo=NY)
        if not now - timedelta(days=7) <= start <= now + timedelta(days=400):
            return
        event = Event()
        event.add("uid", uid + "@economic-calendar")
        event.add("summary", title)
        event.add("dtstart", start)
        event.add("dtend", start + duration)
        event.add("dtstamp", now)
        event.add("description", description + "\\nOfficial source: " + url)
        event.add("url", url)
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", title + " tomorrow")
        alarm.add("trigger", timedelta(days=-1))
        event.add_component(alarm)
        cal.add_component(event)
        count += 1
    for year, days in EQUITY_CLOSED.items():
        for mmdd in days:
            d = date.fromisoformat(f"{year}-{mmdd}")
            emit(d, time(9, 30), timedelta(hours=6, minutes=30),
                 f"equity-closed-{d}", "NYSE / Nasdaq CLOSED",
                 "המסחר הרגיל במניות בארה״ב סגור היום. התראה יום מראש. שעות ניו יורק.",
                 NYSE_URL)
    for year, days in EQUITY_EARLY.items():
        for mmdd in days:
            d = date.fromisoformat(f"{year}-{mmdd}")
            emit(d, time(13), timedelta(minutes=15),
                 f"equity-early-{d}", "NYSE / Nasdaq EARLY CLOSE — 13:00 ET",
                 "סגירה מוקדמת של מסחר מניות ב־13:00 שעון ניו יורק (אופציות מסוימות ב־13:15). התראה יום מראש.",
                 NYSE_URL)
    for raw, holiday in CME_SPECIAL_2026:
        d = date.fromisoformat(raw)
        emit(d, time(9), timedelta(minutes=15),
             f"cme-special-{d}", f"CME Globex HOLIDAY HOURS — {holiday}",
             "לוח שעות מיוחד לחג. NQ/ES/GC עשויים לפעול בשעות שונות. זה אינו אישור לסגירה מלאה או לשעת סגירה מסוימת. בדקו את שעות החוזה ב־CME לפני המסחר. התראה יום מראש.",
             CME_URL)
    # SIFMA recommended closures for the US CASH bond market; stocks and
    # CME futures must not inherit these labels or inferred trading hours.
    for iso_day, holiday in BOND_CLOSED.items():
        d = date.fromisoformat(iso_day)
        emit(d, time(9, 30), timedelta(hours=6, minutes=30),
             f"sifma-bond-closed-{d}", f"US Bond Market CLOSED (SIFMA) — {holiday}",
             "SIFMA ממליצה על סגירה מלאה בשוק האג״ח האמריקאי (שוק מזומן). "
             "NYSE/Nasdaq וחוזי CME עשויים להמשיך לסחור כרגיל; זו אינה הודעת סגירה של CME. "
             "התראה 24 שעות לפני תחילת האירוע. יש לאמת חריגים מול SIFMA.",
             SIFMA_URL)
    for iso_day, (holiday, clock) in BOND_EARLY.items():
        d = date.fromisoformat(iso_day)
        emit(d, clock, timedelta(minutes=15),
             f"sifma-bond-early-{d}",
             f"US Bond Market EARLY CLOSE (SIFMA) — {clock.strftime('%H:%M')} ET — {holiday}",
             "SIFMA ממליצה על סיום מוקדם של המסחר בשוק האג״ח המזומן. "
             "אין להסיק מכך את שעות המסחר ב־NYSE/Nasdaq או בחוזי CME. "
             "התראה 24 שעות לפני שעת הסגירה המומלצת.",
             SIFMA_URL)
    return count
