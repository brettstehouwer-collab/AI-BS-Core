import requests
from bs4 import BeautifulSoup
import json
import time
import re

# 1. Drop Page DOM Scanner
r_dom = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r_dom.text, 'html.parser')
cards = soup.find_all(lambda tag: tag.name == 'div' and tag.has_attr('class') and 'dl-card' in tag['class'] and 'dl-card-grid' not in tag['class'])
unlocked = []
for c in cards:
    is_locked = any('locked' in cls for cls in c.get('class', []))
    btn = c.find(['button', 'a'])
    btn_style = btn.get('style', '') if btn else ''
    btn_disabled = btn.has_attr('disabled') if btn else True
    variant_id = btn.get('data-variant-id') or btn.get('data-id') if btn else None
    href = btn.get('href', '') if btn else ''
    img = c.find('img')
    alt = img.get('alt', 'Pack') if img else 'Pack'
    
    if not is_locked or (variant_id and not btn_disabled) or (href and 'checkout' in href):
        unlocked.append((alt, variant_id, href))

# 2. Collections Feed
r_col = requests.get('https://cymatics.fm/collections/all/products.json?sort_by=created-descending&limit=10', headers={'User-Agent': 'Mozilla/5.0'})
recent_free_products = []
if r_col.status_code == 200:
    for p in r_col.json().get('products', []):
        for v in p.get('variants', []):
            if str(v.get('price')) in ['0.00', '0']:
                recent_free_products.append((p.get('title'), v.get('id'), v.get('price')))

# 3. YouTube Chat Probe
r_yt = requests.get('https://www.youtube.com/live_chat?v=xZ9FOZ2g878', headers={'User-Agent': 'Mozilla/5.0'})
yt_chat_links = []
if r_yt.status_code == 200:
    patterns = [
        r'https?://[^\s"\'<>]+\.(?:zip|rar|7z)',
        r'https?://drive\.google\.com/[^\s"\'<>]+',
        r'https?://(?:www\.)?dropbox\.com/[^\s"\'<>]+',
        r'https?://we\.tl/[^\s"\'<>]+',
        r'https?://cymatics\.fm/[^\s"\'<>]+'
    ]
    for pat in patterns:
        for m in re.findall(pat, r_yt.text):
            if not any(k in m.lower() for k in ['schema.org', 'w3.org', 'google.com/search', 'gstatic.com']):
                yt_chat_links.append(m)

# 4. Heartbeat
hb = json.load(open(r'C:\AI-BS\saved_data\cymatics_heartbeat.json'))
hb_age = round(time.time() - hb.get('timestamp', 0), 2)

print("=== REAL-TIME MULTI-CHANNEL PROBE REPORT ===")
print(f"Channel 1 (Drop Page DOM): {len(cards)} total cards | {len(unlocked)} unlocked on DOM")
if unlocked:
    for u in unlocked:
        print(f"  [⚡ UNLOCKED DROP]: {u[0]} (ID: {u[1]}, Link: {u[2]})")
else:
    print("  -> No cards have unlocked on the website grid yet.")

print(f"\nChannel 4 (Recent Free Store Catalog Products): {len(recent_free_products)} found")
for rp in recent_free_products[:5]:
    print(f"  -> {rp[0]} (Variant ID: {rp[1]}, Price: ${rp[2]})")

print(f"\nChannel 6 (YouTube Live Chat Links): {len(yt_chat_links)} links extracted")
for l in list(set(yt_chat_links))[:5]:
    print(f"  -> {l}")

print(f"\nWatchdog Heartbeat Status: {hb.get('status')} | PID: {hb.get('pid')} | Latency: {hb_age}s")
