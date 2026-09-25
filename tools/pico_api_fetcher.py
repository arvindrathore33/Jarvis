import asyncio
from playwright.async_api import async_playwright
import json

async def fetch_pico_challenges(cookies_dict):
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )

        # Set cookies
        formatted_cookies = []
        for name, value in cookies_dict.items():
            formatted_cookies.append({
                'name': name,
                'value': value,
                'domain': 'play.picoctf.org',
                'path': '/'
            })
        await context.add_cookies(formatted_cookies)

        page = await context.new_page()
        
        # Navigate to the API endpoint
        print("[*] Navigating to PicoCTF API...")
        url = "https://play.picoctf.org/api/challenges/?page=1&page_size=100"
        
        # We try to go to the main page first to ensure Cloudflare is happy
        await page.goto("https://play.picoctf.org/")
        await asyncio.sleep(5) # Wait for potential redirect/checks
        
        response = await page.goto(url)
        content = await page.content()
        
        # Try to extract JSON from the page (Chromium might wrap it in <pre> tags)
        try:
            # Get raw text from the page
            text = await page.evaluate("() => document.body.innerText")
            data = json.loads(text)
            print(f"[+] Success! Found {len(data.get('results', []))} challenges.")
            return data
        except Exception as e:
            print(f"[-] Failed to parse JSON: {e}")
            print(f"[-] Response was: {text[:500]}")
            return None
        finally:
            await browser.close()

if __name__ == "__main__":
    cookies = {
        'sessionid': 'sxmfa8f4wpr8t9c2chmk69q14fwev8c9',
        'csrftoken': 'GHg7MfQbVUY8VeBiXkwccuDqPGPxzYKi',
        'cf_clearance': '0C5p.lIMpluqm0YBPleNIvYRTBq8DIE6a2L8fHJWAZc-1781269850-1.2.1.1-FnwD9PCR_pFUwOU0KLHQzVNlexn4CiZitMo6_pPUjifbSSkzoXRmlGxzSYq_Tz0z4c_2jD0Y6oKc9pM_yRbmFqGQbKP3rCocvHjNPov82IUAhRpBYa46T.PGQcx1lhZYKYe8TJmCKywwU2Jdhs57W0vxpAhGJPauOT8B.0pImZbeR1mij1fh2zJ404qG6xs__OXO7BjyxKUHV7A9BWZd9mKYvB0nXXQTeH5MKd6vfYqcfz6vW._tVDer_mN1M_g6.AtctCp9EbjNr8GDSXvRkMv0vHNyZAqpFWSGNVTGqWY5QgJU_RO5eJU2OW1VMigS1wOrJ_2xBzrbUOk94Ax2MA'
    }
    result = asyncio.run(fetch_pico_challenges(cookies))
    if result:
        with open("pico_challenges.json", "w") as f:
            json.dump(result, f, indent=4)
