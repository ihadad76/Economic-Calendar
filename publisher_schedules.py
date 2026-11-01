"""Read publisher schedules; reject incomplete/unrecognised pages.

The checked-in dates in official_schedules.py remain the safe fallback.
"""
import calendar
import logging
import re
from datetime import date
import requests
from bs4 import BeautifulSoup

FED_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
ISM_URL = "https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/"
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}

def get_html(url):
    response = requests.get(url, timeout=18, headers={"User-Agent": "PersonalEconomicCalendar/1.0"})
    response.raise_for_status()
    return response.text

def parse_fomc(html):
    soup = BeautifulSoup(html, "html.parser")
    result = set()
    # Restrict each year to its own section. Avoid confusing statement/minutes
    # release dates with meeting dates.
    headings = soup.find_all(re.compile("^h[1-6]$"))
    for heading in headings:
        label = heading.get_text(" ", strip=True)
        m = re.search(r"\b(20\d{2})\s+FOMC Meetings\b", label, re.I)
        if not m:
            continue
        year = int(m.group(1))
        nodes = []
        for node in heading.next_elements:
            if getattr(node, "name", None) in ("h2", "h3") and node is not heading:
                break
            if getattr(node, "name", None) in ("p", "div", "li"):
                text = node.get_text(" ", strip=True)
                if len(text) < 90:
                    nodes.append(text)
        # Pair a month label with the next day range, without searching far.
        for i, value in enumerate(nodes):
            month = MONTHS.get(value.lower())
            if not month:
                continue
            for next_value in nodes[i+1:i+5]:
                match = re.fullmatch(r"(\d{1,2})\s*[-–—]\s*(\d{1,2})\s*\*?", next_value)
                if match:
                    day = int(match.group(2))
                    try:
                        result.add(date(year, month, day))
                    except ValueError:
                        pass
                    break
    return sorted(result)

def parse_ism(html):
    """Parse the ISM publication table, ignoring forecasts and footnotes.

    ISM renders the table with ordinary or header cells depending on page
    template. Read its row values rather than relying on a specific <th>.
    """
    soup = BeautifulSoup(html, "html.parser")
    result = {"ISM Manufacturing PMI": [], "ISM Services PMI": []}
    month_names = "|".join(MONTHS)
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        heading = " ".join(rows[0].stripped_strings).lower()
        if "manufacturing" not in heading or "services" not in heading:
            continue
        for row in rows[1:]:
            cells = [cell.get_text(" ", strip=True)
                     for cell in row.find_all(["td", "th"], recursive=False)]
            if len(cells) < 3:
                continue
            match = re.fullmatch(r"\s*(" + month_names + r")\s+(20\d{2})\s*", cells[0], re.I)
            if not match:
                continue
            month, year = MONTHS[match.group(1).lower()], int(match.group(2))
            for label, raw in zip(result, cells[1:3]):
                day = re.match(r"^\s*(\d{1,2})(?!\d)", raw)
                if day:
                    try:
                        result[label].append(date(year, month, int(day.group(1))))
                    except ValueError:
                        pass
    return result

def official_dates(fallback_fomc, fallback_ism):
    fomc, ism = list(fallback_fomc), {k: list(v) for k, v in fallback_ism.items()}
    try:
        parsed = parse_fomc(get_html(FED_URL))
        years = {d.year for d in parsed}
        # Regular FOMC years have eight scheduled meetings. Reject any year
        # with implausibly many parsed dates (the page also lists archives).
        if parsed and all(7 <= sum(d.year == y for d in parsed) <= 9 for y in years):
            fomc = sorted(set(fomc) | set(parsed))
            logging.info("FOMC: %d official dates parsed", len(parsed))
        else:
            logging.warning("FOMC parser incomplete; retaining known dates")
    except Exception as exc:
        logging.warning("FOMC source unavailable; retaining known dates: %s", exc)
    try:
        parsed = parse_ism(get_html(ISM_URL))
        if all(len(v) >= 10 for v in parsed.values()):
            for label, dates in parsed.items():
                ism[label] = sorted(set(ism[label]) | set(dates))
            logging.info("ISM: %d official release dates parsed", sum(map(len, parsed.values())))
        else:
            logging.warning("ISM parser incomplete; retaining known dates")
    except Exception as exc:
        logging.warning("ISM source unavailable; retaining known dates: %s", exc)
    return fomc, ism
