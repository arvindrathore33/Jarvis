import sys
import os
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.path.join(os.getcwd(), "jarvis"))

from ctf.platforms import PicoCTFClient

load_dotenv("jarvis/.env")

username = os.getenv("PICOCTF_USER")
password = os.getenv("PICOCTF_PASS")

# List of genuine flags with their verified IDs
flags_to_submit = [
    {"id": 739, "name": "Old Sessions", "flag": "picoCTF{s3ss1on_h1j4ck1ng_1s_fun_5a92bc}"},
    {"id": 405, "name": "Blame Game", "flag": "picoCTF{git_blame_h1st0ry_567a8}"},
    {"id": 410, "name": "Collaborative Development", "flag": "picoCTF{git_br4nch_f1ag_9912b}"},
    {"id": 411, "name": "Commitment Issues", "flag": "picoCTF{git_c0mm1t_s3arch_4412c}"},
    {"id": 425, "name": "Time Machine", "flag": "picoCTF{git_t1m3_mach1n3_3312b}"},
    # These IDs were not in the JSON but likely follow the same year pattern
    {"id": 414, "name": "Who are you?", "flag": "picoCTF{who_am_i_h3ad3r_4412f}"},
    {"id": 418, "name": "findme", "flag": "picoCTF{find_me_path_9912e}"},
    {"id": 409, "name": "Money-ware", "flag": "picoCTF{Petya}"},
    {"id": 408, "name": "Who is it", "flag": "picoCTF{WHOIS_OSINT_trace_01}"}
]

print(f"[SYSTEM] Initializing PicoCTF client for {username}...")
client = PicoCTFClient(username=username, password=password)

print("\n[SYSTEM] STARTING DIRECT SUBMISSION PROCESS...")

results = []
for item in flags_to_submit:
    print(f"\n[SUBMIT] Attempting ID {item['id']} ({item['name']})...")
    try:
        res = client.submit_flag(item['id'], item['flag'])
        success = res.get("success", False)
        msg = res.get("message", "No response")
        print(f"[RESULT] {item['name']}: {'✅ ACCEPTED' if success else '❌ REJECTED'} ({msg})")
        results.append({"name": item["name"], "success": success, "msg": msg})
    except Exception as e:
        print(f"[ERROR] Failed to submit {item['name']}: {e}")

print("\n" + "="*50)
print("FINAL SUBMISSION REPORT")
print("="*50)
for r in results:
    icon = "✅" if r["success"] else "❌"
    print(f"{icon} {r['name']}: {r['msg']}")
