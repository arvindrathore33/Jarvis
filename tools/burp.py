# tools/burp_integration.py
import requests

class BurpClient:
    def __init__(self, api_key, host="http://localhost:1337"):
        self.base = host
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def get_issues(self, target_url):
        r = requests.get(f"{self.base}/v0.1/scan",
                        headers=self.headers,
                        params={"base_url": target_url})
        return r.json()

    def start_active_scan(self, url):
        r = requests.post(f"{self.base}/v0.1/scan",
                         headers=self.headers,
                         json={"urls": [url]})
        return r.json().get("task_id")