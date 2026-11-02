"""S&P Global US PMI releases, sourced from the publisher's live calendar.

Fail closed: missing or unrecognised schedule entries are omitted, never guessed.
"""
import calendar
import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from icalendar import Event, Alarm
from event_descriptions import event_description

URL = "https://pmi.spglobal.com/Public/Release/ReleaseDates?language=en"
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
NY = ZoneInfo("America/New_York")

def parse_releases(html):
    soup = BeautifulSoup(html, "html.parser")
    # Publisher lists entries under month/day headings with times in UTC.
    lines = [re.sub(r"\s+", " ", x).strip() for x in soup.get_text("\n").splitlines()]
    lines = [x for x in lines if x]
    year = None
    day = None
    result = {}
    for i, line in enumerate(lines):
        ym = re.fullmatch(r"20\d{2}", line)
        if ym:
            year = int(line)
            day = None
            continue
        dm = re.fullmatch(r"(" + "|".join(MONTHS) + r")\s+(\d{1,2})", line, re.I)
        if dm and year:
            try:
                day = datetime(year, MONTHS[dm.group(1).lower()], int(dm.group(2)))
            except ValueError:
                day = None
            continue
        if day is None:
            continue
        # Allow both one-line and split time/description publisher layouts.
        match = re.match(r"^(\d{2}:\d{2})\s*(?:UTC)?\s*(.*)$", line, re.I)
        if not match:
            continue
        title = match.group(2) or (lines[i + 1] if i + 1 < len(lines) else "")
        title = re.sub(r"\s+", " ", title)
        flash = bool(re.search(r"\bFlash\b", title, re.I))
        us = bool(re.search(r"\b(?:US|United States)\b", title, re.I))
        if not us or not re.search(r"\bPMI\b", title, re.I):
            continue
        # US flash release combines manufacturing and services; final releases separate.
        if flash:
            types = ("Manufacturing", "Services")
        elif re.search(r"Manufacturing", title, re.I):
            types = ("Manufacturing",)
        elif re.search(r"Services", title, re.I):
            types = ("Services",)
        else:
            continue
        hour, minute = map(int, match.group(1).split(":"))
        moment = day.replace(hour=hour, minute=minute, tzinfo=timezone.utc)
        for sector in types:
            key = f"S&P Global US {sector} PMI ({'Flash' if flash else 'Final'})"
            result[(key, moment)] = (key, moment)
    return sorted(result.values(), key=lambda x: x[1])

def add_spglobal_pmi(cal, now):
    try:
        response = requests.get(URL, timeout=20, headers={"User-Agent": "PersonalEconomicCalendar/1.0"})
        response.raise_for_status()
        releases = parse_releases(response.text)
        # Reject an empty or implausibly large parse.
        if not 1 <= len(releases) <= 120:
            logging.warning("S&P PMI calendar unrecognised; no speculative events added")
            return 0
        count = 0
        for label, moment in releases:
            if not now - timedelta(days=7) <= moment <= now + timedelta(days=400):
                continue
            event = Event()
            event.add("uid", "spglobal-" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") + "-" + moment.strftime("%Y%m%dT%H%MZ") + "@economic-calendar")
            event.add("summary", label)
            event.add("dtstart", moment.astimezone(NY))
            event.add("dtend", (moment + timedelta(minutes=15)).astimezone(NY))
            event.add("dtstamp", now)
            event.add("description", event_description(label, URL, "שעת הפרסום נקראה מלוח S&P Global ב־UTC. מועדים עשויים להשתנות; יש לאמת מול המפרסם."))
            event.add("url", URL)
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", label + " in 30 minutes")
            alarm.add("trigger", timedelta(minutes=-30))
            event.add_component(alarm)
            cal.add_component(event)
            count += 1
        logging.info("S&P Global US PMI: %d events added from publisher schedule", count)
        return count
    except Exception as exc:
        logging.warning("S&P Global PMI schedule unavailable; skipping unverified events: %s", exc)
        return 0
