#!/usr/bin/env python3
"""
crypto_solver.py — CTF Crypto Challenge Auto-Solver
Usage: python crypto_solver.py
Covers: ROT, Caesar, XOR, Base encodings, Vigenere, RSA, Hash cracking
"""

import base64
import string
import itertools
import binascii
import hashlib
import sys

FLAG_PATTERNS = ['HTB{', 'THM{', 'picoCTF{', 'FLAG{', 'flag{', 'CTF{']

def looks_like_flag(text):
    text = text.strip()
    return any(p in text for p in FLAG_PATTERNS) or ('{' in text and '}' in text and len(text) < 200)

def looks_like_english(text):
    common = ['the', 'and', 'for', 'you', 'flag', 'this', 'with']
    lower = text.lower()
    return sum(1 for w in common if w in lower) >= 1

def log(msg, level="+"):
    colors = {"+": "\033[92m", "*": "\033[94m", "!": "\033[93m", "-": "\033[91m"}
    print(f"{colors.get(level,'')}[{level}] {msg}\033[0m")

# ── Encoding Detectors ────────────────────────────────────

def try_all_bases(data):
    log("Trying base encodings...", "*")
    results = []

    # Base64
    for s in [data, data.replace(' ', '+'), data.replace('-', '+').replace('_', '/')]:
        try:
            decoded = base64.b64decode(s + '==').decode('utf-8', errors='ignore')
            if decoded.isprintable() and len(decoded) > 2:
                results.append(('base64', decoded))
                log(f"Base64: {decoded[:100]}", "+")
                if looks_like_flag(decoded):
                    return results
        except:
            pass

    # Base32
    try:
        decoded = base64.b32decode(data.upper() + '=' * 8).decode('utf-8', errors='ignore')
        if decoded.isprintable():
            results.append(('base32', decoded))
            log(f"Base32: {decoded[:100]}", "+")
    except:
        pass

    # Base58 (Bitcoin alphabet)
    try:
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        n = 0
        for char in data:
            if char in alphabet:
                n = n * 58 + alphabet.index(char)
        decoded = n.to_bytes((n.bit_length() + 7) // 8, 'big').decode('utf-8', errors='ignore')
        if decoded.isprintable() and len(decoded) > 2:
            results.append(('base58', decoded))
            log(f"Base58: {decoded[:100]}", "+")
    except:
        pass

    # Hex
    try:
        clean = data.replace(' ', '').replace('0x', '').replace('\n', '')
        if all(c in '0123456789abcdefABCDEF' for c in clean):
            decoded = bytes.fromhex(clean).decode('utf-8', errors='ignore')
            if decoded.isprintable() and len(decoded) > 2:
                results.append(('hex', decoded))
                log(f"Hex: {decoded[:100]}", "+")
    except:
        pass

    # Binary
    try:
        clean = data.replace(' ', '').replace('\n', '')
        if all(c in '01' for c in clean) and len(clean) % 8 == 0:
            decoded = ''.join(chr(int(clean[i:i+8], 2)) for i in range(0, len(clean), 8))
            if decoded.isprintable():
                results.append(('binary', decoded))
                log(f"Binary: {decoded[:100]}", "+")
    except:
        pass

    # URL decode
    try:
        from urllib.parse import unquote
        decoded = unquote(data)
        if decoded != data:
            results.append(('url_decode', decoded))
            log(f"URL decode: {decoded[:100]}", "+")
    except:
        pass

    return results


# ── Classical Ciphers ─────────────────────────────────────

def try_caesar(ciphertext):
    log("Trying Caesar cipher (all 25 shifts)...", "*")
    results = []
    for shift in range(1, 26):
        result = ''
        for c in ciphertext:
            if c.isalpha():
                base = ord('A') if c.isupper() else ord('a')
                result += chr((ord(c) - base - shift) % 26 + base)
            else:
                result += c
        if looks_like_flag(result) or looks_like_english(result):
            results.append((f'caesar_{shift}', result))
            log(f"Caesar shift {shift}: {result[:100]}", "+")
    return results


def try_rot13(text):
    log("Trying ROT13...", "*")
    result = text.translate(str.maketrans(
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
        'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'
    ))
    log(f"ROT13: {result[:100]}", "+")
    return result


def try_atbash(text):
    log("Trying Atbash cipher...", "*")
    result = ''
    for c in text:
        if c.isupper():
            result += chr(ord('Z') - (ord(c) - ord('A')))
        elif c.islower():
            result += chr(ord('z') - (ord(c) - ord('a')))
        else:
            result += c
    log(f"Atbash: {result[:100]}", "+")
    return result


def try_xor(data, max_keylen=16):
    log("Trying XOR with common keys...", "*")
    results = []
    if isinstance(data, str):
        try:
            raw = bytes.fromhex(data.replace(' ', ''))
        except:
            raw = data.encode()
    else:
        raw = data

    common_keys = [b'key', b'secret', b'flag', b'ctf', b'admin', b'password']
    for k in range(1, 256):
        xored = bytes(b ^ k for b in raw)
        try:
            decoded = xored.decode('utf-8', errors='ignore')
            if looks_like_flag(decoded) or (decoded.isprintable() and looks_like_english(decoded)):
                results.append((f'xor_single_{k}', decoded))
                log(f"XOR key 0x{k:02x}: {decoded[:100]}", "+")
        except:
            pass

    for key in common_keys:
        xored = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
        try:
            decoded = xored.decode('utf-8', errors='ignore')
            if looks_like_flag(decoded) or looks_like_english(decoded):
                results.append((f'xor_{key}', decoded))
                log(f"XOR key '{key}': {decoded[:100]}", "+")
        except:
            pass

    return results


def try_vigenere(ciphertext, max_keylen=6):
    log("Trying Vigenere with common keys...", "*")
    results = []
    common_keys = ['key', 'flag', 'ctf', 'secret', 'crypto', 'hack', 'admin']

    for key in common_keys:
        result = ''
        key_idx = 0
        for c in ciphertext:
            if c.isalpha():
                shift = ord(key[key_idx % len(key)].lower()) - ord('a')
                base = ord('A') if c.isupper() else ord('a')
                result += chr((ord(c) - base - shift) % 26 + base)
                key_idx += 1
            else:
                result += c
        if looks_like_flag(result) or looks_like_english(result):
            results.append((f'vigenere_{key}', result))
            log(f"Vigenere key '{key}': {result[:100]}", "+")
    return results


def try_morse(text):
    log("Trying Morse code...", "*")
    morse = {
        '.-':'A','-.-.':'C','-.':'D','.':'E','..-.':'F',
        '--.':'G','....':'H','..':'I','.---':'J','-.-':'K',
        '.-..':'L','--':'M','-.':'N','---':'O','.--.':'P',
        '--.-':'Q','.-.':'R','...':'S','-':'T','..-':'U',
        '...-':'V','.--':'W','-..-':'X','-.--':'Y','--..':'Z',
        '.----':'1','..---':'2','...--':'3','....-':'4',
        '.....':'5','-....':'6','--...':'7','---..':'8',
        '----.':'9','-----':'0',
    }
    try:
        words = text.strip().split('   ')
        result = ''
        for word in words:
            for code in word.split(' '):
                result += morse.get(code, '?')
            result += ' '
        log(f"Morse: {result.strip()[:100]}", "+")
        return result.strip()
    except:
        return ''


def crack_hash(hash_str):
    log("Trying hash crack with common wordlist...", "*")
    common_passwords = [
        'password', 'admin', 'flag', 'secret', '123456', 'letmein',
        'qwerty', 'abc123', 'monkey', 'master', 'dragon', 'sunshine',
        'princess', 'welcome', 'shadow', 'superman', 'michael', 'football',
        'pass', 'test', 'root', 'hello', 'world', 'hacker', 'ctf',
    ]
    hash_funcs = {
        32: [hashlib.md5],
        40: [hashlib.sha1],
        56: [hashlib.sha224],
        64: [hashlib.sha256],
        96: [hashlib.sha384],
        128: [hashlib.sha512],
    }
    funcs = hash_funcs.get(len(hash_str.strip()), [hashlib.md5, hashlib.sha1, hashlib.sha256])

    for password in common_passwords:
        for fn in funcs:
            if fn(password.encode()).hexdigest() == hash_str.lower().strip():
                log(f"Hash cracked! {hash_str} = '{password}'", "+")
                return password
    log("Hash not in common wordlist. Try rockyou.txt with hashcat.", "!")
    return None


# ── RSA Helpers ───────────────────────────────────────────

def rsa_small_e(n, e, c):
    log("Trying RSA small e cube root attack (e=3)...", "*")
    try:
        import gmpy2
        m, exact = gmpy2.iroot(c, e)
        if exact:
            plaintext = m.to_bytes((m.bit_length() + 7) // 8, 'big')
            decoded = plaintext.decode('utf-8', errors='ignore')
            log(f"RSA small e result: {decoded[:100]}", "+")
            return decoded
    except ImportError:
        log("gmpy2 not installed. Run: pip install gmpy2", "!")
    except:
        pass
    return None


# ── Main ──────────────────────────────────────────────────

def solve(data):
    print(f"""
\033[92m╔══════════════════════════════════════╗
║   CTF CRYPTO AUTO-SOLVER             ║
╚══════════════════════════════════════╝\033[0m
Input: {data[:60]}...
""")
    all_results = []

    all_results.extend(try_all_bases(data))
    all_results.append(('rot13', try_rot13(data)))
    all_results.append(('atbash', try_atbash(data)))
    all_results.extend(try_caesar(data))
    all_results.extend(try_xor(data))
    all_results.extend(try_vigenere(data))
    all_results.append(('morse', try_morse(data)))

    if all(c in '0123456789abcdefABCDEF' for c in data.strip()) and len(data.strip()) in [32, 40, 64]:
        crack_hash(data.strip())

    print("\n\033[92m── RESULTS ──")
    flags = [(name, val) for name, val in all_results if val and looks_like_flag(val)]
    if flags:
        for name, val in flags:
            print(f"  FLAG via {name}: {val}")
    else:
        print("  No flag auto-detected.")
        print("  Top readable results:")
        readable = [(n, v) for n, v in all_results if v and isinstance(v, str) and v.isprintable() and len(v) > 3][:5]
        for n, v in readable:
            print(f"    [{n}] {v[:80]}")
    print("\033[0m")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        solve(sys.argv[1])
    else:
        data = input("[?] Enter ciphertext/encoded data: ").strip()
        solve(data)
