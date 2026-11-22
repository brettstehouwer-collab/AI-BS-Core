import requests
import json
payload = {'model': 'stehouwer_llm', 'messages': [{'role': 'user', 'content': 'hello'}]}
try:
    r = requests.post('http://127.0.0.1:8080/api/chat', json=payload)
    print(f'STATUS: {r.status_code}')
    print(r.text)
except Exception as e:
    print(f'Exception: {e}')
