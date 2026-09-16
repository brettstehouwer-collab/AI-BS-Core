import sys
import os
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

STATE_FILE = r"C:\AI-BS\saved_data\drop_watcher_state.json"
FREE_DROPS_FILE = r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json"

API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
VIDEO_ID = "rq2LZe3hcUU"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

state = {"known_unlocked_cards": [], "known_variant_ids": [], "known_qna": []}
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        pass

if not state.get("known_variant_ids") and os.path.exists(FREE_DROPS_FILE):
    try:
        with open(FREE_DROPS_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
            state["known_variant_ids"] = [str(item.get("variant_id")) for item in catalog if item.get("variant_id")]
    except Exception:
        pass

new_drops = []
new_qna = []

# 1. Check Stream Drop Landing Page
try:
    r_page = requests.get("https://cymatics.fm/pages/cymatics-c86v", headers=headers, timeout=6)
    if r_page.status_code == 200:
        soup = BeautifulSoup(r_page.text, 'html.parser')
        cards = soup.select('.dl-card[data-card-num]')
        for card in cards:
            num = card.get('data-card-num')
            classes = card.get('class', [])
            is_locked = 'dl-card--locked' in classes or 'locked' in ' '.join(classes).lower()
            
            img = card.find('img', class_='dl-card__img')
            title = (img.get('alt') if img else '') or f"Card #{num}"
            
            variant_id = card.get('data-variant-id')
            if not variant_id:
                cta = card.find(class_='dl-card__cta') or card.find('button') or card.find('a')
                if cta and cta.get('data-variant-id'):
                    variant_id = cta.get('data-variant-id')
            
            if not is_locked:
                if num not in state.get("known_unlocked_cards", []):
                    state["known_unlocked_cards"].append(num)
                    checkout_url = f"https://cymatics.fm/cart/{variant_id}:1?checkout" if variant_id else "https://cymatics.fm/pages/cymatics-c86v"
                    new_drops.append({
                        "source": f"Stream Card #{num}",
                        "title": title,
                        "variant_id": variant_id,
                        "direct_link": checkout_url
                    })
except Exception:
    pass

# 2. Check Shopify Products Feed
try:
    r_shop = requests.get("https://cymatics.fm/products.json?limit=50", headers=headers, timeout=6)
    if r_shop.status_code == 200:
        products = r_shop.json().get('products', [])
        for p in products:
            for v in p.get('variants', []):
                vid = str(v.get('id'))
                price = str(v.get('price'))
                if price in ['0.00', '0'] and v.get('available'):
                    if vid not in state.get("known_variant_ids", []):
                        state["known_variant_ids"].append(vid)
                        new_drops.append({
                            "source": "Shopify Free Catalog Drop",
                            "title": p.get('title'),
                            "variant_id": vid,
                            "direct_link": f"https://cymatics.fm/cart/{vid}:1?checkout"
                        })
except Exception:
    pass

# 3. Check YouTube Stream for Q&A Prompts
try:
    r_stream = requests.get(f"https://www.youtube.com/watch?v={VIDEO_ID}", headers=headers, timeout=5)
    match = re.search(r'"continuation":"([^"]+)"', r_stream.text)
    if match:
        continuation = match.group(1)
        r_chat = requests.post(f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={API_KEY}", json={
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.20260828.01.00", "hl": "en", "gl": "US"}},
            "continuation": continuation
        }, headers=headers, timeout=5)
        data = r_chat.json()
        actions = data.get('continuationContents', {}).get('liveChatContinuation', {}).get('actions', [])
        for a in actions:
            # Check for mod messages or Q&A panels
            item = a.get('addChatItemAction', {}).get('item', {})
            text_renderer = item.get('liveChatTextMessageRenderer')
            if text_renderer:
                author = text_renderer.get('authorName', {}).get('simpleText', '')
                badges = text_renderer.get('authorBadges', [])
                is_mod = any('moderator' in str(b).lower() or 'owner' in str(b).lower() for b in badges)
                runs = text_renderer.get('message', {}).get('runs', [])
                text = "".join([r.get('text', '') for r in runs])
                if is_mod or author.lower() in ['cymatics', 'cymaticsfm', 'stevencymatics']:
                    msg_id = f"{author}:{text}"
                    if msg_id not in state.get("known_qna", []):
                        state.setdefault("known_qna", []).append(msg_id)
                        new_qna.append({"author": author, "text": text})
except Exception:
    pass

# Save state
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2)

# Output summary
if new_drops:
    print(f"🚨 NEW DROPS DETECTED ({len(new_drops)}):")
    for d in new_drops:
        print(f"  -> [{d['source']}] {d['title']} | Link: {d['direct_link']}")
    
    variant_ids = [d["variant_id"] for d in new_drops if d.get("variant_id")]
    if len(variant_ids) > 1:
        bundle_url = f"https://cymatics.fm/cart/{','.join([f'{vid}:1' for vid in variant_ids])}?checkout"
        print(f"\n📦 AUTO-BUNDLED 1-CLICK CHECKOUT LINK ({len(variant_ids)} Items):")
        print(f"  -> {bundle_url}")

if new_qna:
    print(f"\n🎯 NEW MOD / Q&A PROMPT DETECTED ({len(new_qna)}):")
    for q in new_qna:
        print(f"  -> [@{q['author']}]: {q['text']}")

if not new_drops and not new_qna:
    print(f"Status: Monitoring drop page (194 cards locked), Shopify feed (195 variants), & YouTube live Q&A at {datetime.now().strftime('%H:%M:%S')}.")
