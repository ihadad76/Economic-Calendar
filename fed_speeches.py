"""Conservative parser for the Fed's public monthly event calendar.

Only scheduled speeches explicitly identified as 'Chair'/'Chairman' (not
'Vice Chair') with a published date and time are included. Any uncertain
markup is ignored rather than inventing an event.
"""
import calendar as monthcal
import logging
import re
from datetime import date, datetime, time, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from official_schedules import append_event

BASE = "https://www.federalreserve.gov"
TIME = re.compile(r"\b(1[0-2]|0?[1-9]):([0-5]\d)\s*([ap])\.?m\.?", re.I)
CHAIR = re.compile(r"\b(?:speech|discussion|remarks|testimony)\s*[-–:]\s*(?:fed(?:eral reserve)?\s+)?chair(?:man|woman|person)?\b", re.I)
EXCLUDE = re.compile(r"\bvice\s+chair\b", re.I)

def parse_month(html, year, month, now, url):
    soup = BeautifulSoup(html, "html.parser")
    # Some months have no Speeches section at all. Search individual rows;
    # the strict speech/discussion + chair filter prevents unrelated releases.
    result = []
    rows = soup.find_all("tr")
    for row in rows:
        text = " ".join(row.stripped_strings)
        if not CHAIR.search(text) or EXCLUDE.search(text):
            continue
        clock = TIME.search(text)
        if not clock:
            continue
        # Only accept a single, unambiguous calendar day in a dedicated cell.
        days = []
        for cell in row.find_all(["td", "th"], recursive=False):
            val = cell.get_text(" ", strip=True)
            if re.fullmatch(r"\d{1,2}", val):
                days.append(int(val))
        if len(days) != 1 or not 1 <= days[0] <= monthcal.monthrange(year, month)[1]:
            continue
        hour = int(clock.group(1)) % 12 + (12 if clock.group(3).lower() == "p" else 0)
        d = date(year, month, days[0])
        if datetime.combine(d, time(hour, int(clock.group(2))), tzinfo=__import__("zoneinfo").ZoneInfo("America/New_York")) < now.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")) - timedelta(days=7):
            continue
        result.append((d, time(hour, int(clock.group(2))), text[:160]))
    return result

def add_chair_speeches(cal, now):
    total = 0
    # Current month and next two months. New speeches are often announced
    # with little notice; repeated scheduled runs refresh the subscription.
    session = requests.Session()
    session.headers["User-Agent"] = "EconomicCalendar/1.0 (public schedule)"
    for offset in range(3):
        index = now.year * 12 + now.month - 1 + offset
        year, month = divmod(index, 12)
        month += 1
        url = f"{BASE}/newsevents/{year}-{monthcal.month_name[month].lower()}.htm"
        try:
            response = session.get(url, timeout=18)
            response.raise_for_status()
            for day, clock, detail in parse_month(response.text, year, month, now, url):
                total += append_event(cal, now, day, clock, "Fed Chair Speech",
                    f"fed-chair-speech-{day}-{clock.strftime('%H%M')}", url)
        except (requests.RequestException, ValueError) as exc:
            logging.info("Fed monthly calendar not yet available (%s): %s", url, exc)
    logging.info("Added %d verified chair speeches", total)
    return total
