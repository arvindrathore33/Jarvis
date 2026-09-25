#!/usr/bin/env python3
"""
exercise_room.py — JARVIS Autonomous Training Room
Generates fresh CTF challenges using Gemini/Groq and trains JARVIS to solve them.

From jarvisplan.txt: "making an exercise room for jarvis where he can train
automatically by using gemini and claude"

Features:
  - Generates realistic CTF challenges via Gemini API
  - Trains JARVIS's solver on generated challenges
  - Scores performance and logs to memory
  - Builds a track record for improvement

Usage:
    python exercise_room.py              # interactive mode
    python exercise_room.py --batch 5   # run 5 training rounds
    python exercise_room.py --category web  # train specific category
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime
from typing import Optional

# Add jarvis dir to path
JARVIS_DIR = os.path.expanduser("~/jarvis")
if JARVIS_DIR not in sys.path:
    sys.path.insert(0, JARVIS_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(JARVIS_DIR, ".env"))

# ── Colors ────────────────────────────────────────────────────────────────────
G  = "\033[92m"  # green
Y  = "\033[93m"  # yellow
R  = "\033[91m"  # red
C  = "\033[96m"  # cyan
B  = "\033[94m"  # blue
M  = "\033[95m"  # magenta
W  = "\033[97m"  # white
NC = "\033[0m"   # reset

BANNER = f"""
{C}╔══════════════════════════════════════════════════════════╗
║          🏋️  JARVIS EXERCISE ROOM  🏋️                    ║
║      Autonomous CTF Training via Gemini + Groq            ║
╚══════════════════════════════════════════════════════════╝{NC}
"""

# ── Challenge Templates (used as generation seeds) ────────────────────────────
CHALLENGE_SEEDS = {
    "web": [
        "SQL injection in login form",
        "Broken JWT authentication",
        "SSTI in Flask template",
        "IDOR in user profile API",
        "XSS stored in comment field",
        "Cookie session hijacking",
        "Directory traversal to read /flag.txt",
        "SSRF to internal metadata service",
        "XXE in XML upload endpoint",
        "Command injection in ping utility",
        "Open redirect to steal OAuth tokens",
        "Race condition in bank transfer",
        "GraphQL introspection leak",
        "HTTP request smuggling",
        "Prototype pollution in Node.js",
    ],
    "crypto": [
        "Classic Caesar cipher with known plaintext",
        "RSA with small exponent e=3",
        "XOR cipher with repeating key",
        "Base64 encoded flag inside base64",
        "Vigenere cipher with short key",
        "MD5 hash cracking with rockyou",
        "AES-ECB mode block swap attack",
        "LCG random number predictor",
        "OTP reuse with two ciphertexts",
        "RSA common modulus attack",
    ],
    "forensics": [
        "PNG with hidden data in LSB",
        "PCAP with credentials in HTTP traffic",
        "ZIP file with password in comment",
        "PDF with hidden text layer",
        "EXIF metadata with GPS coordinates",
        "Audio steganography with spectral analysis",
        "Memory dump with flag in process",
        "Binwalk on JPEG with embedded ZIP",
        "Strings in binary with encoded flag",
        "Network capture with FTP credentials",
    ],
    "misc": [
        "Python sandbox escape",
        "Brainfuck code with hidden message",
        "QR code with obfuscated data",
        "Git history with deleted flag",
        "Regex bypass in input validation",
        "Pyjail escape via builtins",
        "Morse code in audio file",
        "Base conversion chain",
        "Whitespace encoding in source",
        "URL encoding bypass",
    ]
}

LOG_DIR = os.path.join(JARVIS_DIR, "memory_logs")
TRAINING_LOG = os.path.join(LOG_DIR, "exercise_room.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)


# ── Challenge Generator via Brain ─────────────────────────────────────────────
def generate_challenge(category: str, difficulty: str = "medium", brain_func=None) -> dict:
    """
    Uses Gemini/Groq to generate a realistic CTF challenge + solution.
    Returns: {name, description, category, flag, hints, solution_steps}
    """
    if brain_func is None:
        from brain import jarvis_brain
        brain_func = jarvis_brain

    seed = random.choice(CHALLENGE_SEEDS.get(category, CHALLENGE_SEEDS["misc"]))
    flag = f"picoCTF{{training_{category}_{random.randint(1000,9999)}}}"

    prompt = f"""Generate a realistic CTF training challenge with these requirements:

Category: {category}
Difficulty: {difficulty}
Theme: {seed}
Flag (must use exactly): {flag}

Return ONLY valid JSON in this format:
{{
  "name": "Challenge Name",
  "description": "Full challenge description including any URLs, files, or context. The flag {flag} should be hidden inside the challenge environment, not visible in the description.",
  "category": "{category}",
  "difficulty": "{difficulty}",
  "flag": "{flag}",
  "hints": ["hint 1", "hint 2"],
  "solution_steps": ["step 1: ...", "step 2: ...", "step 3: find the flag"],
  "tools_needed": ["tool1", "tool2"],
  "learning_objective": "What skill this teaches"
}}

Make the challenge realistic and educational. The description should feel like a real CTF challenge."""

    try:
        reply, provider = brain_func(
            [{"role": "user", "content": prompt}],
            "You are a CTF challenge designer. Output only valid JSON, no markdown."
        )
        # Parse JSON from reply
        json_match = __import__("re").search(r'\{.*\}', reply, __import__("re").DOTALL)
        if json_match:
            challenge = json.loads(json_match.group(0))
            challenge["generated_by"] = provider
            challenge["generated_at"] = datetime.now().isoformat()
            return challenge
    except Exception as e:
        print(f"{Y}[EXERCISE] Challenge generation error: {e}{NC}")

    # Fallback: hand-crafted challenge
    return {
        "name": f"Training: {seed}",
        "description": f"Solve this {category} challenge involving {seed}. Flag: HIDDEN",
        "category": category,
        "difficulty": difficulty,
        "flag": flag,
        "hints": [f"Think about {seed.split()[0]} techniques"],
        "solution_steps": [f"Research {seed}", "Apply the technique", "Extract the flag"],
        "tools_needed": [],
        "learning_objective": seed,
        "generated_by": "fallback",
        "generated_at": datetime.now().isoformat()
    }


# ── Training Round ─────────────────────────────────────────────────────────────
def run_training_round(category: str = None, difficulty: str = "medium", verbose: bool = True) -> dict:
    """
    One full training cycle:
    1. Generate challenge with Gemini
    2. Try to solve it with JARVIS solver
    3. Score + log
    """
    from brain import jarvis_brain

    if category is None:
        category = random.choice(list(CHALLENGE_SEEDS.keys()))

    if verbose:
        print(f"\n{C}{'─'*60}{NC}")
        print(f"{B}[TRAINING] Round: {category.upper()} | Difficulty: {difficulty}{NC}")

    # Step 1: Generate challenge
    if verbose:
        print(f"{Y}[STEP 1] Generating challenge via Gemini...{NC}")
    challenge = generate_challenge(category, difficulty, jarvis_brain)
    if verbose:
        print(f"{G}[✓] Challenge: {challenge.get('name', '?')}{NC}")
        print(f"[*] Learning objective: {challenge.get('learning_objective', '?')}")

    # Step 2: Try AI solve (using the solution steps as guidance for the brain)
    if verbose:
        print(f"\n{Y}[STEP 2] JARVIS solving...{NC}")

    start_time = time.time()
    solved = False
    jarvis_flag = None
    jarvis_reasoning = ""

    try:
        solve_prompt = f"""You are solving a CTF challenge.

Name: {challenge['name']}
Category: {challenge['category']}
Difficulty: {challenge['difficulty']}
Description: {challenge['description']}

Hints available: {', '.join(challenge.get('hints', []))}

Analyze this challenge step by step and attempt to find the flag.
The flag format is: picoCTF{{...}}
Think through: {', '.join(challenge.get('solution_steps', ['analyze', 'exploit', 'capture flag']))}

Provide your reasoning and the flag if found."""

        reply, provider = jarvis_brain(
            [{"role": "user", "content": solve_prompt}],
            f"You are JARVIS, an expert CTF solver specializing in {category} challenges."
        )
        jarvis_reasoning = reply

        # Check if JARVIS found the correct flag
        import re
        flags_found = re.findall(r'picoCTF\{[^}]+\}|CTF\{[^}]+\}|flag\{[^}]+\}', reply, re.IGNORECASE)
        for f in flags_found:
            if f == challenge["flag"] or category in f.lower():
                jarvis_flag = f
                solved = (f == challenge["flag"])
                break

        if verbose:
            print(f"{G if solved else R}[JARVIS] Reasoning preview:{NC}")
            print(f"  {reply[:300]}...")

    except Exception as e:
        jarvis_reasoning = f"Solver error: {e}"
        if verbose:
            print(f"{R}[ERROR] {e}{NC}")

    elapsed = time.time() - start_time

    # Step 3: Score
    correct = jarvis_flag == challenge["flag"]
    score = 100 if correct else (30 if jarvis_flag else 0)

    result = {
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "difficulty": difficulty,
        "challenge_name": challenge.get("name"),
        "flag_expected": challenge["flag"],
        "flag_found": jarvis_flag,
        "correct": correct,
        "score": score,
        "time_seconds": round(elapsed, 1),
        "generated_by": challenge.get("generated_by", "?"),
        "solution_steps": challenge.get("solution_steps", []),
        "tools_needed": challenge.get("tools_needed", []),
        "learning_objective": challenge.get("learning_objective"),
        "jarvis_reasoning_preview": jarvis_reasoning[:500],
    }

    # Step 4: Log
    with open(TRAINING_LOG, "a") as f:
        f.write(json.dumps(result) + "\n")

    if verbose:
        print(f"\n{C}{'─'*60}{NC}")
        status = f"{G}✓ CORRECT" if correct else f"{R}✗ INCORRECT"
        print(f"[RESULT] {status}{NC}")
        print(f"[RESULT] Expected: {challenge['flag']}")
        print(f"[RESULT] Found:    {jarvis_flag or 'None'}")
        print(f"[RESULT] Score: {score}/100 | Time: {elapsed:.1f}s")
        print(f"[RESULT] Generated by: {challenge.get('generated_by', '?').upper()}")

        # Show solution steps as learning material
        if not correct:
            print(f"\n{M}[LEARNING] How it should be solved:{NC}")
            for i, step in enumerate(challenge.get("solution_steps", []), 1):
                print(f"  {i}. {step}")

    return result


# ── Stats Dashboard ────────────────────────────────────────────────────────────
def show_training_stats():
    """Parse training log and show performance stats."""
    if not os.path.exists(TRAINING_LOG):
        print(f"{Y}No training history yet. Run some rounds first!{NC}")
        return

    records = []
    with open(TRAINING_LOG) as f:
        for line in f:
            try:
                records.append(json.loads(line.strip()))
            except:
                pass

    if not records:
        print("No records found.")
        return

    total = len(records)
    correct = sum(1 for r in records if r.get("correct"))
    avg_score = sum(r.get("score", 0) for r in records) / total
    avg_time = sum(r.get("time_seconds", 0) for r in records) / total

    print(f"\n{C}{'═'*60}")
    print(f"  📊  JARVIS TRAINING PERFORMANCE DASHBOARD")
    print(f"{'═'*60}{NC}")
    print(f"  Total rounds:   {total}")
    print(f"  Correct:        {G}{correct}{NC} / {total} ({correct/total*100:.0f}%)")
    print(f"  Avg score:      {avg_score:.0f}/100")
    print(f"  Avg time:       {avg_time:.1f}s / round")
    print()

    # Per-category stats
    cats = {}
    for r in records:
        cat = r.get("category", "misc")
        if cat not in cats:
            cats[cat] = {"total": 0, "correct": 0}
        cats[cat]["total"] += 1
        if r.get("correct"):
            cats[cat]["correct"] += 1

    print(f"  {W}Category Breakdown:{NC}")
    for cat, stats in sorted(cats.items()):
        pct = stats["correct"] / stats["total"] * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        color = G if pct >= 70 else Y if pct >= 40 else R
        print(f"  {cat:<12} {color}{bar}{NC} {pct:.0f}% ({stats['correct']}/{stats['total']})")

    # Recent 5 rounds
    print(f"\n  {W}Recent 5 Rounds:{NC}")
    for r in records[-5:]:
        status = f"{G}✓{NC}" if r.get("correct") else f"{R}✗{NC}"
        print(f"  {status} [{r.get('category','?'):10}] {r.get('challenge_name','?')[:40]:40} {r.get('score',0):3}pts")

    print(f"\n{C}{'═'*60}{NC}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description="JARVIS Exercise Room — CTF Auto-Trainer")
    parser.add_argument("--batch", type=int, default=1, help="Number of training rounds (default: 1)")
    parser.add_argument("--category", type=str, default=None,
                        choices=list(CHALLENGE_SEEDS.keys()) + [None],
                        help="Challenge category (default: random)")
    parser.add_argument("--difficulty", type=str, default="medium",
                        choices=["easy", "medium", "hard"],
                        help="Challenge difficulty (default: medium)")
    parser.add_argument("--stats", action="store_true", help="Show training stats only")
    parser.add_argument("--quiet", action="store_true", help="Less verbose output")

    args = parser.parse_args()

    if args.stats:
        show_training_stats()
        return

    results = []
    for i in range(args.batch):
        if args.batch > 1:
            print(f"\n{M}{'═'*60}")
            print(f"  ROUND {i+1}/{args.batch}")
            print(f"{'═'*60}{NC}")
        result = run_training_round(
            category=args.category,
            difficulty=args.difficulty,
            verbose=not args.quiet
        )
        results.append(result)

    if args.batch > 1:
        correct = sum(1 for r in results if r.get("correct"))
        avg = sum(r.get("score", 0) for r in results) / len(results)
        print(f"\n{C}{'═'*60}")
        print(f"  BATCH COMPLETE: {correct}/{args.batch} correct | Avg: {avg:.0f}/100")
        print(f"{'═'*60}{NC}")

    # Show updated stats
    show_training_stats()


if __name__ == "__main__":
    main()
