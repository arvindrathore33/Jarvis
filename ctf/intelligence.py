"""
ctf/intelligence.py — NVD CVE Feed + LoRA Fine-tuning + Performance Tracing
Three long-term advantage systems bundled together.
Drop into ~/jarvis/ctf/intelligence.py

--- SETUP ---
# Add to crontab for daily CVE updates:
#   0 6 * * * cd ~/jarvis && python -c "from ctf.intelligence import update_cve_feed; update_cve_feed()"

# For LoRA fine-tuning (requires GPU):
#   pip install transformers peft datasets bitsandbytes --break-system-packages

# For tracing:
#   pip install opentelemetry-sdk opentelemetry-exporter-otlp --break-system-packages
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path

JARVIS_DIR   = os.path.expanduser("~/jarvis")
DB_PATH      = os.path.join(JARVIS_DIR, "memory", "jarvis.db")
JSONL_PATH   = os.path.join(JARVIS_DIR, "memory", "finetune_data.jsonl")
CVE_DB_PATH  = os.path.join(JARVIS_DIR, "memory", "cve_feed.db")


# ═══════════════════════════════════════════════════════════════
#  1. NVD CVE LIVE FEED
#  Fixes the training cutoff blindspot completely
# ═══════════════════════════════════════════════════════════════

def _init_cve_db():
    os.makedirs(os.path.dirname(CVE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(CVE_DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS cves (
        cve_id      TEXT PRIMARY KEY,
        description TEXT,
        severity    TEXT,
        score       REAL,
        published   TEXT,
        modified    TEXT,
        cpe         TEXT,
        "references"  TEXT,
        indexed_at  TEXT
    )""")
    conn.commit()
    return conn


def update_cve_feed(days_back: int = 1, max_results: int = 2000):
    """
    Fetch recent CVEs from NVD API v2 and store in local SQLite.
    Run daily via cron: 0 6 * * * python -c "from ctf.intelligence import update_cve_feed; update_cve_feed()"
    """
    conn = _init_cve_db()
    end_date   = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)

    # NVD API v2 format
    params = {
        "pubStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate":   end_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "resultsPerPage": 200,
        "startIndex": 0,
    }

    total_fetched = 0
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    while total_fetched < max_results:
        try:
            resp = requests.get(url, params=params, timeout=30,
                                headers={"User-Agent": "JARVIS-CTFAgent/2.0"})
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[CVE] Fetch failed: {e}")
            break

        vulns = data.get("vulnerabilities", [])
        if not vulns:
            break

        for item in vulns:
            cve   = item.get("cve", {})
            cve_id = cve.get("id", "")

            # Description
            descs = cve.get("descriptions", [])
            desc  = next((d["value"] for d in descs if d.get("lang") == "en"), "")

            # Severity
            metrics = cve.get("metrics", {})
            score   = 0.0
            severity = "UNKNOWN"
            for metric_key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                metric_list = metrics.get(metric_key, [])
                if metric_list:
                    cvss_data = metric_list[0].get("cvssData", {})
                    score     = cvss_data.get("baseScore", 0.0)
                    severity  = cvss_data.get("baseSeverity", "UNKNOWN")
                    break

            # CPE (affected products)
            cpe_list = []
            for config in cve.get("configurations", []):
                for node in config.get("nodes", []):
                    for match in node.get("cpeMatch", []):
                        cpe_list.append(match.get("criteria", ""))

            # References
            refs = [r.get("url", "") for r in cve.get("references", [])][:5]

            conn.execute("""INSERT OR REPLACE INTO cves
                (cve_id, description, severity, score, published, modified, cpe, "references", indexed_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (cve_id, desc[:1000], severity, score,
                 cve.get("published", ""),
                 cve.get("lastModified", ""),
                 json.dumps(cpe_list[:10]),
                 json.dumps(refs),
                 datetime.utcnow().isoformat()))

            total_fetched += 1

        conn.commit()
        print(f"[CVE] Indexed {total_fetched} CVEs so far...")

        # Pagination
        total_results = data.get("totalResults", 0)
        params["startIndex"] += len(vulns)
        if params["startIndex"] >= total_results:
            break

        # NVD rate limit: 5 req/30s without API key, 50 req/30s with key
        import time; time.sleep(6)

    conn.close()
    print(f"[CVE] Done. Total indexed: {total_fetched} CVEs")

    # Also index into ChromaDB for RAG
    _index_cves_to_chromadb(total_fetched)
    return total_fetched


def _index_cves_to_chromadb(limit: int = 500):
    """Push recent high-severity CVEs into ChromaDB for RAG retrieval."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=os.path.join(JARVIS_DIR, "memory", "chromadb"))
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        coll = client.get_or_create_collection("cve_feed", embedding_function=ef)

        conn = sqlite3.connect(CVE_DB_PATH)
        rows = conn.execute("""SELECT cve_id, description, severity, score
                               FROM cves WHERE score >= 7.0
                               ORDER BY indexed_at DESC LIMIT ?""", (limit,)).fetchall()
        conn.close()

        if not rows:
            return

        ids      = [r[0] for r in rows]
        docs     = [f"{r[0]}: {r[1]}" for r in rows]
        metas    = [{"severity": r[2], "score": r[3]} for r in rows]
        coll.upsert(ids=ids, documents=docs, metadatas=metas)
        print(f"[CVE] Indexed {len(rows)} high-severity CVEs into ChromaDB RAG")
    except Exception as e:
        print(f"[CVE] ChromaDB indexing failed: {e}")


def search_cves(query: str, min_score: float = 5.0, limit: int = 5) -> list:
    """Search local CVE database for relevant vulnerabilities."""
    if not os.path.exists(CVE_DB_PATH):
        return []
    conn = sqlite3.connect(CVE_DB_PATH)
    rows = conn.execute("""SELECT cve_id, description, severity, score
                           FROM cves
                           WHERE description LIKE ? AND score >= ?
                           ORDER BY score DESC LIMIT ?""",
                        (f"%{query}%", min_score, limit)).fetchall()
    conn.close()
    return [{"cve_id": r[0], "description": r[1], "severity": r[2], "score": r[3]} for r in rows]


def get_cve_count() -> int:
    """Return total CVEs in local database."""
    if not os.path.exists(CVE_DB_PATH):
        return 0
    conn = sqlite3.connect(CVE_DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM cves").fetchone()[0]
    conn.close()
    return count


# ═══════════════════════════════════════════════════════════════
#  2. LORA FINE-TUNING PIPELINE
#  Your permanent competitive edge — model trained on your data
# ═══════════════════════════════════════════════════════════════

def build_finetune_dataset(output_path: str = JSONL_PATH) -> int:
    """
    Build a LoRA fine-tuning dataset from JARVIS's solve history.
    Pulls from SQLite sessions, CTF writeups, and stored findings.
    Returns: number of training examples written.
    """
    examples = []

    # Pull from sessions database
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""SELECT command, response FROM sessions
                               WHERE length(response) > 100
                               ORDER BY timestamp DESC LIMIT 2000""").fetchall()
        conn.close()
        for cmd, resp in rows:
            examples.append({
                "messages": [
                    {"role": "system",  "content": "You are JARVIS, an elite cybersecurity AI."},
                    {"role": "user",    "content": cmd},
                    {"role": "assistant","content": resp},
                ]
            })
    except Exception as e:
        print(f"[FINETUNE] Sessions load failed: {e}")

    # Pull from CTF writeups
    writeup_dir = os.path.join(JARVIS_DIR, "output", "writeups")
    if os.path.exists(writeup_dir):
        for wfile in Path(writeup_dir).glob("*.md"):
            content = wfile.read_text(errors="replace")
            if "FLAG FOUND" in content and len(content) > 200:
                # Convert writeup to instruction-following example
                challenge_name = wfile.stem.replace("_", " ")
                examples.append({
                    "messages": [
                        {"role": "system",   "content": "You are JARVIS, an elite CTF-solving AI."},
                        {"role": "user",     "content": f"Solve this CTF challenge: {challenge_name}"},
                        {"role": "assistant","content": content[:2000]},
                    ]
                })

    # Write JSONL
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"[FINETUNE] Dataset built: {len(examples)} examples → {output_path}")
    return len(examples)


def run_lora_finetuning(base_model: str = "mistralai/Mistral-7B-v0.1",
                         dataset_path: str = JSONL_PATH,
                         output_dir: str = os.path.join(JARVIS_DIR, "models", "jarvis-finetune"),
                         num_epochs: int = 3):
    """
    Fine-tune a base model on JARVIS's accumulated data using LoRA (PEFT).
    Requires: pip install transformers peft datasets bitsandbytes accelerate
    RTX 4060 (8GB): use 4-bit quantization, r=8, batch_size=1
    RTX 3060 (12GB): use 4-bit quantization, r=16, batch_size=2
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
        from peft import LoraConfig, get_peft_model, TaskType
        from datasets import load_dataset
        import torch
    except ImportError:
        print("[FINETUNE] Install required: pip install transformers peft datasets bitsandbytes accelerate --break-system-packages")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"[FINETUNE] Starting LoRA fine-tune on {base_model}")
    print(f"[FINETUNE] Dataset: {dataset_path}")
    print(f"[FINETUNE] Output: {output_dir}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    tokenizer.pad_token = tokenizer.eos_token

    # Load model with 4-bit quantization (fits on RTX 4060/3060)
    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model.config.use_cache = False
    model.enable_input_require_grads()

    # LoRA config — r=8 for 8GB VRAM, r=16 for 12GB
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load dataset
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    def tokenize(example):
        messages = example["messages"]
        text = ""
        for msg in messages:
            text += f"<{msg['role']}>\n{msg['content']}\n</{msg['role']}>\n"
        res = tokenizer(text, truncation=True, max_length=1024, padding="max_length")
        res["labels"] = res["input_ids"].copy()
        return res

    tokenized = dataset.map(tokenize, remove_columns=dataset.column_names)

    # Training args
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        optim="paged_adamw_32bit",
        save_steps=50,
        logging_steps=10,
        learning_rate=2e-4,
        fp16=True,
        max_grad_norm=0.3,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
        gradient_checkpointing=True,
        save_total_limit=1,
    )

    from transformers import Trainer, DataCollatorForSeq2Seq
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
    )

    print("[FINETUNE] Training started — this takes ~4-8 hours on RTX 4060...")
    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"[FINETUNE] Model saved to {output_dir}")
    print(f"[FINETUNE] To use with Ollama: ollama create jarvis-custom -f {output_dir}/Modelfile")


# ═══════════════════════════════════════════════════════════════
#  3. PERFORMANCE TRACING
#  Know your solve rate week over week
# ═══════════════════════════════════════════════════════════════

METRICS_DB = os.path.join(JARVIS_DIR, "memory", "metrics.db")


def _init_metrics_db():
    os.makedirs(os.path.dirname(METRICS_DB), exist_ok=True)
    conn = sqlite3.connect(METRICS_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS solves (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge   TEXT,
        category    TEXT,
        solved      INTEGER,
        steps       INTEGER,
        elapsed_sec REAL,
        tools_run   INTEGER,
        flag        TEXT,
        model       TEXT,
        mode        TEXT,
        timestamp   TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tool_timings (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        tool      TEXT,
        elapsed   REAL,
        success   INTEGER,
        timestamp TEXT
    )""")
    conn.commit()
    return conn


def record_solve(result: dict, model: str = "", mode: str = "single"):
    """Record a CTF solve attempt for performance tracking."""
    conn = _init_metrics_db()
    tree = result.get("tree_summary", {})
    conn.execute("""INSERT INTO solves
        (challenge, category, solved, steps, elapsed_sec, tools_run, flag, model, mode, timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?)""", (
        result.get("challenge_name", "unknown"),
        result.get("category", ""),
        1 if result.get("solved") else 0,
        result.get("steps", 0),
        result.get("elapsed_sec", 0),
        tree.get("tools_run", 0),
        result.get("flag", ""),
        model,
        mode,
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()


def record_tool_timing(tool: str, elapsed: float, success: bool):
    """Record how long a tool took and whether it succeeded."""
    conn = _init_metrics_db()
    conn.execute("INSERT INTO tool_timings (tool, elapsed, success, timestamp) VALUES (?,?,?,?)",
                 (tool, elapsed, 1 if success else 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_performance_report(days: int = 30) -> dict:
    """
    Generate performance report for the last N days.
    Returns solve rates, best tools, average steps, etc.
    """
    if not os.path.exists(METRICS_DB):
        return {"error": "No metrics data yet — run some CTF challenges first"}

    conn = sqlite3.connect(METRICS_DB)
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    total = conn.execute("SELECT COUNT(*) FROM solves WHERE timestamp > ?", (cutoff,)).fetchone()[0]
    solved = conn.execute("SELECT COUNT(*) FROM solves WHERE timestamp > ? AND solved=1", (cutoff,)).fetchone()[0]

    # Per-category solve rate
    cat_stats = conn.execute("""SELECT category,
        COUNT(*) as total, SUM(solved) as solved_count,
        AVG(steps) as avg_steps, AVG(elapsed_sec) as avg_time
        FROM solves WHERE timestamp > ? GROUP BY category""", (cutoff,)).fetchall()

    # Tool performance
    tool_stats = conn.execute("""SELECT tool,
        COUNT(*) as calls, AVG(elapsed) as avg_time, AVG(success) as success_rate
        FROM tool_timings WHERE timestamp > ? GROUP BY tool
        ORDER BY calls DESC LIMIT 10""", (cutoff,)).fetchall()

    # Week-over-week solve rate
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    prev_week = (datetime.utcnow() - timedelta(days=14)).isoformat()
    this_week_rate = conn.execute(
        "SELECT AVG(solved) FROM solves WHERE timestamp BETWEEN ? AND ?",
        (week_ago, datetime.utcnow().isoformat())
    ).fetchone()[0] or 0
    last_week_rate = conn.execute(
        "SELECT AVG(solved) FROM solves WHERE timestamp BETWEEN ? AND ?",
        (prev_week, week_ago)
    ).fetchone()[0] or 0

    conn.close()

    return {
        "period_days":      days,
        "total_attempts":   total,
        "total_solved":     solved,
        "solve_rate":       round(solved / total * 100, 1) if total else 0,
        "this_week_rate":   round(this_week_rate * 100, 1),
        "last_week_rate":   round(last_week_rate * 100, 1),
        "week_delta":       round((this_week_rate - last_week_rate) * 100, 1),
        "category_stats":   [
            {"category": r[0], "total": r[1], "solved": r[2],
             "solve_rate": round(r[2]/r[1]*100, 1) if r[1] else 0,
             "avg_steps": round(r[3] or 0, 1), "avg_time_sec": round(r[4] or 0, 1)}
            for r in cat_stats
        ],
        "top_tools": [
            {"tool": r[0], "calls": r[1],
             "avg_time_sec": round(r[2] or 0, 2),
             "success_rate": round((r[3] or 0) * 100, 1)}
            for r in tool_stats
        ],
    }


def print_performance_dashboard():
    """Print a formatted performance dashboard to terminal."""
    report = get_performance_report(30)
    if "error" in report:
        print(f"[METRICS] {report['error']}")
        return

    print("\n" + "="*50)
    print("  JARVIS PERFORMANCE DASHBOARD (Last 30 days)")
    print("="*50)
    print(f"  Total attempts:  {report['total_attempts']}")
    print(f"  Solved:          {report['total_solved']} ({report['solve_rate']}%)")
    delta = report['week_delta']
    arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
    print(f"  This week rate:  {report['this_week_rate']}% {arrow} ({delta:+.1f}% vs last week)")

    print("\n  BY CATEGORY:")
    for cat in sorted(report["category_stats"], key=lambda x: x["solve_rate"], reverse=True):
        bar = "█" * int(cat["solve_rate"] / 10)
        print(f"  {cat['category']:<12} {bar:<10} {cat['solve_rate']}% ({cat['solved']}/{cat['total']})")

    print("\n  TOP TOOLS (by usage):")
    for tool in report["top_tools"][:5]:
        print(f"  {tool['tool']:<20} {tool['calls']} calls, {tool['success_rate']}% success, avg {tool['avg_time_sec']}s")
    print("="*50 + "\n")
