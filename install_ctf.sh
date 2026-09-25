#!/bin/bash
# ============================================================
#  JARVIS CTF ENHANCEMENT — Full Install Script
#  Platform: Arch Linux
#  Run as: bash install_ctf.sh
# ============================================================

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[JARVIS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

JARVIS_DIR="$HOME/jarvis"
cd "$JARVIS_DIR" || { err "~/jarvis not found. Run from correct directory."; exit 1; }

log "Starting JARVIS CTF Enhancement Install..."

# ── 1. System packages ───────────────────────────────────────
log "Installing system packages..."
sudo pacman -S --needed --noconfirm \
    binwalk exiftool foremost steghide john hashcat \
    gdb nmap wireshark-cli tshark python-pip \
    ghidra upx ltrace strace wget curl unzip \
    zbar imagemagick ffmpeg 2>/dev/null || warn "Some packages may need AUR"

# AUR packages (using yay)
if command -v yay &>/dev/null; then
    log "Installing AUR packages..."
    yay -S --needed --noconfirm \
        zsteg stegseek pwndbg one_gadget ropgadget \
        volatility3 python-pycdc 2>/dev/null || warn "Some AUR packages skipped"
else
    warn "yay not found — install manually: zsteg, stegseek, pwndbg, volatility3"
fi

# ── 2. Python packages ───────────────────────────────────────
log "Installing Python packages..."
pip install --break-system-packages --quiet \
    pwntools \
    pycryptodome \
    chromadb \
    sentence-transformers \
    python-dotenv \
    requests \
    flask \
    flask-socketio \
    sympy \
    pillow \
    python-magic

# ── 3. RsaCtfTool ────────────────────────────────────────────
if ! command -v RsaCtfTool.py &>/dev/null; then
    log "Installing RsaCtfTool..."
    git clone https://github.com/RsaCtfTool/RsaCtfTool.git /tmp/RsaCtfTool 2>/dev/null || true
    pip install --break-system-packages -r /tmp/RsaCtfTool/requirements.txt --quiet
    sudo cp /tmp/RsaCtfTool/RsaCtfTool.py /usr/local/bin/
    sudo chmod +x /usr/local/bin/RsaCtfTool.py
    log "RsaCtfTool installed"
fi

# ── 4. Upgrade Ollama model ──────────────────────────────────
log "Pulling deepseek-coder-v2 (better reasoning for CTF)..."
ollama pull deepseek-coder-v2:16b || warn "Model pull failed — run manually: ollama pull deepseek-coder-v2:16b"

# ── 5. Create CTF directory structure ────────────────────────
log "Creating CTF directory structure..."
mkdir -p "$JARVIS_DIR/ctf"
mkdir -p "$JARVIS_DIR/output/writeups"
mkdir -p "$JARVIS_DIR/memory/chromadb"
mkdir -p "$JARVIS_DIR/memory/ctf_knowledge"
mkdir -p "$JARVIS_DIR/challenges"       # drop challenge files here

# ── 6. Copy new CTF files ────────────────────────────────────
log "Copying CTF module files..."

# These should be in current directory (where you ran the script)
for f in prompts.py task_tree.py tools.py rag.py solver.py; do
    if [ -f "$f" ]; then
        cp "$f" "$JARVIS_DIR/ctf/$f"
        log "  Copied ctf/$f"
    else
        warn "  $f not found in current dir — copy manually to ~/jarvis/ctf/"
    fi
done

# Create __init__.py
touch "$JARVIS_DIR/ctf/__init__.py"

# ── 7. Update .env ───────────────────────────────────────────
log "Updating .env..."
ENV_FILE="$JARVIS_DIR/.env"
if ! grep -q "JARVIS_MODEL" "$ENV_FILE" 2>/dev/null; then
    echo "JARVIS_MODEL=deepseek-coder-v2:16b" >> "$ENV_FILE"
fi
if ! grep -q "CTF_MODEL" "$ENV_FILE" 2>/dev/null; then
    echo "CTF_MODEL=deepseek-coder-v2:16b" >> "$ENV_FILE"
fi

# ── 8. Pull CTF writeup knowledge base ───────────────────────
log "Pulling public CTF writeup knowledge base..."
KNOWLEDGE_DIR="$JARVIS_DIR/memory/ctf_knowledge"
if [ ! -d "$KNOWLEDGE_DIR/hacktricks" ]; then
    git clone --depth=1 https://github.com/carlospolop/hacktricks "$KNOWLEDGE_DIR/hacktricks" 2>/dev/null || \
        warn "HackTricks clone failed — add manually"
fi
if [ ! -d "$KNOWLEDGE_DIR/payloads" ]; then
    git clone --depth=1 https://github.com/swisskyrepo/PayloadsAllTheThings "$KNOWLEDGE_DIR/payloads" 2>/dev/null || \
        warn "PayloadsAllTheThings clone failed"
fi

# ── 9. Index knowledge into ChromaDB ─────────────────────────
log "Indexing knowledge into ChromaDB..."
python3 - <<'PYEOF'
import sys, os
sys.path.insert(0, os.path.expanduser("~/jarvis"))
try:
    from ctf.rag import CTFRag
    rag = CTFRag()
    rag.feed_writeup_directory("~/jarvis/memory/ctf_knowledge/hacktricks")
    print("[JARVIS] HackTricks indexed into ChromaDB")
except Exception as e:
    print(f"[WARN] Indexing skipped: {e}")
PYEOF

# ── 10. Verify install ────────────────────────────────────────
log "Verifying installation..."
python3 - <<'PYEOF'
checks = [
    ("pwntools",           "from pwn import *"),
    ("pycryptodome",       "from Crypto.Cipher import AES"),
    ("chromadb",           "import chromadb"),
    ("sentence-transformers", "from sentence_transformers import SentenceTransformer"),
    ("ctf.prompts",        "import sys,os; sys.path.insert(0,'./'); from ctf.prompts import get_ctf_prompt"),
    ("ctf.task_tree",      "from ctf.task_tree import TaskTree"),
    ("ctf.tools",          "from ctf.tools import CTF_TOOLS"),
    ("ctf.rag",            "from ctf.rag import CTFRag"),
    ("ctf.solver",         "from ctf.solver import CTFSolver"),
]
import subprocess, os
os.chdir(os.path.expanduser("~/jarvis"))
all_ok = True
for name, imp in checks:
    try:
        exec(imp)
        print(f"  ✓ {name}")
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        all_ok = False
print("\n[JARVIS] All OK!" if all_ok else "\n[WARN] Some checks failed — see above")
PYEOF

echo ""
log "============================================"
log "  JARVIS CTF Enhancement Complete!"
log "============================================"
log "New file structure:"
echo "  ~/jarvis/"
echo "  ├── ctf/"
echo "  │   ├── __init__.py"
echo "  │   ├── prompts.py      ← 6 specialist prompts"
echo "  │   ├── task_tree.py    ← Stateful task tree"
echo "  │   ├── tools.py        ← Full CTF tool suite"
echo "  │   ├── rag.py          ← 2-stage RAG system"
echo "  │   └── solver.py       ← Main autonomous solver"
echo "  ├── main.py             ← Updated (add 'ctf' command)"
echo "  └── memory/chromadb/    ← CTF knowledge base"
echo ""
log "To start: cd ~/jarvis && python main.py"
log "Then type 'ctf' to enter CTF mode"
