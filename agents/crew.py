"""
JARVIS Agents — lightweight multi-agent system
No crewai dependency, works on Python 3.11
"""

import ollama
import os

MODEL = os.getenv("JARVIS_MODEL", "dolphin-mistral")

def _run(role, goal, task):
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"You are a {role}. Your goal: {goal}. Be technical and precise."},
            {"role": "user",   "content": task}
        ]
    )
    return response["message"]["content"]

def run_full_assessment(target, recon_data):
    print("[AGENT 1/3] Recon Specialist analyzing...")
    recon = _run(
        "Elite Recon Specialist",
        "Discover complete attack surface on authorized targets",
        f"Analyze recon data for {target} and list all attack vectors:\n{recon_data}"
    )
    print("[AGENT 2/3] Vulnerability Analyst working...")
    vulns = _run(
        "Vulnerability Analyst",
        "Identify and analyze vulnerabilities from recon data",
        f"Based on this recon for {target}, identify vulnerabilities and exploitation steps:\n{recon}"
    )
    print("[AGENT 3/3] Report Writer generating...")
    report = _run(
        "Penetration Test Report Writer",
        "Write clear professional vulnerability reports",
        f"Write a professional pentest report for {target} based on:\n{vulns}"
    )
    return f"=== RECON ===\n{recon}\n\n=== VULNS ===\n{vulns}\n\n=== REPORT ===\n{report}"
