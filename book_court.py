#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import config

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler("booking.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Booker")

# --- UTILITY FUNCTIONS ---

def parse_args():
    parser = argparse.ArgumentParser(description="CourtReserve Sniper")
    parser.add_argument("--date", type=str, help="Target date (MM/DD/YYYY)", default=config.TARGET_DATE)
    parser.add_argument("--time", type=str, help="Target time (e.g. '7:30 PM')", default=config.TARGET_TIME)
    parser.add_argument("--offset", type=int, help="Days from today to book", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Run logic but do NOT click save")
    return parser.parse_args()

def get_target_date(args):
    if args.offset is not None:
        target = datetime.now() + timedelta(days=args.offset)
        return target.strftime("%m/%d/%Y")
    return args.date

def parse_duration_minutes(duration_str):
    minutes = 0
    if "hour" in duration_str:
        parts = duration_str.split("hour")
        minutes += int(parts[0].strip()) * 60
        if "minutes" in duration_str:
            min_part = parts[1].split("minutes")[0].replace("&", "").strip()
            minutes += int(min_part)
    elif "minutes" in duration_str:
        minutes += int(duration_str.split("minutes")[0].strip())
    return minutes

# --- BROWSER ACTIONS ---

async def navigate_to_date(page, target_date):
    logger.info(f"📅 Navigating to {target_date}...")
    is_already_there = await page.evaluate(f"""() => {{
        var s = $("#CourtsScheduler").data("kendoScheduler");
        if (!s) return false;
        var c = s.date();
        c.setHours(0,0,0,0);
        var t = new Date("{target_date}");
        t.setHours(0,0,0,0);
        return c.getTime() === t.getTime();
    }}""")
    
    if is_already_there:
        logger.info("✅ Already on target date.")
        return

    await page.evaluate(f"""() => {{
        var s = $("#CourtsScheduler").data("kendoScheduler");
        s.date(new Date("{target_date}"));
        s.dataSource.read();
    }}""")

    try:
        await page.wait_for_load_state("networkidle")
        target_dt = datetime.strptime(target_date, "%m/%d/%Y")
        day_name = target_dt.strftime("%A")
        await page.wait_for_selector(f'.k-lg-date-format:has-text("{day_name}")', timeout=6000)
    except Exception as e:
        logger.warning(f"⚠️ UI date update lag: {e}")

async def select_court(page, target_time, duration_mins):
    logger.info("🔍 Analyzing court availability...")
    try:
        await page.wait_for_selector(config.SELECTORS["scheduler"], state="visible", timeout=10000)
    except:
        logger.error("❌ Scheduler not found.")
        return False

    date_str = await page.evaluate('$("#CourtsScheduler").data("kendoScheduler").date().toDateString()')
    full_start = f"{date_str} {target_time}"
    
    valid_courts = await page.evaluate(f"""() => {{
        var scheduler = $("#CourtsScheduler").data("kendoScheduler");
        if (!scheduler) return [];
        var resources = scheduler.resources[0].dataSource.data();
        var events = scheduler.dataSource.data();
        var start = new Date("{full_start}");
        var end = new Date(start.getTime() + {duration_mins} * 60000);
        var available = [];

        for (var i=0; i<resources.length; i++) {{
            var r = resources[i];
            var isTaken = false;
            for (var j=0; j<events.length; j++) {{
                var ev = events[j];
                if (ev.CourtLabel === r.Value) {{
                    if (ev.start < end && ev.end > start) {{ isTaken = true; break; }}
                }}
            }}
            if (!isTaken) available.push(r.Value);
        }}
        return available;
    }}""")

    if not valid_courts:
        logger.error("❌ NO COURTS AVAILABLE.")
        return False

    sorted_courts = []
    for pref in config.PREFERRED_COURTS:
        if pref in valid_courts: sorted_courts.append(pref)
    for court in valid_courts:
        if court not in sorted_courts: sorted_courts.append(court)

    logger.info(f"✅ Found courts: {sorted_courts}")
    btn_text = f"Reserve {target_time}"
    for court in sorted_courts:
        selector = f'{config.SELECTORS["reserve_btn"]}[data-courtlabel="{court}"]:has-text("{btn_text}")'
        if await page.locator(selector).first.is_visible():
            logger.info(f"🖱️ Clicking Reserve on '{court}'")
            await page.click(selector)
            return True

    logger.error("❌ Courts available in data, but buttons hidden.")
    return False

async def fill_form(page):
    """
    Fills form using Hybrid approach (Playwright Type + JS Select).
    Robustly handles timing issues via polling.
    """
    logger.info("📝 Filling details...")
    await page.wait_for_selector(config.SELECTORS["modal_title"], timeout=5000)

    # 1. DURATION (Polling JS Injection)
    logger.info(f"Selecting Duration: {config.DURATION}")
    duration_result = await page.evaluate(f"""async () => {{
        var input = $("input[name='Duration']");
        var widget = input.data("kendoDropDownList");
        if (!widget) return {{ status: "no_widget" }};
        
        var targetText = "{config.DURATION}";
        var maxTime = 5000;
        var start = Date.now();
        
        while (Date.now() - start < maxTime) {{
            var options = widget.dataSource.data();
            
            if (options.length > 0) {{
                var foundIndex = -1;
                for (var i = 0; i < options.length; i++) {{
                    if (options[i].Text.trim() === targetText) {{
                        foundIndex = i;
                        break;
                    }}
                }}
                
                if (foundIndex > -1) {{
                    widget.select(foundIndex);
                    widget.trigger("change");
                    await new Promise(r => setTimeout(r, 1000));
                    if (widget.text().trim() === targetText) return {{ status: "success" }};
                }} else {{
                    var avail = [];
                    for(var k=0; k<options.length; k++) avail.push(options[k].Text);
                    return {{ status: "option_missing", available: avail }};
                }}
            }}
            await new Promise(r => setTimeout(r, 200));
        }}
        return {{ status: "timeout_data" }};
    }}""")
    
    if duration_result["status"] == "success":
        logger.info(f"✅ Duration set to {config.DURATION}")
    elif duration_result["status"] == "option_missing":
        logger.error(f"❌ Option missing. Available: {duration_result.get('available')}")
        raise Exception("Duration option mismatch")
    else:
        logger.error("❌ Duration selection failed.")
        raise Exception("Duration error")

    # 2. PARTNER
    if config.PARTNER_NAME:
        logger.info(f"👤 Adding partner: {config.PARTNER_NAME}")
        await page.click(config.SELECTORS["partner_input"])
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.type(config.PARTNER_NAME, delay=100) 

        select_script = f"""async () => {{
            var widget = $("#OwnersDropdown").data("kendoComboBox");
            if (!widget) return "widget_not_found";
            for (var i = 0; i < 40; i++) {{
                var results = widget.dataSource.view();
                if (results && results.length > 0) {{
                    widget.select(0);
                    widget.trigger("change");
                    widget.close(); 
                    return "success";
                }}
                await new Promise(r => setTimeout(r, 100));
            }}
            return "timeout";
        }}"""
        
        res = await page.evaluate(select_script)
        if res != "success": logger.warning("⚠️ Partner selection issues.")

    # 3. WAIVER
    try:
        is_checked = await page.evaluate("() => $('#DisclosureAgree').prop('checked')")
        if not is_checked:
            if await page.locator(config.SELECTORS["waiver_label"]).is_visible():
                await page.click(config.SELECTORS["waiver_label"])
    except: pass

async def wait_for_snipe():
    """
    Standard sleep-based wait.
    Efficient and CPU friendly.
    """
    target_dt = datetime.combine(datetime.now().date(), datetime.strptime(config.EXECUTION_TIME, "%H:%M:%S").time())
    
    # Add buffer
    fire_time = target_dt + timedelta(seconds=config.SNIPE_BUFFER_SECONDS)
    
    now = datetime.now()
    remaining = (fire_time - now).total_seconds()
    
    if remaining > 3600:
        logger.warning(f"⚠️ You are {remaining/60:.1f} minutes early. Ensure session doesn't timeout.")
    elif remaining < 0:
        logger.warning(f"⚠️ Target time passed {abs(remaining):.2f}s ago. Clicking immediately.")
        return

    logger.info(f"⏳ Sleeping for {remaining:.2f} seconds until {fire_time.strftime('%H:%M:%S')}...")
    
    # Efficient async sleep (0% CPU usage)
    if remaining > 0:
        await asyncio.sleep(remaining)

    logger.info(f"⚡ WAKE UP & FIRE! (Time: {datetime.now().strftime('%H:%M:%S')})")

async def main():
    args = parse_args()
    target_date = get_target_date(args)
    logger.info(f"🚀 START | Date: {target_date} | Time: {args.time}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=config.HEADLESS)
        context = await browser.new_context(user_agent=config.USER_AGENT)
        await context.tracing.start(screenshots=True, snapshots=True)
        page = await context.new_page()

        try:
            # 1. Login & Navigate
            await page.goto(config.LOGIN_URL)
            await page.fill(config.SELECTORS["email"], config.USERNAME)
            await page.fill(config.SELECTORS["password"], config.PASSWORD)
            await page.click(config.SELECTORS["login_btn"])
            try: await page.wait_for_url("**/Online/Portal/**", timeout=15000)
            except: pass
            
            await page.goto(config.get_scheduler_url())
            await navigate_to_date(page, target_date)

            # 2. Pre-Fill Form
            dur_mins = parse_duration_minutes(config.DURATION)
            if not await select_court(page, args.time, dur_mins):
                raise Exception("Slot selection failed")

            await fill_form(page)
            logger.info("✅ FORM PRE-FILLED. Holding for execution time...")

            # 3. Wait & Snipe
            if args.dry_run:
                logger.info("🛑 DRY RUN: Skipping save.")
            else:
                await wait_for_snipe()
                await page.click(config.SELECTORS["save_btn"])
                logger.info("✅ SAVE BUTTON CLICKED")
                
                # Wait for result
                await asyncio.sleep(5)
                await page.screenshot(path="success_booking.png")

        except Exception as e:
            logger.error(f"💥 ERROR: {e}")
            await context.tracing.stop(path="trace_error.zip")
            sys.exit(1)
        finally:
            await context.tracing.stop()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())