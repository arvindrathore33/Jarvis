import cloudscraper
import json

class PicoCTFClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        # create_scraper is better at handling CF challenges
        self.scraper = cloudscraper.create_scraper()
        self.base_url = "https://play.picoctf.org"

    def login(self):
        # 1. Fetch CSRF token from landing page
        try:
            r = self.scraper.get(f"{self.base_url}/")
            csrf_token = self.scraper.cookies.get("token")
        except Exception as e:
            print(f"[-] Failed to fetch initial page: {e}")
            return False

        # 2. Perform login
        login_url = f"{self.base_url}/api/user/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        headers = {
            "X-CSRF-Token": csrf_token,
            "Content-Type": "application/json",
            "Referer": f"{self.base_url}/"
        }

        response = self.scraper.post(login_url, json=payload, headers=headers)

        if response.status_code == 200:
            print("[+] Login successful!")
            return True
        else:
            print(f"[-] Login failed: {response.status_code} - {response.text}")
            return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        client = PicoCTFClient(sys.argv[1], sys.argv[2])
        client.login()
    else:
        print("Usage: python auth_pico.py <username> <password>")
