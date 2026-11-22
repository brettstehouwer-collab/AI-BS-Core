import json
import os

paths = [
    r'C:\AI-BS\backend\data\cached_emails.json',
    r'C:\AI-BS\backend\data\emails.json',
    r'C:\AI-BS\backend\data\email_inbox.json'
]

for p in paths:
    if os.path.exists(p):
        print(f"Checking {p}...")
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            if isinstance(data, list):
                for em in data:
                    subj = em.get('subject', '')
                    sender = em.get('from', '')
                    body = em.get('body', '') or em.get('snippet', '')
                    combined = f"{subj} {sender} {body}".lower()
                    if 'nda' in combined or 'disclosure' in combined or 'agreement' in combined:
                        print(f"  MATCH: Subject: '{subj}', From: '{sender}', Date: '{em.get('date')}'")
