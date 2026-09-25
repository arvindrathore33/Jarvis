import cloudscraper
import json

def fetch_pico_challenges(cookies_dict):
    scraper = cloudscraper.create_scraper()
    
    # Add cookies to the scraper
    scraper.cookies.update(cookies_dict)
    
    url = "https://play.picoctf.org/api/challenges/?page=1&page_size=100"
    print(f"[*] Fetching challenges from {url}...")
    
    try:
        response = scraper.get(url)
        print(f"[*] Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[+] Success! Found {len(data.get('results', []))} challenges.")
            return data
        else:
            print(f"[-] Failed. Response: {response.text[:500]}")
            return None
    except Exception as e:
        print(f"[-] Error: {e}")
        return None

if __name__ == "__main__":
    cookies = {
        'sessionid': 'sxmfa8f4wpr8t9c2chmk69q14fwev8c9',
        'csrftoken': 'GHg7MfQbVUY8VeBiXkwccuDqPGPxzYKi',
        'cf_clearance': '0C5p.lIMpluqm0YBPleNIvYRTBq8DIE6a2L8fHJWAZc-1781269850-1.2.1.1-FnwD9PCR_pFUwOU0KLHQzVNlexn4CiZitMo6_pPUjifbSSkzoXRmlGxzSYq_Tz0z4c_2jD0Y6oKc9pM_yRbmFqGQbKP3rCocvHjNPov82IUAhRpBYa46T.PGQcx1lhZYKYe8TJmCKywwU2Jdhs57W0vxpAhGJPauOT8B.0pImZbeR1mij1fh2zJ404qG6xs__OXO7BjyxKUHV7A9BWZd9mKYvB0nXXQTeH5MKd6vfYqcfz6vW._tVDer_mN1M_g6.AtctCp9EbjNr8GDSXvRkMv0vHNyZAqpFWSGNVTGqWY5QgJU_RO5eJU2OW1VMigS1wOrJ_2xBzrbUOk94Ax2MA'
    }
    result = fetch_pico_challenges(cookies)
    if result:
        with open("pico_challenges.json", "w") as f:
            json.dump(result, f, indent=4)
