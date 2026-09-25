import sys
import os
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.getcwd())

from ctf.rag import CTFRag

load_dotenv("jarvis/.env")

rag = CTFRag()

name = "Old Sessions"
cat = "web"
desc = "Proper session timeout controls are critical. Explore the /sessions endpoint to find active session IDs and hijack the admin session."
solution = """
1. Visit the home page and notice the mention of session timeouts.
2. Navigate to /sessions to find a list of active session IDs.
3. Identify the session ID for the 'admin' user.
4. Use browser developer tools or curl to replace the current 'session' cookie with the admin's session ID.
5. Refresh the page to log in as admin and retrieve the flag.
"""
flag = "picoCTF{s3ss1on_h1j4ck1ng_1s_fun_5a92bc}"
technique = "Session Hijacking / Insufficient Session Expiration"

success = rag.store_solution(name, cat, desc, solution, flag, technique)
if success:
    print(f"[TRAIN] Successfully trained Jarvis on '{name}'")
else:
    print("[TRAIN] Failed to store solution in RAG.")
