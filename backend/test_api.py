"""Test API script."""

import time

import httpx

URL = "http://127.0.0.1:8000/api/screenplay/adapt"
files = {
    'file': (
        'source.pdf',
        open("C:/AI-BS/screenplay_projects/Default Project/source.pdf", 'rb'),
        'application/pdf'
    )
}
data = {'project_name': 'Default Project', 'adaptation_type': 'Feature Film'}

print("Starting API request...")
r = httpx.post(URL, files=files, data=data, timeout=30.0)
print(r.status_code, r.text)

print("Polling status...")
for i in range(15):
    time.sleep(2)
    status_url = (
        "http://127.0.0.1:8000/api/screenplay/adapt/status"
        "?project_name=Default Project"
    )
    r = httpx.get(status_url)
    print(r.json())
