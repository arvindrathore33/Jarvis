#!/usr/bin/env python3
"""
ctf_today.py — JARVIS Daily CTF Launcher
One command to start today's CTF challenge with full autonomous support.

Usage:
    python ctf_today.py                         # Interactive mode
    python ctf_today.py --url http://chall:1337 # Direct URL solve
    python ctf_today.py --pico                  # Fetch from PicoCTF
    python ctf_today.py --file challenge.png    # File challenge
    python ctf_today.py --text "ciphertext"     # Crypto/misc

Features:
    - Auto-detects challenge type
    - Fetches PicoCTF challenges if --pico is set
    - Runs full autonomous solver pipeline
    - Auto-submits flag if found
    - Saves writeup + trains memory
"""

import os
import sys
import argparse
import time
from datetime import datetime

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

BANNER = f"""
{C}╔══════════════════════════════════════════════════════════════╗
║    ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗                  ║
║    ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝                  ║
║    ██║███████║██████╔╝██║   ██║██║███████╗                  ║
║    ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║                  ║
║    ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║  CTF TODAY       ║
║    ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝  {datetime.now().strftime('%Y-%m-%d')}  ║
╚══════════════════════════════════════════════════════════════╝{NC}
"""


def fetch_pico_challenges() -> list:
    """Fetch today's unsolved PicoCTF challenges."""
    print(f"{B}[PICO] Fetching challenges from PicoCTF...{NC}")
    try:
        from ctf.platforms import PicoCTFClient
        user = os.getenv("PICOCTF_USER", "")
        passwd = os.getenv("PICOCTF_PASS", "")
        if not user or not passwd:
            print(f"{R}[PICO] No credentials in .env! Set PICOCTF_USER and PICOCTF_PASS{NC}")
            return []
        client = PicoCTFClient(username=user, password=passwd)
        challenges = client.get_challenges()
        print(f"{G}[PICO] Fetched {len(challenges)} challenges{NC}")
        return challenges
    except Exception as e:
        print(f"{R}[PICO] Error: {e}{NC}")
        return []


def display_challenge_menu(challenges: list) -> dict:
    """Let user pick a challenge from the list."""
    print(f"\n{W}Available Challenges:{NC}")
    print(f"{'─'*60}")
    for i, c in enumerate(challenges[:20], 1):
        cat = c.get("category", "?")
        pts = c.get("value", "?")
        name = c.get("name", "?")
        solved = "✓" if c.get("solved_by_me", False) else " "
        print(f"  {G if solved=='✓' else NC}{i:2}. [{solved}] {name:<35} {cat:<15} {pts}pts{NC}")

    print(f"\n  0. Manual entry (paste description)")
    choice = input(f"\n{C}Select challenge (number): {NC}").strip()

    if choice == "0":
        return {
            "name": input("Challenge name: "),
            "description": input("Description/URL: "),
            "category": input("Category (web/crypto/forensics/misc): "),
            "id": None
        }

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(challenges):
            return challenges[idx]
    except:
        pass
    return {}


def run_ctf_solve(target: str, description: str, category: str,
                  files: list = None, challenge_id: int = None,
                  pico_client=None, verbose: bool = True) -> dict:
    """
    Full autonomous CTF solve pipeline.
    """
    files = files or []

    print(f"\n{C}{'═'*60}")
    print(f"  🎯 TARGET: {target}")
    print(f"  📂 CATEGORY: {category.upper() if category else 'AUTO-DETECT'}")
    print(f"  🕐 STARTED: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═'*60}{NC}")

    start = time.time()

    # ── Step 1: Auto-detect & route ───────────────────────────────────────
    try:
        from tools.ctf.ctf_engine import CTFEngine
        engine = CTFEngine()
        result = engine.auto_solve(
            target=target,
            description=description,
            category_hint=category,
            files=files,
            verbose=verbose
        )
    except ImportError:
        # Fallback to direct CTFSolver
        from ctf.solver_v2 import CTFSolver
        solver = CTFSolver()
        result = solver.solve(
            challenge_name=target,
            description=description,
            category=category or "misc",
            files=files
        )

    elapsed = time.time() - start

    # ── Step 2: Report ────────────────────────────────────────────────────
    flag = result.get("flag")
    print(f"\n{C}{'═'*60}")
    print(f"  ⏱️  Elapsed: {elapsed:.1f}s")

    if flag:
        print(f"  {G}🚩 FLAG FOUND: {flag}{NC}")
    else:
        print(f"  {R}❌ No flag found automatically{NC}")
        print(f"  {Y}💡 Try manual analysis or ask JARVIS: python main.py{NC}")

    # ── Step 3: Auto-submit if PicoCTF ───────────────────────────────────
    if flag and pico_client and challenge_id:
        print(f"\n{B}[PICO] Auto-submitting flag...{NC}")
        try:
            sub = pico_client.submit_flag(challenge_id, flag)
            if sub.get("success"):
                print(f"{G}[PICO] ✅ FLAG ACCEPTED! Challenge solved!{NC}")
            else:
                print(f"{R}[PICO] ❌ Flag rejected: {sub.get('message', '')}{NC}")
            result["submission"] = sub
        except Exception as e:
            print(f"{R}[PICO] Submit error: {e}{NC}")

    # ── Step 4: Save writeup ──────────────────────────────────────────────
    writeup_dir = os.path.join(JARVIS_DIR, "output/writeups")
    os.makedirs(writeup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    safe_name = "".join(c if c.isalnum() else "_" for c in (target or "unknown"))[:30]
    writeup_path = os.path.join(writeup_dir, f"ctf_{safe_name}_{ts}.md")

    with open(writeup_path, "w") as f:
        f.write(f"# CTF Writeup: {target}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Category:** {result.get('category', category)}\n")
        f.write(f"**Confidence:** {result.get('confidence', 0):.0%}\n")
        f.write(f"**Flag:** `{flag or 'NOT FOUND'}`\n")
        f.write(f"**Time:** {elapsed:.1f}s\n\n")
        f.write(f"## Description\n{description}\n\n")
        f.write(f"## Analysis\n{result.get('output', '')[:3000]}\n\n")
        if flag:
            f.write(f"## Result\n🚩 **FLAG: `{flag}`**\n")

    print(f"\n{DIM}[WRITEUP] Saved: {writeup_path}{NC}")
    print(f"{C}{'═'*60}{NC}\n")

    return result


def interactive_mode():
    """Interactive CTF solve session."""
    print(BANNER)

    print(f"{W}How do you want to start?{NC}")
    print(f"  1. Paste challenge description (manual)")
    print(f"  2. Enter a URL to attack")
    print(f"  3. Analyze a file")
    print(f"  4. Fetch from PicoCTF (auto-login)")
    print(f"  5. Run training round first")
    print(f"  0. Exit")

    choice = input(f"\n{C}> {NC}").strip()

    if choice == "1":
        name = input(f"{C}Challenge name: {NC}").strip()
        desc = input(f"{C}Paste description (or URL/text): {NC}").strip()
        cat  = input(f"{C}Category (web/crypto/forensics/binary/misc/auto): {NC}").strip()
        run_ctf_solve(name, desc, cat if cat != "auto" else "")

    elif choice == "2":
        url  = input(f"{C}Target URL: {NC}").strip()
        desc = input(f"{C}Challenge description (optional): {NC}").strip()
        run_ctf_solve(url, desc, "web")

    elif choice == "3":
        path = input(f"{C}File path: {NC}").strip()
        desc = input(f"{C}Challenge description (optional): {NC}").strip()
        cat  = input(f"{C}Category (forensics/crypto/binary): {NC}").strip()
        if os.path.exists(path):
            run_ctf_solve(path, desc, cat, files=[path])
        else:
            print(f"{R}File not found: {path}{NC}")

    elif choice == "4":
        challenges = fetch_pico_challenges()
        if challenges:
            chall = display_challenge_menu(challenges)
            if chall:
                # Try to get full detail
                try:
                    from ctf.platforms import PicoCTFClient
                    client = PicoCTFClient(
                        username=os.getenv("PICOCTF_USER", ""),
                        password=os.getenv("PICOCTF_PASS", "")
                    )
                    if chall.get("id"):
                        detail = client.get_challenge_detail(chall["id"])
                        desc = detail.get("description", chall.get("description", ""))
                    else:
                        desc = chall.get("description", "")

                    run_ctf_solve(
                        target=chall.get("name", "challenge"),
                        description=desc,
                        category=chall.get("category", ""),
                        challenge_id=chall.get("id"),
                        pico_client=client
                    )
                except Exception as e:
                    print(f"{R}Error: {e}{NC}")

    elif choice == "5":
        print(f"\n{M}Starting 1 training round...{NC}")
        from exercise_room import run_training_round
        run_training_round(verbose=True)

    elif choice == "0":
        print(f"{DIM}Goodbye, Arvind.{NC}")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="JARVIS CTF Today — One-click CTF solver"
    )
    parser.add_argument("--url",  type=str, help="Target URL to attack")
    parser.add_argument("--file", type=str, help="Challenge file to analyze")
    parser.add_argument("--text", type=str, help="Challenge text/ciphertext")
    parser.add_argument("--desc", type=str, default="", help="Challenge description")
    parser.add_argument("--cat",  type=str, default="", help="Category hint")
    parser.add_argument("--pico", action="store_true", help="Fetch from PicoCTF")
    parser.add_argument("--name", type=str, default="Today's Challenge", help="Challenge name")
    args = parser.parse_args()

    print(BANNER)

    # ── Direct mode ───────────────────────────────────────────────────────
    if args.url:
        run_ctf_solve(args.url, args.desc, args.cat or "web")

    elif args.file:
        if not os.path.exists(args.file):
            print(f"{R}File not found: {args.file}{NC}")
            sys.exit(1)
        run_ctf_solve(args.file, args.desc, args.cat or "forensics", files=[args.file])

    elif args.text:
        run_ctf_solve(args.text, args.desc, args.cat or "crypto")

    elif args.pico:
        challenges = fetch_pico_challenges()
        if challenges:
            chall = display_challenge_menu(challenges)
            if chall:
                run_ctf_solve(
                    target=chall.get("name", "challenge"),
                    description=chall.get("description", ""),
                    category=chall.get("category", ""),
                    challenge_id=chall.get("id")
                )
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
