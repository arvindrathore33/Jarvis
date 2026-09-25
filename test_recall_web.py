import sys
import os
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.getcwd())

from ctf.solver_v2 import CTFSolver
from ctf.rag import CTFRag

load_dotenv("jarvis/.env")

rag = CTFRag()
context = rag.get_combined_context("SSTI1", "web")
print("[RECALL TEST] Context for SSTI1:")
print(context)

if "SSTI1" in context and "Jinja2" in context:
    print("\n[RECALL TEST] SUCCESS: Jarvis recalled the SSTI1 solution!")
else:
    print("\n[RECALL TEST] FAILED: Jarvis could not find the solution in RAG.")
