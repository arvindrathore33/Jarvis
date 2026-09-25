# tools/cve_updater.py — run as daily cron
import requests, sqlite3

def fetch_recent_cves(days_back=1):
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    params = {"pubStartDate": ..., "pubEndDate": ...}
    resp = requests.get(url, params=params).json()
    for item in resp["vulnerabilities"]:
        cve = item["cve"]
        store_cve(cve["id"], cve["descriptions"][0]["value"],
                  cve.get("metrics", {}))

# Add to crontab: 0 6 * * * python ~/jarvis/tools/cve_updater.py