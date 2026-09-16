import requests
from bs4 import BeautifulSoup
import re
import json

url = "https://cymatics.fm/pages/downloads-mirror-hub"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

print(f"Page Title: {soup.title.string if soup.title else 'N/A'}")

# Find all text content on the page
content_divs = soup.find_all(['div', 'section', 'article', 'main'])
for div in content_divs:
    text = div.get_text(separator='\n', strip=True)
    if 'mirror' in text.lower() or 'download' in text.lower():
        lines = [l for l in text.split('\n') if l.strip()]
        if 2 < len(lines) < 50:
            print("--- Content Block ---")
            print('\n'.join(lines[:20]))

# Search for any hidden scripts, JSON state, or mirror tables
scripts = soup.find_all('script')
print(f"\nTotal script tags: {len(scripts)}")
for s in scripts:
    if s.string and any(k in s.string.lower() for k in ['mirror', 'drive.google', 'dropbox', 's3.amazonaws', 'cloudfront', 'download']):
        print("--- Script with Mirrors ---")
        print(s.string[:500])

# Direct regex for all URLs
all_urls = re.findall(r'https?://[^\s"\'<>]+', r.text)
mirror_urls = set()
for u in all_urls:
    u_clean = u.rstrip('",;\\)}]>')
    if any(k in u_clean.lower() for k in ['drive.google', 'dropbox', 'we.tl', 'wetransfer', 'mediafire', 's3.amazonaws', 'cdn.shopify', 'cymatics.fm/pages', 'download']):
        mirror_urls.add(u_clean)

print("\n--- Extracted Mirror & Asset Links ---")
for mu in sorted(list(mirror_urls)):
    print("  ->", mu)
