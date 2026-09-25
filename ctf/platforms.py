"""
ctf/platforms.py — CTF Platform API Integration
Auto-fetch challenges, auto-submit flags — no manual copy-paste.
Supports: CTFd (most competitions), HackTheBox, PicoCTF
Drop into ~/jarvis/ctf/platforms.py

Usage:
    from ctf.platforms import CTFdClient, HTBClient, auto_submit_flag

    # CTFd (most competitions use this)
    client = CTFdClient("https://ctf.example.com", token="YOUR_TOKEN")
    challenges = client.get_challenges()
    client.submit_flag(challenge_id=1, flag="CTF{found_it}")

    # HackTheBox
    htb = HTBClient(api_key="YOUR_HTB_API_KEY")
    machines = htb.get_active_machines()
    htb.submit_flag(machine_id=123, flag="HTB{found_it}")
"""

import requests
import json
import os
from typing import Optional


# ═══════════════════════════════════════════════════════════════
#  CTFd CLIENT (used by most competitions)
# ═══════════════════════════════════════════════════════════════

class CTFdClient:
    """
    Works with any CTFd-based competition.
    Get token: Login → Profile → Access Tokens → Generate
    """

    def __init__(self, base_url: str, token: str = "", username: str = "", password: str = ""):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "JARVIS-CTFAgent/2.0",
            "Content-Type": "application/json",
        })
        if token:
            self.session.headers["Authorization"] = f"Token {token}"
        elif username and password:
            self._login(username, password)

    def _login(self, username: str, password: str):
        """Login with credentials and get session token."""
        # Get CSRF nonce first
        r = self.session.get(f"{self.base}/login")
        nonce = ""
        if "nonce" in r.text:
            import re
            m = re.search(r'name="nonce".*?value="([^"]+)"', r.text)
            if m:
                nonce = m.group(1)
        self.session.post(f"{self.base}/login", data={
            "name": username, "password": password, "nonce": nonce
        })

    def get_challenges(self, category: str = "") -> list:
        """Fetch all available challenges."""
        r = self.session.get(f"{self.base}/api/v1/challenges")
        if r.status_code != 200:
            return []
        data = r.json().get("data", [])
        if category:
            data = [c for c in data if c.get("category", "").lower() == category.lower()]
        return data

    def get_challenge_detail(self, challenge_id: int) -> dict:
        """Get full challenge info including description and files."""
        r = self.session.get(f"{self.base}/api/v1/challenges/{challenge_id}")
        if r.status_code != 200:
            return {}
        detail = r.json().get("data", {})

        # Also fetch attached files
        files_r = self.session.get(f"{self.base}/api/v1/files?challenge_id={challenge_id}")
        if files_r.status_code == 200:
            detail["files"] = files_r.json().get("data", [])

        return detail

    def download_challenge_file(self, file_url: str, save_dir: str = "~/jarvis/challenges") -> str:
        """Download a challenge attachment file."""
        save_dir = os.path.expanduser(save_dir)
        os.makedirs(save_dir, exist_ok=True)
        filename = file_url.split("/")[-1].split("?")[0]
        local_path = os.path.join(save_dir, filename)
        url = file_url if file_url.startswith("http") else f"{self.base}/{file_url.lstrip('/')}"
        r = self.session.get(url, stream=True)
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return local_path

    def submit_flag(self, challenge_id: int, flag: str) -> dict:
        """Submit a flag and return result."""
        r = self.session.post(f"{self.base}/api/v1/challenges/attempt", json={
            "challenge_id": challenge_id,
            "submission": flag.strip()
        })
        if r.status_code != 200:
            return {"success": False, "error": f"HTTP {r.status_code}"}
        data = r.json()
        status = data.get("data", {}).get("status", "")
        return {
            "success": status == "correct",
            "status": status,
            "message": data.get("data", {}).get("message", ""),
            "flag": flag,
            "challenge_id": challenge_id,
        }

    def get_scoreboard(self) -> list:
        """Get current scoreboard."""
        r = self.session.get(f"{self.base}/api/v1/scoreboard")
        return r.json().get("data", []) if r.status_code == 200 else []

    def get_my_solves(self) -> list:
        """Get challenges already solved by current user."""
        r = self.session.get(f"{self.base}/api/v1/challenges?solved=1")
        return r.json().get("data", []) if r.status_code == 200 else []

    def get_unsolved_challenges(self, category: str = "") -> list:
        """Get only challenges not yet solved."""
        all_challs = self.get_challenges(category)
        solved = {c["id"] for c in self.get_my_solves()}
        return [c for c in all_challs if c["id"] not in solved]


# ═══════════════════════════════════════════════════════════════
#  HACKTHEBOX CLIENT
# ═══════════════════════════════════════════════════════════════

class HTBClient:
    """
    HackTheBox API client.
    Get API key: HTB Profile → API Key → Create App Token
    """

    BASE = "https://www.hackthebox.com/api/v4"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "JARVIS-CTFAgent/2.0",
        })

    def get_active_machines(self) -> list:
        """Get currently active HTB machines."""
        r = self.session.get(f"{self.BASE}/machine/list/paginated?per_page=20&difficulty=all")
        return r.json().get("data", []) if r.status_code == 200 else []

    def get_machine_info(self, machine_id: int) -> dict:
        """Get full machine details."""
        r = self.session.get(f"{self.BASE}/machine/profile/{machine_id}")
        return r.json().get("info", {}) if r.status_code == 200 else {}

    def submit_user_flag(self, machine_id: int, flag: str) -> dict:
        """Submit user (low-priv) flag."""
        r = self.session.post(f"{self.BASE}/machine/own", json={
            "id": machine_id, "flag": flag.strip(), "difficulty": 50
        })
        data = r.json()
        return {
            "success": data.get("success", False),
            "message": data.get("message", ""),
            "flag": flag,
            "type": "user"
        }

    def submit_root_flag(self, machine_id: int, flag: str) -> dict:
        """Submit root flag."""
        r = self.session.post(f"{self.BASE}/machine/own", json={
            "id": machine_id, "flag": flag.strip(), "difficulty": 50, "type": "root"
        })
        data = r.json()
        return {
            "success": data.get("success", False),
            "message": data.get("message", ""),
            "flag": flag,
            "type": "root"
        }

    def start_machine(self, machine_id: int) -> dict:
        """Spawn a machine instance."""
        r = self.session.post(f"{self.BASE}/vm/spawn", json={"id": machine_id})
        return r.json()

    def get_active_machine_ip(self) -> str:
        """Get IP of currently running machine."""
        r = self.session.get(f"{self.BASE}/machine/active")
        data = r.json()
        return data.get("info", {}).get("ip", "")

    def get_challenges(self, category: str = "") -> list:
        """Get HTB challenges (not machines)."""
        r = self.session.get(f"{self.BASE}/challenge/list")
        data = r.json().get("challenges", [])
        if category:
            data = [c for c in data if c.get("category_name", "").lower() == category.lower()]
        return data

    def submit_challenge_flag(self, challenge_id: int, flag: str) -> dict:
        """Submit CTF challenge flag."""
        r = self.session.post(f"{self.BASE}/challenge/own", json={
            "id": challenge_id, "flag": flag.strip(), "difficulty": 50
        })
        data = r.json()
        return {
            "success": data.get("success", 0) == 1,
            "message": data.get("message", ""),
            "flag": flag,
        }


# ═══════════════════════════════════════════════════════════════
#  PICOCTF CLIENT
# ═══════════════════════════════════════════════════════════════

class PicoCTFClient:
    """PicoCTF platform client (used for practice/learning)."""

    BASE = "https://play.picoctf.org/api"

    def __init__(self, username: str = "", password: str = "", token: str = "", cookies: dict = None):
        import cloudscraper
        self.session = cloudscraper.create_scraper()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        if cookies:
            self.session.cookies.update(cookies)
        if token:
            self.session.headers["Authorization"] = f"Token {token}"
        elif username and password:
            self._login(username, password)

    def _login(self, username: str, password: str):
        r = self.session.post(f"{self.BASE}/user/login/", json={
            "username": username, "password": password
        })
        if r.status_code == 200:
            token = r.json().get("token", "")
            self.session.headers["Authorization"] = f"Token {token}"

    def get_challenges(self, category: str = "") -> list:
        r = self.session.get(f"{self.BASE}/challenges/?page=1&page_size=100")
        data = r.json().get("results", [])
        if category:
            data = [c for c in data if c.get("category", "").lower() == category.lower()]
        return data

    def get_challenge_detail(self, challenge_id: int) -> dict:
        """Get full challenge info including description and files."""
        r = self.session.get(f"{self.BASE}/challenges/{challenge_id}/")
        if r.status_code != 200:
            return {}
        return r.json()

    def download_challenge_file(self, file_url: str, save_dir: str = "~/jarvis/challenges") -> str:
        """Download a challenge attachment file."""
        save_dir = os.path.expanduser(save_dir)
        os.makedirs(save_dir, exist_ok=True)
        filename = file_url.split("/")[-1].split("?")[0]
        local_path = os.path.join(save_dir, filename)
        
        # PicoCTF files are usually hosted on a different subdomain or path
        url = file_url if file_url.startswith("http") else f"https://artifacts.picoctf.net/{file_url.lstrip('/')}"
        r = self.session.get(url, stream=True)
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return local_path

    def submit_flag(self, challenge_id: int, flag: str) -> dict:
        r = self.session.post(f"{self.BASE}/challenges/{challenge_id}/submit_flag/", json={
            "flag": flag.strip()
        })
        data = r.json()
        return {
            "success": data.get("correct", False),
            "message": data.get("message", ""),
            "flag": flag,
        }


# ═══════════════════════════════════════════════════════════════
#  UNIVERSAL AUTO-SUBMIT
# ═══════════════════════════════════════════════════════════════

def auto_submit_flag(flag: str, platform: str = "", challenge_id: int = 0,
                     machine_id: int = 0) -> dict:
    """
    Auto-submit a found flag using environment variables for credentials.
    Set in ~/jarvis/.env:
      CTFD_URL=https://ctf.example.com
      CTFD_TOKEN=your_token
      HTB_API_KEY=your_key
      PICOCTF_USER=your_username
      PICOCTF_PASS=your_password
    """
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/jarvis/.env"))

    results = []

    if platform in ("ctfd", "") and os.getenv("CTFD_URL"):
        try:
            client = CTFdClient(
                os.getenv("CTFD_URL"),
                token=os.getenv("CTFD_TOKEN", "")
            )
            if challenge_id:
                result = client.submit_flag(challenge_id, flag)
                result["platform"] = "CTFd"
                results.append(result)
        except Exception as e:
            results.append({"platform": "CTFd", "success": False, "error": str(e)})

    if platform in ("htb", "") and os.getenv("HTB_API_KEY"):
        try:
            client = HTBClient(os.getenv("HTB_API_KEY"))
            if machine_id:
                result = client.submit_user_flag(machine_id, flag)
            elif challenge_id:
                result = client.submit_challenge_flag(challenge_id, flag)
            else:
                result = {"success": False, "error": "Need machine_id or challenge_id"}
            result["platform"] = "HTB"
            results.append(result)
        except Exception as e:
            results.append({"platform": "HTB", "success": False, "error": str(e)})

    if not results:
        return {"success": False, "error": "No platform configured. Set CTFD_URL or HTB_API_KEY in .env"}

    # Return first successful submission
    for r in results:
        if r.get("success"):
            return r
    return results[0]


# ═══════════════════════════════════════════════════════════════
#  INTERACTIVE CHALLENGE FETCHER
#  Feeds directly into CTFSolver.solve()
# ═══════════════════════════════════════════════════════════════

def fetch_and_solve(platform_client, challenge_id: int,
                    solver, save_dir: str = "~/jarvis/challenges") -> dict:
    """
    Complete end-to-end: fetch challenge → download files → solve → submit flag.

    Usage:
        client = CTFdClient("https://ctf.example.com", token="TOKEN")
        from ctf.solver import CTFSolver
        solver = CTFSolver()
        result = fetch_and_solve(client, challenge_id=42, solver=solver)
        print(result)
    """
    # 1. Fetch challenge details
    if hasattr(platform_client, "get_challenge_detail"):
        detail = platform_client.get_challenge_detail(challenge_id)
    else:
        detail = {}

    name        = detail.get("name", f"Challenge #{challenge_id}")
    description = detail.get("description", "")
    category_raw = detail.get("category", "")
    category = category_raw.get("name", "") if isinstance(category_raw, dict) else category_raw
    files_meta  = detail.get("files", [])

    print(f"[PLATFORM] Fetched: {name} [{category}]")

    # 2. Download attached files
    local_files = []
    for f in files_meta:
        url = f.get("location", f.get("url", ""))
        if url:
            try:
                path = platform_client.download_challenge_file(url, save_dir)
                local_files.append(path)
                print(f"[PLATFORM] Downloaded: {path}")
            except Exception as e:
                print(f"[PLATFORM] File download failed: {e}")

    # 3. Run solver
    result = solver.solve(
        challenge_name=name,
        description=description,
        category=category,
        files=local_files,
    )

    # 4. Auto-submit if flag found
    if result.get("flag"):
        submit_result = platform_client.submit_flag(challenge_id, result["flag"])
        result["submission"] = submit_result
        if submit_result.get("success"):
            print(f"[PLATFORM] ✓ FLAG ACCEPTED: {result['flag']}")
        else:
            print(f"[PLATFORM] ✗ Flag rejected: {submit_result.get('message')}")
    else:
        result["submission"] = {"success": False, "error": "No flag found"}

    return result
