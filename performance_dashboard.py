#!/usr/bin/env python3
"""
performance_dashboard.py — JARVIS Performance Dashboard
Visual terminal dashboard showing JARVIS's CTF stats and brain health.

From jarvisplan.txt: "performance dashboard"

Shows:
  - CTF solve rate by category
  - Brain API usage (Gemini/Groq/Local)
  - Training room stats
  - Today's readiness score
  - Recent solve history
"""

import os
import sys
import json
from datetime import datetime, date
from typing import Optional

JARVIS_DIR = os.path.expanduser("~/jarvis")
if JARVIS_DIR not in sys.path:
    sys.path.insert(0, JARVIS_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(JARVIS_DIR, ".env"))

# ── Colors ────────────────────────────────────────────────────────────────────
G  = "\033[92m"
Y  = "\033[93m"
R  = "\033[91m"
C  = "\033[96m"
B  = "\033[94m"
M  = "\033[95m"
W  = "\033[1;97m"
DIM= "\033[2m"
NC = "\033[0m"

def bar(pct: float, width: int = 20, fill="█", empty="░") -> str:
    filled = int(pct / 100 * width)
    return fill * filled + empty * (width - filled)

def color_pct(pct: float) -> str:
    c = G if pct >= 70 else Y if pct >= 40 else R
    return f"{c}{pct:.0f}%{NC}"


def check_brain_health() -> dict:
    """Test all brain APIs and return status."""
    results = {}

    # Gemini
    try:
        from brain import ask_gemini
        r = ask_gemini([{"role": "user", "content": "ping"}], "Say: PONG")
        results["gemini"] = {"status": "✅ ONLINE", "ok": True}
    except Exception as e:
        results["gemini"] = {"status": f"❌ {str(e)[:40]}", "ok": False}

    # Groq
    try:
        from brain import ask_groq
        r = ask_groq([{"role": "user", "content": "ping"}], "Say: PONG")
        results["groq"] = {"status": "✅ ONLINE", "ok": True}
    except Exception as e:
        results["groq"] = {"status": f"❌ {str(e)[:40]}", "ok": False}

    # Local Ollama
    try:
        import subprocess
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            model_count = len([l for l in out.stdout.splitlines() if l.strip() and "NAME" not in l])
            results["ollama"] = {"status": f"✅ ONLINE ({model_count} models)", "ok": True}
        else:
            results["ollama"] = {"status": "⚠️  No models / offline", "ok": False}
    except Exception as e:
        results["ollama"] = {"status": f"❌ {str(e)[:40]}", "ok": False}

    return results


def check_ctf_tools() -> dict:
    """Check CTF tool availability."""
    import subprocess
    tools = {
        "nmap": "port scanner",
        "ffuf": "web fuzzer",
        "gobuster": "dir bruteforce",
        "sqlmap": "SQLi tester",
        "binwalk": "firmware analysis",
        "exiftool": "metadata extractor",
        "steghide": "steganography",
        "john": "password cracker",
        "hashcat": "GPU hash cracking",
    }
    results = {}
    for tool, desc in tools.items():
        ok = subprocess.run(["which", tool], capture_output=True).returncode == 0
        results[tool] = {"desc": desc, "ok": ok}
    return results


def load_training_stats() -> dict:
    """Load stats from exercise room log."""
    log_path = os.path.join(JARVIS_DIR, "memory_logs/exercise_room.jsonl")
    if not os.path.exists(log_path):
        return {"total": 0, "correct": 0, "categories": {}, "recent": []}

    records = []
    with open(log_path) as f:
        for line in f:
            try:
                records.append(json.loads(line.strip()))
            except:
                pass

    cats = {}
    for r in records:
        cat = r.get("category", "misc")
        if cat not in cats:
            cats[cat] = {"total": 0, "correct": 0}
        cats[cat]["total"] += 1
        if r.get("correct"):
            cats[cat]["correct"] += 1

    return {
        "total": len(records),
        "correct": sum(1 for r in records if r.get("correct")),
        "avg_score": sum(r.get("score", 0) for r in records) / len(records) if records else 0,
        "categories": cats,
        "recent": records[-5:] if records else []
    }


def load_solve_history() -> list:
    """Load CTF solve history from JARVIS memory."""
    db_path = os.path.join(JARVIS_DIR, "memory/ctf_sessions.db")
    history = []
    try:
        import sqlite3
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT * FROM sessions ORDER BY timestamp DESC LIMIT 10")
            rows = cur.fetchall()
            conn.close()
            history = rows
    except:
        pass
    return history


def compute_readiness_score(brain: dict, tools: dict, training: dict) -> int:
    """
    Compute today's readiness score (0-100).
    Weighted: Brain 40% + Tools 30% + Training 30%
    """
    brain_ok = sum(1 for v in brain.values() if v["ok"])
    brain_score = (brain_ok / len(brain)) * 100 if brain else 0

    tools_ok = sum(1 for v in tools.values() if v["ok"])
    tools_score = (tools_ok / len(tools)) * 100 if tools else 0

    training_score = training.get("avg_score", 0)

    # Weight: Brain APIs most important for autonomous solving
    readiness = int(brain_score * 0.40 + tools_score * 0.30 + training_score * 0.30)
    return readiness


def print_dashboard():
    """Print the full performance dashboard."""
    width = 64

    print(f"\n{C}╔{'═'*width}╗")
    print(f"║{W}{'🔮  JARVIS PERFORMANCE DASHBOARD':^{width}}{C}║")
    print(f"║{DIM}{datetime.now().strftime('%A, %B %d %Y  %H:%M'):^{width}}{C}║")
    print(f"╚{'═'*width}╝{NC}\n")

    # ── Brain Health ──────────────────────────────────────────────────────
    print(f"{M}  ▶  BRAIN API STATUS{NC}")
    print(f"  {'─'*width}")
    print(f"  Checking APIs (this takes ~5s)...", end="\r")
    brain = check_brain_health()

    api_map = [
        ("gemini", "Gemini 2.5 Flash", "Primary (1500 req/day)"),
        ("groq",   "Groq Llama-3.3",  "Fallback (14400 req/day)"),
        ("ollama", "Local Ollama",     "Offline backup"),
    ]
    for key, name, note in api_map:
        info = brain.get(key, {})
        status = info.get("status", "❓ Unknown")
        color = G if info.get("ok") else R
        print(f"  {color}{name:<25}{NC} {status:<30} {DIM}{note}{NC}")
    print()

    # ── CTF Tool Check ────────────────────────────────────────────────────
    print(f"{M}  ▶  CTF ARSENAL STATUS{NC}")
    print(f"  {'─'*width}")
    tools = check_ctf_tools()
    row = []
    for tool, info in tools.items():
        c = G if info["ok"] else R
        row.append(f"{c}{'✓' if info['ok'] else '✗'} {tool}{NC}")
        if len(row) == 3:
            print(f"  {'  '.join(row)}")
            row = []
    if row:
        print(f"  {'  '.join(row)}")
    print()

    # ── Training Stats ────────────────────────────────────────────────────
    print(f"{M}  ▶  TRAINING ROOM STATS{NC}")
    print(f"  {'─'*width}")
    training = load_training_stats()

    if training["total"] == 0:
        print(f"  {Y}No training rounds yet. Run: python exercise_room.py{NC}")
    else:
        total = training["total"]
        correct = training["correct"]
        avg = training.get("avg_score", 0)
        pct = correct / total * 100 if total else 0

        print(f"  Rounds completed: {W}{total}{NC}")
        print(f"  Overall accuracy: {color_pct(pct)} ({correct}/{total})")
        print(f"  Average score:    {color_pct(avg)}")
        print()

        if training["categories"]:
            print(f"  {W}By Category:{NC}")
            for cat, stats in sorted(training["categories"].items()):
                p = stats["correct"] / stats["total"] * 100
                b = bar(p, 15)
                c = G if p >= 70 else Y if p >= 40 else R
                print(f"  {cat:<12} {c}{b}{NC} {p:.0f}% ({stats['correct']}/{stats['total']})")
    print()

    # ── Readiness Score ───────────────────────────────────────────────────
    tools_check = check_ctf_tools() if 'tools' not in dir() else tools
    readiness = compute_readiness_score(brain, tools, training)
    color = G if readiness >= 75 else Y if readiness >= 50 else R

    print(f"{M}  ▶  TODAY'S READINESS SCORE{NC}")
    print(f"  {'─'*width}")
    print(f"  {color}{bar(readiness, 30)} {readiness}/100{NC}")

    if readiness >= 75:
        print(f"  {G}🟢 READY FOR BATTLE — All systems nominal!{NC}")
    elif readiness >= 50:
        print(f"  {Y}🟡 PARTIALLY READY — Some issues to fix{NC}")
    else:
        print(f"  {R}🔴 NOT READY — Critical issues found{NC}")

    # Recommendations
    print(f"\n  {W}💡 Recommendations:{NC}")
    if not brain.get("gemini", {}).get("ok"):
        print(f"  {R}• Fix Gemini API key in ~/jarvis/.env{NC}")
    if not brain.get("groq", {}).get("ok"):
        print(f"  {R}• Fix Groq API key in ~/jarvis/.env{NC}")
    missing_tools = [t for t, v in tools.items() if not v["ok"]]
    if missing_tools:
        print(f"  {Y}• Install missing tools: {', '.join(missing_tools[:4])}{NC}")
    if training["total"] < 5:
        print(f"  {B}• Run training rounds: python exercise_room.py --batch 5{NC}")
    if training.get("avg_score", 0) < 50:
        print(f"  {B}• Practice more: python exercise_room.py --category web{NC}")
    if readiness >= 75 and training["total"] >= 5:
        print(f"  {G}• Start today's CTF: python ctf_today.py{NC}")

    print(f"\n{C}╔{'═'*width}╗")
    print(f"║{DIM}{'JARVIS v5.1  |  Autonomous Cybersecurity AI':^{width}}{C}║")
    print(f"╚{'═'*width}╝{NC}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="JARVIS Performance Dashboard")
    parser.add_argument("--quick", action="store_true", help="Skip API tests (faster)")
    args = parser.parse_args()

    if args.quick:
        # Skip brain tests for speed
        training = load_training_stats()
        tools = check_ctf_tools()
        print_dashboard.__globals__["check_brain_health"] = lambda: {
            "gemini": {"status": "⏩ skipped", "ok": True},
            "groq":   {"status": "⏩ skipped", "ok": True},
            "ollama": {"status": "⏩ skipped", "ok": True},
        }

    print_dashboard()
