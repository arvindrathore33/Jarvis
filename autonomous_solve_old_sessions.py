import sys
import os
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.path.join(os.getcwd(), "jarvis"))

from ctf.solver_v2 import CTFSolver

load_dotenv("jarvis/.env")

# 1. Initialize solver (NO MANUAL HINTS)
solver = CTFSolver()

# 2. Basic challenge info (Just like a user would enter)
description = """
Check out this social media platform.
URL: http://localhost:5001
"""

print("[JARVIS] Sir, I am initiating a TRULY autonomous solve for 'Old Sessions'.")
print("[JARVIS] I will rely solely on my training and RAG memory.")

# 3. Run solver
result = solver.solve(
    challenge_name="Old Sessions",
    description=description,
    category="web",
    max_steps=10
)

if result.get("solved"):
    print(f"\n[JARVIS] MISSION SUCCESS! Flag: {result['flag']}")
    print(f"[JARVIS] Solved in {result.get('steps')} steps.")
else:
    print("\n[JARVIS] Autonomous solve failed. I may need more training on this model.")
