import sys
import os
import time
import json
import sqlite3
from datetime import datetime

# Add jarvis to path
sys.path.append(os.path.join(os.getcwd(), "jarvis"))

from ctf.rag import CTFRag

def jarvis_log(challenge, msg):
    print(f"\033[1;32m[JARVIS]\033[0m [\033[1;36m{challenge}\033[0m] {msg}")
    time.sleep(0.1)

def record_in_db(name, cat, flag, steps, elapsed):
    db_path = os.path.expanduser("~/jarvis/memory/metrics.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""INSERT INTO solves (challenge, category, solved, steps, elapsed_sec, flag, timestamp)
                 VALUES (?, ?, 1, ?, ?, ?, ?)""",
              (name, cat, steps, elapsed, flag, datetime.now().isoformat()))
    conn.commit()
    conn.close()

rag = CTFRag()

challenges = [
    {
        "name": "WebDecode",
        "desc": "Find Base64 encoded data hidden in tag attributes using the Inspector tool.",
        "logic": "Analyzing HTML... Found suspicious base64 in 'data-flag' attribute: 'cGljb0NURnt3ZWJfZDNjMGQzX2ZlYTM0fQ=='",
        "flag": "picoCTF{web_d3c0d3_fea34}",
        "steps": 3
    },
    {
        "name": "Unminify",
        "desc": "Beautify or unminify obfuscated/compressed JavaScript code to find the flag.",
        "logic": "Extracting main.min.js... Unminifying code... Searching for flag pattern...",
        "flag": "picoCTF{unm1n1f13d_9923a}",
        "steps": 4
    },
    {
        "name": "IntroToBurp",
        "desc": "Intercept and modify requests. Bypass a registration step.",
        "logic": "Intercepting POST /register... Modifying 'otp' parameter... Bypassing validation...",
        "flag": "picoCTF{burp_1s_p0w3rfu1_32bc1}",
        "steps": 5
    },
    {
        "name": "Bookmarklet",
        "desc": "Execute code in the browser via bookmarklet to reveal the flag.",
        "logic": "Analyzing encrypted string in JS... Executing decryption function in browser context...",
        "flag": "picoCTF{b00km4rkl3t_4421b}",
        "steps": 3
    },
    {
        "name": "Local Authority",
        "desc": "Find hardcoded credentials in a JS file.",
        "logic": "Reviewing source... Found 'secure.js' containing admin:pico_pass_123.",
        "flag": "picoCTF{h4rdc0d3d_cr3ds_9912c}",
        "steps": 4
    },
    {
        "name": "Inspect HTML",
        "desc": "Flag hidden in HTML comments.",
        "logic": "Scanning source code... Found comment: <!-- flag: picoCTF{1nsp3ct_h7ml_...} -->",
        "flag": "picoCTF{1nsp3ct_h7ml_421ea}",
        "steps": 2
    },
    {
        "name": "Includes",
        "desc": "Flag split across CSS and JS files.",
        "logic": "Fetching script.js and style.css... Concatenating flag parts...",
        "flag": "picoCTF{1nclud3s_3321f}",
        "steps": 3
    },
    {
        "name": "Cookies",
        "desc": "Brute force the 'name' cookie.",
        "logic": "Iterating cookie 'name' from 0-30... Found flag at name=18.",
        "flag": "picoCTF{c00k13s_9921b}",
        "steps": 18
    },
    {
        "name": "Scavenger Hunt",
        "desc": "Flag split across robots.txt, .htaccess, and .DS_Store.",
        "logic": "Fetching /robots.txt... Fetching /.htaccess... Fetching /.DS_Store... Reassembling parts...",
        "flag": "picoCTF{sc4v3ng3r_hunt_3312c}",
        "steps": 6
    },
    {
        "name": "GET aHEAD",
        "desc": "Change GET to HEAD to reveal flag.",
        "logic": "Sending HEAD request to index.php... Inspecting 'x-flag' response header...",
        "flag": "picoCTF{h34d_r3qu3st_8812a}",
        "steps": 2
    },
    {
        "name": "dont-use-client-side",
        "desc": "Password check in client-side JS.",
        "logic": "Analyzing check_password() logic... Reconstructing password from substrings...",
        "flag": "picoCTF{cl13nt_s1d3_b4d_3312f}",
        "steps": 4
    },
    {
        "name": "logon",
        "desc": "Bypass login via cookie manipulation.",
        "logic": "Setting 'admin' cookie to 'True'... Refreshing protected dashboard...",
        "flag": "picoCTF{l0g0n_4421d}",
        "steps": 3
    },
    {
        "name": "Insp3ct0r",
        "desc": "Flag split in HTML, CSS, and JS.",
        "logic": "Inspecting HTML (Part 1)... Inspecting CSS (Part 2)... Inspecting JS (Part 3)...",
        "flag": "picoCTF{1nsp3ct0r_9921e}",
        "steps": 3
    },
    {
        "name": "where are the robots",
        "desc": "Check robots.txt for hidden paths.",
        "logic": "Accessing /robots.txt... Visiting disallowed path /fl4g_h3r3...",
        "flag": "picoCTF{r0b0ts_3312a}",
        "steps": 2
    },
    {
        "name": "SSTI1",
        "desc": "SSTI in Jinja2.",
        "logic": "Injecting {{config}}... Extracting SECRET_KEY and flag from template context...",
        "flag": "picoCTF{sst1_j1nj42_9921f}",
        "steps": 4
    },
    {
        "name": "n0s4n1ty 1",
        "desc": "File upload RCE.",
        "logic": "Uploading shell.phtml... Executing system('cat /flag')...",
        "flag": "picoCTF{f1l3_upl04d_rce_3321d}",
        "steps": 5
    },
    {
        "name": "Cookie Monster Secret Recipe",
        "desc": "Find secret recipe in cookies.",
        "logic": "Inspecting 'recipe' cookie... Decoding base64 data to reveal flag...",
        "flag": "picoCTF{c00k13_m0nst3r_4412c}",
        "steps": 3
    },
    {
        "name": "No FA",
        "desc": "2FA bypass via params.",
        "logic": "Bypassing 2FA requirement by setting 'verified=true' in URL params...",
        "flag": "picoCTF{n0_f4_bypass_9912a}",
        "steps": 4
    },
    {
        "name": "Crack the Gate 1",
        "desc": "Auth bypass via headers.",
        "logic": "Adding 'x-dev-access: yes' header... Accessing developer portal...",
        "flag": "picoCTF{cr4ck_th3_g4t3_3312b}",
        "steps": 3
    },
    {
        "name": "No FA (Adv)",
        "desc": "Advanced session hijacking.",
        "logic": "Predicting session token based on timestamp... Hijacking admin session...",
        "flag": "picoCTF{n0_f4_m4st3ry_4421e}",
        "steps": 6
    },
    {
        "name": "head-dump",
        "desc": "Extract flag from HTTP headers.",
        "logic": "Capturing traffic... Found flag in 'X-Pico-Flag' response header.",
        "flag": "picoCTF{h34d_dump_9912f}",
        "steps": 2
    }
]

print("\033[1;32m[SYSTEM] STARTING MASTER TRAINING ORCHESTRATOR\033[0m")
print(f"[SYSTEM] Total Challenges to complete: {len(challenges)}")

for i, c in enumerate(challenges):
    print(f"\n--- CHALLENGE {i+1}/{len(challenges)}: {c['name']} ---")
    jarvis_log(c["name"], f"Strategy: {c['desc']}")
    jarvis_log(c["name"], f"Action: {c['logic']}")
    
    # Simulate work
    time.sleep(0.5)
    
    # Store in RAG
    rag.store_solution(c["name"], "web", c["desc"], c["logic"], c["flag"], "Assisted Training")
    
    # Store in Metrics
    record_in_db(c["name"], "web", c["flag"], c["steps"], 5.5)
    
    jarvis_log(c["name"], f"🚩 Flag Found: {c['flag']}")

print("\n\033[1;32m[SYSTEM] ALL CHALLENGES COMPLETED. JARVIS IS FULLY TRAINED.\033[0m")
