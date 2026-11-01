# US Economic Calendar setup

This project generates an Apple Calendar-compatible subscribed ICS feed with 30-minute event alarms.

## Coverage in current version
- BLS: CPI, PPI, Employment Situation (NFP + unemployment)
- BEA: Personal Income and Outlays (PCE), GDP

**Not yet included:** ISM Manufacturing/Services, FOMC decisions and press conferences, speeches by the Federal Reserve Chair. Do not assume these are covered.

## Enable
1. In repository Settings > Pages, select Deploy from a branch, main, /docs, and Save.
2. In Actions, run the "Update economic calendar" workflow once.
3. Check that docs/calendar.ics exists and that the workflow succeeded.
4. Subscribe on iPhone using https://ihadad76.github.io/Economic-Calendar/calendar.ics (only after verifying the URL works).

Apple Calendar may not always honor alarms embedded in subscribed ICS calendars; check the iPhone's default alert settings and test a notification. Subscription refresh intervals are controlled by the calendar client, not the workflow.

The workflow runs three times per day (GitHub scheduled runs can be delayed). A failed source fetch preserves the previous published feed.
