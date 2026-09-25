#!/usr/bin/env python3
"""
daily_audit.py — JARVIS Daily Audit & Health Check
Automates performance tracking, CVE updates, and system verification.

Run at start of every CTF session:
  python daily_audit.py

New scripts available today:
  python exercise_room.py       ← autonomous training via Gemini
  python performance_dashboard.py ← visual stats dashboard
  python ctf_today.py           ← one-click CTF challenge solver
  python tools/ctf/ctf_engine.py <url>  ← auto-router
"""

import os
import sys
import subprocess
from datetime import datetime

JARVIS_DIR = os.path.expanduser("~/jarvis")
LOG_PATH = os.path.join(JARVIS_DIR, "memory_logs/audit_log.txt")

def log_audit(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[*] {msg}")

def run_cmd(cmd, description):
    log_audit(f"Running: {description}...")
    try:
        # Use full path to venv python
        python_bin = os.path.join(JARVIS_DIR, "venv/bin/python")
        result = subprocess.run([python_bin, "-c", cmd], capture_output=True, text=True, cwd=JARVIS_DIR)
        if result.returncode == 0:
            log_audit(f"Success: {description}")
            print(result.stdout)
        else:
            log_audit(f"Failed: {description} (Error: {result.stderr.strip()})")
    except Exception as e:
        log_audit(f"Error: {description} ({e})")

def check_tools():
    tools = ["nmap", "ffuf", "gobuster", "sqlmap", "subfinder", "whatweb"]
    missing = []
    for t in tools:
        if subprocess.run(["which", t], capture_output=True).returncode != 0:
            missing.append(t)
    
    if missing:
        log_audit(f"Missing tools: {', '.join(missing)}")
    else:
        log_audit("All core tools present.")

def check_brain_apis():
    """Test Gemini and Groq API connectivity."""
    log_audit("Checking Brain API chain...")
    try:
        sys.path.insert(0, JARVIS_DIR)
        from dotenv import load_dotenv
        load_dotenv(os.path.join(JARVIS_DIR, ".env"))
        from brain import ask_gemini, ask_groq

        # Test Gemini
        try:
            ask_gemini([{"role": "user", "content": "ping"}], "Say PONG")
            log_audit("[✓] Gemini API: ONLINE")
        except Exception as e:
            log_audit(f"[✗] Gemini API: OFFLINE ({str(e)[:60]})")

        # Test Groq
        try:
            ask_groq([{"role": "user", "content": "ping"}], "Say PONG")
            log_audit("[✓] Groq API: ONLINE")
        except Exception as e:
            log_audit(f"[✗] Groq API: OFFLINE ({str(e)[:60]})")

    except Exception as e:
        log_audit(f"Brain API check failed: {e}")


def check_ollama():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            log_audit("Ollama is online.")
            # Check for required models
            models = ["deepseek-coder-v2:16b", "dolphin-mistral", "llava"]
            for m in models:
                if m in result.stdout:
                    log_audit(f"Model present: {m}")
                else:
                    log_audit(f"Model MISSING: {m}")
        else:
            log_audit("Ollama is OFFLINE or error listing models.")
    except Exception as e:
        log_audit(f"Ollama check failed: {e}")

def main():
    log_audit("--- DAILY AUDIT STARTED ---")

    # 1. Brain API Health (MOST IMPORTANT)
    check_brain_apis()

    # 2. Performance Dashboard
    run_cmd("from ctf.intelligence import print_performance_dashboard; print_performance_dashboard()", "Performance Dashboard")

    # 3. CVE Update
    run_cmd("from ctf.intelligence import update_cve_feed; update_cve_feed()", "CVE Feed Update")

    # 4. Tool Check
    check_tools()

    # 5. Ollama Check (optional, local backend)
    check_ollama()

    log_audit("--- DAILY AUDIT COMPLETE ---")
    log_audit("NEXT STEPS: python ctf_today.py  |  python exercise_room.py  |  python performance_dashboard.py")

if __name__ == "__main__":
    main()
