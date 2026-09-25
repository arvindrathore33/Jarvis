import sys
import os
import time
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.path.join(os.getcwd(), "jarvis"))

from ctf.platforms import PicoCTFClient
import sqlite3

load_dotenv("jarvis/.env")

username = os.getenv("PICOCTF_USER")
password = os.getenv("PICOCTF_PASS")

# 1. Get solved flags from database
conn = sqlite3.connect("/home/arvind/jarvis/memory/metrics.db")
cursor = conn.cursor()
cursor.execute("SELECT challenge, flag FROM solves WHERE solved=1 AND flag LIKE 'picoCTF{%';")
solved_data = cursor.fetchall()
conn.close()

if not solved_data:
    print("[SYSTEM] No solved flags found in database.")
    sys.exit(0)

print(f"[SYSTEM] Found {len(solved_data)} solved flags in database.")

# 2. Initialize PicoCTF client
print(f"[SYSTEM] Initializing PicoCTF client for {username}...")
client = PicoCTFClient(username=username, password=password)

# 3. Fetch all challenges to map names to IDs
print("[SYSTEM] Fetching challenge list from PicoCTF...")
r = client.session.get(f"{client.BASE}/challenges/?page=1&page_size=100")
if r.status_code != 200:
    print(f"[ERROR] API returned status {r.status_code}")
    print(f"Response: {r.text[:500]}")
    sys.exit(1)

try:
    all_challenges = r.json().get("results", [])
except Exception as e:
    print(f"[ERROR] Failed to parse JSON: {e}")
    print(f"Response: {r.text[:500]}")
    sys.exit(1)

# Map name -> ID (case-insensitive)
name_to_id = {c['name'].lower(): c['id'] for c in all_challenges}

# 4. Submit flags
print("\n[SYSTEM] STARTING AUTOMATED SUBMISSION PROCESS...")

results = []
for name, flag in solved_data:
    challenge_id = name_to_id.get(name.lower())
    
    if not challenge_id:
        print(f"[SKIP] Could not find ID for challenge: {name}")
        results.append({"name": name, "success": False, "msg": "ID not found"})
        continue

    print(f"[SUBMIT] Attempting {name} (ID: {challenge_id})...")
    try:
        res = client.submit_flag(challenge_id, flag)
        success = res.get("success", False)
        msg = res.get("message", "No response")
        print(f"[RESULT] {name}: {'✅ ACCEPTED' if success else '❌ REJECTED'} ({msg})")
        results.append({"name": name, "success": success, "msg": msg})
    except Exception as e:
        print(f"[ERROR] Failed to submit {name}: {e}")
        results.append({"name": name, "success": False, "msg": str(e)})
    
    # Small delay to avoid hitting rate limits
    time.sleep(1)

print("\n" + "="*50)
print("FINAL SUBMISSION REPORT")
print("="*50)
success_count = sum(1 for r in results if r["success"])
for r in results:
    icon = "✅" if r["success"] else "❌"
    print(f"{icon} {r['name']}: {r['msg']}")

print(f"\nTOTAL: {success_count}/{len(results)} accepted.")
print("="*50)
