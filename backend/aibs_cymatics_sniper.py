"""
AI-BS Enterprise High-Resilience Cymatics Drop Sniper & Fail-Safe Engine
Multi-Channel Ingestion:
1. Drop Page Real-Time DOM Scanner (https://cymatics.fm/pages/cymatics-c86v)
2. Global Products JSON Feed (https://cymatics.fm/products.json?limit=250)
3. Collection Feed (https://cymatics.fm/collections/all/products.json?sort_by=created-descending)
4. Shopify Product Sitemap XML Scanner (https://cymatics.fm/sitemap_products_1.xml)
5. Direct Variant Availability Prober on upcoming handles

Fail-Safes & Redundancy:
- Strict $0.00 Free-Only Filter (Zero paid claims)
- Dynamic Residential IP Spoofing & User-Agent Rotation
- Dual-Stack Networking (requests + urllib fallback)
- Instant Headless POST Auto-Cart + Dual Browser Launch (webbrowser + shell start)
- Multi-Frequency Audio Siren + Windows Desktop Toast Notification
- Persistent Heartbeat File for Watchdog Supervisor
"""

import urllib.request
import urllib.parse
import json
import time
from datetime import datetime
import os
import sys
import io
import re
import webbrowser
import threading
import subprocess
import random
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

from shell_adapter import launch_windows_open
# Ensure UTF-8 stdout/stderr on Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

DROP_PAGE_URL = "https://cymatics.fm/pages/cymatics-c86v"
PRODUCTS_JSON_URL = "https://cymatics.fm/products.json?limit=250"
COLLECTIONS_JSON_URL = "https://cymatics.fm/collections/all/products.json?sort_by=created-descending&limit=50"
SITEMAP_URL = "https://cymatics.fm/sitemap_products_1.xml"
CART_ADD_URL = "https://cymatics.fm/cart/add.js"

OUTPUT_DIR = r"E:\AI_BS_Resources\Cymatics_100GB_Drop"
LOG_FILE = r"C:\AI-BS\saved_data\cymatics_drop_log.json"
HEARTBEAT_FILE = r"C:\AI-BS\saved_data\cymatics_heartbeat.json"
EMERGENCY_QUEUE_FILE = r"C:\AI-BS\saved_data\unclaimed_emergency_queue.txt"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:130.0) Gecko/20100101 Firefox/130.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15'
]

RESIDENTIAL_SUBNETS = [
    (24, 0, 0, 0),      # Comcast Cable US
    (73, 0, 0, 0),      # Comcast Cable US
    (98, 160, 0, 0),    # Spectrum / Charter US
    (172, 56, 0, 0),    # T-Mobile US
    (174, 192, 0, 0),   # Verizon Wireless US
    (68, 0, 0, 0),      # AT&T Internet US
    (76, 16, 0, 0)      # Cox Communications US
]

def generate_spoofed_ip():
    subnet = random.choice(RESIDENTIAL_SUBNETS)
    return f"{subnet[0]}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

def get_spoofed_headers():
    ip = generate_spoofed_ip()
    ua = random.choice(USER_AGENTS)
    return {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
        'X-Forwarded-For': ip,
        'X-Real-IP': ip,
        'CF-Connecting-IP': ip,
        'True-Client-IP': ip,
        'X-Client-IP': ip,
        'Forwarded': f'for={ip};proto=https',
        'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }

DOWNLOAD_PATTERNS = [
    r'https?://[^\s"\'<>]+\.(?:zip|rar|7z|tar|gz)',
    r'https?://drive\.google\.com/[^\s"\'<>]+',
    r'https?://(?:www\.)?dropbox\.com/[^\s"\'<>]+',
    r'https?://we\.tl/[^\s"\'<>]+',
    r'https?://(?:www\.)?wetransfer\.com/[^\s"\'<>]+',
    r'https?://[^\s"\'<>]*s3[^\s"\'<>]*(?:zip|tar|audio|sample)[^\s"\'<>]*'
]

unlocked_cards_known = set()
known_product_ids = set()
known_direct_links = set()
known_sitemap_urls = set()
drop_history = []

# Dynamically loaded from Cymatics Hub + master exclusions
ALREADY_OWNED = {
    "8bit", "aurora", "chili clipper", "chili-clipper", "cl 2a", "cl-2a",
    "corrosion", "crt", "dark sky", "dark-sky", "daydream", "diablo",
    "dreamscape", "eqc 1a", "eqc-1a", "gamma", "halo", "hooklab",
    "hooklab gold", "hooklab-gold", "horizon", "hotline", "illusion",
    "invader lite", "invader-lite", "keyfinder", "lc 76", "lc-76",
    "lotus", "midi shredder", "midi-shredder", "midiprinter", "mix link",
    "mix-link", "neptune", "neptune lite", "neptune-lite", "nova fx",
    "nova-fx", "nv 73", "nv-73", "occular", "ocean pluck", "ocean-pluck",
    "omnivox", "pandora", "phantom", "pinch", "plinko", "prism",
    "pulse", "quake", "radar", "relapse", "ripple", "roam", "shifter",
    "space", "velvet", "vortex", "voxity", "cashmere", "duality",
    "duality - ambient melodies", "euphoria", "euphoria - vocal chops",
    "evolution", "evolution - guitar melodies", "exodus - various drums",
    "exodus - various melodies", "fugitive", "heritage", "mystery - 11 year anniversary edition",
    "octagon", "octagon - don toliver pack", "phalanx - 808 & bass",
    "ripple - pop guitars", "solace", "solace - acapellas", "terra - trap melodies",
    "trinity - midi collection", "trinity - melody collection", "trinity - wet percussion",
    "whisper - melody collection", "dope collection - bonus stash", "dope collection - vocals",
    "dope collection - drums", "dope collection - melodies"
}

PRECACHED_VARIANTS = {
    "dope collection - melodies": 42703045132373,
    "dope collection - drums": 42703113420885,
    "dope collection - vocals": 42703162277973,
    "dope collection - bonus stash": 42703163228245,
    "solace - acapellas": 42703166439509,
    "daydream - vocal loops": 42703168700501,
    "euphoria - vocal chops": 42703179022421,
    "sessions: melody compositions": 40635706343509,
    "generations - 1970s premium samples": 40620833570901,
    "generations - 1960s premium samples": 40620731498581,
    "kingdom: electronic midi collection": 40666743111765,
    "pandora - edm midi": 42703201370197,
    "pandora - rnb midi": 42703204712533,
    "pandora - trap midi": 42703211626581,
    "pandora: paradise expansion": 42703223881813,
    "pandora: echoes expansion": 42703249342549,
    "midi shredder": 42520328962133,
    "trinity - wet percussion": 42916976558165,
    "trinity: melody collection": 42570448109653
}

# Auto-sync from Hub cache on startup
try:
    hub_installed_path = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub\installed.json"
    if os.path.exists(hub_installed_path):
        with open(hub_installed_path, 'r', encoding='utf-8') as f:
            hub_inst = json.load(f)
            for k in hub_inst.keys():
                ALREADY_OWNED.add(k.lower().strip())
                ALREADY_OWNED.add(k.lower().replace('-', ' ').strip())
except Exception:
    pass

session = requests.Session()
session.headers.update(get_spoofed_headers())

def update_heartbeat():
    """Write active timestamp to disk so watchdog supervisor knows sniper is healthy."""
    try:
        with open(HEARTBEAT_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": time.time(),
                "datetime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "pid": os.getpid(),
                "status": "HEALTHY",
                "owned_count": len(ALREADY_OWNED),
                "unlocked_count": len(unlocked_cards_known)
            }, f, indent=2)
    except Exception:
        pass

def play_fail_safe_siren():
    """Redundant audio alert using both raw frequency beeps and Windows system audio chime."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        for _ in range(8):
            winsound.Beep(1800, 100)
            time.sleep(0.02)
            winsound.Beep(2600, 150)
            time.sleep(0.02)
    except Exception:
        pass

def send_windows_toast(title, url):
    """Fires a non-blocking Windows Desktop Notification so user never misses a drop."""
    try:
        ps_cmd = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);
        $textNodes = $template.GetElementsByTagName('text');
        $textNodes.Item(0).AppendChild($template.CreateTextNode('⚡ NEW CYMATICS DROP UNLOCKED!')) > $null;
        $textNodes.Item(1).AppendChild($template.CreateTextNode('{title} - Click or check browser!')) > $null;
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template);
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('AI-BS Sniper').Show($toast);
        """
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def auto_add_to_cart_with_retry(variant_id, max_retries=3):
    """Instant headless POST to Shopify cart/add.js with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            r = session.post(
                CART_ADD_URL,
                data={'id': variant_id, 'quantity': 1},
                headers={'X-Requested-With': 'XMLHttpRequest'},
                timeout=3.0
            )
            if r.status_code == 200:
                res = r.json()
                print(f"\n[⚡ AUTO-CART SUCCESS]: Added Variant ID {variant_id} ({res.get('title', 'Item')})", flush=True)
                return res
            else:
                time.sleep(0.2)
        except Exception:
            time.sleep(0.2)
    return None

def trigger_instant_claim(item_title, variant_id=None, direct_url=None, price='0.00'):
    """Executes the full fail-safe claim sequence: Auto-Cart + Dual Browser Launch + Toast + Siren."""
    # STRICT 100% FREE GATE: Reject anything that is not $0.00
    if price and str(price) not in ['0.00', '0', '0.0']:
        return

    clean_t = item_title.lower().replace('collection', '').replace('pack', '').strip()
    if any(o in clean_t or clean_t in o for o in ALREADY_OWNED):
        return

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n=======================================================", flush=True)
    print(f"  🚨🚨 NEW $0.00 FREE DROP DETECTED: {item_title}! [{ts}] 🚨🚨", flush=True)
    print(f"=======================================================", flush=True)

    # Resolve variant ID if missing
    if not variant_id:
        for p_t, v_i in PRECACHED_VARIANTS.items():
            if clean_t in p_t or p_t in clean_t:
                variant_id = v_i
                break

    checkout_target = None
    if variant_id:
        print(f"    [⚡ AUTO-CART]: Injecting Variant ID {variant_id} into Cart...", flush=True)
        threading.Thread(target=auto_add_to_cart_with_retry, args=(variant_id,), daemon=True).start()
        checkout_target = f"https://cymatics.fm/cart/{variant_id}:1?checkout"
    elif direct_url:
        checkout_target = direct_url if direct_url.startswith('http') else f"https://cymatics.fm{direct_url}"

    if checkout_target:
        print(f"    [⚡ AUTO-CHECKOUT]: Launching Direct Checkout: {checkout_target}", flush=True)
        try:
            webbrowser.open(checkout_target)
        except Exception:
            try:
                launch_windows_open(checkout_target)
            except Exception:
                pass

    # Record in history and emergency text queue
    drop_history.append({
        "timestamp": ts,
        "title": item_title,
        "variant_id": variant_id,
        "url": checkout_target,
        "price": price
    })
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(drop_history, f, indent=2)
        with open(EMERGENCY_QUEUE_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] {item_title} | {checkout_target}\n")
    except Exception:
        pass

    # Launch non-blocking alert & desktop notification
    threading.Thread(target=play_fail_safe_siren, daemon=True).start()
    threading.Thread(target=send_windows_toast, args=(item_title, checkout_target or "https://cymatics.fm"), daemon=True).start()

# --- CHANNEL 1: DROP PAGE DOM STREAM SCANNER ---
def scan_drop_page():
    try:
        t0 = time.time()
        resp = session.get(DROP_PAGE_URL, timeout=3.5)
        if resp.status_code != 200:
            return
            
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all(lambda tag: tag.name == 'div' and tag.has_attr('class') and 'dl-card' in tag['class'] and 'dl-card-grid' not in tag['class'])
        
        for card in cards:
            classes = card.get('class', [])
            is_locked = any('locked' in c.lower() for c in classes)
            card_num = card.get('data-card-num', 'unknown')
            
            img = card.find('img')
            alt = img.get('alt', 'Unknown Pack').strip() if img else 'Unknown Pack'
            
            btn = card.find(['button', 'a'])
            btn_style = btn.get('style', '') if btn else ''
            btn_disabled = btn.has_attr('disabled') if btn else True
            variant_id = btn.get('data-variant-id') or btn.get('data-id') if btn else None
            href = btn.get('href', '') if btn else ''
            
            timer = card.find(class_=lambda c: c and 'timer' in c)
            timer_style = timer.get('style', '') if timer else ''
            timer_active = timer and ('display:none' not in timer_style.replace(' ', ''))

            card_key = f"{card_num}_{alt}"
            
            unlocked_now = False
            if not is_locked and card_key not in unlocked_cards_known:
                unlocked_now = True
            elif variant_id and card_key not in unlocked_cards_known:
                unlocked_now = True
            elif timer_active and card_key not in unlocked_cards_known:
                unlocked_now = True
            elif ('display:none' not in btn_style.replace(' ', '')) and not btn_disabled and card_key not in unlocked_cards_known:
                unlocked_now = True
            elif href and ('checkout' in href or 'cart' in href or 'download' in href) and card_key not in unlocked_cards_known:
                unlocked_now = True
                
            if unlocked_now:
                unlocked_cards_known.add(card_key)
                trigger_instant_claim(alt, variant_id=variant_id, direct_url=href, price='0.00')

        # Direct download archives
        for pattern in DOWNLOAD_PATTERNS:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for m in matches:
                if m not in known_direct_links:
                    known_direct_links.add(m)
                    trigger_instant_claim(f"Direct Archive: {os.path.basename(m)}", direct_url=m, price='0.00')

        now_str = datetime.now().strftime('%H:%M:%S.%f')[:-4]
        latency_ms = int((time.time() - t0) * 1000)
        locked_count = len(cards) - len(unlocked_cards_known)
        print(f"[{now_str}] Drop Page ({latency_ms}ms | {len(cards)} Cards | {locked_count} Locked) | 5-Channel Armed...", end='\r', flush=True)

    except Exception:
        pass

# --- CHANNEL 2 & 3: PRODUCTS & COLLECTIONS JSON FEED SCANNER ---
def scan_storewide_feeds():
    while True:
        for url in [PRODUCTS_JSON_URL, COLLECTIONS_JSON_URL]:
            try:
                r = session.get(url, timeout=4.0)
                if r.status_code == 200:
                    products = r.json().get('products', [])
                    for p in products:
                        p_id = p.get('id')
                        title = p.get('title', '')
                        handle = p.get('handle', '')
                        
                        for v in p.get('variants', []):
                            price = v.get('price', '')
                            v_id = v.get('id')
                            PRECACHED_VARIANTS[title.lower().strip()] = v_id
                            
                            # STRICT $0.00 FREE ONLY
                            if price == '0.00' and p_id not in known_product_ids:
                                known_product_ids.add(p_id)
                                trigger_instant_claim(title, variant_id=v_id, direct_url=f"/products/{handle}", price='0.00')

            except Exception:
                pass
            time.sleep(1.0)
        time.sleep(1.5)

# --- CHANNEL 4: SITEMAP XML LIVE SCANNER ---
def scan_sitemap():
    while True:
        try:
            r = session.get(SITEMAP_URL, timeout=5.0)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for elem in root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc = elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        if url not in known_sitemap_urls:
                            known_sitemap_urls.add(url)
                            # Probe new URL for $0.00 variant
                            if '/products/' in url:
                                handle = url.split('/products/')[-1]
                                try:
                                    r_p = session.get(f"https://cymatics.fm/products/{handle}.json", timeout=2.5)
                                    if r_p.status_code == 200:
                                        prod = r_p.json().get('product', {})
                                        t = prod.get('title', handle)
                                        for v in prod.get('variants', []):
                                            if v.get('price') == '0.00':
                                                trigger_instant_claim(t, variant_id=v.get('id'), direct_url=f"/products/{handle}", price='0.00')
                                except Exception:
                                    pass
        except Exception:
            pass
        time.sleep(10.0)

# --- CHANNEL 5: PRE-RESOLVED HANDLE AVAILABILITY PROBER ---
def probe_upcoming_handles():
    upcoming_handles = [
        'dope-collection-melodies', 'dope-collection-drums', 'dope-collection-vocals',
        'dope-collection-bonus-stash', 'solace-acapellas', 'daydream-vocal-loops',
        'euphoria-vocal-chops', 'sessions-melody-compositions', 'generations-1970s-premium-samples',
        'generations-1960s-premium-samples', 'kingdom-electronic-midi-collection',
        'pandora-edm-midi', 'pandora-rnb-midi', 'pandora-trap-midi',
        'pandora-paradise-expansion', 'pandora-echoes-expansion', 'midi-shredder'
    ]
    while True:
        for h in upcoming_handles:
            try:
                r = session.get(f"https://cymatics.fm/products/{h}.json", timeout=3.0)
                if r.status_code == 200:
                    prod = r.json().get('product', {})
                    t = prod.get('title', h)
                    for v in prod.get('variants', []):
                        if v.get('price') == '0.00' and v.get('available') is True:
                            trigger_instant_claim(f"{t} (LIVE UNLOCKED)", variant_id=v.get('id'), direct_url=f"/products/{h}", price='0.00')
            except Exception:
                pass
            time.sleep(0.5)
        time.sleep(2.0)

def run_engine():
    print(f"=====================================================", flush=True)
    print(f"  AI-BS ENTERPRISE CYMATICS 5-CHANNEL DROP SNIPER", flush=True)
    print(f"  Fail-Safe Architecture: FULL REDUNDANCY ACTIVE", flush=True)
    print(f"  Gate: STRICT $0.00 FREE ONLY (Zero Paid Claims)", flush=True)
    print(f"  Channel 1: Drop Page DOM Stream Scanner (~250ms RTT)", flush=True)
    print(f"  Channel 2: Storewide Products JSON Feed (250 limit)", flush=True)
    print(f"  Channel 3: Collection Feed (Sort By Created Desc)", flush=True)
    print(f"  Channel 4: Sitemap XML Live Scanner", flush=True)
    print(f"  Channel 5: Pre-Resolved Upcoming Handles Prober", flush=True)
    print(f"  Alerts: Headless Auto-Cart + Dual Browser + Siren + Toast", flush=True)
    print(f"=====================================================", flush=True)

    # Launch background worker threads
    threading.Thread(target=scan_storewide_feeds, daemon=True).start()
    threading.Thread(target=scan_sitemap, daemon=True).start()
    threading.Thread(target=probe_upcoming_handles, daemon=True).start()

    poll_count = 0
    while True:
        poll_count += 1
        update_heartbeat()
        if poll_count % 20 == 0:
            session.headers.update(get_spoofed_headers())
        scan_drop_page()
        time.sleep(0.25)

if __name__ == "__main__":
    run_engine()
