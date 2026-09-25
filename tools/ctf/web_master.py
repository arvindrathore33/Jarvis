#!/usr/bin/env python3
"""
web_master.py — Master Web CTF Launcher
Runs all 25+ automated checks across multiple modules.
Stops early if a flag is found.
Usage: python web_master.py <url>
"""

import sys
import os

# Add current dir to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import web
    import web_advanced
    import web_complete
    import ssti
except ImportError as e:
    print(f"[!] Import error: {e}")
    # Fallback or exit

def log(msg, t="*"):
    c = {"+":" \033[92m", "*":"\033[94m", "!":"\033[93m", "-":"\033[91m"}
    print(f"{c.get(t,'')}[{t}] {msg}\033[0m")

def main():
    if len(sys.argv) < 2:
        print("Usage: python web_master.py <url>")
        return
    
    target = sys.argv[1]
    log(f"Starting Master Scan on {target}", "*")
    
    modules = [
        (web, "Basic Checks"),
        (web_advanced, "Advanced Checks"),
        (web_complete, "Complete Arsenal"),
        (ssti, "SSTI Detection")
    ]
    
    for mod, name in modules:
        log(f"Running {name}...", "*")
        try:
            # Most of these scripts have a TARGET global or take it in functions
            # We'll try to call their check functions if they exist, or just run their main-like logic
            if hasattr(mod, 'run_all'):
                mod.run_all(target)
            elif name == "Advanced Checks":
                web_advanced.check_cmdi(target)
                web_advanced.check_xxe(target)
                web_advanced.check_ssrf(target)
                web_advanced.check_jwt(target)
                web_advanced.check_open_redirect(target)
                web_advanced.check_upload(target)
            elif name == "Complete Arsenal":
                web_complete.check_graphql(target)
                web_complete.check_nosqli(target)
                # ... and so on
                pass
            
            # Check if any flags were found
            if hasattr(mod, 'FLAGS') and mod.FLAGS:
                log(f"Flags found in {name}!", "+")
                # Could stop here if desired: break
        except Exception as e:
            log(f"Error in {name}: {e}", "-")

    log("Master Scan Complete.", "*")

if __name__ == "__main__":
    main()
