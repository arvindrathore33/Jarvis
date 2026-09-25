import sys, os
sys.path.insert(0, '/home/arvind/jarvis')
from ctf.platforms import PicoCTFClient, fetch_and_solve
from ctf.solver_v2 import CTFSolver
import json

def run_solve(challenge_id):
    cookies = {
        'sessionid': 'sxmfa8f4wpr8t9c2chmk69q14fwev8c9',
        'csrftoken': 'GHg7MfQbVUY8VeBiXkwccuDqPGPxzYKi',
        'cf_clearance': '0C5p.lIMpluqm0YBPleNIvYRTBq8DIE6a2L8fHJWAZc-1781269850-1.2.1.1-FnwD9PCR_pFUwOU0KLHQzVNlexn4CiZitMo6_pPUjifbSSkzoXRmlGxzSYq_Tz0z4c_2jD0Y6oKc9pM_yRbmFqGQbKP3rCocvHjNPov82IUAhRpBYa46T.PGQcx1lhZYKYe8TJmCKywwU2Jdhs57W0vxpAhGJPauOT8B.0pImZbeR1mij1fh2zJ404qG6xs__OXO7BjyxKUHV7A9BWZd9mKYvB0nXXQTeH5MKd6vfYqcfz6vW._tVDer_mN1M_g6.AtctCp9EbjNr8GDSXvRkMv0vHNyZAqpFWSGNVTGqWY5QgJU_RO5eJU2OW1VMigS1wOrJ_2xBzrbUOk94Ax2MA'
    }

    client = PicoCTFClient(cookies=cookies)
    solver = CTFSolver()
    
    # Manually setting description if it fails to fetch (grounding)
    desc_map = {
        739: "I found this old website, but I cannot seem to log in as admin. Can you help me? URL: http://saturn.picoctf.net:56643/",
        427: "I found this website, can you decode the secret? URL: http://saturn.picoctf.net:51151/"
    }
    
    print(f'[*] Starting autonomous solve for challenge {challenge_id}...')
    try:
        # Override fetch_and_solve logic slightly to ensure we have the description
        detail = client.get_challenge_detail(challenge_id)
        description = detail.get('description', desc_map.get(challenge_id, ""))
        name = detail.get('name', f"Challenge #{challenge_id}")
        category = "Web Exploitation" # Force for now to ensure correct prompt
        
        result = solver.solve(
            challenge_name=name,
            description=description,
            category=category
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cid = int(sys.argv[1])
        res = run_solve(cid)
        print(json.dumps(res, indent=2))
    else:
        print("Usage: python runner.py <challenge_id>")
