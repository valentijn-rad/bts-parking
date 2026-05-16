# BTS Parking Checker

Watches the Brussels Expo parking booking calendar and emails you the moment
**July** becomes bookable, so you can grab Parking C for the BTS concert on
**2 July 2026**.

Site watched: <https://parking.tickets.brussels-expo.com/schedule?language=en>

---

## How the checker works

The site uses a **FullCalendar** widget. The current month is shown in a header
(`#calendar .fc-center h2`, e.g. `MAY 2026`) with a next-month button
(`#calendar button.fc-next-button`). When the following month is **not** yet
bookable, the site sets that button to `visibility: hidden` / disabled.

Each run (`checker.py`) does the following:

1. If `notified.flag` exists, exit immediately (already alerted — stays quiet).
2. Launch headless Chromium via Playwright and load the schedule page.
3. Dismiss any cookie banner (privacy-preserving choice first).
4. Save the rendered HTML to `last_page.html` for debugging.
5. Read the calendar month header.
6. Loop, up to 8 times:
   - If the next-month button is hidden/disabled → the next month is **not**
     bookable yet → log "July not bookable yet" and stop (no email).
   - Otherwise click it, read the new month header.
   - If the header contains **"July"** → **trigger**.
   - If the month did not change after a click → stop.
7. On trigger: email every address in `recipients`, then write
   `notified.flag` so future runs stay silent (no spam).
8. On any error: log it to `checker.log` and exit cleanly; the next scheduled
   run tries again.

**Trigger condition:** the calendar advances far enough that the header reads
"July 2026". It does **not** verify Parking C specifically — confirm that
yourself when you get the alert.

Windows Task Scheduler runs `checker.py` every 15 minutes, 24/7.

---

## One-time setup

### 1. Gmail App Password

A normal Gmail password will not work for SMTP.

- Enable 2-Step Verification: <https://myaccount.google.com/security>
- Create an App Password: <https://myaccount.google.com/apppasswords>
- You get a 16-character code like `abcd efgh ijkl mnop`.

### 2. Create `config.json`

Copy `config.example.json` to `config.json` and fill it in:

```json
{
  "email": "your.address@gmail.com",
  "app_password": "abcd efgh ijkl mnop",
  "recipients": [
    "your.address@gmail.com",
    "friend@example.com"
  ]
}
```

- `email` + `app_password` — the Gmail account that **sends** (SMTP login).
- `recipients` — everyone who **receives** the alert. Add as many as you like.
  Omit it to default to just the sender.

`config.json` holds a credential — it is not committed and not shared.

### 3. Test the email

```
cd "C:\Claude Projects\bts-parking"
python checker.py --test-email
```

Prints `OK - test email sent` and delivers a test message to every recipient.
If it prints `FAILED`, check `checker.log` — almost always a wrong App
Password or 2-Step Verification not enabled.

### 4. Go live

Double-click **`setup.bat`**. It registers the scheduled task
("BTS Parking Checker", every 15 min) and does one test run. Check
`checker.log` — you should see `MAY 2026 → JUNE 2026 → July not bookable yet`.

---

## Day-to-day

- **Stop watching:** double-click `uninstall.bat`.
- **Re-arm after an alert or test:** delete `notified.flag`.
- **See what happened:** open `checker.log` (one block per run).
- **Selectors broke (site changed):** inspect `last_page.html`.

---

## Files

| File                  | Purpose                                          |
|-----------------------|--------------------------------------------------|
| `checker.py`          | The checker (also `--test-email`).               |
| `config.json`         | Your Gmail + recipients (you create this).       |
| `config.example.json` | Template to copy.                                |
| `setup.bat`           | Registers the every-15-min scheduled task.       |
| `uninstall.bat`       | Removes the scheduled task.                      |
| `checker.log`         | Run history.                                     |
| `last_page.html`      | Latest page snapshot, for debugging.             |
| `notified.flag`       | Created after alerting; delete to re-arm.        |

---

## Requirements

- Python 3.13 (installed)
- `playwright` package + Chromium (installed via
  `pip install playwright` and `python -m playwright install chromium`)
