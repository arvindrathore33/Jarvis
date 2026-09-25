import sys
import os
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.getcwd())

from ctf.rag import CTFRag

load_dotenv("jarvis/.env")

rag = CTFRag()

challenges = [
    {
        "name": "Old Sessions",
        "desc": "Proper session timeout controls are critical. Explore the /sessions endpoint to find active session IDs and hijack the admin session.",
        "solution": "1. Visit home. 2. Go to /sessions. 3. Find admin session ID. 4. Set 'session' cookie to admin ID. 5. Refresh for flag.",
        "flag": "picoCTF{s3ss1on_h1j4ck1ng_1s_fun_5a92bc}",
        "technique": "Session Hijacking / Insufficient Session Expiration"
    },
    {
        "name": "WebDecode",
        "desc": "Find Base64 encoded data hidden in tag attributes using the Inspector tool.",
        "solution": "1. Inspect HTML source. 2. Look for base64 strings in attributes (e.g., 'data-flag'). 3. Decode base64 to get flag.",
        "flag": "picoCTF{web_d3c0d3_...}",
        "technique": "Inspector / Base64 Decoding"
    },
    {
        "name": "Unminify",
        "desc": "Beautify or unminify obfuscated/compressed JavaScript code to find the flag.",
        "solution": "1. Find minified JS file. 2. Use a beautifier. 3. Search for 'picoCTF' string in the code.",
        "flag": "picoCTF{unm1n1f13d_...}",
        "technique": "JS De-obfuscation / Unminification"
    },
    {
        "name": "IntroToBurp",
        "desc": "Intercept and modify requests. Bypass a registration step or capture hidden data.",
        "solution": "1. Intercept registration request. 2. Remove or modify 'otp' or '2fa' parameter. 3. Forward to bypass check.",
        "flag": "picoCTF{burp_1s_p0w3rfu1_...}",
        "technique": "Proxy Interception / Request Manipulation"
    },
    {
        "name": "Bookmarklet",
        "desc": "Create a JavaScript bookmarklet to execute code in the browser and reveal the flag.",
        "solution": "1. Copy provided JS code. 2. Create bookmark with 'javascript:' prefix. 3. Run on page to decrypt/reveal flag.",
        "flag": "picoCTF{b00km4rkl3t_...}",
        "technique": "JS Execution / Bookmarklets"
    },
    {
        "name": "Local Authority",
        "desc": "Find hardcoded credentials in a JS file used for a login form.",
        "solution": "1. Open login page. 2. Check 'Debugger' or 'Sources' tab for JS files. 3. Find 'secure.js' or similar with 'admin/password' pair.",
        "flag": "picoCTF{h4rdc0d3d_cr3ds_...}",
        "technique": "Information Disclosure / JS Analysis"
    },
    {
        "name": "Inspect HTML",
        "desc": "A simple website where the flag is hidden in the HTML comments.",
        "solution": "1. Right-click → View Page Source. 2. Search for 'picoCTF' or look at comments <!-- ... -->.",
        "flag": "picoCTF{1nsp3ct_h7ml_...}",
        "technique": "Source Code Inspection"
    },
    {
        "name": "Includes",
        "desc": "The flag is split across external files like CSS and JS.",
        "solution": "1. Inspect HTML. 2. Open linked CSS file for part 1. 3. Open linked JS file for part 2. 4. Combine parts.",
        "flag": "picoCTF{1nclud3s_...}",
        "technique": "External Resource Analysis"
    },
    {
        "name": "Cookies",
        "desc": "Brute force or manipulate a 'name' cookie to find the flag.",
        "solution": "1. Intercept request. 2. Notice 'name' cookie (e.g., 0). 3. Iterate name=1, 2, 3... until flag appears.",
        "flag": "picoCTF{c00k13s_...}",
        "technique": "Cookie Manipulation / Brute Force"
    },
    {
        "name": "Scavenger Hunt",
        "desc": "Flag split across HTML, CSS, JS, robots.txt, .htaccess, and .DS_Store.",
        "solution": "1. HTML, CSS, JS for parts 1-3. 2. /robots.txt for part 4. 3. /.htaccess for part 5. 4. /.DS_Store for part 6.",
        "flag": "picoCTF{sc4v3ng3r_hunt_...}",
        "technique": "Asset Discovery / Hidden Files"
    },
    {
        "name": "GET aHEAD",
        "desc": "Change a GET request to a HEAD request to reveal the flag.",
        "solution": "1. Use curl or Burp. 2. Send 'HEAD /' to the target server. 3. Check response headers for the flag.",
        "flag": "picoCTF{h34d_r3qu3st_...}",
        "technique": "HTTP Method Manipulation"
    },
    {
        "name": "dont-use-client-side",
        "desc": "Demonstrates why sensitive logic (like password checking) should not be handled entirely in client-side JS.",
        "solution": "1. Inspect JS source. 2. Find function checking the password. 3. Reconstruction the password from the split 'if' checks.",
        "flag": "picoCTF{cl13nt_s1d3_b4d_...}",
        "technique": "Client-Side Logic Reversal"
    },
    {
        "name": "logon",
        "desc": "Bypass login by manipulating cookies.",
        "solution": "1. Login with any creds. 2. Notice 'admin' cookie is 'False'. 3. Change 'admin' cookie to 'True'. 4. Refresh.",
        "flag": "picoCTF{l0g0n_...}",
        "technique": "Cookie Manipulation"
    },
    {
        "name": "Insp3ct0r",
        "desc": "Flag split into three parts hidden in HTML, CSS, and JS source files.",
        "solution": "1. HTML source (part 1). 2. CSS file (part 2). 3. JS file (part 3).",
        "flag": "picoCTF{1nsp3ct0r_...}",
        "technique": "Source Code Inspection"
    },
    {
        "name": "where are the robots",
        "desc": "Check robots.txt for disallowed paths.",
        "solution": "1. Navigate to /robots.txt. 2. Find 'Disallow: /xxxx'. 3. Visit /xxxx to get flag.",
        "flag": "picoCTF{r0b0ts_...}",
        "technique": "Robots.txt Analysis"
    },
    {
        "name": "SSTI1",
        "desc": "Server-Side Template Injection in Flask/Jinja2.",
        "solution": "1. Inject {{7*7}} to confirm SSTI. 2. Use {{config}} or {{url_for.__globals__}} to leak info/flag.",
        "flag": "picoCTF{sst1_j1nj42_...}",
        "technique": "SSTI (Flask/Jinja2)"
    },
    {
        "name": "n0s4n1ty 1",
        "desc": "File upload vulnerability to achieve Remote Code Execution (RCE).",
        "solution": "1. Upload a PHP shell or similar. 2. Bypass filters (rename to .phtml). 3. Execute 'id' or 'cat /flag'.",
        "flag": "picoCTF{f1l3_upl04d_rce_...}",
        "technique": "File Upload / RCE"
    },
    {
        "name": "Cookie Monster Secret Recipe",
        "desc": "Find hidden cookie recipe using browser tools and cookie inspection.",
        "solution": "1. Inspect cookies. 2. Look for 'recipe' or encoded data. 3. Check hidden elements in HTML.",
        "flag": "picoCTF{c00k13_m0nst3r_...}",
        "technique": "Cookie Analysis"
    },
    {
        "name": "No FA",
        "desc": "Leaked data challenge focusing on 2FA bypass or salt-less hashes.",
        "solution": "1. Analyze leaked database. 2. Crack hashes with rockyou (salt-less). 3. Bypass 2FA if needed via param manipulation.",
        "flag": "picoCTF{n0_f4_bypass_...}",
        "technique": "Hash Cracking / Auth Bypass"
    },
    {
        "name": "Crack the Gate 1",
        "desc": "Authentication bypass or credential cracking challenge.",
        "solution": "1. Analyze login mechanism. 2. Brute force or bypass logic check. 3. Retrieve flag from protected area.",
        "flag": "picoCTF{cr4ck_th3_g4t3_...}",
        "technique": "Auth Bypass"
    },
    {
        "name": "No FA (Adv)",
        "desc": "Advanced 2FA bypass or session management challenge.",
        "solution": "1. Analyze 2FA token generation. 2. Predict tokens or bypass verification endpoint. 3. Access admin dashboard.",
        "flag": "picoCTF{n0_f4_m4st3ry_...}",
        "technique": "Auth Bypass / 2FA Prediction"
    }
]

cat = "web"
for c in challenges:
    success = rag.store_solution(c["name"], cat, c["desc"], c["solution"], c["flag"], c["technique"])
    if success:
        print(f"[BATCH] Trained: {c['name']}")
    else:
        print(f"[BATCH] Failed: {c['name']}")

print("\n[BATCH] Completed training for all 21 Web Exploitation challenges.")
