#!/usr/bin/env python3
import asyncio
import logging
from playwright.async_api import async_playwright
import config
from book_court import navigate_to_date, select_court, fill_form, parse_duration_minutes

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("Tester")

async def run_visual_test():
    async with async_playwright() as p:
        logger.info("👀 Launching VISUAL MODE")
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(user_agent=config.USER_AGENT)
        page = await context.new_page()

        try:
            await page.goto(config.LOGIN_URL)
            await page.fill(config.SELECTORS["email"], config.USERNAME)
            await page.fill(config.SELECTORS["password"], config.PASSWORD)
            await page.click(config.SELECTORS["login_btn"])
            await page.wait_for_url("**/Online/Portal/**")

            await page.goto(config.get_scheduler_url())
            await navigate_to_date(page, config.TARGET_DATE)
            
            dur = parse_duration_minutes(config.DURATION)
            success = await select_court(page, config.TARGET_TIME, dur)
            
            if success:
                await fill_form(page)
                logger.info("-" * 30)
                logger.info("✅ READY TO SAVE. PAUSING.")
                logger.info("Check: Duration, Partner in list, Waiver checked.")
                logger.info("-" * 30)
                await page.pause()
            else:
                logger.error("Test failed: No court found.")
                await page.pause()

        except Exception as e:
            logger.error(e)
            await page.pause()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_visual_test())