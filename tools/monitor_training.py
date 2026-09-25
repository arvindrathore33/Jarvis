import time
import os

log_file = "/home/arvind/jarvis/memory_logs/sql_ghost.log"
completed = False

print("Monitoring SQLi Ghost Trainer...")
while not completed:
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()
            if "Data extracted" in content:
                completed = True
                # Trigger sound alert (using system beep or standard audio output)
                print("\a") # Terminal bell
                print("[SYSTEM] Training Complete: Flag/Data Extracted.")
                with open("/home/arvind/jarvis/memory_logs/final_status.txt", "w") as sf:
                    sf.write("SUCCESS: Jarvis has mastered SQL Injection on DVWA.")
    time.sleep(5)
