"""
ctf/osint.py — OSINT Intelligence Engine for JARVIS
Handles reconnaissance, infrastructure mapping, and data discovery.
"""

import subprocess
import re
from urllib.parse import urlparse

def _run(cmd: list, timeout: int = 60) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"[ERROR] {str(e)}"

def subdomain_enum(domain: str) -> str:
    """Map subdomains using subfinder."""
    return _run(["subfinder", "-d", domain, "-silent"])

def dns_recon(domain: str) -> str:
    """Extract TXT, SRV, and A records."""
    return _run(["dig", domain, "ANY", "+short"])

def wayback_dump(domain: str) -> str:
    """Query Wayback Machine for historical endpoints."""
    # Simplified version using curl; in a real env, use 'waybackurls' tool
    return _run(["curl", "-s", f"http://web.archive.org/cdx/search/cdx?url=*.{domain}&output=text&fl=original&collapse=urlkey"])

def dork_generator(target: str, scope: str = "login") -> str:
    """Generate search dorks for a target."""
    dorks = {
        "login": f"site:{target} inurl:login OR inurl:admin OR inurl:dashboard",
        "leaks": f"site:{target} filetype:sql OR filetype:env OR filetype:json OR filetype:txt",
        "configs": f"site:{target} intitle:index.of"
    }
    return dorks.get(scope, f"site:{target} {scope}")

def github_search(query: str) -> str:
    """Simulated search interface for GitHub OSINT."""
    return f"[OSINT] Querying GitHub for: {query} (Manual verification required)"

def shodan_lookup(ip: str) -> str:
    """Query shodan via cli."""
    return _run(["shodan", "host", ip])
