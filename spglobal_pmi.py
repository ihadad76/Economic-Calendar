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

# Explicitly cross-checked published dates; never extrapolate Flash dates.
# Time: 09:45 US Eastern. Keep this list current as publishers announce dates.
VERIFIED_US_PMI = (
    ("S&P Global US Manufacturing PMI (Final)", "2026-11-02"),
    ("S&P Global US Services PMI (Final)", "2026-11-04"),
    ("S&P Global US Manufacturing PMI (Flash)", "2026-11-23"),
    ("S&P Global US Services PMI (Flash)", "2026-11-23"),
    ("S&P Global US Manufacturing PMI (Final)", "2026-12-01"),
    ("S&P Global US Services PMI (Final)", "2026-12-03"),
)
def verified_fallback():
    return [(label, datetime.fromisoformat(day + "T09:45:00").replace(tzinfo=NY).astimezone(timezone.utc))
            for label, day in VERIFIED_US_PMI]


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


# Secondary published event listing; only accept an explicit next US Flash PMI
# date and time, never infer monthly dates from past releases.
FLASH_BACKUP_URL = "https://www.mtsinsights.com/events/4745/"

def fetch_flash_backup(now):
    response = requests.get(FLASH_BACKUP_URL, timeout=12, headers={"User-Agent": "PersonalEconomicCalendar/1.0"})
    response.raise_for_status()
    text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
    match = re.search(
        r"Next Release\\s+([A-Z][a-z]+)\\s+(\\d{1,2})(?:st|nd|rd|th)?,?\\s+(20\\d{2})\\s*[·\\-–]?\\s*(\\d{1,2}):(\\d{2})\\s*(AM|PM)",
        text, re.I,
    )
    if not match:
        raise ValueError("No explicit next-release timestamp on backup page")
    month = MONTHS.get(match.group(1).lower())
    if not month:
        raise ValueError("Unknown backup month")
    hour = int(match.group(4)) % 12 + (12 if match.group(6).upper() == "PM" else 0)
    minute = int(match.group(5))
    # US Flash PMI is normally 09:45 ET; reject any unexpected clock change
    # pending confirmation from the publisher.
    if (hour, minute) != (9, 45):
        raise ValueError("Unexpected backup release time; manual review required")
    moment = datetime(int(match.group(3)), month, int(match.group(2)),
                      hour, minute, tzinfo=NY).astimezone(timezone.utc)
    if not now - timedelta(days=7) <= moment <= now + timedelta(days=65):
        raise ValueError("Backup release date outside plausible near-term window")
    return [(f"S&P Global US {sector} PMI (Flash)", moment)
            for sector in ("Manufacturing", "Services")]

def add_spglobal_pmi(cal, now):
    try:
        try:
            response = requests.get(URL, timeout=12, headers={"User-Agent": "PersonalEconomicCalendar/1.0"})
            response.raise_for_status()
            releases = parse_releases(response.text)
            if not 1 <= len(releases) <= 120:
                raise ValueError("Unrecognised publisher calendar")
        except (requests.RequestException, ValueError) as exc:
            logging.warning("S&P Global PMI publisher inaccessible (%s); using %d verified dates only", exc, len(VERIFIED_US_PMI))
            releases = verified_fallback()
            try:
                backup = fetch_flash_backup(now)
                # Only trust the secondary listing when it does not contradict
                # an already-verified flash release for the same month.
                for label, moment in backup:
                    known = [t for name, t in releases
                             if name == label and t.astimezone(NY).strftime("%Y-%m") == moment.astimezone(NY).strftime("%Y-%m")]
                    if known and any(t != moment for t in known):
                        logging.error("PMI backup contradicts verified schedule: %s", label)
                    elif not known:
                        releases.append((label, moment))
                logging.info("S&P Global PMI: checked secondary Flash schedule")
            except Exception as backup_exc:
                logging.warning("PMI secondary Flash source unavailable: %s", backup_exc)
        releases = sorted(set(releases), key=lambda item: item[1])
        future = [moment for _, moment in releases if moment >= now]
        if not future or max(future) < now + timedelta(days=30):
            logging.error("PMI schedule coverage under 30 days: verified dates require refresh")
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
        logging.info("S&P Global US PMI: %d verified events added", count)
        return count
    except Exception as exc:
        logging.warning("S&P Global PMI schedule unavailable; skipping unverified events: %s", exc)
        return 0
