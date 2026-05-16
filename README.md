# BTS Parking Checker

Watches the Brussels Expo parking booking calendar and emails you the moment
**July** becomes bookable, so you can grab Parking C for the BTS concert on
**2 July 2026**.

Site watched: <https://parking.tickets.brussels-expo.com/schedule?language=en>

Runs in the **cloud for free** via GitHub Actions (recommended), or **locally**
via Windows Task Scheduler.

---

## How the checker works

The site uses a **FullCalendar** widget. The current month is shown in a header
(`#calendar .fc-center h2`, e.g. `MAY 2026`) with a next-month button
(`#calendar button.fc-next-button`). When the following month is **not** yet
bookable, the site sets that button to `visibility: hidden` / disabled.

Each run (`checker.py`):

1. Loads credentials from env vars (cloud) or `config.json` (local).
2. Launches headless Chromium via Playwright and loads the schedule page.
3. Dismisses any cookie banner (privacy-preserving choice first).
4. Saves the rendered HTML to `last_page.html` for debugging.
5. Reads the calendar month header, then loops up to 8 times:
   - Next-month button hidden/disabled → next month not bookable → stop, no email.
   - Otherwise click it and read the new header.
   - Header contains **"July"** → **trigger**.
6. On trigger: email every recipient, then record the hit so it stops alerting
   (cloud: disables the workflow; local: writes `notified.flag`).
7. On error: log to `checker.log` and exit cleanly; the next run retries.

**Trigger condition:** the calendar reaches "July 2026". It does **not** verify
Parking C specifically — confirm that yourself when you get the alert.

---

## Cloud setup (GitHub Actions, free) — recommended

The workflow `.github/workflows/check.yml` runs `checker.py` every 15 minutes
on GitHub's runners. Your PC does not need to be on.

**You need to do this once:**

1. **Create a GitHub repo** (make it **public** — there's nothing secret in
   the code, and public repos get unlimited Actions minutes; private would run
   out at this frequency). Push this project to it.
2. **Add three repository secrets** under
   *Settings → Secrets and variables → Actions → New repository secret*:
   - `BTS_EMAIL` — the Gmail address that sends (e.g. `you@gmail.com`)
   - `BTS_APP_PASSWORD` — the 16-char Gmail App Password (see below)
   - `BTS_RECIPIENTS` — comma-separated list of who gets the alert,
     e.g. `you@gmail.com, friend@example.com`
3. **Enable Actions** if prompted (*Actions* tab → "I understand my workflows,
   go ahead and enable them").
4. Optionally hit *Actions → BTS Parking Check → Run workflow* to test now.

**What happens:** every ~15 min it checks. While July is unbookable it does
nothing. The moment July appears it emails all recipients **and disables the
workflow** so you don't get repeats. To re-arm, re-enable the workflow in the
*Actions* tab.

> Note: GitHub may delay or coalesce scheduled runs under load (sometimes
> 5–15+ min late). Fine for this use case.

### Gmail App Password

A normal Gmail password will not work for SMTP.

- Enable 2-Step Verification: <https://myaccount.google.com/security>
- Create an App Password: <https://myaccount.google.com/apppasswords>
- You get a 16-character code like `abcd efgh ijkl mnop`.

---

## Local setup (Windows Task Scheduler) — alternative

Only runs while your PC is on.

1. Get a Gmail App Password (above).
2. Copy `config.example.json` to `config.json` and fill it in:
   ```json
   {
     "email": "you@gmail.com",
     "app_password": "abcd efgh ijkl mnop",
     "recipients": ["you@gmail.com", "friend@example.com"]
   }
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   python -m playwright install chromium chromium-headless-shell
   ```
4. Test email: `python checker.py --test-email`
5. Double-click `setup.bat` to register the every-15-min task.
   Remove later with `uninstall.bat`.

Local "notify once": after alerting it writes `notified.flag`; delete that
file to re-arm.

---

## Files

| File                       | Purpose                                      |
|----------------------------|----------------------------------------------|
| `checker.py`               | The checker (also `--test-email`).           |
| `.github/workflows/check.yml` | Cloud schedule + self-disable.            |
| `requirements.txt`         | Python dependencies.                         |
| `config.json`              | Local credentials (you create; gitignored).  |
| `config.example.json`      | Template to copy.                            |
| `setup.bat` / `uninstall.bat` | Register/remove the local scheduled task. |
| `checker.log`              | Run history (local).                         |
| `last_page.html`           | Latest page snapshot, for debugging.         |
| `notified.flag`            | Local-only "already alerted"; delete to re-arm. |

---

## Credentials precedence

`BTS_EMAIL` / `BTS_APP_PASSWORD` / `BTS_RECIPIENTS` env vars (used by the
cloud workflow) take priority. If `BTS_EMAIL` is unset, `config.json` is used.
`config.json` is gitignored and never leaves your machine.
