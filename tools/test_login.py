import requests
import re

URL = "http://localhost/"
s = requests.Session()

def get_token(url):
    r = s.get(url)
    match = re.search(r"name='user_token' value='([a-f0-9]+)'", r.text)
    return match.group(1) if match else ""

# 1. Login first time
print("First login...")
token = get_token(URL + "login.php")
data = {"username": "admin", "password": "password", "Login": "Login", "user_token": token}
s.post(URL + "login.php", data=data)

# 2. Setup
print("Setting up database...")
token = get_token(URL + "setup.php")
s.post(URL + "setup.php", data={"create_db": "Create / Reset Database", "user_token": token})

# 3. Login again
print("Second login...")
token = get_token(URL + "login.php")
data = {"username": "admin", "password": "password", "Login": "Login", "user_token": token}
s.post(URL + "login.php", data=data)

# 4. Final check
s.cookies.set("security", "low", domain="localhost")
r = s.get(URL + "index.php")
if "Welcome" in r.text:
    print("SUCCESS!")
    print(f"PHPSESSID={s.cookies.get('PHPSESSID')}")
else:
    print("Still failing.")
    print(r.text[:500])
