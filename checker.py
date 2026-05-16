"""
BTS Parking checker.

Loads the Brussels Expo parking calendar, clicks "Next" until the calendar
reaches July, and emails an alert the first time July becomes visible.

Run via Windows Task Scheduler every 15 minutes (see setup.bat).
"""

import json
import smtplib
import sys
import traceback
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
FLAG_PATH = BASE_DIR / "notified.flag"
LOG_PATH = BASE_DIR / "checker.log"
SNAPSHOT_PATH = BASE_DIR / "last_page.html"

URL = "https://parking.tickets.brussels-expo.com/schedule?language=en"

# What we are looking for in the calendar. The concert is 2026-07-02, so the
# trigger is simply: the word "July" appears in the rendered calendar.
TARGET_MONTH = "July"

# Safety cap on how many times we press "Next" before giving up for this run.
MAX_NEXT_CLICKS = 8


def log(message: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def get_recipients(config: dict) -> list:
    """Recipients list, defaulting to the sender if not specified."""
    recipients = config.get("recipients") or [config["email"]]
    if isinstance(recipients, str):
        recipients = [recipients]
    return [r.strip() for r in recipients if r.strip()]


def send_email(config: dict, subject: str, html_body: str) -> None:
    recipients = get_recipients(config)
    msg = MIMEMultipart("alternative")
    msg["From"] = config["email"]
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config["email"], config["app_password"])
        server.send_message(msg, to_addrs=recipients)
    log(f"Email sent to {len(recipients)} recipient(s): {subject}")


# --- Selectors for the FullCalendar widget on this site ---
MONTH_HEADER = "#calendar .fc-center h2"
NEXT_BUTTON = "#calendar button.fc-next-button"


def dismiss_cookie_banner(page) -> None:
    """Best-effort: dismiss a cookie banner with the most privacy-preserving
    option so it does not block calendar interaction."""
    candidates = [
        "#onetrust-reject-all-handler",
        "button:has-text('Reject')",
        "button:has-text('Decline')",
        "button:has-text('Only essential')",
        "button:has-text('Necessary only')",
        "button:has-text('Refuse')",
        "#onetrust-accept-btn-handler",
        "button:has-text('Accept')",  # last resort, only to unblock the page
    ]
    for selector in candidates:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0 and loc.is_visible():
                loc.click(timeout=2000)
                log(f"Dismissed cookie banner via: {selector}")
                page.wait_for_timeout(800)
                return
        except Exception:
            continue


def get_month_label(page) -> str:
    """Return the calendar header text, e.g. 'May 2026'. Empty if not found."""
    try:
        loc = page.locator(MONTH_HEADER).first
        if loc.count() > 0:
            return (loc.inner_text(timeout=3000) or "").strip()
    except Exception:
        pass
    return ""


def next_is_available(page) -> bool:
    """The site hides (visibility:hidden) or disables the next-month button
    when the following month is not yet bookable. True only if we can advance."""
    try:
        loc = page.locator(NEXT_BUTTON).first
        if loc.count() == 0:
            return False
        if not loc.is_enabled():
            return False
        visibility = loc.evaluate(
            "el => getComputedStyle(el).visibility"
        )
        return visibility != "hidden"
    except Exception:
        return False


def click_next(page) -> bool:
    try:
        loc = page.locator(NEXT_BUTTON).first
        loc.click(timeout=3000)
        page.wait_for_timeout(1500)
        return True
    except Exception:
        return False


def check_availability() -> bool:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2500)
            dismiss_cookie_banner(page)
            page.wait_for_timeout(1000)

            # Always save the latest rendered HTML for debugging.
            try:
                SNAPSHOT_PATH.write_text(page.content(), encoding="utf-8")
            except Exception:
                pass

            label = get_month_label(page)
            log(f"Calendar opened on: '{label or '(unknown)'}'")
            if TARGET_MONTH.lower() in label.lower():
                log("July already visible on first load.")
                return True

            for attempt in range(1, MAX_NEXT_CLICKS + 1):
                if not next_is_available(page):
                    log(
                        f"Next-month control unavailable at '{label}' "
                        f"(attempt {attempt}). July not bookable yet."
                    )
                    return False

                prev_label = label
                click_next(page)
                label = get_month_label(page)
                log(f"Advanced to: '{label or '(unknown)'}'")

                if TARGET_MONTH.lower() in label.lower():
                    log(f"July became visible after {attempt} click(s).")
                    SNAPSHOT_PATH.write_text(page.content(), encoding="utf-8")
                    return True

                if label and label == prev_label:
                    log("Month did not change after click; stopping.")
                    return False

            log("July not reached within click limit.")
            return False
        finally:
            browser.close()


def send_test_email() -> None:
    try:
        config = load_config()
    except FileNotFoundError:
        log("config.json not found. Copy config.example.json and fill it in.")
        sys.exit(1)
    try:
        send_email(
            config,
            "BTS Parking checker - test email",
            f"""
            <h2>Test email - your BTS parking checker can send mail.</h2>
            <p>If you're reading this, Gmail SMTP is configured correctly.
            The real alert will look similar and link to:</p>
            <p><a href="{URL}">{URL}</a></p>
            <p style="color:#888;font-size:12px">
            Sent {datetime.now():%Y-%m-%d %H:%M:%S}.</p>
            """,
        )
        log("Test email sent successfully.")
        print("OK - test email sent. Check your inbox.")
    except Exception:
        log("Test email FAILED:\n" + traceback.format_exc())
        print("FAILED - see checker.log for details.")
        sys.exit(1)


def main() -> None:
    if "--test-email" in sys.argv:
        send_test_email()
        return

    log("--- Run start ---")

    if FLAG_PATH.exists():
        log("notified.flag present; already alerted. Delete it to re-arm. Exiting.")
        return

    try:
        config = load_config()
    except FileNotFoundError:
        log("config.json not found. Copy config.example.json and fill it in.")
        sys.exit(1)

    try:
        available = check_availability()
    except Exception:
        log("ERROR during check:\n" + traceback.format_exc())
        return

    if not available:
        log("--- Run end (no change) ---")
        return

    try:
        send_email(
            config,
            "BTS Parking ALERT - July is now on the booking calendar",
            f"""
            <h2>July is now available on the Brussels Expo parking calendar</h2>
            <p>The booking calendar has advanced to July. Go book
            <strong>Parking C for July 2</strong> before it sells out:</p>
            <p><a href="{URL}">{URL}</a></p>
            <p style="color:#888;font-size:12px">
            Sent automatically by the BTS parking checker at
            {datetime.now():%Y-%m-%d %H:%M:%S}.</p>
            """,
        )
        FLAG_PATH.write_text(
            f"Notified at {datetime.now():%Y-%m-%d %H:%M:%S}\n", encoding="utf-8"
        )
        log("Notification sent and flag written. Will stay quiet until re-armed.")
    except Exception:
        log("ERROR sending email (will retry next run):\n" + traceback.format_exc())

    log("--- Run end ---")


if __name__ == "__main__":
    main()
