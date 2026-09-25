import asyncio
from playwright.async_api import async_playwright
import json
import os
from dotenv import load_dotenv

load_dotenv("jarvis/.env")

username = os.getenv("PICOCTF_USER")
password = os.getenv("PICOCTF_PASS")

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"[SYSTEM] Navigating to PicoCTF login...")
        await page.goto("https://play.picoctf.org/login", wait_until="networkidle")
        
        # Check if we are stuck on Cloudflare
        content = await page.content()
        if "Just a moment..." in content or "cloudflare" in content.lower():
            print("[SYSTEM] Cloudflare detected, waiting for clearance...")
            await page.wait_for_timeout(15000)

        print(f"[SYSTEM] Entering credentials...")
        try:
            await page.wait_for_selector('input[name="username"]', timeout=30000)
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            
            print(f"[SYSTEM] Waiting for login completion...")
            await page.wait_for_timeout(10000)
            
            # Try to get token from localStorage
            token = await page.evaluate("window.localStorage.getItem('token')")
            if not token:
                # Sometimes it's in a different key or we need to be on the practice page
                await page.goto("https://play.picoctf.org/practice", wait_until="networkidle")
                await page.wait_for_timeout(5000)
                token = await page.evaluate("window.localStorage.getItem('token')")
            
            if token:
                print(f"[SUCCESS] Captured Token: {token[:10]}...")
                with open("pico_token.txt", "w") as f:
                    f.write(token)
            else:
                print("[WARNING] Could not find token in localStorage.")
                # Print all localStorage keys for debugging
                keys = await page.evaluate("Object.keys(window.localStorage)")
                print(f"[DEBUG] LocalStorage keys: {keys}")

        except Exception as e:
            print(f"[ERROR] {e}")

        # Get cookies
        cookies = await context.cookies()
        with open("pico_session_cookies.json", "w") as f:
            json.dump(cookies, f)
        
        print("[SYSTEM] Cookies saved to pico_session_cookies.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
