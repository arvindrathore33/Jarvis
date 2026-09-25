import chromadb
import sqlite3
import json
import os
import schedule
import time
import threading

_chroma_lock = threading.Lock()

DB_PATH = os.path.expanduser("~/jarvis/memory/jarvis.db")
chroma_client = chromadb.PersistentClient(
    path=os.path.expanduser("~/jarvis/memory/vectordb")
)
collection = chroma_client.get_or_create_collection("jarvis_knowledge")

def store_finding(target, finding, outcome):
    with _chroma_lock:
        try:
            collection.add(
                documents=[finding],
                metadatas=[{"target": target, "outcome": outcome}],
                ids=[f"{target}_{abs(hash(finding))}"]
            )
        except Exception:
            pass

def recall_similar(query, n=3):
    try:
        results = collection.query(query_texts=[query], n_results=n)
        return results['documents'][0] if results['documents'] else []
    except:
        return []

def build_finetune_dataset():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT command, response FROM sessions WHERE response != ''")
    rows = c.fetchall()
    conn.close()
    dataset = [{"prompt": cmd, "completion": resp} for cmd, resp in rows]
    path = os.path.expanduser("~/jarvis/memory/finetune_data.jsonl")
    with open(path, 'w') as f:
        for item in dataset:
            f.write(json.dumps(item) + '\n')
    print(f"[JARVIS LEARNING] Dataset built: {len(dataset)} examples")

def weekly_finetune():
    print("[JARVIS LEARNING] Building weekly fine-tune dataset...")
    build_finetune_dataset()

schedule.every().week.do(weekly_finetune)

def start_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(3600)

threading.Thread(target=start_scheduler, daemon=True).start()
