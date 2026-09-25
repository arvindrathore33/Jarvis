import sys
import os
import json
from dotenv import load_dotenv

# Add jarvis to path
sys.path.append(os.path.join(os.getcwd(), "jarvis"))

from ctf.platforms import PicoCTFClient

load_dotenv("jarvis/.env")

username = os.getenv("PICOCTF_USER")
password = os.getenv("PICOCTF_PASS")

client = PicoCTFClient(username=username, password=password)

# Fetch details for WebDecode (ID: 427)
print(f"[SYSTEM] Fetching details for WebDecode (ID: 427)...")
detail = client.get_challenge_detail(427)

print(json.dumps(detail, indent=2))
