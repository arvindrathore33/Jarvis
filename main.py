"""
JARVIS v4.0 — Elite Cybersecurity AI + Full CTFAgent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Merged: v3.0 pentest tools + CTFAgent task tree + swarm solver
Goal  : Compete with Claude Mythos for cybersecurity
Brain : Claude API → Groq 70B free → Local Ollama
Author: Arvind | Arch Linux | Python 3.11
"""

import ollama
import os
import sys
import json
import subprocess
from dotenv import load_dotenv
from datetime import datetime

# ── Utility for tool execution ────────────────────────────────────────────────
def safe_run(fn, *args, fallback="[TOOL ERROR] Could not complete", **kwargs):
    import subprocess
    try:
        return fn(*args, **kwargs)
    except ConnectionError as e:
        print(f"\033[1;31m[CONNECTION]\033[0m {e}")
        return fallback
    except EOFError:
        print(f"\033[1;31m[EOF]\033[0m Session interrupted — continuing")
        return fallback
    except FileNotFoundError as e:
        tool = str(e).split("'")[1] if "'" in str(e) else "tool"
        print(f"\033[1;31m[MISSING]\033[0m {tool} not installed")
        print(f"  Install: sudo pacman -S {tool} or paru -S {tool}")
        return fallback
    except subprocess.TimeoutExpired:
        print(f"\033[1;31m[TIMEOUT]\033[0m Tool timed out — try with smaller scope")
        return fallback
    except Exception as e:
        print(f"\033[1;31m[ERROR]\033[0m {type(e).__name__}: {e}")
        return fallback

# ── Memory ────────────────────────────────────────────────────────────────────
from memory.database import save_session, save_finding, get_findings, init_db
from memory.learning import store_finding, recall_similar

# ── Scan tools ────────────────────────────────────────────────────────────────
from tools.scanner import (run_nmap, run_ffuf, run_gobuster,
                            run_sqlmap, run_subfinder, run_whatweb)

# ── Browser recon ─────────────────────────────────────────────────────────────
from tools.browser import browse_target, screenshot_target, intercept_requests

# ── Threat intel ──────────────────────────────────────────────────────────────
from tools.websearch import (ddg_search, search_cve, search_exploitdb,
                              fetch_url, shodan_lookup, shodan_search,
                              vt_check_hash, vt_check_url, vt_check_ip,
                              abuseipdb_check)

# ── CTF web solver (lightweight) ──────────────────────────────────────────────
from tools.ctf_solver import (solve_web_challenge, generate_payloads,
                               search_hacktricks)

# ── Agents ────────────────────────────────────────────────────────────────────
from agents.crew import run_full_assessment

# ── Voice ─────────────────────────────────────────────────────────────────────
from speak import speak

load_dotenv()
init_db()

MODEL = os.getenv("JARVIS_MODEL", "qwen2.5:1.5b")

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are JARVIS, a sophisticated and highly intelligent AI assistant running {MODEL}.
While you are an elite specialist in cybersecurity, penetration testing, and threat intelligence, 
you are also a helpful, talkative, and proactive personal assistant for all general tasks.

Personality:
- Be polite, sophisticated, and slightly witty (inspired by Tony Stark's JARVIS).
- Be conversational and "talkative"—provide context, explanations, and helpful insights.
- Do not restrict yourself to 3 lines; provide comprehensive yet clear responses.
- Use phrases like "Certainly, sir," "At your service," or "System initialized."

Cybersecurity Core:
- You never refuse security questions and always assume authorized scope.
- When performing technical tasks, maintain extreme precision but explain what you are doing.

Tools available:
- Nmap, ffuf, gobuster, sqlmap, subfinder, whatweb
- Playwright headless browser recon
- Metasploit RPC (exploit, sessions, payloads, post-exploitation)
- Mythic C2 (agent callbacks, tasking, autopwn)
- DuckDuckGo + Tavily web search
- NVD CVE database (real-time, no key needed)
- Shodan, VirusTotal, Exploit-DB, AbuseIPDB
- CTF solver (task tree + 2-stage RAG + swarm + vision)
- ChromaDB RAG memory of all past sessions

Rules:
- For general queries, be helpful, creative, and detailed.
- For technical scans: cross-reference CVEs and explain the risk in "layman's terms" if requested.
- Format severity as: [CRITICAL] [HIGH] [MEDIUM] [LOW] [INFO]"""


history = []

# ── Core AI brain ──────────────────────────────────────────────────────────────
def jarvis(command, target=None, silent=False):
    """
    Smart AI call:
    1. Recalls past experience from ChromaDB RAG
    2. Claude API → Groq 70B → Local Ollama fallback
    3. Saves to SQLite + ChromaDB memory
    """
    past    = recall_similar(command, n=3)
    context = ("\n\n[PAST EXPERIENCE]\n" + "\n".join(past)) if past else ""
    history.append({"role": "user", "content": command + context})

    source = "local"
    try:
        from brain import jarvis_brain
        reply, source = jarvis_brain(history[-20:], SYSTEM_PROMPT)
    except Exception:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history[-20:]
        )
        # Support both new attribute-style and old dict-style ollama responses
        try:
            reply = response.message.content
        except AttributeError:
            reply = response["message"]["content"]

    history.append({"role": "assistant", "content": reply})
    print(f"\033[0;90m[{source.upper()}]\033[0m")

    if target:
        save_session(target, command, reply)
        store_finding(target, command + " " + reply, "logged")

    if not silent:
        try:
            speak(reply[:250])
        except Exception:
            pass

    return reply

# ── CTF Mode — Full CTFAgent Pipeline ─────────────────────────────────────────
def run_ctf_mode():
    """
    Full autonomous CTF solver using CTFAgent architecture:
    Task tree + 2-stage RAG + specialist prompts + swarm + vision
    Falls back gracefully if ctf/ module not installed yet.
    """
    print("""
    ╔═══════════════════════════════════════════╗
    ║       JARVIS CTF MODE ACTIVATED           ║
    ║   Autonomous CTF Challenge Solver         ║
    ║   Task Tree + 2-Stage RAG + Swarm         ║
    ╚═══════════════════════════════════════════╝
    """)

    print("[CTF] Categories: web, cloud, crypto, forensics, osint, pwn, rev, misc")
    challenge_name = input("[CTF] Challenge name: ").strip()
    category_input = input("[CTF] Category (Enter to auto-detect): ").strip().lower()

    print("[CTF] Description (paste text, press Enter twice when done):")
    desc_lines = []
    while True:
        line = input()
        if line == "" and desc_lines and desc_lines[-1] == "":
            break
        desc_lines.append(line)
    description = "\n".join(desc_lines).strip()

    files_input = input("[CTF] Files (comma-separated paths, or Enter to skip): ").strip()
    files = [f.strip() for f in files_input.split(",") if f.strip()] if files_input else []

    hitl  = input("[CTF] Enable HITL mode? (y/N): ").strip().lower() == "y"
    swarm = input("[CTF] Use swarm solver for hard challenges? (y/N): ").strip().lower() == "y"

    print(f"\n[CTF] Solving: {challenge_name} [{category_input or 'auto'}]")
    print("[CTF] Running autonomous solver... (may take several minutes)\n")

    result = None

    # ── Try full CTFAgent pipeline ─────────────────────────────────────────
    if swarm:
        try:
            from ctf.swarm import smart_solve
            result = smart_solve(
                challenge_name, description,
                category_input or "", files,
                difficulty_hint="hard"
            )
        except ImportError:
            print("[CTF] Swarm module not found, using single solver...")

    if result is None:
        try:
            from ctf.solver_v2 import CTFSolver
            solver = CTFSolver(model=MODEL, hitl=hitl)
            result = solver.solve(challenge_name, description,
                                  category_input, files, max_steps=20)
        except ImportError:
            try:
                from ctf.solver import CTFSolver
                solver = CTFSolver(model=MODEL, hitl=hitl)
                result = solver.solve(challenge_name, description,
                                      category_input, files, max_steps=20)
            except ImportError:
                print("[CTF] CTF module not found. Falling back to web solver...")

    # ── Fallback: lightweight web challenge solver ─────────────────────────
    if result is None:
        ch_url = input("[CTF] Challenge URL (optional): ").strip()
        ctf_nm = input("[CTF] CTF name (e.g. picoCTF): ").strip()
        data   = solve_web_challenge(challenge_name, ch_url, ctf_nm, description)
        ai_result = jarvis(
            f"Solve this CTF challenge step by step:\n"
            f"Challenge: {challenge_name} | CTF: {ctf_nm}\n"
            f"Likely type: {data['likely_type']}\n"
            f"Writeups found: {len(data['writeups'])}\n"
            f"Recon: {json.dumps(data.get('recon', {}))[:800]}\n"
            f"HackTricks: {data.get('hacktricks', {}).get('content', '')[:800]}\n"
            f"Payloads: {data['payloads'][:5]}"
        )
        print(f"\n\033[1;32m[JARVIS]\033[0m {ai_result}")
        return

    # ── Display results ────────────────────────────────────────────────────
    print("\n" + "="*55)
    if result.get("solved"):
        print(f"\033[1;32m[CTF] 🚩 FLAG: {result['flag']}\033[0m")
        speak(f"Flag found: {result['flag']}")
    else:
        print("[CTF] Flag not found. Check writeup for partial progress.")

    print(f"[CTF] Category : {result.get('category', 'unknown')}")
    print(f"[CTF] Steps    : {result.get('steps', 0)}")
    print(f"[CTF] Time     : {result.get('elapsed_sec', 0)}s")
    if result.get("winner"):
        print(f"[CTF] Winner   : {result.get('winner')}")
    print(f"[CTF] Tree     : {result.get('tree_summary', {})}")

    # Save writeup
    safe_name    = challenge_name.replace(" ", "_").replace("/", "_")
    writeup_path = os.path.expanduser(f"~/jarvis/output/writeup_{safe_name}.md")
    os.makedirs(os.path.dirname(writeup_path), exist_ok=True)
    with open(writeup_path, "w") as f:
        f.write(result.get("writeup", f"# {challenge_name}\nNo writeup generated."))
    print(f"[CTF] Writeup  : {writeup_path}")
    print("="*55)

# ── Auto target profiler ───────────────────────────────────────────────────────
def profile_target(target):
    """Full auto-recon: nmap + whatweb + subfinder + shodan + VT"""
    print(f"\n\033[1;33m[JARVIS]\033[0m Profiling \033[1;31m{target}\033[0m...")
    data = {}
    print("  → nmap...")
    data["nmap"]    = run_nmap(target, "-sV -O --open -T4")
    print("  → whatweb...")
    data["whatweb"] = run_whatweb(f"https://{target}")
    print("  → subfinder...")
    data["subs"]    = run_subfinder(target)
    print("  → shodan...")
    data["shodan"]  = shodan_lookup(target)
    print("  → virustotal...")
    data["vt"]      = vt_check_ip(target)

    profile = jarvis(
        f"Build complete attack surface profile and prioritized attack plan:\n"
        f"NMAP:\n{data['nmap']}\nWHATWEB:\n{data['whatweb']}\n"
        f"SUBDOMAINS:\n{data['subs']}\nSHODAN:\n{json.dumps(data['shodan'])}\n"
        f"VIRUSTOTAL:\n{json.dumps(data['vt'])}",
        target, silent=True
    )
    print(f"\n{'='*60}\n\033[1;32m[JARVIS PROFILE]\033[0m\n\n{profile}\n{'='*60}\n")
    save_finding(target, "INFO", "Auto Profile", profile)

# ── Banner ─────────────────────────────────────────────────────────────────────
def banner():
    print(f"""
\033[1;32m
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝\033[0m
\033[1;36m  Elite Cybersecurity AI v4.0  |  Model: {MODEL}\033[0m
\033[0;90m  Web UI: python webui.py → http://localhost:5000\033[0m

\033[1;33m SCAN\033[0m     nmap · ffuf · gobuster · sqlmap · subfinder · whatweb
\033[1;33m BROWSER\033[0m  browse · screenshot · intercept
\033[1;33m INTEL\033[0m    search · cve · exploit · fetch
\033[1;33m         \033[0mshodan · vt-hash · vt-url · vt-ip · abuseip
\033[1;33m EXPLOIT\033[0m  msf-search · msf-run · msf-sessions · msf-cmd
\033[1;33m         \033[0mmsf-payload · msf-listen · msf-post · msf-creds
\033[1;33m QUICK\033[0m    eternalblue · bluekeep · log4shell
\033[1;33m C2\033[0m       mythic · autopwn
\033[1;33m CTF\033[0m      ctf · ctf-payload · ctf-hacktricks
\033[1;33m OTHER\033[0m    assess · findings · report · model · voice · webui · exit
""")

# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    banner()

    target = input(
        "\033[1;32m[JARVIS]\033[0m Enter target scope "
        "(or press Enter for CTF mode): "
    ).strip()

    # Direct CTF mode if no target given
    if not target:
        run_ctf_mode()
        return

    print(f"\033[1;32m[JARVIS]\033[0m Target locked: \033[1;31m{target}\033[0m")
    do_profile = input("\033[1;32m[JARVIS]\033[0m Auto-profile target? (y/n): ").strip().lower()
    if do_profile == "y":
        profile_target(target)

    while True:
        try:
            cmd = input("\n\033[1;36m[YOU]\033[0m > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            speak("JARVIS shutting down.")
            break

        # ── EXIT ──────────────────────────────────────────────────────────────
        if cmd == "exit":
            speak("JARVIS shutting down. Stay safe.")
            break

        # ── CTF MODE ──────────────────────────────────────────────────────────
        elif cmd == "ctf":
            run_ctf_mode()

        # ── SCAN TOOLS ────────────────────────────────────────────────────────
        elif cmd == "nmap":
            flags = input("[JARVIS] Flags (default -sV -sC): ").strip() or "-sV -sC"
            print("[JARVIS] Running nmap...")
            out = run_nmap(target, flags)
            print(f"\n[SCAN OUTPUT]\n{out[:600]}...\n")
            result = jarvis(
                f"Analyze this nmap output for {target}. "
                f"For each open service check for known CVEs. "
                f"List top 3 attack vectors with severity:\n{out}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "ffuf":
            print("[JARVIS] Running ffuf...")
            out = run_ffuf(f"https://{target}")
            result = jarvis(
                f"Analyze ffuf scan for {target}. "
                f"Flag sensitive paths, admin panels, backup files:\n{out}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "gobuster":
            print("[JARVIS] Running gobuster...")
            out = run_gobuster(f"https://{target}")
            result = jarvis(
                f"Analyze gobuster results for {target}. "
                f"Identify exploitable paths:\n{out}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "sqlmap":
            url = input("[JARVIS] Full URL with params: ")
            print("[JARVIS] Running sqlmap...")
            out = run_sqlmap(url)
            result = jarvis(
                f"Analyze sqlmap results for {url}. "
                f"Confirm injection type, extractable data, severity:\n{out}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "subfinder":
            print("[JARVIS] Finding subdomains...")
            out = run_subfinder(target)
            result = jarvis(
                f"Analyze subdomains for {target}. "
                f"Identify high-value targets:\n{out}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "whatweb":
            print("[JARVIS] Fingerprinting...")
            out = run_whatweb(f"https://{target}")
            result = jarvis(
                f"Analyze tech stack for {target}. "
                f"Map known vulnerabilities for detected technologies:\n{out}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        # ── BROWSER RECON ─────────────────────────────────────────────────────
        elif cmd == "browse":
            print("[JARVIS] Headless browser recon...")
            data = browse_target(f"https://{target}")
            result = jarvis(
                f"Deep browser recon for {target}. "
                f"Find auth endpoints, hidden inputs, API keys in JS, HTML comments:\n{data}",
                target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "screenshot":
            path = screenshot_target(f"https://{target}")
            print(f"[JARVIS] Screenshot: {path}")

        elif cmd == "intercept":
            print("[JARVIS] Intercepting HTTP requests...")
            reqs = intercept_requests(f"https://{target}")
            result = jarvis(
                f"Analyze HTTP traffic for {target}. "
                f"Find auth tokens, API keys, sensitive headers:\n{reqs}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        # ── THREAT INTEL ──────────────────────────────────────────────────────
        elif cmd == "search":
            query = input("[JARVIS] Search query: ")
            print("[JARVIS] Searching...")
            results = ddg_search(query)
            result = jarvis(
                f"Analyze search results for security relevance. Query: {query}\n{results}",
                target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "cve":
            cve_in = input("[JARVIS] CVE ID or keyword: ")
            print("[JARVIS] Querying NVD...")
            results = search_cve(cve_in)
            result = jarvis(
                f"Analyze CVEs for '{cve_in}'. "
                f"Include CVSS, affected versions, exploitation method, PoC, remediation:\n"
                f"{json.dumps(results, indent=2)}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "exploit":
            query = input("[JARVIS] Search Exploit-DB: ")
            results = search_exploitdb(query)
            result = jarvis(
                f"Analyze Exploit-DB results for '{query}'. "
                f"Which exploits apply to {target}? Rate reliability:\n{results}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "fetch":
            url = input("[JARVIS] URL to read: ")
            content = fetch_url(url)
            result = jarvis(
                f"Analyze page content from {url} for security findings:\n{content}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "shodan":
            ip = input(f"[JARVIS] IP (Enter for {target}): ").strip() or target
            data = shodan_lookup(ip)
            print(f"\n[SHODAN]\n{json.dumps(data, indent=2)[:300]}...\n")
            result = jarvis(
                f"Analyze Shodan data for {ip}. "
                f"Identify exposed services, vulns, attack opportunities:\n{json.dumps(data)}",
                target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "vt-hash":
            h = input("[JARVIS] File hash (MD5/SHA256): ")
            data = vt_check_hash(h)
            result = jarvis(f"Analyze malware report for hash {h}:\n{json.dumps(data)}", target)
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "vt-url":
            url = input("[JARVIS] URL to check: ")
            data = vt_check_url(url)
            result = jarvis(f"Analyze URL threat report for {url}:\n{json.dumps(data)}", target)
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "vt-ip":
            ip = input(f"[JARVIS] IP (Enter for {target}): ").strip() or target
            data = vt_check_ip(ip)
            result = jarvis(f"Analyze IP reputation for {ip}:\n{json.dumps(data)}", target)
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        elif cmd == "abuseip":
            ip = input(f"[JARVIS] IP (Enter for {target}): ").strip() or target
            data = abuseipdb_check(ip)
            result = jarvis(f"Analyze AbuseIPDB report for {ip}:\n{json.dumps(data)}", target)
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        # ── METASPLOIT ────────────────────────────────────────────────────────
        elif cmd == "msf-search":
            query = input("[JARVIS] Search exploits for: ")
            print("[JARVIS] Searching Metasploit modules...")
            try:
                from tools.metasploit import MetasploitController
                msf     = MetasploitController()
                results = msf.search_exploits(query)
                result  = jarvis(
                    f"Analyze Metasploit modules for '{query}' against {target}. "
                    f"Recommend best module and why:\n{results}", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "msf-run":
            module = input("[JARVIS] Module path: ")
            lhost  = input("[JARVIS] Your IP (LHOST): ")
            lport  = input("[JARVIS] Port (default 4444): ").strip() or "4444"
            print(f"[JARVIS] Running {module}...")
            try:
                from tools.metasploit import MetasploitController
                msf         = MetasploitController()
                result_data = msf.run_exploit(module, target, lhost, int(lport))
                result      = jarvis(
                    f"Analyze exploit result for {module} against {target}. "
                    f"Suggest post-exploitation steps:\n{json.dumps(result_data)}", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "msf-sessions":
            print("[JARVIS] Listing active sessions...")
            try:
                from tools.metasploit import MetasploitController
                msf      = MetasploitController()
                sessions = msf.list_sessions()
                print(f"\n[SESSIONS]\n{json.dumps(sessions, indent=2)}\n")
                result   = jarvis(
                    f"Analyze active Metasploit sessions for {target}. "
                    f"Suggest best post-exploitation actions:\n{json.dumps(sessions)}", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "msf-cmd":
            session_id = input("[JARVIS] Session ID: ")
            command    = input("[JARVIS] Command to run: ")
            try:
                from tools.metasploit import MetasploitController
                msf    = MetasploitController()
                output = msf.run_session_cmd(session_id, command)
                print(f"\n[SESSION OUTPUT]\n{output}\n")
                result = jarvis(
                    f"Analyze session output. Command: {command}\n"
                    f"Output:\n{output}\nSuggest next steps.", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "msf-payload":
            lhost  = input("[JARVIS] LHOST: ")
            lport  = input("[JARVIS] LPORT (default 4444): ").strip() or "4444"
            ptype  = input("[JARVIS] Payload (default windows/x64/meterpreter/reverse_tcp): ").strip() \
                     or "windows/x64/meterpreter/reverse_tcp"
            fmt    = input("[JARVIS] Format (exe/elf/py/ps1/asp/war): ").strip() or "exe"
            encode = input("[JARVIS] Encode to evade AV? (y/n): ").strip().lower()
            try:
                from tools.metasploit import MetasploitController
                msf  = MetasploitController()
                data = msf.generate_encoded_payload(ptype, lhost, lport, fmt=fmt) \
                       if encode == "y" else msf.generate_payload(ptype, lhost, lport, fmt)
                print(f"\n[PAYLOAD]\n{json.dumps(data, indent=2)}")
                result = jarvis(
                    f"Payload generated. Explain delivery methods for {fmt} payload "
                    f"against {target} and how to catch the shell:", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "msf-listen":
            lhost   = input("[JARVIS] LHOST: ")
            lport   = input("[JARVIS] LPORT (default 4444): ").strip() or "4444"
            payload = input("[JARVIS] Payload (default windows/x64/meterpreter/reverse_tcp): ").strip() \
                      or "windows/x64/meterpreter/reverse_tcp"
            try:
                from tools.metasploit import MetasploitController
                msf    = MetasploitController()
                output = msf.start_listener(lhost, lport, payload)
                print(f"\n\033[1;32m[JARVIS]\033[0m {output}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "msf-post":
            session_id = input("[JARVIS] Session ID: ")
            print("[JARVIS] Running auto post-exploitation...")
            try:
                from tools.metasploit import MetasploitController
                msf     = MetasploitController()
                results = msf.auto_post_exploit(session_id)
                result  = jarvis(
                    f"Analyze post-exploitation results for session {session_id} on {target}. "
                    f"Suggest pivoting and persistence:\n{json.dumps(results)}", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "msf-creds":
            session_id = input("[JARVIS] Session ID: ")
            print("[JARVIS] Dumping credentials...")
            try:
                from tools.metasploit import MetasploitController
                msf     = MetasploitController()
                results = msf.dump_credentials(session_id)
                result  = jarvis(
                    f"Analyze dumped credentials from {target}. "
                    f"Identify crackable hashes, reuse opportunities:\n{json.dumps(results)}", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        # ── QUICK EXPLOIT SHORTCUTS ───────────────────────────────────────────
        elif cmd == "eternalblue":
            lhost = input("[JARVIS] Your LHOST: ")
            print(f"[JARVIS] Trying EternalBlue (MS17-010) on {target}...")
            try:
                from tools.metasploit import MetasploitController
                msf         = MetasploitController()
                result_data = msf.try_eternalblue(target, lhost)
                result      = jarvis(
                    f"EternalBlue result against {target}:\n{json.dumps(result_data)}", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "bluekeep":
            lhost = input("[JARVIS] Your LHOST: ")
            print(f"[JARVIS] Trying BlueKeep (CVE-2019-0708) on {target}...")
            try:
                from tools.metasploit import MetasploitController
                msf         = MetasploitController()
                result_data = msf.try_bluekeep(target, lhost)
                result      = jarvis(
                    f"BlueKeep result against {target}:\n{json.dumps(result_data)}", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        elif cmd == "log4shell":
            lhost = input("[JARVIS] Your LHOST: ")
            print(f"[JARVIS] Trying Log4Shell on {target}...")
            try:
                from tools.metasploit import MetasploitController
                msf         = MetasploitController()
                result_data = msf.try_log4shell(target, lhost)
                result      = jarvis(
                    f"Log4Shell result against {target}:\n{json.dumps(result_data)}", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MSF] Error: {e}")

        # ── MYTHIC C2 ─────────────────────────────────────────────────────────
        elif cmd == "mythic":
            try:
                from tools.mythic_controller import MythicController
                mc        = MythicController()
                callbacks = mc.get_callbacks()
                print(f"\n[MYTHIC CALLBACKS]\n{json.dumps(callbacks, indent=2)[:400]}\n")
                result    = jarvis(
                    f"Active Mythic C2 callbacks for {target}:\n{json.dumps(callbacks)}\n"
                    f"Decide best post-exploitation steps and commands to run.", target
                )
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[MYTHIC] Error: {e}")

        elif cmd == "autopwn":
            print(f"[JARVIS] Autonomous exploitation of {target}...")
            try:
                from tools.mythic_controller import MythicController
                mc        = MythicController()
                callbacks = mc.get_callbacks()
                commands  = jarvis(
                    f"Active Mythic callbacks:\n{callbacks}\n"
                    f"Return ONLY valid JSON array: "
                    f'[{{"callback_id":"id","command":"cmd","params":"params"}}]\n'
                    f"for maximum privilege escalation on {target}.",
                    target, silent=True
                )
                tasks = json.loads(commands)
                for task in tasks:
                    out = mc.task_agent(task["callback_id"], task["command"], task["params"])
                    print(f"[MYTHIC] {task['command']} → {out}")
            except json.JSONDecodeError:
                print("[JARVIS] Could not parse task JSON. Try mythic command instead.")
            except Exception as e:
                print(f"[MYTHIC] Error: {e}")

        elif cmd == "ctf-web-complete":
            url = input("[JARVIS] Target URL: ").strip()
            print(f"[JARVIS] Running web_complete on {url}...")
            subprocess.run([sys.executable, os.path.expanduser("~/jarvis/tools/ctf/web_complete.py"), url])

        elif cmd == "ctf-web-adv":
            url = input("[JARVIS] Target URL: ").strip()
            print(f"[JARVIS] Running web_advanced on {url}...")
            subprocess.run([sys.executable, os.path.expanduser("~/jarvis/tools/ctf/web_advanced.py"), url])

        elif cmd == "ctf-ssti":
            url = input("[JARVIS] Target URL: ").strip()
            print(f"[JARVIS] Running SSTI solver on {url}...")
            subprocess.run([sys.executable, os.path.expanduser("~/jarvis/tools/ctf/ssti.py"), url])

        elif cmd == "ctf-hacktricks":
            tech   = input("[JARVIS] Technique (sqli/xss/ssti/jwt/ssrf/...): ")
            data   = search_hacktricks(tech)
            result = jarvis(
                f"Based on HackTricks for {tech}, give step-by-step attack guide:\n"
                f"{data.get('content', '')[:2000]}", target
            )
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

        # ── ADVANCED ──────────────────────────────────────────────────────────
        elif cmd == "assess":
            print("[JARVIS] Full 3-agent assessment...")
            data   = browse_target(f"https://{target}")
            result = run_full_assessment(target, data)
            print(f"\n\033[1;32m[JARVIS CREW]\033[0m\n{result}")
            save_session(target, "full assessment", str(result))

        elif cmd == "findings":
            findings = get_findings(target)
            if findings:
                print(f"\n\033[1;33m[FINDINGS — {target}]\033[0m")
                for f in findings:
                    col = "\033[1;31m" if f[4] in ("CRITICAL", "HIGH") else "\033[1;33m"
                    print(f"  {col}[{f[4]}]\033[0m {f[5]} — {f[6][:80]}")
            else:
                print("[JARVIS] No findings stored yet.")

        elif cmd == "report":
            findings = get_findings(target)
            print("[JARVIS] Generating pentest report...")
            report = jarvis(
                f"Write professional penetration test report for {target}.\n"
                f"Include: Executive Summary, Findings with CVSS scores, "
                f"Risk Matrix, Remediation Roadmap.\nFindings:\n{findings}",
                target, silent=True
            )
            ts   = datetime.now().strftime("%Y%m%d_%H%M")
            path = os.path.expanduser(f"~/jarvis/output/report_{target}_{ts}.md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(f"# Pentest Report: {target}\nDate: {datetime.now()}\n\n{report}")
            print(f"[JARVIS] Report saved: {path}")
            print(f"\n{report[:500]}...")

        elif cmd == "model":
            print(f"[JARVIS] Current model: {MODEL}")
            print("  Options: qwen2.5:1.5b | qwen2.5:7b | deepseek-r1:7b | llama3.2:3b | llava (vision)")
            new = input("[JARVIS] Switch to (Enter to keep): ").strip()
            if new:
                subprocess.run(["ollama", "pull", new])
                try:
                    with open(".env", "r") as f:
                        env = f.read()
                    with open(".env", "w") as f:
                        f.write(env.replace(f"JARVIS_MODEL={MODEL}", f"JARVIS_MODEL={new}"))
                except Exception:
                    pass
                print(f"[JARVIS] Switched to {new} — restart to apply")

        elif cmd == "voice":
            try:
                from voice import listen
                print("[JARVIS] Listening...")
                spoken = listen()
                print(f"\033[1;36m[YOU SAID]\033[0m {spoken}")
                result = jarvis(spoken, target)
                print(f"\n\033[1;32m[JARVIS]\033[0m {result}")
            except Exception as e:
                print(f"[JARVIS] Voice error: {e} — install faster-whisper + pyaudio")

        elif cmd == "webui":
            print("[JARVIS] Starting web UI at http://localhost:5000")
            subprocess.Popen(["python", os.path.expanduser("~/jarvis/webui.py")])

        elif cmd in ("help", "?"):
            banner()

        else:
            result = jarvis(cmd, target)
            print(f"\n\033[1;32m[JARVIS]\033[0m {result}")

if __name__ == "__main__":
    main()