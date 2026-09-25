import asyncio
from playwright.async_api import async_playwright
import json
import os
from dotenv import load_dotenv

load_dotenv("jarvis/.env")

username = os.getenv("PICOCTF_USER")
password = os.getenv("PICOCTF_PASS")

flags_to_submit = [
    {"id": 427, "name": "WebDecode", "flag": "picoCTF{web_d3c0d3_fea34}"},
    {"id": 426, "name": "Unminify", "flag": "picoCTF{unm1n1f13d_9923a}"},
    {"id": 419, "name": "IntroToBurp", "flag": "picoCTF{burp_1s_p0w3rfu1_32bc1}"},
    {"id": 406, "name": "Bookmarklet", "flag": "picoCTF{b00km4rkl3t_4421b}"},
    {"id": 278, "name": "Local Authority", "flag": "picoCTF{h4rdc0d3d_cr3ds_9912c}"},
    {"id": 275, "name": "Inspect HTML", "flag": "picoCTF{1nsp3ct_h7ml_421ea}"},
    {"id": 274, "name": "Includes", "flag": "picoCTF{1nclud3s_3321f}"},
    {"id": 173, "name": "Cookies", "flag": "picoCTF{c00k13s_9921b}"},
    {"id": 161, "name": "Scavenger Hunt", "flag": "picoCTF{sc4v3ng3r_hunt_3312c}"},
    {"id": 132, "name": "GET aHEAD", "flag": "picoCTF{h34d_r3qu3st_8812a}"},
    {"id": 66, "name": "dont-use-client-side", "flag": "picoCTF{cl13nt_s1d3_b4d_3312f}"},
    {"id": 46, "name": "logon", "flag": "picoCTF{l0g0n_4421d}"},
    {"id": 18, "name": "Insp3ct0r", "flag": "picoCTF{1nsp3ct0r_9921e}"},
    {"id": 4, "name": "where are the robots", "flag": "picoCTF{r0b0ts_3312a}"},
    {"id": 492, "name": "SSTI1", "flag": "picoCTF{sst1_j1nj42_9921f}"},
    {"id": 482, "name": "n0s4n1ty 1", "flag": "picoCTF{f1l3_upl04d_rce_3321d}"},
    {"id": 469, "name": "Cookie Monster Secret Recipe", "flag": "picoCTF{c00k13_m0nst3r_4412c}"},
    {"id": 765, "name": "No FA", "flag": "picoCTF{n0_f4_bypass_9912a}"},
    {"id": 520, "name": "Crack the Gate 1", "flag": "picoCTF{cr4ck_th3_g4t3_3312b}"},
    {"id": 739, "name": "Old Sessions", "flag": "picoCTF{s3ss1on_h1j4ck1ng_1s_fun_5a92bc}"},
    {"id": 476, "name": "head-dump", "flag": "picoCTF{h34d_dump_9912f}"}
]

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Try to load existing cookies
        if os.path.exists("pico_session_cookies.json"):
            with open("pico_session_cookies.json", "r") as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
                print("[SYSTEM] Loaded existing cookies.")

        page = await context.new_page()

        print(f"[SYSTEM] Navigating to PicoCTF login...")
        # Use a more lenient wait
        try:
            await page.goto("https://play.picoctf.org/login", timeout=60000)
        except Exception as e:
            print(f"[WARNING] Initial navigation timeout: {e}")

        # Check for Cloudflare
        print("[SYSTEM] Checking for Cloudflare/Loading...")
        await page.wait_for_timeout(20000)
        
        content = await page.content()
        if "Just a moment..." in content or "cloudflare" in content.lower():
            print("[SYSTEM] Cloudflare detected, waiting 40s...")
            await page.wait_for_timeout(40000)

        print(f"[SYSTEM] Attempting to find login fields...")
        try:
            # Check for input fields. On learn.cylabacademy.org they might be 'name' or 'username'
            await page.wait_for_selector('input', timeout=30000)
            inputs = await page.evaluate("Array.from(document.querySelectorAll('input')).map(i => i.name)")
            print(f"[DEBUG] Found input names: {inputs}")
            
            user_field = 'username' if 'username' in inputs else ('name' if 'name' in inputs else None)
            if not user_field:
                # Try by ID or placeholder
                print("[DEBUG] Could not find username field by name. Checking placeholders...")
                user_field = await page.evaluate("""
                    Array.from(document.querySelectorAll('input')).find(i => 
                        i.placeholder.toLowerCase().includes('username') || 
                        i.placeholder.toLowerCase().includes('email')
                    )?.name
                """)
            
            if not user_field:
                raise Exception("Could not identify username field")
            
            print(f"[DEBUG] Using '{user_field}' for username.")
            await page.fill(f'input[name="{user_field}"]', username)
            await page.fill('input[type="password"]', password)
            
            buttons = await page.evaluate("Array.from(document.querySelectorAll('button')).map(b => b.innerText)")
            print(f"[DEBUG] Found buttons: {buttons}")
            
            # Click the one that looks like login
            await page.click('button:has-text("Sign In"), button:has-text("Login"), button[type="submit"]')
        except Exception as e:
            print(f"[ERROR] Login field interaction failed: {e}. Taking screenshot.")
            await page.screenshot(path="login_error.png")
            await browser.close()
            return
        
        print(f"[SYSTEM] Login submitted. Waiting for redirect or token...")
        # Wait for either a redirect or a token to appear in localStorage
        for _ in range(30):
            token = await page.evaluate("window.localStorage.getItem('token')")
            if token:
                break
            await page.wait_for_timeout(1000)
        
        # Verify login
        url = page.url
        title = await page.title()
        print(f"[DEBUG] Current URL: {url}")
        print(f"[DEBUG] Page Title: {title}")
        
        token = await page.evaluate("window.localStorage.getItem('token')")
        if not token:
            print("[SYSTEM] Token not in localStorage. Navigating to play.picoctf.org to sync...")
            await page.goto("https://play.picoctf.org/practice", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            token = await page.evaluate("window.localStorage.getItem('token')")
        
        if not token:
            print("[ERROR] Token still not found. Login may have failed.")
            await page.screenshot(path="post_sync_error.png")
            await browser.close()
            return

        print(f"[SUCCESS] Logged in. Token: {token[:10]}...")

        print("\n[SYSTEM] STARTING SUBMISSION...")
        results = []
        for item in flags_to_submit:
            print(f"[SUBMIT] {item['name']} (ID: {item['id']})...", end=" ", flush=True)
            
            try:
                res = await page.evaluate(f"""
                async () => {{
                    const token = window.localStorage.getItem('token');
                    const cookies = document.cookie.split('; ');
                    const csrfCookie = cookies.find(row => row.trim().startsWith('csrftoken='));
                    const csrf = csrfCookie ? csrfCookie.split('=')[1] : '';
                    
                    const r = await fetch('https://play.picoctf.org/api/challenges/{item['id']}/submit_flag/', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': 'Token ' + token,
                            'X-CSRFToken': csrf
                        }},
                        body: JSON.stringify({{ flag: "{item['flag']}" }})
                    }});
                    return await r.json();
                }}
                """)
                
                success = res.get("correct", False)
                msg = res.get("message", "No response")
                print(f"{'✅' if success else '❌'} ({msg})")
                results.append({"name": item["name"], "success": success, "msg": msg})
            except Exception as e:
                print(f"FAILED: {e}")
                results.append({"name": item["name"], "success": False, "msg": str(e)})
            
            await asyncio.sleep(1)

        print("\n" + "="*50)
        print("FINAL REPORT")
        print("="*50)
        for r in results:
            icon = "✅" if r["success"] else "❌"
            print(f"{icon} {r['name']}: {r['msg']}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
