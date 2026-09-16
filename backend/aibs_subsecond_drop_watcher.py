"""
AI-BS 50-Worker Sub-Second Drop Watcher Daemon
50 concurrent asynchronous worker threads executing sub-second scan loops (~50ms) across all Cymatics endpoints.
"""

import time
import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import threading
import random
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')

STATE_FILE = r"C:\AI-BS\saved_data\drop_watcher_state.json"
HEARTBEAT_FILE = r"C:\AI-BS\saved_data\subsecond_heartbeat.json"
ALERT_FILE = r"C:\AI-BS\saved_data\NEW_DROP_ALERT.json"
LOG_FILE = r"C:\AI-BS\saved_data\cymatics_subsecond_drops.log"
FREE_DROPS_FILE = r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json"

NUM_WORKERS = 50
WORKER_LOOP_SLEEP_SEC = 0.050  # 50ms loop interval

ENDPOINTS = [
    ("PAGE", "https://cymatics.fm/pages/cymatics-c86v"),
    ("PRODUCTS", "https://cymatics.fm/products.json?limit=50"),
    ("COLLECTION_ALL", "https://cymatics.fm/collections/all/products.json?sort_by=created-descending&limit=50"),
    ("COLLECTION_FREE", "https://cymatics.fm/collections/free-packs/products.json?limit=50"),
    ("STREAM_PAGE", "https://cymatics.fm/pages/cymatics-2026-livestream-w2-ls")
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
]

RESIDENTIAL_SUBNETS = [
    (24, 0, 0, 0), (73, 0, 0, 0), (98, 160, 0, 0), (172, 56, 0, 0), (174, 192, 0, 0), (68, 0, 0, 0), (76, 16, 0, 0)
]

lock = threading.Lock()
state = {"known_unlocked_cards": [], "known_variant_ids": []}
total_requests = 0
running = True

# Load state
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

def get_headers():
    subnet = random.choice(RESIDENTIAL_SUBNETS)
    ip = f"{subnet[0]}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'X-Forwarded-For': ip,
        'X-Real-IP': ip
    }

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def handle_new_drops(new_drops):
    if not new_drops:
        return
    with lock:
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            with open(ALERT_FILE, "w", encoding="utf-8") as f:
                json.dump(new_drops, f, indent=2)
        except Exception:
            pass
    for d in new_drops:
        log(f"🚨 [NEW DROP DETECTED] {d['source']}: {d['title']} -> {d['direct_link']}")

def worker_scan_loop(worker_id):
    global total_requests, running
    session = requests.Session()
    
    while running:
        try:
            # Pick endpoint round-robin / randomized
            ep_type, ep_url = random.choice(ENDPOINTS)
            headers = get_headers()
            
            if ep_type in ["PAGE", "STREAM_PAGE"]:
                r = session.get(ep_url, headers=headers, timeout=2.5)
                with lock:
                    total_requests += 1
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    cards = soup.select('.dl-card[data-card-num]')
                    new_cards = []
                    for card in cards:
                        num = card.get('data-card-num')
                        classes = card.get('class', [])
                        is_locked = 'dl-card--locked' in classes or 'locked' in ' '.join(classes).lower()
                        
                        with lock:
                            known = num in state.get("known_unlocked_cards", [])
                        
                        if not is_locked and not known:
                            img = card.find('img', class_='dl-card__img')
                            title = (img.get('alt') if img else '') or f"Card #{num}"
                            variant_id = card.get('data-variant-id', '')
                            cta = card.find(class_='dl-card__cta') or card.find('button') or card.find('a')
                            if not variant_id and cta:
                                variant_id = cta.get('data-variant-id', '')
                            
                            with lock:
                                state["known_unlocked_cards"].append(num)
                            link = f"https://cymatics.fm/cart/{variant_id}:1?checkout" if variant_id else ep_url
                            new_cards.append({
                                "source": f"Stream Card #{num} (Worker {worker_id})",
                                "title": title,
                                "variant_id": variant_id,
                                "direct_link": link,
                                "timestamp": datetime.now().isoformat()
                            })
                    if new_cards:
                        handle_new_drops(new_cards)
                        
            elif ep_type in ["PRODUCTS", "COLLECTION_ALL", "COLLECTION_FREE"]:
                r = session.get(ep_url, headers=headers, timeout=2.5)
                with lock:
                    total_requests += 1
                if r.status_code == 200:
                    products = r.json().get('products', [])
                    new_prods = []
                    for p in products:
                        for v in p.get('variants', []):
                            vid = str(v.get('id'))
                            price = str(v.get('price'))
                            if price in ['0.00', '0'] and v.get('available'):
                                with lock:
                                    known = vid in state.get("known_variant_ids", [])
                                if not known:
                                    with lock:
                                        state["known_variant_ids"].append(vid)
                                    new_prods.append({
                                        "source": f"Shopify {ep_type} (Worker {worker_id})",
                                        "title": p.get('title'),
                                        "variant_id": vid,
                                        "direct_link": f"https://cymatics.fm/cart/{vid}:1?checkout",
                                        "timestamp": datetime.now().isoformat()
                                    })
                    if new_prods:
                        handle_new_drops(new_prods)

            time.sleep(WORKER_LOOP_SLEEP_SEC)
        except Exception:
            time.sleep(0.1)

def heartbeat_loop():
    global running, total_requests
    last_req = 0
    iteration = 0
    while running:
        iteration += 1
        time.sleep(1.0)
        with lock:
            cur_req = total_requests
            rps = cur_req - last_req
            last_req = cur_req
            unlocked = len(state.get("known_unlocked_cards", []))
            variants = len(state.get("known_variant_ids", []))
            
        try:
            with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": time.time(),
                    "workers": NUM_WORKERS,
                    "interval_ms": 50,
                    "total_requests": cur_req,
                    "req_per_sec": rps,
                    "monitored_variants": variants,
                    "unlocked_cards_count": unlocked
                }, f)
        except Exception:
            pass
            
        if iteration % 10 == 0:
            log(f"[Heartbeat] {NUM_WORKERS} Workers active | Speed: {rps} req/sec | Total: {cur_req} scans | Unlocked: {unlocked} | Tracked Variants: {variants}")

def main():
    log(f"Starting AI-BS 50-Worker Sub-Second Drop Scan Engine ({NUM_WORKERS} Parallel Workers @ {WORKER_LOOP_SLEEP_SEC*1000:.0f}ms loop)")
    
    # Start heartbeat monitor
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()
    
    # Spawn 50 worker threads
    threads = []
    for i in range(NUM_WORKERS):
        t = threading.Thread(target=worker_scan_loop, args=(i+1,), daemon=True)
        t.start()
        threads.append(t)
        
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
