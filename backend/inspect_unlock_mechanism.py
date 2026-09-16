import sys
import requests
from bs4 import BeautifulSoup
import re

sys.stdout.reconfigure(encoding='utf-8')

url = "https://cymatics.fm/pages/cymatics-c86v"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

scripts = soup.find_all('script')

print(f"Total scripts: {len(scripts)}")

for i, s in enumerate(scripts):
    text = s.string or ""
    src = s.get('src', '')
    if any(k in text.lower() or k in src.lower() for k in ['lwa', 'cloudfunctions', 'firebase', 'unlock', 'stream', 'c86', 'socket', 'pusher', 'channel', 'drop']):
        print(f"\n--- SCRIPT #{i} (src: {src}) ---")
        lines = [line for line in text.split('\n') if any(k in line.lower() for k in ['http', 'fetch', 'api', 'unlock', 'state', 'card', 'function', 'url'])]
        for l in lines[:20]:
            print(f"  {l.strip()}")
