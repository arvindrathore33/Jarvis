# tools/websearch.py

import requests
from bs4 import BeautifulSoup
import json
import os
import base64
from dotenv import load_dotenv

load_dotenv()

SHODAN_KEY = os.getenv("SHODAN_API_KEY", "")
VT_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
TAVILY_KEY = os.getenv("TAVILY_API_KEY", "")
ABUSEIPDB_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
NVD_KEY = os.getenv("NVD_API_KEY", "")

# ── Option 1: DuckDuckGo (zero setup, zero cost) ──────────────────
def ddg_search(query, max_results=5):
    headers = {"User-Agent": "Mozilla/5.0"}
    params = {"q": query, "format": "json", "no_html": 1}
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params=params, headers=headers, timeout=10
        )
        data = r.json()
        results = []
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", "")
                })
        return results
    except Exception as e:
        return [{"error": str(e)}]

# ── Option 2: Tavily (best for AI agents, 1000 free/month) ────────
def tavily_search(query, max_results=5):
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": True
            },
            timeout=15
        )
        data = r.json()
        return {
            "answer": data.get("answer", ""),
            "results": data.get("results", [])
        }
    except Exception as e:
        return {"error": str(e)}

# ── CVE-specific search (NVD API, completely free) ─────────────────
def search_cve(keyword_or_id):
    try:
        headers = {}
        if NVD_KEY:
            headers["apiKey"] = NVD_KEY
            
        # Direct CVE ID lookup
        if keyword_or_id.upper().startswith("CVE-"):
            r = requests.get(
                f"https://services.nvd.nist.gov/rest/json/cves/2.0",
                params={"cveId": keyword_or_id.upper()},
                headers=headers,
                timeout=15
            )
        else:
            # Keyword search
            r = requests.get(
                f"https://services.nvd.nist.gov/rest/json/cves/2.0",
                params={"keywordSearch": keyword_or_id, "resultsPerPage": 5},
                headers=headers,
                timeout=15
            )
        data = r.json()
        vulns = data.get("vulnerabilities", [])
        results = []
        for v in vulns:
            cve = v.get("cve", {})
            desc = cve.get("descriptions", [{}])[0].get("value", "")
            metrics = cve.get("metrics", {})
            cvss = (
                metrics.get("cvssMetricV31", [{}])[0]
                    .get("cvssData", {})
                    .get("baseScore", "N/A")
            )
            results.append({
                "id":          cve.get("id"),
                "description": desc[:300],
                "cvss_score":  cvss,
                "published":   cve.get("published", "")[:10]
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]

# ── Exploit-DB search (scrape, free) ───────────────────────────────
def search_exploitdb(query):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(
            f"https://www.exploit-db.com/search",
            params={"q": query},
            headers=headers, timeout=15
        )
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for row in soup.select("table tbody tr")[:5]:
            cols = row.find_all("td")
            if len(cols) > 3:
                results.append({
                    "date":  cols[0].text.strip(),
                    "title": cols[4].text.strip() if len(cols) > 4 else "",
                    "type":  cols[5].text.strip() if len(cols) > 5 else "",
                    "link":  "https://exploit-db.com" + (cols[4].find("a") or {}).get("href", "")
                })
        return results
    except Exception as e:
        return [{"error": str(e)}]

# ── Fetch and read a URL (for deep recon) ─────────────────────────
def fetch_url(url, max_chars=3000):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:max_chars]
    except Exception as e:
        return f"Error: {e}"

# ── Shodan Intelligence ───────────────────────────────────────────
def shodan_lookup(ip):
    if not SHODAN_KEY: return {"error": "Missing SHODAN_API_KEY"}
    try:
        r = requests.get(f"https://api.shodan.io/shodan/host/{ip}?key={SHODAN_KEY}", timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def shodan_search(query):
    if not SHODAN_KEY: return {"error": "Missing SHODAN_API_KEY"}
    try:
        r = requests.get(f"https://api.shodan.io/shodan/host/search?key={SHODAN_KEY}&query={query}", timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── VirusTotal Intelligence ───────────────────────────────────────
def vt_check_hash(file_hash):
    if not VT_KEY: return {"error": "Missing VIRUSTOTAL_API_KEY"}
    try:
        headers = {"x-apikey": VT_KEY}
        r = requests.get(f"https://www.virustotal.com/api/v3/files/{file_hash}", headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def vt_check_url(url):
    if not VT_KEY: return {"error": "Missing VIRUSTOTAL_API_KEY"}
    try:
        headers = {"x-apikey": VT_KEY}
        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
        r = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def vt_check_ip(ip):
    if not VT_KEY: return {"error": "Missing VIRUSTOTAL_API_KEY"}
    try:
        headers = {"x-apikey": VT_KEY}
        r = requests.get(f"https://www.virustotal.com/api/v3/ip_addresses/{ip}", headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── AbuseIPDB Reputation ──────────────────────────────────────────
def abuseipdb_check(ip):
    if not ABUSEIPDB_KEY: return {"error": "Missing ABUSEIPDB_API_KEY"}
    try:
        headers = {"Key": ABUSEIPDB_KEY, "Accept": "application/json"}
        params = {"ipAddress": ip, "maxAgeInDays": "90"}
        r = requests.get("https://api.abuseipdb.com/api/v2/check", headers=headers, params=params, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
