# CourtReserve Booker

Automated booking tool for CourtReserve using Playwright. Features intelligent calendar navigation, conflict detection via Kendo UI DataSource, and precise execution timing.

## Setup

1.  **Install Python 3.8+**
2.  **Install Libraries:**
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```
3.  **Configure:**
    Edit `config.py` with your credentials and generic preferences.

## Usage

### 1. Visual Test (Development)
Run this to see the bot in action. It will perform all steps **except** clicking the final "Save" button.
```bash
python test_book.py
```

### 2. Book Specific Date (Manual)
Book a slot for a specific day.
```bash
python book_court.py --date "12/25/2025" --time "6:00 PM"
```

### 3. Automation (Cron)
Book exactly 28 days in advance. Ideal for daily Cron jobs.
```bash
python book_court.py --offset 28
```

**Example Crontab (Runs daily at 7:58 AM):**
```bash
58 7 * * * cd /path/to/script && /usr/bin/python3 book_court.py --offset 28 >> cron.log 2>&1
```

## Debugging

If the script fails in headless mode (production):
1.  Check `booking.log` for text logs.
2.  **View Trace:** The script generates `trace_error.zip` on failure.
    *   Go to trace.playwright.dev
    *   Upload `trace_error.zip`
    *   You will see a frame-by-frame replay of exactly what the bot saw (screenshots, network calls, and DOM snapshots).

## Logic Features

*   **Priority Courts:** Define `PREFERRED_COURTS = ["Court 1", "Court 2"]` in `config.py`. The bot tries them in order before settling for any available court.
*   **Exact Match Duration:** Uses `:text-is()` to avoid confusing "1 hour" with "1 hour 30 mins".
*   **Smart Waiting:** If `EXECUTION_TIME` is set (e.g., "08:00:00"), the bot fills the form and sleeps until that exact second to click "Save", maximizing your chances of beating others to the slot.
