#!/usr/bin/env python3
"""
forensics_solver.py — CTF Forensics Auto-Solver
Usage: python forensics_solver.py <file>
Covers: File signatures, steganography, metadata, hidden data, PCAP, memory
"""

import sys
import os
import re
import struct
import string
import subprocess

FILE = sys.argv[1] if len(sys.argv) > 1 else input("[?] Enter file path: ").strip()
FLAGS_FOUND = []
FLAG_PATTERNS = [r'HTB\{[^}]+\}', r'THM\{[^}]+\}', r'picoCTF\{[^}]+\}',
                 r'FLAG\{[^}]+\}', r'flag\{[^}]+\}', r'CTF\{[^}]+\}']

def log(msg, level="*"):
    colors = {"*": "\033[94m", "+": "\033[92m", "-": "\033[91m", "!": "\033[93m"}
    print(f"{colors.get(level,'')}[{level}] {msg}\033[0m")

def find_flags(data):
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='ignore')
    found = []
    for p in FLAG_PATTERNS:
        matches = re.findall(p, data, re.IGNORECASE)
        for m in matches:
            if m not in FLAGS_FOUND:
                FLAGS_FOUND.append(m)
                found.append(m)
                log(f"FLAG: {m}", "+")
    return found

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout + r.stderr
    except:
        return ""

# ── File Identification ───────────────────────────────────

def identify_file():
    log(f"Identifying file: {FILE}", "*")
    signatures = {
        b'\x89PNG': 'PNG image',
        b'\xFF\xD8\xFF': 'JPEG image',
        b'GIF8': 'GIF image',
        b'PK\x03\x04': 'ZIP archive',
        b'PK\x05\x06': 'ZIP archive (empty)',
        b'\x1f\x8b': 'GZIP compressed',
        b'BZh': 'BZIP2 compressed',
        b'\xfd7zXZ': 'XZ compressed',
        b'Rar!': 'RAR archive',
        b'\x7fELF': 'ELF executable',
        b'MZ': 'Windows PE executable',
        b'%PDF': 'PDF document',
        b'\xd0\xcf\x11\xe0': 'Microsoft Office (old)',
        b'RIFF': 'WAV/AVI file',
        b'ftyp': 'MP4 video',
        b'OggS': 'OGG audio',
        b'\xff\xfb': 'MP3 audio',
        b'IDAT': 'PNG data chunk',
        b'<?xml': 'XML document',
        b'<!DOCTYPE': 'HTML document',
    }
    with open(FILE, 'rb') as f:
        header = f.read(16)
    for sig, name in signatures.items():
        if header.startswith(sig) or sig in header:
            log(f"File type detected: {name}", "+")
            return name
    log("Unknown file type — checking with 'file' command", "!")
    out = run_cmd(['file', FILE])
    log(out.strip(), "!")
    return out


def get_file_size():
    size = os.path.getsize(FILE)
    log(f"File size: {size} bytes ({size/1024:.2f} KB)")


# ── String Extraction ─────────────────────────────────────

def extract_strings(min_len=4):
    log("Extracting strings...", "*")
    with open(FILE, 'rb') as f:
        data = f.read()

    printable = set(bytes(string.printable, 'ascii'))
    results = []
    current = []
    for byte in data:
        if byte in printable:
            current.append(chr(byte))
        else:
            if len(current) >= min_len:
                s = ''.join(current)
                results.append(s)
                find_flags(s)
            current = []

    log(f"Found {len(results)} strings", "+")
    interesting = [s for s in results if any(k in s.lower() for k in
                   ['flag', 'password', 'secret', 'key', 'admin', 'token', 'http'])]
    for s in interesting[:20]:
        log(f"  Interesting string: {s[:100]}", "!")
    return results


# ── Metadata Extraction ───────────────────────────────────

def extract_metadata():
    log("Extracting metadata...", "*")
    out = run_cmd(['exiftool', FILE])
    if out:
        log("ExifTool output:", "+")
        print(out[:1000])
        find_flags(out)
    else:
        log("exiftool not installed. Run: sudo pacman -S perl-image-exiftool", "!")


# ── Steganography Checks ──────────────────────────────────

def check_steghide():
    log("Trying steghide with common passwords...", "*")
    passwords = ['', 'password', 'flag', 'secret', 'admin', 'ctf', 'stego',
                 'hidden', '123456', 'abc123', FILE.split('.')[0]]
    for pwd in passwords:
        out = run_cmd(['steghide', 'extract', '-sf', FILE, '-p', pwd, '-xf', '/tmp/steg_out.txt'])
        if 'wrote' in out.lower() or 'extracted' in out.lower():
            log(f"Steghide extracted with password: '{pwd}'", "+")
            if os.path.exists('/tmp/steg_out.txt'):
                with open('/tmp/steg_out.txt', 'r', errors='ignore') as f:
                    content = f.read()
                log(f"Content: {content[:200]}", "+")
                find_flags(content)
                return
    log("Steghide: nothing found with common passwords", "-")


def check_binwalk():
    log("Running binwalk to find embedded files...", "*")
    out = run_cmd(['binwalk', FILE])
    if out:
        print(out[:1000])
        find_flags(out)
        if any(x in out for x in ['Zip', 'JPEG', 'PNG', 'ELF', 'gzip']):
            log("Embedded files found! Extracting...", "+")
            run_cmd(['binwalk', '--extract', '--quiet', FILE])
            extract_dir = f"_{os.path.basename(FILE)}.extracted"
            if os.path.exists(extract_dir):
                log(f"Extracted to: {extract_dir}", "+")
    else:
        log("binwalk not installed. Run: sudo pacman -S binwalk", "!")


def check_lsb_png():
    log("Checking PNG LSB steganography...", "*")
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(FILE)
        arr = np.array(img)
        bits = arr.flatten() & 1
        chars = []
        for i in range(0, len(bits) - 7, 8):
            byte = int(''.join(str(b) for b in bits[i:i+8]), 2)
            if 32 <= byte <= 126:
                chars.append(chr(byte))
            elif byte == 0:
                break
        result = ''.join(chars)
        if result and len(result) > 4:
            log(f"LSB data: {result[:200]}", "+")
            find_flags(result)
    except ImportError:
        log("PIL not installed. Run: pip install Pillow numpy", "!")
    except Exception as e:
        log(f"LSB check failed: {e}", "-")


def check_zsteg():
    log("Running zsteg on PNG...", "*")
    out = run_cmd(['zsteg', FILE])
    if out and 'error' not in out.lower():
        print(out[:500])
        find_flags(out)
    else:
        log("zsteg not installed. Run: gem install zsteg", "!")


# ── PCAP Analysis ─────────────────────────────────────────

def analyze_pcap():
    log("Analyzing PCAP file...", "*")
    out = run_cmd(['strings', FILE])
    find_flags(out)

    tshark_out = run_cmd(['tshark', '-r', FILE, '-T', 'fields',
                          '-e', 'http.request.uri', '-e', 'http.file_data'])
    if tshark_out:
        log("HTTP traffic found:", "+")
        print(tshark_out[:500])
        find_flags(tshark_out)

    dns_out = run_cmd(['tshark', '-r', FILE, '-Y', 'dns', '-T', 'fields',
                       '-e', 'dns.qry.name'])
    if dns_out:
        log("DNS queries:", "+")
        print(dns_out[:500])
        find_flags(dns_out)


# ── Hidden Data Checks ────────────────────────────────────

def check_appended_data():
    log("Checking for appended data after EOF...", "*")
    with open(FILE, 'rb') as f:
        data = f.read()

    eof_markers = {
        b'\xff\xd9': 'JPEG',
        b'IEND\xaeB`\x82': 'PNG',
        b'</html>': 'HTML',
    }
    for marker, ftype in eof_markers.items():
        idx = data.rfind(marker)
        if idx != -1 and idx < len(data) - len(marker):
            appended = data[idx + len(marker):]
            if appended.strip():
                log(f"Data after {ftype} EOF marker: {appended[:200]}", "+")
                find_flags(appended.decode('utf-8', errors='ignore'))


def check_zip_comment():
    log("Checking ZIP comment for hidden data...", "*")
    try:
        import zipfile
        with zipfile.ZipFile(FILE) as z:
            if z.comment:
                comment = z.comment.decode('utf-8', errors='ignore')
                log(f"ZIP comment: {comment}", "+")
                find_flags(comment)
            for name in z.namelist():
                log(f"ZIP entry: {name}", "!")
                with z.open(name) as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    find_flags(content)
    except Exception as e:
        pass


def check_pdf():
    log("Analyzing PDF for hidden content...", "*")
    out = run_cmd(['pdftotext', FILE, '-'])
    if out:
        find_flags(out)
        log(f"PDF text: {out[:300]}", "+")
    strings_out = run_cmd(['strings', FILE])
    find_flags(strings_out)


# ── Main ──────────────────────────────────────────────────

def solve():
    print(f"""
\033[92m╔══════════════════════════════════════╗
║   CTF FORENSICS AUTO-SOLVER          ║
║   File: {os.path.basename(FILE):<30}║
╚══════════════════════════════════════╝\033[0m
""")
    if not os.path.exists(FILE):
        log(f"File not found: {FILE}", "-")
        return

    file_type = identify_file()
    get_file_size()
    extract_strings()
    extract_metadata()
    check_appended_data()
    check_binwalk()
    check_zip_comment()

    ft = file_type.lower() if file_type else ''
    if 'png' in ft or 'jpeg' in ft or 'image' in ft:
        check_steghide()
        check_zsteg()
        check_lsb_png()
    elif 'pcap' in FILE.lower() or 'cap' in FILE.lower():
        analyze_pcap()
    elif 'pdf' in ft or FILE.endswith('.pdf'):
        check_pdf()
    elif 'zip' in ft or FILE.endswith('.zip'):
        check_zip_comment()

    print("\n\033[92m── RESULTS ──")
    if FLAGS_FOUND:
        for f in FLAGS_FOUND:
            print(f"  ✓ FLAG: {f}")
    else:
        print("  No flags auto-detected.")
        print("  Try: stegsolve, Audacity (audio), Volatility (memory dump)")
    print("\033[0m")


if __name__ == "__main__":
    solve()
