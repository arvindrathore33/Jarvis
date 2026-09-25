# PicoCTF Technical Knowledge Base

## 1. Overview
PicoCTF is an educational CTF platform developed by Carnegie Mellon University. It is designed to be a continuous learning environment (PicoGym) as well as a competitive event platform.

## 2. Infrastructure & Architecture
- **API Endpoint:** `https://play.picoctf.org/api`
- **Authentication:** REST API using Token-based authentication (`Authorization: Token <key>`) or Session-based cookies (`sessionid`, `csrftoken`).
- **Challenge Hosting:** Challenges are hosted across various subdomains (e.g., `saturn.picoctf.net`, `atlas.picoctf.net`, `titan.picoctf.net`).
- **Bot Mitigation:** Uses Cloudflare Managed Challenge (WAF). Automated access requires `cloudscraper` or high-level browser automation with clearance cookie rotation.

## 3. Challenge Categories
- **General Skills:** Linux CLI, basic scripting, encoding (Base64, Hex).
- **Web Exploitation:** SQLi, XSS, SSRF, SSTI, Cookie manipulation, JWT, Inspector-based discovery.
- **Cryptography:** RSA, AES, Caesar/Vigenere, Hashing, Custom ciphers.
- **Forensics:** File analysis (magic bytes), Steganography, PCAP analysis, Memory forensics.
- **Reverse Engineering:** Binary analysis (Ghidra/Radare2), Decompilation, Static/Dynamic analysis.
- **Binary Exploitation:** Buffer overflows, ROP, Format strings, Heap exploitation.

## 4. Flag Format
- Standard format: `picoCTF{...}`
- Regex for detection: `picoCTF\{[A-Za-z0-9_!@#$%^&*()]+\}`

## 5. Automation Strategy (Jarvis)
- **Fetcher:** Use `PicoCTFClient` with `cloudscraper`.
- **Solver:** Map categories to `solver_v2.py` prompts.
- **Submission:** Auto-submit via `submit_flag` API endpoint using existing session cookies.
