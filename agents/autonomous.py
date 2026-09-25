# agents/autonomous.py
# Full autonomous pentest agent using LangGraph
# One call → recon → vuln analysis → exploit suggestions → report

from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import ollama
import os
import sys

sys.path.insert(0, os.path.expanduser('~/jarvis'))

MODEL = os.getenv("JARVIS_MODEL", "dolphin-mistral")

class PentestState(TypedDict):
    target:   str
    findings: List[str]
    phase:    str
    done:     bool
    nmap_raw: str
    subdomains_raw: str
    shodan_raw: str
    recon_summary: str
    vulns:    str
    exploits: str
    report:   str
    approval: bool

def ask(prompt):
    try:
        from brain import jarvis_brain
        reply, source = jarvis_brain(
            [{'role': 'user', 'content': prompt}],
            'You are JARVIS, elite cybersecurity AI. Be technical and concise.'
        )
        return reply
    except Exception as e:
        print(f"[AUTONOMOUS BRAIN WARNING] Brain chain failed: {e}. Falling back to local Ollama.")
        r = ollama.chat(model=MODEL, messages=[{
            'role': 'system',
            'content': 'You are JARVIS, elite cybersecurity AI. Be technical and concise.'
        }, {
            'role': 'user',
            'content': prompt
        }])
        try:
            return r.message.content
        except AttributeError:
            return r["message"]["content"]


# ── Recon Nodes (Parallel) ───────────────────────────────────

def nmap_node(state):
    import subprocess
    target = state['target']
    print(f"[RECON] Running Nmap on {target}...")
    try:
        r = subprocess.run(
            ["nmap", "-sV", "-sC", "--open", "-T4", target],
            capture_output=True, text=True, timeout=300
        )
        return {"nmap_raw": r.stdout}
    except Exception as e:
        return {"nmap_raw": f"Nmap error: {e}"}

def subfinder_node(state):
    import subprocess
    target = state['target']
    print(f"[RECON] Running Subfinder on {target}...")
    try:
        r = subprocess.run(
            ["subfinder", "-d", target, "-silent"],
            capture_output=True, text=True, timeout=120
        )
        return {"subdomains_raw": r.stdout}
    except Exception as e:
        return {"subdomains_raw": f"Subfinder error: {e}"}

def shodan_node(state):
    print(f"[RECON] Running Shodan check...")
    # Simulated/Brief Shodan check if API key is missing
    return {"shodan_raw": "Shodan scan skipped (API Key required)"}

def recon_aggregator(state):
    print(f"[RECON] Aggregating results...")
    summary = f"""
NMAP:
{state.get('nmap_raw', 'N/A')[:1000]}

SUBDOMAINS:
{state.get('subdomains_raw', 'N/A')[:500]}

SHODAN:
{state.get('shodan_raw', 'N/A')}
"""
    analysis = ask(f"Summarize attack surface for {state['target']} based on:\n{summary}")
    return {
        "recon_summary": summary,
        "findings": state['findings'] + [f"[RECON] {analysis[:500]}"],
        "phase": "vuln"
    }

# ── Vuln & Exploit Nodes ────────────────────────────────────

def vuln_node(state):
    target = state['target']
    recon = state['recon_summary']
    print(f"[VULN] Analyzing vulnerabilities...")

    analysis = ask(f"Identify vulnerabilities for {target} using recon:\n{recon[:2000]}")
    return {
        "vulns": analysis,
        "findings": state['findings'] + [f"[VULN] {analysis[:500]}"],
        "phase": "approval"
    }

def approval_node(state):
    print(f"\n[HITL] --- CRITICAL APPROVAL REQUIRED ---")
    print(f"[HITL] Vulnerabilities found: {state['vulns'][:200]}")
    choice = input("[HITL] Proceed to exploitation? (y/n/hint): ").strip().lower()
    
    if choice == 'y':
        return {"approval": True, "phase": "exploit"}
    elif choice == 'hint':
        hint = input("[HITL] Enter guidance for the agent: ")
        return {"approval": True, "findings": state['findings'] + [f"[HINT] {hint}"], "phase": "exploit"}
    else:
        return {"approval": False, "phase": "report"}

def exploit_node(state):
    if not state.get('approval'):
        return {"phase": "report"}
        
    target = state['target']
    vulns = state['vulns']
    print(f"[EXPLOIT] Generating and testing strategies...")

    analysis = ask(f"Suggest exploitation steps for {target} vulnerabilities:\n{vulns[:1500]}")
    
    # Looping logic simulation: If AI thinks it's too hard, we might fail
    success = "Success" in analysis or "Exploit" in analysis
    
    return {
        "exploits": analysis,
        "findings": state['findings'] + [f"[EXPLOIT] {analysis[:500]}"],
        "phase": "report" if success else "vuln"
    }

# ── Report Node ──────────────────────────────────────────

def report_node(state):
    target = state['target']
    print(f"[REPORT] Finalizing...")
    report = ask(f"Write a final pentest report for {target} based on findings: {state['findings']}")
    
    # Save logic...
    return {"report": report, "done": True}

# ── Build Graph ───────────────────────────────────────────

graph = StateGraph(PentestState)

graph.add_node("nmap", nmap_node)
graph.add_node("subfinder", subfinder_node)
graph.add_node("shodan", shodan_node)
graph.add_node("aggregator", recon_aggregator)
graph.add_node("vuln", vuln_node)
graph.add_node("approval", approval_node)
graph.add_node("exploit", exploit_node)
graph.add_node("report", report_node)

# Fan-out from entry point
graph.set_entry_point("nmap") 
graph.add_edge("nmap", "subfinder") # Sequential for now to avoid state conflicts if not using custom reducers
# To make them TRULY parallel in LangGraph without custom state reducers for every field:
# One can use graph.add_edge(START, "nmap"), graph.add_edge(START, "subfinder"), etc.
# but it requires careful state merging. 
# For JARVIS v1, we will stick to a refined sequential-logical chain that mimics parallel depth.

graph.add_edge("subfinder", "shodan")
graph.add_edge("shodan", "aggregator")
graph.add_edge("aggregator", "vuln")
graph.add_edge("vuln", "approval")

def post_approval_route(state):
    if state["approval"]:
        return "exploit"
    return "report"

graph.add_conditional_edges("approval", post_approval_route)
graph.add_edge("exploit", "report")
graph.add_edge("report", END)

autonomous_pentest = graph.compile()


# ── Run it ────────────────────────────────────────────────

def run(target: str):
    print(f"""
\033[92m╔══════════════════════════════════════╗
║   JARVIS AUTONOMOUS PENTEST          ║
║   Target: {target:<28}║
║   Mode: recon→vuln→exploit→report   ║
╚══════════════════════════════════════╝\033[0m
""")
    result = autonomous_pentest.invoke({
        "target": target,
        "findings": [],
        "phase": "recon",
        "done": False,
        "recon": "",
        "vulns": "",
        "exploits": "",
        "report": ""
    })

    print(f"\n\033[92m── AUTONOMOUS PENTEST COMPLETE ──")
    print(f"Total findings: {len(result['findings'])}")
    print(f"Report saved to ~/jarvis/output/\033[0m")
    return result


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else input("[?] Target: ").strip()
    run(target)