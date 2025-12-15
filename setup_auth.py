#!/usr/bin/env python3
import asyncio
import config
from playwright.async_api import async_playwright

async def setup():
    async with async_playwright() as p:
        # Run visible so you can see what happens
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("Go to login...")
        await page.goto(config.LOGIN_URL)
        
        print("Filling credentials...")
        await page.fill(config.SELECTORS["email"], config.USERNAME)
        await page.fill(config.SELECTORS["password"], config.PASSWORD)
        await page.click(config.SELECTORS["login_btn"])

        print("Waiting for redirect...")
        await page.wait_for_url("**/Online/Portal/**", timeout=30000)
        
        print(f"✅ Logged in! Saving to {config.AUTH_FILE}...")
        await context.storage_state(path=config.AUTH_FILE)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(setup())