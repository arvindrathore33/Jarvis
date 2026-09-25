#!/usr/bin/env python3
"""
tools/ctf/ctf_engine.py — JARVIS CTF Auto-Router Engine
Automatically detects challenge type and routes to the right solver.

Challenge types handled:
  web       → web_master.py (25+ checks)
  crypto    → crypto_solver.py
  forensics → forensics_solver.py
  binary    → pwntools.py
  misc      → heuristic + brain fallback
  osint     → web search + OSINT tools

Usage:
    from tools.ctf.ctf_engine import CTFEngine
    engine = CTFEngine()
    result = engine.auto_solve("http://challenge.ctf.local:1337", description, category_hint)
"""

import os
import sys
import re
from typing import Optional

# ── Category keyword scoring ──────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "web": [
        "http", "website", "login", "cookie", "header", "sql", "xss", "csrf",
        "injection", "upload", "flask", "php", "jwt", "admin", "session",
        "url", "api", "endpoint", "server", "port 80", "port 443", "ssti",
        "ssrf", "xxe", "idor", "redirect", "graphql", "nosql", "smuggling",
        "prototype", "cors", "race condition", "websocket", "oauth"
    ],
    "crypto": [
        "cipher", "encrypt", "decrypt", "rsa", "aes", "base64", "caesar",
        "rot13", "xor", "hash", "md5", "sha", "vigenere", "morse", "hex",
        "binary", "encoding", "key", "plaintext", "ciphertext", "modular",
        "prime", "lcg", "lfsr", "elliptic", "otp", "padding oracle",
        "stream cipher", "block cipher"
    ],
    "forensics": [
        "file", "image", "png", "jpg", "jpeg", "wav", "mp3", "pdf", "zip",
        "pcap", "wireshark", "steganography", "stego", "metadata", "exif",
        "strings", "binwalk", "hidden", "audio", "video", "memory", "dump",
        "volatility", "network capture", "traffic", "disk", "partition"
    ],
    "binary": [
        "binary", "exploit", "overflow", "rop", "ret2", "shellcode", "libc",
        "buffer", "stack", "heap", "pwn", "gdb", "elf", "32-bit", "64-bit",
        "pwntools", "format string", "use after free", "uaf", "got", "plt",
        "rop chain", "canary", "aslr", "pie", "nx bit"
    ],
    "osint": [
        "osint", "open source", "social media", "username", "profile",
        "find", "locate", "investigate", "geolocation", "google", "linkedin",
        "twitter", "instagram", "github", "email", "phone", "person",
        "who is", "whois", "dns", "domain", "certificate"
    ],
    "misc": [
        "misc", "reversing", "reverse engineering", "disassemble", "decompile",
        "python", "javascript", "lua", "brainfuck", "esoteric", "qr code",
        "barcode", "maze", "game", "trivia", "sanity"
    ]
}


def detect_category(description: str, category_hint: str = "") -> tuple[str, float]:
    """
    Score each category based on keyword presence in description + hint.
    Returns (best_category, confidence_score).
    """
    text = (description + " " + category_hint).lower()
    scores = {}

    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        scores[cat] = score

    # Boost if category_hint explicitly matches
    if category_hint.lower() in CATEGORY_KEYWORDS:
        scores[category_hint.lower()] += 10

    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    confidence = scores[best] / total

    if scores[best] == 0:
        best = "misc"
        confidence = 0.1

    return best, confidence


def is_url(target: str) -> bool:
    return target.startswith("http://") or target.startswith("https://")


class CTFEngine:
    """
    Master auto-router for CTF challenge solving.
    Detects category → routes to best solver → returns flag or analysis.
    """

    def __init__(self, jarvis_dir: str = None):
        self.jarvis_dir = jarvis_dir or os.path.expanduser("~/jarvis")
        # Ensure jarvis dir is in path for imports
        if self.jarvis_dir not in sys.path:
            sys.path.insert(0, self.jarvis_dir)

    def auto_solve(
        self,
        target: str,
        description: str = "",
        category_hint: str = "",
        files: list = None,
        verbose: bool = True
    ) -> dict:
        """
        Full auto-solve pipeline:
          1. Detect category
          2. Route to appropriate solver
          3. Return result dict with flag (if found)
        """
        files = files or []
        category, confidence = detect_category(description, category_hint)

        if verbose:
            print(f"\n\033[96m[ENGINE] 🔍 Category detected: {category.upper()} (confidence: {confidence:.0%})\033[0m")
            print(f"[ENGINE] Target: {target}")

        result = {
            "category": category,
            "confidence": confidence,
            "target": target,
            "flag": None,
            "method": None,
            "output": "",
        }

        # ── Route to solver ──────────────────────────────────────────────
        try:
            if category == "web" and is_url(target):
                result.update(self._solve_web(target, description, verbose))
            elif category == "crypto":
                result.update(self._solve_crypto(target, description, files, verbose))
            elif category == "forensics":
                result.update(self._solve_forensics(target, files, verbose))
            elif category == "binary":
                result.update(self._solve_binary(target, files, verbose))
            elif category == "osint":
                result.update(self._solve_osint(target, description, verbose))
            else:
                # Misc / fallback → use the full CTFSolver
                result.update(self._solve_via_ai(target, description, category, files, verbose))

        except Exception as e:
            result["output"] = f"[ENGINE ERROR] {e}"
            if verbose:
                print(f"\033[91m[ENGINE] Error: {e}\033[0m")

        return result

    def _solve_web(self, url: str, description: str, verbose: bool) -> dict:
        """Run all 25 web checks via web_master."""
        if verbose:
            print("\033[94m[ENGINE] 🌐 Running Web Arsenal (25 checks)...\033[0m")
        try:
            from tools.ctf.web_master import main as web_main
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                sys.argv = ["web_master.py", url]
                web_main()
            output = buf.getvalue()
            flag = self._extract_flag(output)
            return {"flag": flag, "method": "web_master_25_checks", "output": output}
        except Exception as e:
            return {"flag": None, "method": "web_error", "output": str(e)}

    def _solve_crypto(self, target: str, description: str, files: list, verbose: bool) -> dict:
        """Try all crypto solvers."""
        if verbose:
            print("\033[94m[ENGINE] 🔐 Running Crypto Solver...\033[0m")
        try:
            from tools.ctf.crypto_solver import solve_all as crypto_solve_all
            # Try solving the description text as ciphertext
            ciphertext = description if description else target
            output = crypto_solve_all(ciphertext)
            flag = self._extract_flag(str(output))
            return {"flag": flag, "method": "crypto_solver", "output": str(output)}
        except Exception as e:
            return {"flag": None, "method": "crypto_error", "output": str(e)}

    def _solve_forensics(self, target: str, files: list, verbose: bool) -> dict:
        """Run forensics analysis on files."""
        if verbose:
            print("\033[94m[ENGINE] 🔬 Running Forensics Solver...\033[0m")
        if not files:
            # Try target as file path
            if os.path.exists(target):
                files = [target]
        try:
            from tools.ctf.forensics_solver import analyze_file
            outputs = []
            flags = []
            for f in files:
                out = analyze_file(f)
                outputs.append(str(out))
                flag = self._extract_flag(str(out))
                if flag:
                    flags.append(flag)
            return {
                "flag": flags[0] if flags else None,
                "method": "forensics_solver",
                "output": "\n".join(outputs)
            }
        except Exception as e:
            return {"flag": None, "method": "forensics_error", "output": str(e)}

    def _solve_binary(self, target: str, files: list, verbose: bool) -> dict:
        """Analyze binary with pwntools."""
        if verbose:
            print("\033[94m[ENGINE] 💣 Running Binary/PWN Analysis...\033[0m")
        binary = files[0] if files else target
        try:
            from tools.ctf.pwntools import run_checksec, generate_exploit_template
            checksec_out = run_checksec(binary) if os.path.exists(binary) else "Binary not found"
            template = generate_exploit_template(binary, 64) if os.path.exists(binary) else ""
            output = f"Checksec:\n{checksec_out}\n\nExploit Template:\n{template}"
            return {"flag": None, "method": "pwntools_analysis", "output": output}
        except Exception as e:
            return {"flag": None, "method": "binary_error", "output": str(e)}

    def _solve_osint(self, target: str, description: str, verbose: bool) -> dict:
        """OSINT search."""
        if verbose:
            print("\033[94m[ENGINE] 🕵️ Running OSINT tools...\033[0m")
        try:
            from tools.websearch import ddg_search
            query = f"{target} {description}"
            results = ddg_search(query)
            flag = self._extract_flag(str(results))
            return {"flag": flag, "method": "osint_search", "output": str(results)}
        except Exception as e:
            return {"flag": None, "method": "osint_error", "output": str(e)}

    def _solve_via_ai(self, target: str, description: str, category: str, files: list, verbose: bool) -> dict:
        """Fallback to full CTFSolver v2 with AI brain."""
        if verbose:
            print(f"\033[94m[ENGINE] 🤖 Routing to AI Solver (category: {category})...\033[0m")
        try:
            from ctf.solver_v2 import CTFSolver
            solver = CTFSolver()
            result = solver.solve(
                challenge_name=target,
                description=description,
                category=category,
                files=files
            )
            return result
        except Exception as e:
            return {"flag": None, "method": "ai_solver_error", "output": str(e)}

    @staticmethod
    def _extract_flag(text: str) -> Optional[str]:
        """Extract CTF flag from any text output."""
        patterns = [
            r'picoCTF\{[^}]+\}',
            r'CTF\{[^}]+\}',
            r'flag\{[^}]+\}',
            r'FLAG\{[^}]+\}',
            r'HTB\{[^}]+\}',
            r'THM\{[^}]+\}',
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(0)
        return None


# ── CLI usage ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ctf_engine.py <target_url_or_file> [category]")
        print("  target: URL (http://...) or file path or challenge name")
        print("  category: web/crypto/forensics/binary/osint/misc (auto-detected if omitted)")
        sys.exit(1)

    target = sys.argv[1]
    hint   = sys.argv[2] if len(sys.argv) > 2 else ""

    engine = CTFEngine()
    result = engine.auto_solve(target, category_hint=hint)

    print("\n" + "═"*60)
    if result.get("flag"):
        print(f"\033[92m[✓] FLAG FOUND: {result['flag']}\033[0m")
    else:
        print(f"\033[91m[✗] No flag found automatically\033[0m")
        print(f"[*] Category: {result['category']} ({result['confidence']:.0%})")
        print(f"[*] Output preview: {result.get('output','')[:500]}")
