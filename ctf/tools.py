"""
ctf/tools.py — Full CTF tool suite for JARVIS
Wraps every tool CTFAgent uses: pwntools, binwalk, hashcat, volatility, etc.
Drop into ~/jarvis/ctf/tools.py

Install deps:
  pip install pwntools pycryptodome --break-system-packages
  sudo pacman -S binwalk hashcat john volatility3 ghidra gdb
  pip install python-magic --break-system-packages
"""

import subprocess
import os
import re
import base64
import binascii
from pathlib import Path
try:
    import osint
except ImportError:
    from ctf import osint


# ═══════════════════════════════════════════════════════════════
#  UNIVERSAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _run(cmd: list, timeout: int = 60, input_data: str = None) -> str:
    """Run subprocess, return stdout+stderr as string."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout,
            input=input_data
        )
        out = result.stdout + result.stderr
        return out.strip() or "[No output]"
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT] {' '.join(cmd)} exceeded {timeout}s"
    except FileNotFoundError:
        return f"[NOT INSTALLED] {cmd[0]} — install with: sudo pacman -S {cmd[0]}"
    except Exception as e:
        return f"[ERROR] {str(e)}"


def detect_file_type(filepath: str) -> str:
    """Run `file` command on a file."""
    return _run(["file", filepath])


def run_strings(filepath: str, min_len: int = 6) -> str:
    """Extract printable strings from binary."""
    return _run(["strings", f"-n{min_len}", filepath])


def run_xxd(filepath: str, bytes_count: int = 256) -> str:
    """Hex dump first N bytes of file."""
    return _run(["xxd", "-l", str(bytes_count), filepath])


# ═══════════════════════════════════════════════════════════════
#  WEB TOOLS  (already in JARVIS — kept for completeness)
# ═══════════════════════════════════════════════════════════════

def run_nikto(target_url: str) -> str:
    """Nikto web vulnerability scanner."""
    return _run(["nikto", "-h", target_url, "-maxtime", "60s"], timeout=90)


def run_wfuzz(target_url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt") -> str:
    """Wfuzz directory/parameter fuzzer."""
    return _run(["wfuzz", "-c", "-z", f"file,{wordlist}",
                 "--hc", "404", f"{target_url}/FUZZ"], timeout=60)


def run_curl_headers(target_url: str) -> str:
    """Fetch HTTP headers for fingerprinting."""
    return _run(["curl", "-sI", "--max-time", "10", target_url])


def run_curl_source(target_url: str) -> str:
    """Fetch page source."""
    return _run(["curl", "-sL", "--max-time", "15", target_url])


# ═══════════════════════════════════════════════════════════════
#  CRYPTO TOOLS
# ═══════════════════════════════════════════════════════════════

def run_hashcat(hash_value: str, mode: int = 0,
                wordlist: str = "/usr/share/wordlists/rockyou.txt") -> str:
    """Crack hash with hashcat. Common modes: 0=MD5, 100=SHA1, 1400=SHA256, 1800=SHA512crypt."""
    hashfile = "/tmp/jarvis_hash.txt"
    with open(hashfile, "w") as f:
        f.write(hash_value.strip())
    result = _run(["hashcat", "-m", str(mode), hashfile, wordlist,
                   "--quiet", "--force"], timeout=120)
    # Extract cracked value
    if ":" in result:
        for line in result.splitlines():
            if hash_value.lower() in line.lower() and ":" in line:
                return f"CRACKED: {line}"
    return result


def run_john(hashfile: str, wordlist: str = "/usr/share/wordlists/rockyou.txt") -> str:
    """Run John the Ripper on a hash file."""
    return _run(["john", hashfile, f"--wordlist={wordlist}"], timeout=120)


def identify_hash(hash_value: str) -> str:
    """Use hashid to identify hash type."""
    return _run(["hashid", hash_value])


def xor_decode(data: bytes, key: bytes) -> bytes:
    """XOR decode bytes with repeating key."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def xor_single_byte_bruteforce(ciphertext: bytes) -> list:
    """Try all 256 single-byte XOR keys, return printable results."""
    results = []
    for key in range(256):
        try:
            decoded = bytes(b ^ key for b in ciphertext)
            text = decoded.decode("utf-8", errors="replace")
            # Score: count printable ASCII
            score = sum(1 for c in text if 32 <= ord(c) < 127)
            if score > len(ciphertext) * 0.7:
                results.append({"key": hex(key), "text": text[:200], "score": score})
        except Exception:
            continue
    return sorted(results, key=lambda x: x["score"], reverse=True)[:5]


def try_encodings(data: str) -> dict:
    """Try common encodings: base64, hex, rot13, binary, morse."""
    results = {}
    # Base64
    try:
        results["base64"] = base64.b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        pass
    # Hex
    try:
        results["hex"] = bytes.fromhex(data.replace(" ", "")).decode("utf-8", errors="replace")
    except Exception:
        pass
    # ROT13
    results["rot13"] = data.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
    ))
    # Base32
    try:
        results["base32"] = base64.b32decode(data + "=" * (8 - len(data) % 8) if len(data) % 8 else data).decode()
    except Exception:
        pass
    # Binary
    try:
        bits = data.replace(" ", "")
        if all(c in "01" for c in bits) and len(bits) % 8 == 0:
            results["binary"] = "".join(chr(int(bits[i:i+8], 2)) for i in range(0, len(bits), 8))
    except Exception:
        pass
    return {k: v for k, v in results.items() if v and v != data}


def run_rsa_ctf_tool(n: int = None, e: int = None,
                      c: int = None, pubkey_file: str = None) -> str:
    """Run RsaCtfTool for common RSA attacks."""
    cmd = ["RsaCtfTool.py"]
    if pubkey_file:
        cmd += ["--publickey", pubkey_file, "--private"]
    elif n and e:
        cmd += ["-n", str(n), "-e", str(e)]
        if c:
            cmd += ["--decrypt", str(c)]
        cmd += ["--attack", "all"]
    return _run(cmd, timeout=120)


# ═══════════════════════════════════════════════════════════════
#  FORENSICS TOOLS
# ═══════════════════════════════════════════════════════════════

def run_binwalk(filepath: str, extract: bool = False) -> str:
    """Analyze/extract embedded files from binary."""
    cmd = ["binwalk"]
    if extract:
        cmd += ["-e", "--run-as=root"]
    cmd.append(filepath)
    return _run(cmd, timeout=60)


def run_exiftool(filepath: str) -> str:
    """Extract metadata from files."""
    return _run(["exiftool", filepath])


def run_foremost(filepath: str, output_dir: str = "/tmp/foremost_out") -> str:
    """Carve files from binary using foremost."""
    os.makedirs(output_dir, exist_ok=True)
    result = _run(["foremost", "-o", output_dir, filepath], timeout=60)
    # List what was carved
    carved = []
    for root, dirs, files in os.walk(output_dir):
        for f in files:
            if f != "audit.txt":
                carved.append(os.path.join(root, f))
    if carved:
        result += f"\nCarved files:\n" + "\n".join(carved)
    return result


def run_steghide_extract(filepath: str, password: str = "") -> str:
    """Extract steganographic data from image."""
    return _run(["steghide", "extract", "-sf", filepath,
                 "-p", password, "-f"], timeout=30)


def run_zsteg(filepath: str) -> str:
    """Detect steganography in PNG/BMP files (LSB, etc)."""
    return _run(["zsteg", filepath], timeout=30)


def run_stegseek(filepath: str, wordlist: str = "/usr/share/wordlists/rockyou.txt") -> str:
    """Fast steghide password brute force."""
    return _run(["stegseek", filepath, wordlist], timeout=60)


def run_tshark_streams(pcap_file: str) -> str:
    """Extract TCP streams from PCAP."""
    return _run(["tshark", "-r", pcap_file,
                 "-q", "-z", "conv,tcp"], timeout=30)


def run_tshark_follow(pcap_file: str, stream_id: int = 0) -> str:
    """Follow specific TCP stream."""
    return _run(["tshark", "-r", pcap_file,
                 "-z", f"follow,tcp,ascii,{stream_id}", "-q"], timeout=30)


def run_tshark_http(pcap_file: str) -> str:
    """Extract HTTP objects from PCAP."""
    outdir = "/tmp/pcap_http"
    os.makedirs(outdir, exist_ok=True)
    result = _run(["tshark", "-r", pcap_file,
                   "--export-objects", f"http,{outdir}"], timeout=30)
    files = os.listdir(outdir)
    return result + f"\nExtracted HTTP objects: {files}"


def run_volatility(dump_file: str, plugin: str, profile: str = "") -> str:
    """Run Volatility3 plugin on memory dump."""
    cmd = ["vol", "-f", dump_file]
    if profile:
        cmd += ["--profile", profile]
    cmd.append(f"windows.{plugin}" if not "." in plugin else plugin)
    return _run(cmd, timeout=120)


def run_volatility_pslist(dump_file: str) -> str:
    return run_volatility(dump_file, "pslist.PsList")

def run_volatility_netscan(dump_file: str) -> str:
    return run_volatility(dump_file, "netscan.NetScan")

def run_volatility_filescan(dump_file: str) -> str:
    return run_volatility(dump_file, "filescan.FileScan")

def run_volatility_dumpfiles(dump_file: str, addr: str) -> str:
    return run_volatility(dump_file, f"dumpfiles.DumpFiles --physaddr {addr}")


# ═══════════════════════════════════════════════════════════════
#  PWN / BINARY EXPLOITATION TOOLS
# ═══════════════════════════════════════════════════════════════

def run_checksec(binary_path: str) -> str:
    """Check binary security properties."""
    result = _run(["checksec", "--file", binary_path])
    if "[NOT INSTALLED]" in result:
        # Try pwntools checksec
        return _run(["python3", "-c",
                     f"from pwn import *; e=ELF('{binary_path}'); "
                     f"print(e.checksec())"])
    return result


def run_ropgadget(binary_path: str) -> str:
    """Find ROP gadgets in binary."""
    return _run(["ROPgadget", "--binary", binary_path,
                 "--rop", "--nojop"], timeout=30)


def run_one_gadget(libc_path: str) -> str:
    """Find one-gadget RCE in libc."""
    return _run(["one_gadget", libc_path], timeout=30)


def run_gdb_info(binary_path: str, commands: str = "info functions\ninfo security") -> str:
    """Run GDB commands and return output."""
    gdb_script = "/tmp/jarvis_gdb.txt"
    with open(gdb_script, "w") as f:
        f.write(commands + "\nquit\n")
    return _run(["gdb", "-batch", "-x", gdb_script, binary_path], timeout=30)


def run_ltrace(binary_path: str, args: str = "") -> str:
    """Trace library calls."""
    cmd = ["ltrace", "-s", "200"]
    if args:
        cmd += args.split()
    cmd.append(binary_path)
    return _run(cmd, timeout=15)


def run_strace(binary_path: str, args: str = "") -> str:
    """Trace system calls."""
    cmd = ["strace"]
    if args:
        cmd += args.split()
    cmd.append(binary_path)
    return _run(cmd, timeout=15)


def generate_cyclic_pattern(length: int = 200) -> str:
    """Generate de Bruijn cyclic pattern for offset finding."""
    try:
        from pwn import cyclic
        return cyclic(length).decode()
    except ImportError:
        # Manual fallback
        alpha = "abcdefghijklmnopqrstuvwxyz"
        pattern = ""
        for a in alpha:
            for b in alpha:
                for c in alpha:
                    for d in alpha:
                        pattern += a + b + c + d
                        if len(pattern) >= length:
                            return pattern[:length]
        return pattern[:length]


def find_cyclic_offset(value: str) -> str:
    """Find offset of cyclic pattern value."""
    try:
        from pwn import cyclic_find
        val = int(value, 16) if value.startswith("0x") else int(value)
        offset = cyclic_find(val)
        return f"Offset: {offset} bytes"
    except Exception as e:
        return f"[ERROR] {e} — install pwntools: pip install pwntools"


def generate_pwn_template(binary_path: str, remote_host: str = "",
                           remote_port: int = 0) -> str:
    """Generate a pwntools exploit template."""
    binary_name = Path(binary_path).name
    remote_section = ""
    if remote_host:
        remote_section = f"""
# Remote connection
# p = remote('{remote_host}', {remote_port})"""

    return f'''#!/usr/bin/env python3
from pwn import *

# Binary setup
context.binary = '{binary_path}'
context.log_level = 'info'
elf = ELF('{binary_path}', checksec=False)

# Load libc (if needed)
# libc = ELF('./libc.so.6', checksec=False)
{remote_section}
# Local process
p = process('{binary_path}')
# gdb.attach(p, "b main")  # Uncomment to attach GDB

# ── Exploit ────────────────────────────────────────────────────

# Step 1: Find offset
# pattern = cyclic(200)
# p.sendline(pattern)
# core = p.corefile  # then: cyclic_find(core.read(core.rsp, 4))

offset = 0  # TODO: replace with actual offset

# Step 2: Build payload
padding = b"A" * offset

# For ret2libc:
# payload = padding + p64(rop.ret) + p64(rop.rdi.address) + p64(next(elf.search(b'/bin/sh'))) + p64(elf.plt.system)

# For basic overflow:
payload = padding + p64(elf.sym.win) if hasattr(elf.sym, 'win') else padding

# Step 3: Send
p.sendline(payload)
p.interactive()
'''


# ═══════════════════════════════════════════════════════════════
#  REVERSE ENGINEERING TOOLS
# ═══════════════════════════════════════════════════════════════

def run_objdump(binary_path: str, function: str = "main") -> str:
    """Disassemble binary with objdump."""
    return _run(["objdump", "-d", "-M", "intel", binary_path], timeout=30)


def run_ghidra_headless(binary_path: str, project_dir: str = "/tmp/ghidra_proj") -> str:
    """Run Ghidra headless analysis (requires ghidra in PATH)."""
    os.makedirs(project_dir, exist_ok=True)
    project_name = Path(binary_path).stem
    # Script to export decompiled C
    script = "/tmp/ghidra_export.py"
    with open(script, "w") as f:
        f.write("""
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
ifc = DecompInterface()
ifc.openProgram(currentProgram)
for f in currentProgram.getFunctionManager().getFunctions(True):
    r = ifc.decompileFunction(f, 30, ConsoleTaskMonitor())
    if r.decompileCompleted():
        print("=" * 40)
        print(f"Function: {f.getName()}")
        print(r.getDecompiledFunction().getC())
""")
    cmd = ["ghidra_headless" if os.path.exists("/usr/bin/ghidra_headless") else
           "/opt/ghidra/support/analyzeHeadless",
           project_dir, project_name,
           "-import", binary_path,
           "-postScript", script,
           "-deleteProject"]
    return _run(cmd, timeout=180)


def decompile_python_pyc(pyc_file: str) -> str:
    """Decompile Python .pyc bytecode."""
    return _run(["pycdc", pyc_file], timeout=30)


def run_upx_unpack(binary_path: str) -> str:
    """Unpack UPX-packed binary."""
    output_path = binary_path + "_unpacked"
    return _run(["upx", "-d", binary_path, "-o", output_path], timeout=30)


def get_challenge_urls(text: str) -> str:
    """Extract URLs and connection strings (like netcat) from challenge description."""
    urls = re.findall(r'https?://[^\s)\]]+', text)
    nc = re.findall(r'nc\s+[^\s]+\s+\d+', text)
    ssh = re.findall(r'ssh\s+[^\s]+@[^\s]+', text)
    
    found = []
    if urls: found.append(f"URLs: {', '.join(urls)}")
    if nc: found.append(f"Netcat: {', '.join(nc)}")
    if ssh: found.append(f"SSH: {', '.join(ssh)}")
    
    return "\n".join(found) if found else "No URLs or connection strings found in description."


# ═══════════════════════════════════════════════════════════════
#  FLAG DETECTION
# ═══════════════════════════════════════════════════════════════

FLAG_PATTERNS = [
    r"flag\{[^}]+\}",
    r"FLAG\{[^}]+\}",
    r"CTF\{[^}]+\}",
    r"ctf\{[^}]+\}",
    r"picoCTF\{[^}]+\}",
    r"HTB\{[^}]+\}",
    r"DUCTF\{[^}]+\}",
    r"darkCTF\{[^}]+\}",
    r"[a-zA-Z0-9_]+CTF\{[^}]+\}",
    r"[a-zA-Z0-9_]+\{[A-Za-z0-9_!@#$%^&*\-+=.,?/\\]+\}",
]

def find_flag(text: str) -> str | None:
    """Search text for any known CTF flag format."""
    for pattern in FLAG_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0]
    return None


def find_all_flags(text: str) -> list:
    """Find all flag-like strings in text."""
    found = []
    for pattern in FLAG_PATTERNS:
        found.extend(re.findall(pattern, text, re.IGNORECASE))
    return list(set(found))


# ═══════════════════════════════════════════════════════════════
#  CLOUD SECURITY TOOLS
# ═══════════════════════════════════════════════════════════════

def inspect_aws_creds(dummy_arg: str = "") -> str:
    """Scan common paths for AWS credentials and configs."""
    paths = [
        os.path.expanduser("~/.aws/credentials"),
        os.path.expanduser("~/.aws/config"),
        "/tmp/credentials",
        "./credentials"
    ]
    found = []
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    content = f.read()
                # Clean up/mask keys slightly but show profiles
                masked = []
                for line in content.splitlines():
                    if "secret_access_key" in line or "aws_access_key_id" in line:
                        parts = line.split("=")
                        if len(parts) == 2:
                            val = parts[1].strip()
                            masked.append(f"{parts[0]}= {val[:4]}...{val[-4:] if len(val) > 8 else ''}")
                        else:
                            masked.append(line)
                    else:
                        masked.append(line)
                found.append(f"--- File: {p} ---\n" + "\n".join(masked))
            except Exception as e:
                found.append(f"[ERROR] Reading {p}: {e}")
    if not found:
        return "No AWS credential or config files found in standard locations."
    return "\n\n".join(found)


def inspect_kubeconfig(dummy_arg: str = "") -> str:
    """Scan ~/.kube/config or common paths for Kubeconfig context details."""
    paths = [
        os.path.expanduser("~/.kube/config"),
        "/tmp/kubeconfig",
        "./kubeconfig"
    ]
    found = []
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    content = f.read()
                # Extract clusters, contexts, users without listing full private keys
                clusters = re.findall(r'server:\s*(https?://[^\s]+)', content)
                contexts = re.findall(r'name:\s*([^\s]+)\s*\n\s*context:', content)
                users = re.findall(r'name:\s*([^\s]+)\s*\n\s*user:', content)
                info = [
                    f"Clusters: {clusters}",
                    f"Contexts: {contexts}",
                    f"Users: {users}"
                ]
                found.append(f"--- File: {p} ---\n" + "\n".join(info))
            except Exception as e:
                found.append(f"[ERROR] Reading {p}: {e}")
    if not found:
        return "No Kubeconfig files found in standard locations."
    return "\n\n".join(found)


def query_metadata_endpoint(platform: str = "aws") -> str:
    """
    Query cloud metadata endpoints (IMDSv1/v2, GCP metadata, Azure metadata).
    If offline or external, returns simulated/realistic response.
    """
    platform = platform.lower().strip()
    import requests
    
    if platform in ("aws", "imds"):
        # AWS IMDSv2 Token query followed by meta-data
        try:
            # Try to query IMDSv2 locally
            token_res = requests.put("http://169.254.169.254/latest/api/token", 
                                     headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
                                     timeout=2)
            if token_res.status_code == 200:
                token = token_res.text
                meta_res = requests.get("http://169.254.169.254/latest/meta-data/",
                                        headers={"X-aws-ec2-metadata-token": token},
                                        timeout=2)
                return f"[AWS IMDSv2 Active]\n{meta_res.text}"
        except Exception:
            pass
            
        # Try IMDSv1
        try:
            meta_res = requests.get("http://169.254.169.254/latest/meta-data/", timeout=2)
            if meta_res.status_code == 200:
                return f"[AWS IMDSv1 Active]\n{meta_res.text}"
        except Exception:
            pass
            
        # Simulated response if not in AWS
        return (
            "[AWS IMDS SIMULATED RESPONSE]\n"
            "Endpoints available under http://169.254.169.254/latest/meta-data/:\n"
            "  ami-id\n"
            "  hostname\n"
            "  instance-id\n"
            "  instance-type\n"
            "  iam/security-credentials/\n"
            "  iam/security-credentials/ec2-admin-role (Simulated keys: AccessKeyID=ASIA..., SecretAccessKey=xyz...)"
        )
        
    elif platform in ("gcp", "google"):
        try:
            meta_res = requests.get("http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token", 
                                    headers={"Metadata-Flavor": "Google"}, timeout=2)
            if meta_res.status_code == 200:
                return f"[GCP Metadata Active]\n{meta_res.text}"
        except Exception:
            pass
            
        return (
            "[GCP METADATA SIMULATED RESPONSE]\n"
            "Query default token via: http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token\n"
            "Simulated response:\n"
            "{\n"
            "  \"access_token\": \"ya29.c.Ko8B0wc...\",\n"
            "  \"expires_in\": 3599,\n"
            "  \"token_type\": \"Bearer\"\n"
            "}"
        )
        
    elif platform in ("azure", "microsoft"):
        try:
            meta_res = requests.get("http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01",
                                    headers={"Metadata": "true"}, timeout=2)
            if meta_res.status_code == 200:
                return f"[Azure Metadata Active]\n{meta_res.text}"
        except Exception:
            pass
            
        return (
            "[Azure METADATA SIMULATED RESPONSE]\n"
            "Query identity token via: http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01\n"
            "Simulated response:\n"
            "{\n"
            "  \"access_token\": \"eyJhbGciOiJSUzI1NiIs...\",\n"
            "  \"expires_in\": \"3599\",\n"
            "  \"token_type\": \"Bearer\"\n"
            "}"
        )
    return f"Unknown cloud platform: {platform}. Supported: aws, gcp, azure."


def inspect_docker_env(dummy_arg: str = "") -> str:
    """Inspect environment for Docker daemon sockets, service accounts, and container info."""
    details = []
    # Check docker socket
    docker_sock = "/var/run/docker.sock"
    if os.path.exists(docker_sock):
        details.append(f"[DANGER] Docker socket exists at {docker_sock} (Write permission: {os.access(docker_sock, os.W_OK)})")
    else:
        details.append("Docker socket not found at /var/run/docker.sock")
        
    # Check Kubernetes service account token
    k8s_token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    if os.path.exists(k8s_token_path):
        try:
            with open(k8s_token_path, "r") as f:
                token = f.read().strip()
            details.append(f"[INFO] Kubernetes Service Account token found at {k8s_token_path}:\nToken: {token[:20]}...{token[-20:] if len(token) > 40 else ''}")
        except Exception as e:
            details.append(f"Kubernetes token exists but could not be read: {e}")
    else:
        details.append("Kubernetes service account token not found in /var/run/secrets/kubernetes.io/")
        
    # Check environment variables
    env_keys = [k for k in os.environ.keys() if any(x in k.lower() for x in ("aws", "gcp", "azure", "docker", "kube", "secret", "token", "password", "key"))]
    if env_keys:
        details.append(f"Cloud/Secret Environment Variables: {env_keys}")
    else:
        details.append("No cloud/secret environment variables detected.")
        
    return "\n".join(details)


def scan_secrets(target_path: str) -> str:
    """Scan a file or directory for API keys, private keys, AWS/GCP secrets."""
    if not os.path.exists(target_path):
        return f"[ERROR] File or path does not exist: {target_path}"
        
    patterns = {
        "AWS Access Key": r'AKIA[A-Z0-9]{16}',
        "AWS Secret Key": r'[^A-Za-z0-9+/][A-Za-z0-9+/]{40}[^A-Za-z0-9+/]',
        "GCP Service Account": r'"type":\s*"service_account"',
        "Slack Token": r'xox[bapr]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}',
        "JWT Token": r'eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*',
        "Private Key": r'-----BEGIN[A-Z ]+PRIVATE KEY-----',
        "Generic Password/Secret Field": r'(?:password|secret|passwd|api_key|apikey|db_password)\s*[:=]\s*["\']([^"\']+)["\']'
    }
    
    found = []
    
    def scan_file(fpath):
        try:
            with open(fpath, "r", errors="ignore") as f:
                content = f.read()
            file_results = []
            for name, pattern in patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    file_results.append(f"  - {name}: {len(matches)} match(es)")
            if file_results:
                found.append(f"File: {fpath}\n" + "\n".join(file_results))
        except Exception as e:
            found.append(f"File: {fpath} - [ERROR] {e}")
            
    if os.path.isfile(target_path):
        scan_file(target_path)
    else:
        # Scan directory recursively (up to 50 files)
        file_count = 0
        for root, _, files in os.walk(target_path):
            for file in files:
                if file_count >= 50:
                    break
                fpath = os.path.join(root, file)
                # Ignore binaries/images
                if not any(fpath.endswith(ext) for ext in (".png", ".jpg", ".zip", ".tar", ".gz", ".exe", ".pdf", ".pyc", ".db")):
                    scan_file(fpath)
                    file_count += 1
                    
    if not found:
        return "No common secrets or API keys matched in target."
    return "\n\n".join(found)


# ═══════════════════════════════════════════════════════════════
#  ADDITIONAL CRYPTO & OSINT HELPERS
# ═══════════════════════════════════════════════════════════════

def decode_morse(code: str) -> str:
    """Decode Morse code string containing dots and dashes (separated by spaces)."""
    morse_dict = {
        '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
        '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L',
        '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R',
        '...': 'S', '-': 'T', '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X',
        '-.--': 'Y', '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
        '...--': '3', '....-': '4', '.....': '5', '-....': '6', '--...': '7',
        '---..': '8', '----.': '9', '/': ' ', '.-.-.-': '.', '--..--': ',',
        '---...': ':', '..--..': '?', '.----.': "'", '-....-': '-', '-..-.': '/',
        '-.--.': '(', '-.--.-': ')', '.-..-.': '"', '-...-': '=', '.-.-.': '+'
    }
    cleaned = code.strip().replace('/', ' / ')
    decoded = []
    for word in cleaned.split('   '):
        words_decoded = []
        for char in word.split():
            words_decoded.append(morse_dict.get(char, f"[{char}]"))
        decoded.append("".join(words_decoded))
    return " ".join(decoded)


def vigenere_solve(ciphertext: str, key_len: int = 4) -> str:
    """Solve Vigenere cipher if key length is known (or brute-forced)."""
    ciphertext = re.sub(r'[^A-Z]', '', ciphertext.upper())
    if len(ciphertext) == 0:
        return "Ciphertext is empty after filtering."
        
    try:
        k_len = int(key_len)
    except Exception:
        k_len = 4
        
    if k_len <= 0:
        return "Please specify a positive key length."
        
    # Solve for each position
    key = ""
    for i in range(k_len):
        slice_str = ciphertext[i::k_len]
        # Frequency analysis on slice
        counts = [0] * 26
        for char in slice_str:
            counts[ord(char) - ord('A')] += 1
            
        # Find best shift matching English letter distribution
        english_freqs = [0.0817, 0.0149, 0.0278, 0.0425, 0.1270, 0.0223, 0.0202,
                         0.0609, 0.0697, 0.0015, 0.0077, 0.0403, 0.0241, 0.0675,
                         0.0751, 0.0193, 0.0010, 0.0599, 0.0633, 0.0906, 0.0276,
                         0.0098, 0.0236, 0.0015, 0.0197, 0.0007]
        best_shift = 0
        best_score = float('-inf')
        for shift in range(26):
            score = 0
            for j in range(26):
                c_idx = (j + shift) % 26
                score += counts[c_idx] * english_freqs[j]
            if score > best_score:
                best_score = score
                best_shift = shift
        key += chr(ord('A') + best_shift)
        
    return f"Guessed Vigenere Key: {key}"


# ═══════════════════════════════════════════════════════════════
#  TOOL REGISTRY — maps tool names to callables
# ═══════════════════════════════════════════════════════════════

CTF_TOOLS = {
    # Universal
    "file":           detect_file_type,
    "strings":        run_strings,
    "xxd":            run_xxd,

    # Web (existing JARVIS tools + new)
    "curl":           run_curl_source,
    "nikto":          run_nikto,
    "curl_headers":   run_curl_headers,
    "curl_source":    run_curl_source,

    # Crypto
    "hashcat":        lambda h: run_hashcat(h),
    "john":           run_john,
    "identify_hash":  identify_hash,
    "xor_bruteforce": lambda d: str(xor_single_byte_bruteforce(d.encode())),
    "try_encodings":  lambda d: str(try_encodings(d)),
    "rsa_tool":       lambda f: run_rsa_ctf_tool(pubkey_file=f),
    "vigenere_solve": lambda d: vigenere_solve(d),

    # Forensics
    "binwalk":        run_binwalk,
    "binwalk_extract":lambda f: run_binwalk(f, extract=True),
    "exiftool":       run_exiftool,
    "foremost":       run_foremost,
    "steghide":       lambda f: run_steghide_extract(f),
    "zsteg":          run_zsteg,
    "stegseek":       run_stegseek,
    "tshark_streams": run_tshark_streams,
    "tshark_http":    run_tshark_http,
    "vol_pslist":     run_volatility_pslist,
    "vol_netscan":    run_volatility_netscan,
    "vol_filescan":   run_volatility_filescan,
    "decode_morse":   decode_morse,

    # Pwn
    "checksec":       run_checksec,
    "ropgadget":      run_ropgadget,
    "one_gadget":     run_one_gadget,
    "gdb":            run_gdb_info,
    "ltrace":         run_ltrace,
    "strace":         run_strace,
    "cyclic":         lambda n: generate_cyclic_pattern(int(n)),
    "cyclic_find":    find_cyclic_offset,
    "pwn_template":   generate_pwn_template,

    # Rev
    "objdump":        run_objdump,
    "ghidra":         run_ghidra_headless,
    "upx":            run_upx_unpack,
    "decompile_pyc":  decompile_python_pyc,

    # Flag detection
    "find_flag":      find_flag,
    "discover":       get_challenge_urls,

    # OSINT
    "subdomain_enum": osint.subdomain_enum,
    "dns_recon":      osint.dns_recon,
    "wayback_dump":   osint.wayback_dump,
    "dork_gen":       osint.dork_generator,
    "github_search":  osint.github_search,
    "shodan_lookup":  osint.shodan_lookup,

    # Cloud
    "inspect_aws_creds": inspect_aws_creds,
    "inspect_kubeconfig": inspect_kubeconfig,
    "query_metadata_endpoint": query_metadata_endpoint,
    "inspect_docker_env": inspect_docker_env,
    "scan_secrets":   scan_secrets,
}
