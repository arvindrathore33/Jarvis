# JARVIS Project — MASTER MEMORY DOCUMENT v5.1
# Paste this entire file into any Gemini/Claude conversation to restore full context.
# Author: Arvind | Platform: Arch Linux | GPU: RTX 3050 4GB VRAM
# Python: 3.11.x (NOT 3.14) | Venv: ~/jarvis/venv
# Last Updated: Session 3 — Full merge of all sessions

---

## 1. PROJECT IDENTITY

JARVIS (Just A Rather Very Intelligent System) is a locally hosted, fully offline
autonomous cybersecurity AI for bug bounty hunting, penetration testing, and CTF solving.
Goal: Compete with Claude Mythos — best open cybersec AI, fully private, air-gap capable.

Primary model  : qwen2.5:1.5b (via Ollama) — Optimized for 4GB VRAM
Fallback model : dolphin-mistral (currently removed for disk space)
Brain chain    : Claude API → Groq 70B free → Local Ollama (smart fallback)
Training status: LoRA Fine-tune successful (adapter saved); Ghost SQLi Trainer Active.
Stack          : Python 3.11, Flask + Socket.IO, SQLite, ChromaDB, Whisper, pyttsx3
Location       : ~/jarvis/
Venv           : ~/jarvis/venv (ALWAYS: source venv/bin/activate first)

---

## 2. COMPLETE DIRECTORY STRUCTURE

~/jarvis/
├── main.py                     ← master CLI entry point (v4 — ALL commands)
├── brain.py                    ← smart API fallback: Claude→Groq→Local
├── speak.py                    ← pyttsx3 TTS voice output
├── voice.py                    ← faster-whisper STT voice input
├── recon.py                    ← standalone recon script (no AI, just tools)
├── webui.py                    ← Flask + Socket.IO dark terminal dashboard
├── ctf_webui_addon.py          ← CTF panel routes/JS to merge into webui.py
├── daily_audit.py              ← automated health checks
├── exercise_room_old_sessions.py ← Mock challenge server for training
├── train_jarvis_old_sessions.py  ← Automated training script
├── install_ctf.sh              ← one-click Arch Linux install script
├── setup_jarvis.sh             ← one-click script to place all files correctly
├── .env                        ← all API keys + model config
├── requirements.txt            ← pip install -r requirements.txt
├── README.md                   ← full command reference
│
├── agents/
│   ├── __init__.py
│   ├── crew.py                 ← 3-agent pipeline: Recon→VulnAnalyst→ReportWriter
│   └── autonomous.py          ← LangGraph StateGraph autonomous pentest agent
│
├── memory/
│   ├── __init__.py
│   ├── database.py             ← SQLite: save_session, save_finding, get_findings
│   ├── learning.py             ← ChromaDB: store_finding, recall_similar
│   ├── chromadb/               ← vector DB (auto-created)
│   ├── ctf_knowledge/          ← HackTricks + PayloadsAllTheThings (git cloned)
│   ├── finetune_data.jsonl     ← LoRA training dataset (auto-built weekly)
│   ├── cve_feed.db             ← NVD CVE SQLite (daily cron)
│   └── metrics.db              ← performance tracking SQLite
│
├── tools/
│   ├── __init__.py
│   ├── scanner.py              ← run_nmap, run_ffuf, run_gobuster, run_sqlmap,
│   │                              run_subfinder, run_whatweb
│   ├── browser.py              ← Playwright: browse_target, screenshot_target,
│   │                              intercept_requests
│   ├── websearch.py            ← ddg_search, tavily_search, search_cve,
│   │                              shodan_lookup, shodan_search,
│   │                              vt_check_hash, vt_check_url, vt_check_ip,
│   │                              search_exploitdb, abuseipdb_check, fetch_url
│   ├── metasploit.py           ← MetasploitController (full RPC control)
│   ├── mythic_controller.py   ← MythicController (C2 callbacks + tasking)
│   ├── ctf_solver.py          ← solve_web_challenge, generate_payloads,
│   │                              search_hacktricks, identify_challenge_type
│   └── ctf/                   ← WEB CTF ARSENAL (25 automated checks)
│       ├── __init__.py
│       ├── web.py              ← basic web checks (9 categories)
│       ├── web_advanced.py     ← CMDi, XXE, SSRF, JWT, Upload, Open Redirect
│       ├── web_complete.py     ← 15 advanced categories
│       ├── web_master.py       ← master launcher (runs all 25 checks)
│       ├── ssti.py             ← SSTI detector (6 template engines)
│       ├── crypto_solver.py    ← encoding + cipher attacks
│       ├── forensics_solver.py ← file analysis
│       └── ctf_engine.py       ← auto-router for challenge type detection
│
├── ctf/                        ← CTF AI SOLVER MODULE
│   ├── __init__.py
│   ├── prompts.py              ← 6 specialist prompts + auto category detection
│   ├── task_tree.py            ← stateful branching task tree (CTFAgent core)
│   ├── working_memory.py       ← global fact store + repetition detector
│   ├── rag.py                  ← 2-stage RAG system
│   ├── tools.py                ← 30+ CTF tool wrappers + flag detector
│   ├── difficulty.py           ← difficulty estimator + UCB1 node selector
│   ├── swarm.py                ← parallel race solver (3 models simultaneously)
│   ├── vision.py               ← multimodal image/audio analysis (llava)
│   ├── platforms.py            ← CTFd + HTB + PicoCTF API integration
│   ├── intelligence.py         ← CVE feed + LoRA fine-tune + metrics
│   ├── solver.py               ← original solver (use solver_v2 instead)
│   └── solver_v2.py            ← master solver — USE THIS
│
├── knowledge/                  ← git cloned knowledge bases
│   ├── h1-reports/             ← HackerOne disclosed reports
│   ├── payloads/               ← PayloadsAllTheThings
│   ├── owasp/                  ← OWASP testing guide
│   ├── pico_technical.md       ← PicoCTF technical overview
│   └── my_writeups.md          ← personal notes
│
└── output/
    └── writeups/               ← auto-generated markdown writeups per solve

---

## 3. COMPLETE .env FILE

```
# JARVIS v4.0 — Environment Configuration

# AI Model (change to upgrade)
JARVIS_MODEL=deepseek-coder-v2:16b
CTF_MODEL=deepseek-coder-v2:16b
JARVIS_VISION_MODEL=llava

# Smart Brain Fallback Chain
ANTHROPIC_API_KEY=optional_paid          # console.anthropic.com
GROQ_API_KEY=get_free_at_console.groq.com # free 14400 req/day, llama3-70b

# Threat Intel APIs (all free tier)
SHODAN_API_KEY=optional_free_tier        # shodan.io 100/month
VIRUSTOTAL_API_KEY=optional_free_tier    # virustotal.com 500/day
TAVILY_API_KEY=optional_free_tier        # tavily.com 1000/month
ABUSEIPDB_API_KEY=optional_free_tier     # abuseipdb.com 1000/day

# Metasploit RPC
MSF_HOST=127.0.0.1
MSF_PORT=55553
MSF_PASSWORD=msf_password
MSF_SSL=true

# Mythic C2
MYTHIC_URL=https://localhost:7443
MYTHIC_USER=mythic_admin
MYTHIC_PASS=mythic_password

# CTF Platforms
CTFD_URL=https://ctf.example.com
CTFD_TOKEN=your_token_here
HTB_API_KEY=your_htb_api_key
PICOCTF_USER=your_username
PICOCTF_PASS=your_password
```

---

## 4. COMPLETE requirements.txt

```
# Core
python-dotenv
ollama
requests
beautifulsoup4
groq
anthropic

# Memory
chromadb
langchain
langchain-community

# Web UI
flask
flask-socketio

# Browser recon
playwright

# Voice
faster-whisper
pyaudio
pyttsx3

# Metasploit
pymetasploit3

# LangGraph agents
langgraph
langchain-core

# CTF tools
pwntools
pycryptodome
sympy
pillow
numpy
python-magic

# Scheduling
schedule
```

---

## 5. brain.py — SMART FALLBACK CHAIN

```python
"""
JARVIS Smart Brain — Claude API → Groq 70B → Local Ollama
Auto-switches when quota exceeded or API unavailable
"""
import ollama, os, requests

CLAUDE_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_KEY    = os.getenv("GROQ_API_KEY", "")
LOCAL_MODEL = os.getenv("JARVIS_MODEL", "dolphin-mistral")

def ask_claude(messages, system):
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key": CLAUDE_KEY,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": "claude-sonnet-4-20250514", "max_tokens": 2000,
              "system": system, "messages": messages}, timeout=30)
    data = r.json()
    if "error" in data:
        if data["error"].get("type") in ("insufficient_quota","overloaded_error"):
            raise Exception("CLAUDE_QUOTA_EXCEEDED")
        raise Exception(f"Claude error: {data['error']}")
    return data["content"][0]["text"]

def ask_groq(messages, system):
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role":"system","content":system}] + messages,
        max_tokens=2000
    )
    return response.choices[0].message.content

def ask_local(messages, system):
    response = ollama.chat(model=LOCAL_MODEL,
        messages=[{"role":"system","content":system}] + messages)
    return response["message"]["content"]

def jarvis_brain(messages, system):
    """Tier 1: Claude → Tier 2: Groq → Tier 3: Local"""
    if CLAUDE_KEY:
        try:
            return ask_claude(messages, system), "claude"
        except Exception as e:
            print(f"[BRAIN] Claude → {e}")
    if GROQ_KEY:
        try:
            return ask_groq(messages, system), "groq"
        except Exception as e:
            print(f"[BRAIN] Groq → {e}")
    return ask_local(messages, system), "local"
```

---

## 6. agents/autonomous.py — LANGGRAPH AUTONOMOUS PENTEST

```python
"""
JARVIS Autonomous Pentest Agent — LangGraph StateGraph
One call → full autonomous pentest cycle
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import ollama, os, json

MODEL = os.getenv("JARVIS_MODEL", "dolphin-mistral")

class PentestState(TypedDict):
    target:   str
    findings: List[str]
    phase:    str
    done:     bool
    recon:    str
    vulns:    str
    exploits: str
    report:   str

def recon_node(state):
    from tools.scanner import run_nmap, run_subfinder, run_whatweb
    nmap_out = run_nmap(state["target"], "-sV -sC --open -T4")
    subs_out = run_subfinder(state["target"])
    web_out  = run_whatweb(f"https://{state['target']}")
    analysis = ollama.chat(model=MODEL, messages=[{"role":"user",
        "content": f"Analyze recon for {state['target']}:\n"
                   f"NMAP:\n{nmap_out}\nSUBS:\n{subs_out}\nWEB:\n{web_out}"}])
    return {**state, "recon": analysis["message"]["content"],
            "phase": "vuln", "findings": [analysis["message"]["content"][:200]]}

def vuln_node(state):
    from tools.websearch import search_cve
    tech_analysis = ollama.chat(model=MODEL, messages=[{"role":"user",
        "content": f"Extract technology names from:\n{state['recon']}\nReturn comma-separated list only."}])
    techs = tech_analysis["message"]["content"].split(",")
    cves  = []
    for tech in techs[:4]:
        cves.extend(search_cve(tech.strip())[:2])
    analysis = ollama.chat(model=MODEL, messages=[{"role":"user",
        "content": f"Map CVEs to attack surface for {state['target']}:\nCVEs:{json.dumps(cves)}\nRecon:{state['recon']}"}])
    return {**state, "vulns": analysis["message"]["content"], "phase": "exploit"}

def exploit_node(state):
    from tools.websearch import search_exploitdb
    exploits = search_exploitdb(state["target"])
    analysis = ollama.chat(model=MODEL, messages=[{"role":"user",
        "content": f"Generate exploitation strategy for {state['target']}:\nVulns:{state['vulns']}\nExploits:{exploits}"}])
    return {**state, "exploits": analysis["message"]["content"], "phase": "report"}

def report_node(state):
    from memory.database import save_session
    from datetime import datetime
    report = ollama.chat(model=MODEL, messages=[{"role":"user",
        "content": f"Write professional pentest report for {state['target']}:\n"
                   f"Recon:{state['recon']}\nVulns:{state['vulns']}\nExploits:{state['exploits']}"}])
    report_text = report["message"]["content"]
    ts   = datetime.now().strftime("%Y%m%d_%H%M")
    path = os.path.expanduser(f"~/jarvis/output/report_{state['target']}_{ts}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(f"# Pentest Report: {state['target']}\n\n{report_text}")
    save_session(state["target"], "autonomous pentest", report_text)
    print(f"\n[AUTO] Report saved: {path}")
    return {**state, "report": report_text, "done": True}

# Build graph
graph = StateGraph(PentestState)
graph.add_node("recon",   recon_node)
graph.add_node("vuln",    vuln_node)
graph.add_node("exploit", exploit_node)
graph.add_node("report",  report_node)
graph.set_entry_point("recon")
graph.add_edge("recon",   "vuln")
graph.add_edge("vuln",    "exploit")
graph.add_edge("exploit", "report")
graph.add_edge("report",  END)
pentest_graph = graph.compile()

def run_autonomous_pentest(target: str):
    print(f"\n[AUTO] Starting autonomous pentest: {target}")
    result = pentest_graph.invoke(PentestState(
        target=target, findings=[], phase="recon",
        done=False, recon="", vulns="", exploits="", report=""
    ))
    print(f"\n[AUTO] Complete. Phase: {result['phase']}")
    return result

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else input("Target: ")
    run_autonomous_pentest(target)
```

---

## 7. main.py COMMANDS — COMPLETE v4 REFERENCE

### STARTUP
```
Press Enter at target prompt → direct CTF mode
Type a target → full pentest mode
```

### ALL COMMANDS

SCAN:
  nmap          → port scan + CVE cross-reference + AI analysis
  ffuf          → directory fuzzing
  gobuster      → directory brute force
  sqlmap        → SQL injection testing
  subfinder     → subdomain enumeration
  whatweb       → tech fingerprinting

BROWSER:
  browse        → Playwright full page recon
  screenshot    → full page screenshot
  intercept     → capture HTTP requests + headers

THREAT INTEL:
  search        → DuckDuckGo web search
  cve           → NVD CVE lookup (free, no key)
  exploit       → Exploit-DB search
  fetch         → read any URL
  shodan        → Shodan host intelligence
  vt-hash       → VirusTotal file hash
  vt-url        → VirusTotal URL
  vt-ip         → VirusTotal IP
  abuseip       → AbuseIPDB reputation

METASPLOIT:
  msf-search    → search exploit modules
  msf-run       → run any exploit
  msf-sessions  → list active sessions
  msf-cmd       → run command on session
  msf-payload   → generate payload (with AV evasion)
  msf-listen    → start listener
  msf-post      → auto post-exploitation
  msf-creds     → dump credentials + hashdump
  eternalblue   → one-click MS17-010
  bluekeep      → one-click CVE-2019-0708
  log4shell     → one-click Log4Shell

MYTHIC C2:
  mythic        → view callbacks + AI next steps
  autopwn       → autonomous agent tasking

CTF (AI solver):
  ctf           → full autonomous solver (task tree + RAG + swarm)
  ctf-payload   → generate payloads for vuln type
  ctf-hacktricks→ HackTricks step-by-step guide

CTF (web scripts):
  ctf-web       → runs web_master.py (all 25 checks)
  ctf-crypto    → runs crypto_solver.py on ciphertext
  ctf-file      → runs forensics_solver.py on file

AUTONOMOUS:
  auto          → LangGraph full autonomous pentest

ADVANCED:
  deep <query>  → Groq/Claude deep analysis
  assess        → 3-agent crew assessment
  findings      → show saved findings
  report        → generate pentest report
  model         → switch AI model
  voice         → voice input
  webui         → launch web UI
  help / ?      → show banner

---

## 8. CTF AI SOLVER (ctf/) — FULL DETAIL

### Architecture
```
Challenge input
      ↓
detect_category() — keyword scoring
      ↓
get_ctf_prompt() — specialist system prompt
      ↓
rag.get_combined_context()
  Stage 1: category knowledge (hardcoded)
  Stage 2: past solutions (ChromaDB)
      ↓
vision.full_visual_analysis() — image/audio pre-check
      ↓
TaskTree initialized
  _plan() → LLM decomposes into 4-6 subtasks
      ↓
UCB1 loop (selector.select_next):
  _execute_node() — ReAct (Think→Act→Observe)
    check already_tried() before every tool
    call tool, extract_from_output()
    inject working_memory at every LLM call
    find_flag() on all output
  should_abandon() — difficulty-aware pruning
  _expand_tree() — new sibling nodes on failure
      ↓
store in RAG + memory + metrics
```

### Failure modes fixed
```
18% context forgetting     → working_memory.py (inject at every prompt)
16% premature commitment   → difficulty.py + should_abandon()
12% explore/exploit balance→ UCB1 in DifficultyAwareSelector
12% multi-step failures    → extract_from_output() structured parsing
14% knowledge gaps         → 2-stage RAG + HackTricks + CVE feed
```

### Swarm solver (hard challenges)
```python
# 3 models race in parallel, first flag wins
SWARM_CONFIGS = [
  {"name":"Deepseek-Fast",    "model":"deepseek-coder-v2:16b", "strategy":"aggressive"},
  {"name":"Mistral-Creative", "model":"dolphin-mistral",        "strategy":"creative"},
  {"name":"Llama-Methodical", "model":"llama3.1:8b",           "strategy":"methodical"},
]
```

---

## 9. WEB CTF ARSENAL (tools/ctf/) — FULL DETAIL

### tools/ctf/web.py — Basic (9 checks)
  check_source, check_robots, check_cookies, check_admin_bypass,
  check_default_creds, check_sqli, check_idor,
  check_path_traversal, check_api_endpoints

### tools/ctf/web_advanced.py — Advanced (6 checks)
  check_cmdi, check_xxe, check_ssrf, check_jwt,
  check_open_redirect, check_upload

### tools/ctf/ssti.py — SSTI (6 engines)
  Detect: {{7*7}}, ${7*7}, #{7*7}, <%=7*7%>, @{7*7}, *{7*7}
  Exploit: Jinja2, Twig, Freemarker, ERB, Velocity, Thymeleaf

### tools/ctf/web_complete.py — Complete (15 checks)
  check_graphql, check_nosqli, check_prototype_pollution,
  check_cors, check_race_condition, check_oauth,
  check_deserialization, check_ssi, check_verb_tampering,
  check_param_pollution, check_type_juggling, check_mass_assignment,
  check_smuggling, check_websocket

### tools/ctf/web_master.py — Launcher
  Runs ALL 25 checks, stops early if flag found
  Usage: python tools/ctf/web_master.py http://TARGET:PORT

### tools/ctf/crypto_solver.py
  try_all_bases (b64/b32/hex/binary), try_caesar (all 25),
  try_rot13, try_atbash, try_xor (0-255), try_vigenere,
  try_morse, crack_hash, rsa_small_e (cube root e=3)

### tools/ctf/forensics_solver.py
  identify_file, extract_strings, extract_metadata,
  check_steghide, check_binwalk, check_lsb_png,
  check_zsteg, analyze_pcap, check_appended_data,
  check_zip_comment, check_pdf

---

## 10. tools/metasploit.py — FULL API

```python
# Setup: msfrpcd -P msf_password -S -a 127.0.0.1
# Install: pip install pymetasploit3

MetasploitController():
  search_exploits(query)              → search modules
  run_exploit(module, target, lhost, lport, payload)
  list_sessions()                     → active sessions
  run_session_cmd(session_id, cmd)    → run meterpreter command
  run_post_module(session_id, module) → post exploitation
  generate_payload(type, lhost, lport, format)
  generate_encoded_payload(...)       → AV evasion
  start_listener(lhost, lport, payload)
  auto_post_exploit(session_id)       → whoami, sysinfo, getsystem
  dump_credentials(session_id)        → hashdump + mimikatz
  try_eternalblue(target, lhost)      → MS17-010 shortcut
  try_log4shell(target, lhost)        → Log4Shell shortcut
  try_bluekeep(target, lhost)         → CVE-2019-0708 shortcut
```

---

## 11. tools/mythic_controller.py — FULL API

```python
# Setup: git clone https://github.com/its-a-feature/Mythic
#        sudo ./mythic-cli start

MythicController():
  login()                              → get JWT token
  get_callbacks()                      → active agent list
  task_agent(callback_id, cmd, params) → send task to agent
  get_task_output(task_id)             → read task result
  list_payloads()                      → available payload types
```

---

## 12. webui.py — DASHBOARD

Dark terminal-style web UI at http://localhost:5000

Layout:
  Left sidebar  → target input, tool buttons, live findings
  Center        → terminal output with glitch animation
  Right panel   → stats, past targets, quick reference

Flask routes:
  GET  /              → dashboard HTML
  POST /api/chat      → send message to JARVIS
  POST /api/tool      → run tool + AI analysis
  GET  /api/findings  → findings for target
  GET  /api/history   → past targets

One-click buttons: NMAP · FFUF · GOBUSTER · SUBFINDER
                   WHATWEB · SQLMAP · BROWSE · ASSESS · FINDINGS

---

## 13. INSTALL SEQUENCE (Fresh Arch Linux)

```bash
# 1. System packages
sudo pacman -S python python-pip nmap ffuf gobuster sqlmap \
    whatweb portaudio binwalk exiftool steghide john hashcat \
    gdb wireshark-cli tshark wget curl unzip imagemagick
paru -S zsteg stegseek volatility3 subfinder

# 2. Python 3.11 venv (NOT system Python 3.14)
yay -S python311
cd ~/jarvis
python3.11 -m venv venv
source venv/bin/activate
python --version   # must show 3.11.x

# 3. Python packages
pip install -r requirements.txt
playwright install chromium

# 4. Metasploit
sudo pacman -S metasploit
pip install pymetasploit3
msfrpcd -P msf_password -S -a 127.0.0.1 &

# 5. Ollama models
ollama pull dolphin-mistral          # 7B default
ollama pull deepseek-coder-v2:16b    # primary model
ollama pull llama3.1:8b              # swarm model
ollama pull llava                    # vision

# 6. Clone knowledge bases
mkdir -p ~/jarvis/knowledge
cd ~/jarvis/knowledge
git clone https://github.com/reddelexc/hackerone-reports h1-reports
git clone https://github.com/swisskyrepo/PayloadsAllTheThings payloads
git clone https://github.com/HackTricks-wiki/hacktricks
git clone https://github.com/JohnHammond/katana tools/katana
git clone https://github.com/zardus/ctf-tools tools/ctf-tools

# 7. Auto-activate venv
echo 'jarvis() { cd ~/jarvis && source venv/bin/activate && echo "[JARVIS] venv activated"; }' >> ~/.zshrc

# 8. Run
cd ~/jarvis && source venv/bin/activate && python main.py
```

---

## 14. MODEL UPGRADE PATH

```bash
# Current (fast, 4GB RAM)
JARVIS_MODEL=dolphin-mistral

# Better reasoning (5GB RAM)
JARVIS_MODEL=dolphin-llama3:8b

# Best local (10GB RAM) — PRIMARY
JARVIS_MODEL=deepseek-coder-v2:16b

# CTF swarm member
ollama pull llama3.1:8b

# Vision (image analysis)
ollama pull llava

# Brain chain (no hardware needed):
GROQ_API_KEY → free llama3-70b (14400 req/day)
ANTHROPIC_API_KEY → Claude (best quality, paid)
```

---

## 15. KNOWN ISSUES & FIXES

| Issue | Fix |
|-------|-----|
| Python 3.14 breaks packages | python3.11 -m venv venv |
| venv broken in VS Code | rm -rf venv && python3.11 -m venv venv |
| Ollama not responding | sudo systemctl start ollama |
| Same response always | Make prompts specific with actual data + target |
| 3 files merged into one | Split: main.py + brain.py + mythic_controller.py |
| Commands outside while loop | Fix indentation inside while True |
| Missing imports | Add all from tools.websearch import ... at top |
| tiktoken build fails | PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 pip install tiktoken |
| crewai conflicts | Replaced with pure ollama calls in agents/crew.py |
| pip cache consuming disk | pip install --no-cache-dir ... |
| aplay not found (voice) | sudo pacman -S alsa-utils |
| web_master.py path issues | All ctf scripts must be in tools/ctf/ folder |
| MSF not connecting | msfrpcd -P msf_password -S -a 127.0.0.1 |
| Mythic not connecting | sudo ./mythic-cli start (in Mythic dir) |

---

## 16. GITHUB REPOS TO CLONE

```bash
cd ~/jarvis/knowledge

# CTF knowledge
git clone https://github.com/reddelexc/hackerone-reports h1-reports
git clone https://github.com/swisskyrepo/PayloadsAllTheThings payloads
git clone https://github.com/OWASP/wstg owasp
git clone https://github.com/HackTricks-wiki/hacktricks hacktricks

# CTF tools to study
git clone https://github.com/JohnHammond/katana
git clone https://github.com/verialabs/ctf-agent
git clone https://github.com/zardus/ctf-tools

# Index all into ChromaDB
python -c "
from ctf.rag import CTFRag
rag = CTFRag()
rag.feed_writeup_directory('knowledge/hacktricks')
rag.feed_writeup_directory('knowledge/payloads')
print('Indexed')
"
```

---

### Session 5 — CTF Today Readiness (2026-08-01)
- [x] tools/ctf/ctf_engine.py — AUTO-ROUTER (detects category, routes to right solver) ✅
- [x] exercise_room.py — AUTONOMOUS TRAINING ROOM (Gemini generates challenges, JARVIS trains) ✅
- [x] performance_dashboard.py — VISUAL DASHBOARD (brain health, tool status, training stats) ✅
- [x] ctf_today.py — ONE-CLICK CTF LAUNCHER (PicoCTF fetch, auto-solve, auto-submit) ✅
- [x] daily_audit.py — BRAIN API HEALTH CHECK (Gemini + Groq connectivity test) ✅

### jarvisplan.txt items — COMPLETED
- [x] "exercise room for jarvis where he can train automatically by using gemini and claude" → exercise_room.py
- [x] "performance dashboard" → performance_dashboard.py

### Phase 2 — LangGraph (3 critical topics remaining)
- [x] Human-in-the-loop (interrupt + approve risky exploits + resume)
- [x] Parallel nodes (nmap + subfinder + shodan — logic implemented in agents/autonomous.py)
- [ ] Streaming (see each step in real time as graph runs)
- [ ] ReAct pattern (Think→Act→Observe — how Mythos works internally)
- [ ] Multi-agent subgraphs (supervisor + specialist sub-agents)

---

## 18. RESEARCH BASIS & EVOLUTION LOG

### Phase 2 Tooling Evolution
- [x] `tools/nuclei.py` — Integrated into `tools/scanner.py` and `solver_v2.py`
- [x] `tools/semgrep.py` — Integrated into `tools/scanner.py` and `solver_v2.py`
- [x] `tools/ctf/pwntools.py` — New module for binary exploitation automation.
- [x] `agents/autonomous.py` refactored with LangGraph state machine.

### SQLi Ghost Protocol Evolution
As of June 2026, logs in `memory_logs/sql_ghost.log` indicate that simple tamper scripts (space2comment, between, etc.) are frequently failing against modern WAFs.
*Evolution Result:* Ran autonomous training on local DVWA target. **`randomcase`** was identified as a successful bypass vector for DVWA 'low' security in this environment.

### Daily Audit System
A new `daily_audit.py` has been implemented to perform system-wide health checks, performance tracking, and CVE feed updates. Run this at the start of every session.
*Update:* Docker `vuln-lab` is now the official SQL training ground.

- [ ] tools/nuclei.py — 9000+ vulnerability templates
- [ ] tools/semgrep.py — source code vulnerability analysis
- [ ] tools/pwntools.py — CTF binary exploitation
- [ ] Metasploit persistence + pivoting modules
- [ ] Docker sandbox for safe exploit execution

### Phase 4 — Self-improvement
- [ ] fine_tune.py — monthly LoRA on session data
- [ ] Structured output enforcement (typed dicts)
- [ ] CTFd API in main.py CLI
- [ ] Voice command for CTF mode

---

## 18. RESEARCH BASIS

CTFAgent (CCS 2025):
  - Stateful task tree (not linear ReAct) — key innovation
  - 2-stage RAG: category knowledge + past solutions
  - Beats 88% of human teams (auto), 94% (HITL)
  - Uses cloud APIs — JARVIS does it locally

verialabs/ctf-agent (BSidesSF 2026):
  - Won 1st place: solved all 52/52 challenges
  - Swarm pattern: race multiple models, first flag wins
  - JARVIS implements via swarm.py + ThreadPoolExecutor

Claude Mythos (Anthropic, May 2026):
  - 73% expert CTF solve rate
  - Found thousands of zero-days autonomously
  - Only ~40 vetted partner organizations have access
  - Our goal: best accessible open alternative

---

## 19. QUICK START (every session)

```bash
# 1. Activate
cd ~/jarvis && source venv/bin/activate

# 2. Start Ollama (if not service)
ollama serve &

# 3. Start Metasploit RPC (optional)
msfrpcd -P msf_password -S -a 127.0.0.1 &

# 4. Run JARVIS
python main.py          # CLI
python webui.py         # Web UI → http://localhost:5000

# Inside JARVIS:
> nmap                  # scan target
> ctf                   # CTF mode (full autonomous)
> ctf-web               # 25 web checks
> auto                  # LangGraph autonomous pentest
> cve                   # CVE lookup
> deep <query>          # Groq/Claude deep analysis

# Standalone tools:
python tools/ctf/web_master.py http://TARGET:PORT
python tools/ctf/crypto_solver.py "SGVsbG8="
python tools/ctf/forensics_solver.py challenge.png
python agents/autonomous.py 10.129.x.x

# CTF solve test:
python -c "
from ctf.solver_v2 import CTFSolver
solver = CTFSolver()
result = solver.solve('Test', 'Login at http://localhost:5000. Find flag.', 'web')
print(result)
"

# Performance:
python -c "from ctf.intelligence import print_performance_dashboard; print_performance_dashboard()"

# CVE feed update:
python -c "from ctf.intelligence import update_cve_feed; update_cve_feed()"
```

---

## 20. TOTAL CODEBASE

| Session | Files | Lines | Status |
|---------|-------|-------|--------|
| Session 1 | 12 files | ~4,262 | ✅ |
| Session 2 | 11 files | ~3,000 | ✅ |
| Session 3 | 3 files  | ~800   | ✅ |
| Session 4 | 3 files  | ~250   | ✅ |
| **TOTAL** | **29 files** | **~8,312 lines** | |

Key files:
  main.py (v4)           767 lines  ✅
  brain.py                80 lines  ✅
  agents/autonomous.py   100 lines  ✅
  tools/metasploit.py    280 lines  ✅
  tools/mythic_controller.py 100 lines ✅
  ctf/solver_v2.py       470 lines  ✅
  ctf/swarm.py           246 lines  ✅
  tools/ctf/web_master.py runs all 25 checks ✅
  exercise_room_old_sessions.py  (New) ✅
  train_jarvis_old_sessions.py   (New) ✅
  batch_solve_web.py             (New) ✅

---

## 21. SESSION 4 SUMMARY: PICOCTF WEB MASTERY
- **Goal:** Train JARVIS to solve all PicoCTF Web Exploitation challenges autonomously.
- **Outcome:** 21/21 Web challenges solved and recorded.
- **Intelligence Upgrade:** 
  - Populated Stage-2 RAG Memory with 21+ verified solution paths.
  - JARVIS now has "Elite" status in Web Exploitation.
  - Fixed `curl` tool mapping in `ctf/tools.py`.
- **Infrastructure:** Created an "Exercise Room" mock environment for continuous training.

---

## 22. PROJECT VISION

Building a cybersecurity AI that surpasses existing tools by combining:
- Human intuition and creativity (Arvind)
- AI speed, recall, and execution (JARVIS)

Target:
  Month 1 → JARVIS boots, all tools work, CTF scripts run
  Month 3 → autonomous recon + vuln analysis on real HTB machines
  Month 6 → custom fine-tuned model on personal engagement data
  Year 1  → surpasses generic AI tools for authorized bug bounty

The competitive advantage: specificity.
Every other tool is built for everyone.
JARVIS is built by Arvind, for Arvind, trained on his methodology.

---

END OF MASTER MEMORY v5.0
Sessions 1+2+3 combined: ~8,062 lines across 26 files
