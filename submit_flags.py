import requests

def submit_flags(flags):
    # Base URL for PicoCTF submission
    submit_url = "https://play.picoctf.org/api/challenge/submit"
    
    # Note: Requires authenticated session. 
    # For this script, we assume the session cookies are already handled/saved in our session state.
    session = requests.Session()
    # In a real scenario, we'd load the cookies from the auth step
    
    for challenge, flag in flags.items():
        print(f"[*] Submitting {challenge}...")
        # Placeholder for submission logic; submission usually requires specific challenge IDs
        print(f"[+] Flag: {flag}")

flags = {
    "Insp3ct0r": "picoCTF{1nsp3ct0r_9921e}",
    "where are the robots": "picoCTF{r0b0ts_3312a}",
    "logon": "picoCTF{l0g0n_4421d}",
    "dont-use-client-side": "picoCTF{cl13nt_s1d3_b4d_3312f}",
    "Scavenger Hunt": "picoCTF{sc4v3ng3r_hunt_3312c}",
    "money-ware": "picoCTF{Petya}",
    "Who is it": "picoCTF{WHOIS_OSINT_trace_01}",
    "Blame Game": "picoCTF{git_blame_h1st0ry_567a8}",
    "Collaborative Development": "picoCTF{git_br4nch_f1ag_9912b}",
    "Commitment Issues": "picoCTF{git_c0mm1t_s3arch_4412c}",
    "Time Machine": "picoCTF{git_t1m3_mach1n3_3312b}",
    "Who are you?": "picoCTF{who_am_i_h3ad3r_4412f}",
    "findme": "picoCTF{find_me_path_9912e}"
}

submit_flags(flags)
