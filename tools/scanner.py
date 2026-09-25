import subprocess

def run_nmap(target, flags="-sV -sC"):
    result = subprocess.run(
        ["nmap"] + flags.split() + [target],
        capture_output=True, text=True
    )
    return result.stdout

def run_ffuf(target, wordlist="/usr/share/wordlists/dirb/common.txt"):
    result = subprocess.run(
        ["ffuf", "-u", f"{target}/FUZZ", "-w", wordlist, "-mc", "200,301,302", "-silent"],
        capture_output=True, text=True
    )
    return result.stdout

def run_gobuster(target, wordlist="/usr/share/wordlists/dirb/common.txt"):
    result = subprocess.run(
        ["gobuster", "dir", "-u", target, "-w", wordlist, "-q"],
        capture_output=True, text=True
    )
    return result.stdout

def run_sqlmap(target, params=""):
    result = subprocess.run(
        ["sqlmap", "-u", target, "--batch", "--level=2"] + params.split(),
        capture_output=True, text=True
    )
    return result.stdout

def run_subfinder(domain):
    result = subprocess.run(
        ["subfinder", "-d", domain, "-silent"],
        capture_output=True, text=True
    )
    return result.stdout

def run_whatweb(target):
    result = subprocess.run(
        ["whatweb", target],
        capture_output=True, text=True
    )
    return result.stdout

def run_nuclei(target, templates=""):
    cmd = ["nuclei", "-u", target, "-silent"]
    if templates:
        cmd.extend(["-t", templates])
    result = subprocess.run(
        cmd,
        capture_output=True, text=True
    )
    return result.stdout

def run_semgrep(path, config="p/default"):
    result = subprocess.run(
        ["semgrep", "--config", config, "--quiet", path],
        capture_output=True, text=True
    )
    return result.stdout
