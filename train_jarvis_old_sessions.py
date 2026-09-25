import sys
import os
import time
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.getcwd())

from ctf.solver_v2 import CTFSolver

load_dotenv("jarvis/.env")

# Description for Old Sessions
description = """
Proper session timeout controls are critical for securing user accounts. 
If a user logs in on a public or shared computer but doesn't explicitly log out, 
and session expiration dates are misconfigured, the session may remain active indefinitely.
Your friend tells you to check out a new social media platform he built a few years ago.
Challenge URL: http://localhost:5001
"""

solver = CTFSolver()
print("[TRAIN] Starting autonomous solve for 'Old Sessions'...")
result = solver.solve(
    challenge_name="Old Sessions",
    description=description,
    category="web",
    max_steps=15
)

if result.get("solved"):
    print(f"\n[TRAIN] SUCCESS! Flag found: {result['flag']}")
    print(f"[TRAIN] Technique used: {result.get('writeup')}")
else:
    print("\n[TRAIN] FAILED. Jarvis could not find the flag.")
    print(f"[TRAIN] Last steps: {result.get('tree_summary')}")
