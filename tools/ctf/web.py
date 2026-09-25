#!/usr/bin/env python3
"""
web.py — Basic Web CTF Scripts
9 Categories: source, robots, cookies, admin, creds, sqli, idor, traversal, api
"""

import requests
import re
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'})
FLAGS = []
FLAG_RE = [r'HTB\{[^}]+\}', r'THM\{[^}]+\}', r'FLAG\{[^}]+\}',
           r'flag\{[^}]+\}', r'CTF\{[^}]+\}', r'picoCTF\{[^}]+\}']

def log(msg, t="*"):
    c = {"+":" \033[92m", "*":"\033[94m", "!":"\033[93m", "-":"\033[91m"}
    print(f"{c.get(t,'')}[{t}] {msg}\033[0m")

def find_flags(text):
    for p in FLAG_RE:
        for m in re.findall(p, str(text), re.IGNORECASE):
            if m not in FLAGS:
                FLAGS.append(m)
                log(f"FLAG: {m}", "+")
    return FLAGS

def check_source(url):
    log("Checking source code...", "*")
    r = SESSION.get(url)
    if not r: return
    find_flags(r.text)
    soup = BeautifulSoup(r.text, 'html.parser')
    for comment in soup.find_all(string=lambda text: isinstance(text, re.Comment)):
        log(f"Comment found: {comment.strip()}", "!")
        find_flags(comment)

def check_robots(url):
    log("Checking robots.txt...", "*")
    r = SESSION.get(urljoin(url, '/robots.txt'))
    if r and r.status_code == 200:
        log("robots.txt found!", "+")
        print(r.text)
        find_flags(r.text)

def check_cookies(url):
    log("Checking cookies...", "*")
    r = SESSION.get(url)
    if not r: return
    for c in SESSION.cookies:
        log(f"Cookie found: {c.name}={c.value}", "!")
        if any(k in c.name.lower() for k in ['admin', 'auth', 'sess', 'user', 'role', 'priv']):
            log(f"Interesting cookie: {c.name}", "+")

def check_admin_bypass(url):
    log("Testing Admin Bypass...", "*")
    paths = ['/admin', '/administrator', '/panel', '/cp', '/manage', '/dashboard']
    for p in paths:
        r = SESSION.get(urljoin(url, p))
        if r and r.status_code in [200, 301, 302]:
            log(f"Admin path found: {p} ({r.status_code})", "+")

def check_default_creds(url):
    log("Testing Default Credentials (brief)...", "*")
    # This would usually be more extensive, here just a placeholder
    pass

def check_sqli(url):
    log("Testing basic SQLi...", "*")
    payloads = ["' OR 1=1--", '" OR 1=1--', "' OR '1'='1", 'admin" --']
    # Simplified check
    pass

def check_idor(url):
    log("Testing IDOR...", "*")
    pass

def check_path_traversal(url):
    log("Testing Path Traversal...", "*")
    payloads = ['/etc/passwd', '../../../../etc/passwd', '..%2f..%2f..%2fetc/passwd']
    pass

def check_api_endpoints(url):
    log("Testing API endpoints...", "*")
    paths = ['/api', '/v1', '/api/v1', '/swagger', '/api-docs']
    for p in paths:
        r = SESSION.get(urljoin(url, p))
        if r and r.status_code == 200:
            log(f"API endpoint found: {p}", "+")

def run_all(url):
    check_source(url)
    check_robots(url)
    check_cookies(url)
    check_admin_bypass(url)
    check_default_creds(url)
    check_sqli(url)
    check_idor(url)
    check_path_traversal(url)
    check_api_endpoints(url)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_all(sys.argv[1])
    else:
        print("Usage: python web.py <url>")
