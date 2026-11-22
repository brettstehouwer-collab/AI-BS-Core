import json

p = r'C:\AI-BS\backend\core\emails_cache.json'
try:
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
    print(f"Total cached emails: {len(data)}")
    for em in data:
        txt = (str(em.get('subject','')) + ' ' + str(em.get('from','')) + ' ' + str(em.get('body',''))).lower()
        if any(k in txt for k in ['nda', 'non-disclosure', 'nondisclosure', 'agreement', 'contract']):
            print(f"Match: {em.get('subject')} | From: {em.get('from')} | Date: {em.get('date')}")
except Exception as e:
    print(f"Error: {e}")
