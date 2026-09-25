# tools/ctf_solver.py
# Lightweight CTF solver wrapper for JARVIS v4.0

import os
import json
import requests
from bs4 import BeautifulSoup

def solve_web_challenge(name, url, ctf_name, description):
    """
    Lightweight web challenge recon and solver bridge.
    Used as fallback when autonomous solver is unavailable.
    """
    recon_data = {}
    if url:
        try:
            r = requests.get(url, timeout=10)
            recon_data = {
                "status": r.status_code,
                "headers": dict(r.headers),
                "title": BeautifulSoup(r.text, "html.parser").title.string if "html" in r.headers.get("Content-Type", "") else ""
            }
        except:
            recon_data = {"error": "Target unreachable"}

    return {
        "likely_type": "web",
        "writeups": [],
        "recon": recon_data,
        "hacktricks": search_hacktricks("web"),
        "payloads": generate_payloads("web")
    }

def generate_payloads(vuln_type):
    """Simple payload generator for common CTF vulns"""
    payloads = {
        "sqli": ["' OR 1=1--", "admin' --", "' UNION SELECT NULL,NULL--"],
        "xss": ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>"],
        "lfi": ["../../../../etc/passwd", "php://filter/convert.base64-encode/resource=index.php"],
        "ssti": ["{{7*7}}", "${7*7}", "<%= 7*7 %>"],
        "command_injection": ["; id", "| id", "`id`"],
        "web": ["admin", "password", "flag{test}"]
    }
    return payloads.get(vuln_type.lower(), ["Check HackTricks for payloads"])

def search_hacktricks(query):
    """Simulated HackTricks search (bridge to deeper RAG if needed)"""
    return {
        "title": f"HackTricks {query}",
        "content": f"Searching HackTricks for {query}... (Use ctf-hacktricks command for full details)"
    }

def identify_challenge_type(text):
    """Basic keyword-based category detection"""
    text = text.lower()
    if any(k in text for k in ["sql", "login", "cookie", "http", "url", "web"]): return "web"
    if any(k in text for k in ["rsa", "aes", "cipher", "crypto"]): return "crypto"
    if any(k in text for k in ["buffer", "overflow", "pwn", "rop"]): return "pwn"
    if any(k in text for k in ["file", "image", "stego", "exif"]): return "forensics"
    if any(k in text for k in ["binary", "elf", "exe", "asm"]): return "rev"
    return "misc"
