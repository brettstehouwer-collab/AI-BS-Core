import requests
from bs4 import BeautifulSoup
import re
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://cymatics.fm/pages/voxity-vocal-mixing-plugin-a'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

r = requests.get(url, headers=headers)
print(f"Probing {url} -> HTTP {r.status_code}")

if r.status_code == 200:
    soup = BeautifulSoup(r.text, 'html.parser')
    print("Title:", soup.title.string.strip() if soup.title else "No Title")
    
    # 1. Look for buttons, links, CTAs
    links = soup.find_all(['a', 'button'])
    print(f"\nFound {len(links)} interactive elements:")
    for el in links:
        href = el.get('href', '')
        text = el.get_text().strip()
        vid = el.get('data-variant-id', '')
        if any(w in (href + text + str(vid)).lower() for w in ['free', 'download', 'cart', 'buy', 'get', 'bonus', 'pack', 'voxity']):
            print(f'  -> CTA: "{text}" | Href: {href} | Variant: {vid}')
            
    # 2. Check local ownership
    hub_path = os.path.expandvars(r'%APPDATA%\Cymatics\Cymatics Hub\installed.json')
    if os.path.exists(hub_path):
        with open(hub_path, 'r', encoding='utf-8') as f:
            installed = json.load(f)
            is_owned = 'voxity' in installed
            print(f"\nLocal Ownership Check in Cymatics Hub: Voxity installed = {is_owned}")
