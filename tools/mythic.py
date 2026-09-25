# tools/mythic_controller.py
import requests
import json

MYTHIC_URL  = "https://localhost:7443"
MYTHIC_USER = "mythic_admin"
MYTHIC_PASS = "your_password"

class MythicController:
    def __init__(self):
        self.token = None
        self.login()

    def login(self):
        r = requests.post(
            f"{MYTHIC_URL}/auth",
            json={"username": MYTHIC_USER, "password": MYTHIC_PASS},
            verify=False
        )
        self.token = r.json().get("access_token")

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get_callbacks(self):
        """Get all active agent callbacks"""
        r = requests.get(f"{MYTHIC_URL}/api/v1.4/callbacks/",
                        headers=self.headers(), verify=False)
        return r.json()

    def task_agent(self, callback_id, command, params=""):
        """Send a task to a specific agent"""
        r = requests.post(
            f"{MYTHIC_URL}/api/v1.4/tasks/callback/{callback_id}",
            json={"command": command, "params": params},
            headers=self.headers(), verify=False
        )
        return r.json()

    def get_task_output(self, task_id):
        """Get output from a completed task"""
        r = requests.get(
            f"{MYTHIC_URL}/api/v1.4/tasks/{task_id}/responses/",
            headers=self.headers(), verify=False
        )
        return r.json()

    def list_agents(self):
        """List all available payload types"""
        r = requests.get(f"{MYTHIC_URL}/api/v1.4/payloadtypes/",
                        headers=self.headers(), verify=False)
        return r.json()