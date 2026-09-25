"""
ctf/rag.py — Two-Stage CTF RAG System
CTFAgent's key insight: generic RAG fails. CTF RAG needs:
  Stage 1 — category-level knowledge (what techniques exist for web/crypto/pwn)
  Stage 2 — challenge-specific recall (similar past solutions)
Drop into ~/jarvis/ctf/rag.py

Depends on your existing ChromaDB in memory/learning.py
Install: pip install chromadb sentence-transformers --break-system-packages
"""

import os
import json
from pathlib import Path

# ── Optional ChromaDB import ─────────────────────────────────────────────
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

CHROMA_PATH = os.path.expanduser("~/jarvis/memory/chromadb")
KNOWLEDGE_PATH = os.path.expanduser("~/jarvis/memory/ctf_knowledge")


# ═══════════════════════════════════════════════════════════════
#  STAGE 1 — CATEGORY KNOWLEDGE BASE
#  Built-in technique knowledge per category (no ChromaDB needed)
# ═══════════════════════════════════════════════════════════════

CATEGORY_KNOWLEDGE = {
    "web": """
WEB EXPLOITATION TECHNIQUES:
- SQL Injection: ' OR 1=1--, UNION SELECT, blind (boolean/time), error-based
- XSS: <script>alert(1)</script>, stored vs reflected, CSP bypass, DOM XSS
- IDOR: Change user ID in params/path, predict resource IDs (sequential, UUIDs)
- SSRF: Internal IP access via URL param, cloud metadata (169.254.169.254)
- Command Injection: ; id, | whoami, $(cmd), backticks, newline injection
- LFI/RFI: ../../../etc/passwd, php://filter/convert.base64-encode/resource=
- JWT: None algorithm, alg confusion (RS256→HS256), weak secret cracking
- SSTI: {{7*7}}, ${7*7}, #{7*7} — Jinja2/Twig/Freemarker templates
- Auth bypass: Default creds (admin:admin, root:root), SQLi in login, JWT forging
- XXE: External entity injection in XML parsers
TOOLS: sqlmap, ffuf, gobuster, burpsuite, nikto, curl
CHECK FIRST: source code, JS files, /robots.txt, /.git/, /admin, /api/
""",

    "crypto": """
CRYPTOGRAPHY TECHNIQUES:
- Classical: Caesar (shift), Vigenere (key-based), Rail fence, Atbash, Playfair
- Encoding: base64, base32, base58, hex, binary, ASCII, URL encode, morse code
- XOR: Single-byte brute force (256 attempts), multi-byte (Kasiski), known-plaintext
- Hash cracking: MD5/SHA1/SHA256/bcrypt → hashcat or john + rockyou wordlist
- RSA attacks: Small e (cube root), Wiener (small d), common modulus, Fermat (close primes)
- AES: ECB mode (penguin attack), padding oracle, weak IV reuse
- DES/3DES: Weak keys, meet-in-the-middle
APPROACH: CyberChef magic detect first → identify algorithm → find weakness → exploit
TOOLS: python3, pycryptodome, hashcat, john, RsaCtfTool, xortool, CyberChef
""",

    "pwn": """
BINARY EXPLOITATION TECHNIQUES:
STEP 1 ALWAYS: file + checksec + strings on binary
Protections and bypasses:
- NX disabled: Inject shellcode directly
- NX + no PIE + no ASLR: ret2libc with fixed addresses
- NX + PIE: Need leak (printf %p, GOT entry) → calculate base → ret2libc
- Stack canary: Need canary leak first (format string %X$p) → overwrite after
- Full RELRO: GOT is read-only → use ROP chains, one_gadget
Vulnerability classes:
- Buffer overflow: cyclic pattern → find offset → RIP/EIP control
- Format string: printf(buf) → %X$n for write, %X$p for read
- UAF: free() but keep pointer → reallocate to controlled data
- Heap: overflow into chunk header, tcache poisoning, fastbin attack
TOOLS: pwntools, ROPgadget, one_gadget, gdb+pwndbg, checksec
""",

    "forensics": """
FORENSICS TECHNIQUES:
STEP 1 ALWAYS: file + xxd + strings + exiftool on any file
Image forensics:
- PNG/JPG/BMP: Check LSB (zsteg, stegsolve), EXIF, appended data (binwalk)
- Password-protected: stegseek with rockyou, steghide extract -p ""
- File carving: binwalk -e, foremost, photorec
PCAP analysis:
- Follow TCP streams, look for credentials, file transfers, DNS queries
- tshark: filter by protocol, export objects (HTTP, SMB, FTP)
Memory dumps:
- volatility3: pslist, netscan, filescan, dumpfiles, cmdline, clipboard
- Look for: running processes, network connections, files, registry, passwords
Audio files:
- Spectrogram view in Sonic Visualizer or Audacity → flags often hidden visually
- Morse code in audio, DTMF tones
TOOLS: binwalk, exiftool, strings, volatility3, wireshark, tshark, zsteg, steghide
""",

    "rev": """
REVERSE ENGINEERING TECHNIQUES:
STEP 1: file → strings → ltrace/strace → static analysis (Ghidra)
Common patterns:
- strcmp/strncmp with hardcoded string → flag is the argument passed
- XOR encoding: find loop in Ghidra, extract key from constants, decode
- Custom base encoding: find alphabet string, reverse the encoding function
- Anti-debug: ptrace check → NOP it out in hex editor or LD_PRELOAD bypass
- UPX packed: upx -d binary → unpack then analyze
- Python bytecode: .pyc files → pycdc or uncompyle6 to decompile
- Custom VM: map the opcode table, trace interpreter execution
Static analysis workflow (Ghidra):
1. Run auto-analysis
2. Find main(), rename variables
3. Find comparison/validation functions
4. Understand the algorithm
5. Write inverse in Python
TOOLS: Ghidra, gdb+pwndbg, ltrace, strace, strings, objdump, upx, python3
""",

    "misc": """
MISCELLANEOUS TECHNIQUES:
Steganography (non-image):
- Text: zero-width characters, whitespace encoding, unicode homoglyphs
- Audio: spectrogram, morse, DTMF, LSB in WAV
QR/Barcodes: zbarimg, bardecode, online decoders
Scripting challenges: automate with Python, handle binary protocols with pwntools
Jail breaks: import os; os.system('cat flag'), __import__, builtins bypass
Network: custom protocols → Wireshark decode, manual implementation
TOOLS: python3, curl, nmap, Sonic Visualizer, zbarimg, exiftool
""",

    "cloud": """
CLOUD SECURITY & EXPLOITATION TECHNIQUES:
AWS exploitation:
- IMDSv1 vs IMDSv2 lookup: GET http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>
- Storage buckets: Check open S3 buckets (aws s3 ls s3://<name>), readable object policies
- Credentials exposure: Scan config/credentials files (inspect_aws_creds), environment variables
- Privilege Escalation: iam:CreateAccessKey, iam:PutUserPolicy, iam:AttachUserPolicy, iam:PassRole
GCP exploitation:
- Metadata lookup: GET http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token (Metadata-Flavor: Google header)
- Cloud Storage: Check open GCP buckets, IAM permissions
- Service account key exposure: Scan for GCP service account JSON files
Azure exploitation:
- Metadata lookup: GET http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01 (Metadata: true header)
Kubernetes & Docker:
- Service accounts: Inspect `/var/run/secrets/kubernetes.io/serviceaccount/token`
- Kubernetes API: Query Kube API server endpoints, check for anonymous auth
- Docker daemon socket: Check for exposure of `/var/run/docker.sock` (run docker commands inside container to breakout)
- inspect env variables: env, printenv for cloud keys and secrets
TOOLS: aws, gcloud, kubectl, docker, trufflehog, inspect_aws_creds, inspect_kubeconfig, inspect_docker_env, query_metadata_endpoint, scan_secrets
""",

    "osint": """
OSINT (OPEN SOURCE INTELLIGENCE) TECHNIQUES:
Reconnaissance & Mapping:
- Domain OSINT: subfinder subdomain mapping, dig DNS records, whois registry info
- Wayback Machine: Archive lookup for deleted endpoints, credentials, historic source code
- Dorking: Search engines (Google/DuckDuckGo) with site:, filetype: (sql, env, txt, pdf), inurl:, intitle:
- Identity OSINT: Sherlock / WhatsMyName to find target username on social networks
- Repository OSINT: GitHub/GitLab searching for leaked files, commits, public secrets
- Image Geolocation: EXIF metadata extracting, finding landmarks, reverse image lookup
TOOLS: subfinder, dig, curl, sherlock, shodan, exiftool, dork_gen, github_search, wayback_dump
"""
}


class CTFRag:
    """
    Two-stage CTF RAG system.
    Stage 1: Returns built-in category technique knowledge (always available)
    Stage 2: Returns similar past solutions from ChromaDB (requires setup)
    """

    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self._init_chroma()

    def _init_chroma(self):
        if not CHROMA_AVAILABLE:
            return
        try:
            os.makedirs(CHROMA_PATH, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name="ctf_solutions",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"[CTF-RAG] ChromaDB init failed: {e} — Stage 2 disabled")

    # ── Stage 1: Category knowledge ──────────────────────────────────────

    def stage1_category(self, category: str) -> str:
        """Return technique knowledge for the detected category."""
        cat = category.lower().strip()
        aliases = {
            "binary": "pwn", "reverse": "rev", "cryptography": "crypto",
            "reverse engineering": "rev", "web exploitation": "web",
            "osint": "osint", "cloud": "cloud"
        }
        cat = aliases.get(cat, cat)
        knowledge = CATEGORY_KNOWLEDGE.get(cat, CATEGORY_KNOWLEDGE["misc"])
        return f"[STAGE-1 RAG — {cat.upper()} KNOWLEDGE]\n{knowledge}"

    # ── Stage 2: Past solutions ───────────────────────────────────────────

    def stage2_similar(self, challenge_text: str, category: str,
                        n_results: int = 3) -> str:
        """Recall similar past CTF solutions from ChromaDB."""
        if self.collection is None:
            return "[STAGE-2 RAG] No past solutions yet — solve more challenges to build knowledge base"

        try:
            count = self.collection.count()
            if count == 0:
                return "[STAGE-2 RAG] Knowledge base empty — solve challenges to populate it"

            results = self.collection.query(
                query_texts=[f"{category}: {challenge_text}"],
                n_results=min(n_results, count),
                where={"category": {"$eq": category}} if count > 10 else None
            )

            if not results["documents"][0]:
                return "[STAGE-2 RAG] No similar challenges found yet"

            lines = ["[STAGE-2 RAG — SIMILAR PAST SOLUTIONS]"]
            for i, (doc, meta) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0]
            )):
                lines.append(f"\n--- Past Solution {i+1} ---")
                lines.append(f"Challenge: {meta.get('challenge_name', 'Unknown')}")
                lines.append(f"Category: {meta.get('category', 'Unknown')}")
                lines.append(f"Key technique: {meta.get('technique', 'Unknown')}")
                lines.append(f"Solution summary: {doc[:400]}")
            return "\n".join(lines)

        except Exception as e:
            return f"[STAGE-2 RAG] Query failed: {e}"

    def get_combined_context(self, challenge_text: str, category: str) -> str:
        """Run both stages and combine into one context block."""
        stage1 = self.stage1_category(category)
        stage2 = self.stage2_similar(challenge_text, category)
        return f"{stage1}\n\n{stage2}"

    # ── Store solved challenge ────────────────────────────────────────────

    def store_solution(self, challenge_name: str, category: str,
                        description: str, solution_steps: str,
                        flag: str, technique: str = ""):
        """Store a solved challenge for future Stage-2 recall."""
        if self.collection is None:
            return False
        try:
            doc_id = f"ctf_{challenge_name.replace(' ', '_').lower()}"
            document = f"Challenge: {description}\nSolution: {solution_steps}\nFlag: {flag}"
            self.collection.upsert(
                ids=[doc_id],
                documents=[document],
                metadatas=[{
                    "challenge_name": challenge_name,
                    "category": category,
                    "technique": technique,
                    "flag_format": flag[:20] if flag else "",
                }]
            )
            return True
        except Exception as e:
            print(f"[CTF-RAG] Store failed: {e}")
            return False

    # ── Feed public writeups ─────────────────────────────────────────────

    def feed_writeup_directory(self, directory: str):
        """
        Bulk-index a directory of CTF writeups into ChromaDB.
        Usage:
          rag = CTFRag()
          rag.feed_writeup_directory("~/jarvis/knowledge/ctf_writeups")
        Expects .txt or .md files with writeup content.
        """
        if self.collection is None:
            print("[CTF-RAG] ChromaDB not available")
            return

        writeup_dir = Path(directory).expanduser()
        if not writeup_dir.exists():
            print(f"[CTF-RAG] Directory not found: {directory}")
            return

        count = 0
        for filepath in writeup_dir.rglob("*.md"):
            try:
                content = filepath.read_text(errors="replace")[:3000]
                # Try to detect category from path or content
                cat = "misc"
                for c in ["web", "crypto", "pwn", "forensics", "rev"]:
                    if c in str(filepath).lower() or c in content.lower():
                        cat = c
                        break
                doc_id = f"writeup_{filepath.stem}"
                self.collection.upsert(
                    ids=[doc_id],
                    documents=[content],
                    metadatas={"challenge_name": filepath.stem,
                               "category": cat,
                               "source": "writeup",
                               "technique": ""}
                )
                count += 1
            except Exception as e:
                print(f"[CTF-RAG] Failed to index {filepath}: {e}")

        print(f"[CTF-RAG] Indexed {count} writeups from {directory}")
