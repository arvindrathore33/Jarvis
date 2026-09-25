import time
import os
import re
import subprocess
from datetime import datetime

LOG_FILE = "/home/arvind/jarvis/memory_logs/continuous_train.log"
SUPERVISOR_LOG = "/home/arvind/jarvis/memory_logs/supervisor.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SUPERVISOR_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[*] {msg}")

def monitor():
    log("Supervisor online. Monitoring training...")
    while True:
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    content = f.read()
                
                # Detect Stall
                if "Training Cycle Complete" in content[-500:]:
                    log("Training cycle stalled. Restarting...")
                    # Kill current process and restart
                    subprocess.run(["pkill", "-f", "sqli_advanced_trainer.py"])
                    subprocess.Popen(["/home/arvind/jarvis/venv/bin/python", "/home/arvind/jarvis/tools/sqli_advanced_trainer.py"], 
                                     stdout=open(LOG_FILE, "w"), stderr=subprocess.STDOUT)
                    
                # Detect Hallucination/Repeated Errors
                if "AI Call failed" in content[-500:] or "Critical Failure" in content[-500:]:
                    log("Hallucination or API failure detected. Cleaning environment...")
                    subprocess.run(["docker", "restart", "vuln-lab"])
                    
        except Exception as e:
            log(f"Supervisor error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    monitor()
