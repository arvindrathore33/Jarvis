import sys
import os
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.path.join(os.getcwd(), "jarvis"))

from ctf.solver_v2 import CTFSolver

load_dotenv("jarvis/.env")

# 1. Initialize solver
solver = CTFSolver()

# 2. Pre-populate Jarvis's memory with the "hints" we found manually
# This ensures Jarvis is focused on the correct vulnerability
solver.memory.add_endpoint("http://localhost:5001/sessions", note="Lists active sessions")
solver.memory.add("notes", "The /sessions page shows 'User: admin | Session ID: admin_session_777'", source="manual_help")
solver.memory.add_key("admin_session_777", key_type="session_cookie", source="manual_help")

print("[HELP] Injecting findings into Jarvis's memory...")
print("[HELP] Instructing Jarvis to perform the final exploitation step...")

description = """
Vulnerability identified: Publicly accessible /sessions endpoint leaks admin session ID.
Admin session ID: 'admin_session_777'.
Mission: Access 'http://localhost:5001' with the 'session' cookie set to 'admin_session_777' to retrieve the flag.
"""

# 3. Run solver with high-signal guidance
result = solver.solve(
    challenge_name="Old Sessions (Assisted)",
    description=description,
    category="web",
    max_steps=5
)

if result.get("solved"):
    print(f"\n[JARVIS] SUCCESS! Flag found: {result['flag']}")
else:
    print("\n[JARVIS] Flag not found yet. Checking tree...")
    print(result.get("tree_summary"))
