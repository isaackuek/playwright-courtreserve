# config.py

# --- CREDENTIALS ---
USERNAME = "your_email@example.com"
PASSWORD = "your_real_password"

# --- LOCATION SETTINGS ---
# Map friendly names to CourtReserve Location IDs (sId parameter)
LOCATIONS = {
    "Mukilteo": "1478",
    "Redmond": "17109"
}
TARGET_LOCATION = "Redmond"

# --- BOOKING PREFERENCES ---
# If these are found in the available list, they will be selected in this order.
# If none are found, the script selects the first available court.
PREFERRED_COURTS = ["Redmond 4", "Redmond 5", "Redmond 6"]

# Duration must match the dropdown text EXACTLY.
# 1 hour & 30 minutes
# 2 hours
# 2 hours & 30 minutes
DURATION = "2 hours"

# Leave empty "" to book alone.
PARTNER_NAME = ""

# --- TARGET TIMING ---
# Default Date/Time to use if NO command line arguments are passed.
# Note: For automation, it is better to use --offset 28 (4 weeks) via CLI.
TARGET_DATE = "01/11/2026"
TARGET_TIME = "6:00 PM" 

# --- SNIPING CONFIGURATION ---
# The exact time the booking window opens (24h format HH:MM:SS)
# Example: If slots open at 9:00 PM, set this to "21:00:00"
EXECUTION_TIME = "18:00:00" 

# Seconds to wait AFTER the execution time before clicking save.
# 20.0 = Click 20 seconds after the window opens (Safe)
SNIPE_BUFFER_SECONDS = 20.0

# --- SYSTEM SETTINGS ---
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
AUTH_FILE = "auth.json" # Stores cookies/session

# --- URLS ---
LOGIN_URL = "https://app.courtreserve.com/Online/Account/Login/7031"
BASE_SCHEDULER_URL = "https://app.courtreserve.com/Online/Reservations/Bookings/7031"

def get_scheduler_url():
    return f"{BASE_SCHEDULER_URL}?sId={LOCATIONS[TARGET_LOCATION]}"

# --- SELECTORS ---
SELECTORS = {
    "email": 'input[name="email"]',
    "password": 'input[name="password"]',
    "login_btn": 'button[data-testid="Continue"]',
    "scheduler": '#CourtsScheduler',
    "reserve_btn": 'button[data-testid="reserveBtn"]',
    "modal_title": '[data-testid="title"]',
    "partner_input": 'input[name="OwnersDropdown_input"]',
    "waiver_label": "label[for='DisclosureAgree']",
    "save_btn": 'button[data-testid="save-btn"]'
}