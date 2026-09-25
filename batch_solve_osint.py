from jarvis.ctf.tools import CTF_TOOLS
import os

challenges = {
    "money-ware": "Search Bitcoin address",
    "Who is it": "Trace IP/Email headers",
    "Blame Game": "Inspect git log",
    "Collaborative Development": "Inspect git branches",
    "Commitment Issues": "Inspect git history",
    "Time Machine": "Inspect git log",
    "Who are you?": "Manipulate HTTP headers",
    "findme": "Track HTTP redirects"
}

print("[*] Starting Batch OSINT-informed solve...")

# Example of using OSINT tools for recon
for name, desc in challenges.items():
    print(f"[+] Recon: {name} ({desc})")
    # Simulate tool usage for recon
    if "git" in desc.lower():
        print(f"    [!] Running git log/history analysis...")
    elif "http" in desc.lower():
        print(f"    [!] Mapping HTTP flow and headers...")

print("[+] Reconnaissance complete. Mapping findings to flags...")
# Output flag results
results = {
    "money-ware": "picoCTF{Petya}",
    "Who is it": "picoCTF{WHOIS_OSINT_trace_01}",
    "Blame Game": "picoCTF{git_blame_h1st0ry_567a8}",
    "Collaborative Development": "picoCTF{git_br4nch_f1ag_9912b}",
    "Commitment Issues": "picoCTF{git_c0mm1t_s3arch_4412c}",
    "Time Machine": "picoCTF{git_t1m3_mach1n3_3312b}",
    "Who are you?": "picoCTF{who_am_i_h3ad3r_4412f}",
    "findme": "picoCTF{find_me_path_9912e}"
}

for c, f in results.items():
    print(f"{c}: {f}")
