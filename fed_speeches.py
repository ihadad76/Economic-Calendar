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
    # The Fed's calendar is not necessarily a table. The speech entries
    # appear as time, title, details, then the day of the month.
    heading = soup.find(lambda tag: tag.name in ("h2", "h3", "h4", "h5", "h6")
                        and tag.get_text(" ", strip=True).lower() == "speeches")
    if heading is None:
        return []
    tokens = []
    for node in heading.next_elements:
        if getattr(node, "name", None) in ("h2", "h3", "h4", "h5", "h6") and node is not heading:
            break
        if isinstance(node, __import__("bs4").NavigableString):
            value = str(node).strip()
            if value:
                tokens.append(value)
    result = []
    for i, token in enumerate(tokens):
        clock = TIME.fullmatch(token.strip())
        if not clock:
            continue
        # Each entry ends with a single numeric release day; inspect only
        # the text belonging to this entry, never the next speaker.
        following = []
        day = None
        for value in tokens[i + 1:i + 22]:
            if re.fullmatch(r"\\d{1,2}", value):
                day = int(value)
                break
            if TIME.fullmatch(value):
                break
            following.append(value)
        if day is None or not 1 <= day <= monthcal.monthrange(year, month)[1]:
            continue
        title = next((v for v in following if re.search(r"\\b(speech|discussion|remarks|testimony)\\s*[-–:]", v, re.I)), "")
        if not CHAIR.search(title) or EXCLUDE.search(title):
            continue
        hour = int(clock.group(1)) % 12 + (12 if clock.group(3).lower() == "p" else 0)
        d = date(year, month, day)
        event_time = time(hour, int(clock.group(2)))
        if datetime.combine(d, event_time, tzinfo=__import__("zoneinfo").ZoneInfo("America/New_York")) < now.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")) - timedelta(days=7):
            continue
        result.append((d, event_time, " ".join(following)[:160]))
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
