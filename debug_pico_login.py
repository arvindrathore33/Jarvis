import cloudscraper
import os
from dotenv import load_dotenv

load_dotenv("jarvis/.env")
username = os.getenv("PICOCTF_USER")
password = os.getenv("PICOCTF_PASS")

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

print(f"[DEBUG] Attempting login for {username}...")
r = scraper.post("https://play.picoctf.org/api/user/login/", json={
    "username": username,
    "password": password
})

print(f"[DEBUG] Status: {r.status_code}")
print(f"[DEBUG] Content: {r.text[:500]}")

if r.status_code == 200:
    token = r.json().get("token")
    print(f"[DEBUG] Token: {token[:10]}...")
else:
    print("[DEBUG] Login failed.")
