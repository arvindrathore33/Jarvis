import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.path.join(os.getcwd(), "jarvis"))

from ctf.solver_v2 import CTFSolver
from ctf.intelligence import record_solve

load_dotenv("jarvis/.env")

challenges = [
    {"name": "Old Sessions", "cat": "web", "desc": "Proper session timeout controls are critical. Explore the /sessions endpoint to find active session IDs and hijack the admin session. URL: http://localhost:5001"},
    {"name": "WebDecode", "cat": "web", "desc": "Find Base64 encoded data hidden in tag attributes using the Inspector tool. URL: https://play.picoctf.org/practice/challenge/427"},
    {"name": "Unminify", "cat": "web", "desc": "Beautify or unminify obfuscated/compressed JavaScript code to find the flag. URL: https://play.picoctf.org/practice/challenge/426"},
    {"name": "IntroToBurp", "cat": "web", "desc": "Intercept and modify requests. Bypass a registration step or capture hidden data. URL: https://play.picoctf.org/practice/challenge/419"},
    {"name": "Bookmarklet", "cat": "web", "desc": "Create a JavaScript bookmarklet to execute code in the browser and reveal the flag. URL: https://play.picoctf.org/practice/challenge/406"},
    {"name": "Local Authority", "cat": "web", "desc": "Find hardcoded credentials in a JS file used for a login form. URL: https://play.picoctf.org/practice/challenge/278"},
    {"name": "Inspect HTML", "cat": "web", "desc": "A simple website where the flag is hidden in the HTML comments. URL: https://play.picoctf.org/practice/challenge/275"},
    {"name": "Includes", "cat": "web", "desc": "The flag is split across external files like CSS and JS. URL: https://play.picoctf.org/practice/challenge/517"},
    {"name": "Cookies", "cat": "web", "desc": "Brute force or manipulate a 'name' cookie to find the flag. URL: https://play.picoctf.org/practice/challenge/173"},
    {"name": "Scavenger Hunt", "cat": "web", "desc": "Flag split across HTML, CSS, JS, robots.txt, .htaccess, and .DS_Store. URL: https://play.picoctf.org/practice/challenge/161"},
    {"name": "GET aHEAD", "cat": "web", "desc": "Change a GET request to a HEAD request to reveal the flag. URL: https://play.picoctf.org/practice/challenge/172"},
    {"name": "dont-use-client-side", "cat": "web", "desc": "Demonstrates why sensitive logic (like password checking) should not be handled entirely in client-side JS. URL: https://play.picoctf.org/practice/challenge/66"},
    {"name": "logon", "cat": "web", "desc": "Bypass login by manipulating cookies. URL: https://play.picoctf.org/practice/challenge/46"},
    {"name": "Insp3ct0r", "cat": "web", "desc": "Flag split into three parts hidden in HTML, CSS, and JS source files. URL: https://play.picoctf.org/practice/challenge/18"},
    {"name": "where are the robots", "cat": "web", "desc": "Check robots.txt for disallowed paths. URL: https://play.picoctf.org/practice/challenge/4"},
    {"name": "SSTI1", "cat": "web", "desc": "Server-Side Template Injection in Flask/Jinja2. URL: https://play.picoctf.org/practice/challenge/515"},
    {"name": "n0s4n1ty 1", "cat": "web", "desc": "File upload vulnerability to achieve Remote Code Execution (RCE). URL: https://play.picoctf.org/practice/challenge/516"},
    {"name": "Cookie Monster Secret Recipe", "cat": "web", "desc": "Find hidden cookie recipe using browser tools and cookie inspection. URL: https://play.picoctf.org/practice/challenge/519"},
    {"name": "No FA", "cat": "web", "desc": "Leaked data challenge focusing on 2FA bypass or salt-less hashes. URL: https://play.picoctf.org/practice/challenge/520"},
    {"name": "Crack the Gate 1", "cat": "web", "desc": "Authentication bypass or credential cracking challenge. URL: https://play.picoctf.org/practice/challenge/520"},
    {"name": "No FA (Adv)", "cat": "web", "desc": "Advanced 2FA bypass or session management challenge. URL: https://play.picoctf.org/practice/challenge/520"}
]

solver = CTFSolver()
print(f"[BATCH] Starting solve for {len(challenges)} web challenges...")

results = []
for i, c in enumerate(challenges):
    print(f"\n[BATCH] [{i+1}/{len(challenges)}] Solving: {c['name']}")
    try:
        # We limit max_steps for batch processing to avoid getting stuck
        result = solver.solve(
            challenge_name=c["name"],
            description=c["desc"],
            category=c["cat"],
            max_steps=10
        )
        results.append(result)
        status = "SOLVED" if result.get("solved") else "FAILED"
        print(f"[BATCH] Result: {status} | Steps: {result.get('steps')} | Time: {result.get('elapsed_sec')}s")
        if result.get("flag"):
            print(f"[BATCH] Flag: {result['flag']}")
    except Exception as e:
        print(f"[BATCH] ERROR during solve: {e}")
        results.append({"challenge_name": c["name"], "solved": False, "error": str(e)})

# Summary report
print("\n" + "="*50)
print("BATCH SOLVE SUMMARY")
print("="*50)
solved_count = sum(1 for r in results if r.get("solved"))
for r in results:
    icon = "✓" if r.get("solved") else "✗"
    print(f"{icon} {r.get('challenge_name', 'Unknown')}")

print(f"\nTOTAL: {solved_count}/{len(challenges)} solved.")
print("="*50)

# Save summary to file
with open("jarvis/batch_solve_report.txt", "w") as f:
    f.write("PICOCTF WEB BATCH SOLVE REPORT\n")
    f.write(f"Date: {datetime.now().isoformat()}\n")
    f.write(f"Total: {solved_count}/{len(challenges)} solved\n\n")
    for r in results:
        icon = "SOLVED" if r.get("solved") else "FAILED"
        f.write(f"[{icon}] {r.get('challenge_name')}\n")
        if r.get("flag"): f.write(f"  Flag: {r.get('flag')}\n")
        f.write(f"  Steps: {r.get('steps')} | Time: {r.get('elapsed_sec')}s\n\n")

print(f"[BATCH] Report saved to jarvis/batch_solve_report.txt")
