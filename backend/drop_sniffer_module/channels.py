"""
AI-BS Drop Sniffer Module - 5-Channel Ingestion Subsystem
Coordinates real-time polling across:
1. Drop Page DOM Stream Scanner (~250ms RTT)
2. Global Storewide Products JSON Feed (limit 250)
3. Collection Feed (Sort by Created Descending)
4. Shopify Sitemap XML Live Ingest
5. Upcoming Handle Availability Prober
"""

import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup

DROP_PAGE_URL = "https://cymatics.fm/pages/cymatics-c86v"
DOWNLOADS_MIRROR_URL = "https://cymatics.fm/pages/downloads-mirror-hub"
FREE_VAULT_URL = "https://cymatics.fm/free-download-vault/"
PRODUCTS_JSON_URL = "https://cymatics.fm/products.json?limit=250"
COLLECTIONS_JSON_URL = "https://cymatics.fm/collections/all/products.json?sort_by=created-descending&limit=50"
SITEMAP_URL = "https://cymatics.fm/sitemap_products_1.xml"

DOWNLOAD_PATTERNS = [
    r'https?://[^\s"\'<>]+\.(?:zip|rar|7z|tar|gz)',
    r'https?://drive\.google\.com/[^\s"\'<>]+',
    r'https?://(?:www\.)?dropbox\.com/[^\s"\'<>]+',
    r'https?://we\.tl/[^\s"\'<>]+',
    r'https?://(?:www\.)?wetransfer\.com/[^\s"\'<>]+',
    r'https?://[^\s"\'<>]*s3[^\s"\'<>]*(?:zip|tar|audio|sample)[^\s"\'<>]*'
]

UPCOMING_TARGET_HANDLES = [
    'dope-collection-melodies', 'dope-collection-drums', 'dope-collection-vocals',
    'dope-collection-bonus-stash', 'solace-acapellas', 'daydream-vocal-loops',
    'euphoria-vocal-chops', 'sessions-melody-compositions', 'generations-1970s-premium-samples',
    'generations-1960s-premium-samples', 'kingdom-electronic-midi-collection',
    'pandora-edm-midi', 'pandora-rnb-midi', 'pandora-trap-midi',
    'pandora-paradise-expansion', 'pandora-echoes-expansion', 'midi-shredder'
]

class ChannelManager:
    def __init__(self, session, action_dispatcher, exclusion_set):
        self.session = session
        self.action_dispatcher = action_dispatcher
        self.exclusion_set = exclusion_set
        
        self.unlocked_cards_known = set()
        self.known_product_ids = set()
        self.known_direct_links = set()
        self.known_sitemap_urls = set()
        self.precached_variants = {}
        
        self.latest_stats = {
            "total_cards": 194,
            "locked_cards": 194,
            "unlocked_cards": 0,
            "last_poll_latency_ms": 0,
            "last_poll_time": ""
        }

    def is_owned(self, title):
        clean_t = title.lower().replace('collection', '').replace('pack', '').strip()
        for o in self.exclusion_set:
            if o in clean_t or clean_t in o:
                return True
        return False

    def scan_dom_channel(self):
        """Channel 1: High-Frequency Drop Page DOM Scanner."""
        try:
            t0 = time.time()
            resp = self.session.get(DROP_PAGE_URL, timeout=3.5)
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
                if not is_locked and card_key not in self.unlocked_cards_known:
                    unlocked_now = True
                elif variant_id and card_key not in self.unlocked_cards_known:
                    unlocked_now = True
                elif timer_active and card_key not in self.unlocked_cards_known:
                    unlocked_now = True
                elif ('display:none' not in btn_style.replace(' ', '')) and not btn_disabled and card_key not in self.unlocked_cards_known:
                    unlocked_now = True
                elif href and ('checkout' in href or 'cart' in href or 'download' in href) and card_key not in self.unlocked_cards_known:
                    unlocked_now = True
                    
                if unlocked_now:
                    self.unlocked_cards_known.add(card_key)
                    if not self.is_owned(alt):
                        self.action_dispatcher.execute_claim_sequence(alt, variant_id=variant_id, direct_url=href, price='0.00')

            # Direct download links on drop page
            for pattern in DOWNLOAD_PATTERNS:
                for m in re.findall(pattern, html, re.IGNORECASE):
                    if m not in self.known_direct_links:
                        self.known_direct_links.add(m)
                        self.action_dispatcher.execute_claim_sequence(f"Direct Archive: {m.split('/')[-1]}", direct_url=m, price='0.00')

            # Mirror Hub & Free Download Vault scan
            for alt_url in [DOWNLOADS_MIRROR_URL, FREE_VAULT_URL]:
                try:
                    r_alt = self.session.get(alt_url, timeout=3.0)
                    if r_alt.status_code == 200:
                        for pattern in DOWNLOAD_PATTERNS:
                            for m in re.findall(pattern, r_alt.text, re.IGNORECASE):
                                if m not in self.known_direct_links:
                                    self.known_direct_links.add(m)
                                    self.action_dispatcher.execute_claim_sequence(f"Mirror Vault: {m.split('/')[-1]}", direct_url=m, price='0.00')
                except Exception:
                    pass

            latency_ms = int((time.time() - t0) * 1000)
            self.latest_stats = {
                "total_cards": len(cards),
                "locked_cards": len(cards) - len(self.unlocked_cards_known),
                "unlocked_cards": len(self.unlocked_cards_known),
                "last_poll_latency_ms": latency_ms,
                "last_poll_time": datetime.now().strftime('%H:%M:%S')
            }
        except Exception:
            pass

    def scan_catalog_channel(self):
        """Channel 2 & 3: Global Storewide Products & Collections Feed Scanner."""
        while True:
            for url in [PRODUCTS_JSON_URL, COLLECTIONS_JSON_URL]:
                try:
                    r = self.session.get(url, timeout=4.0)
                    if r.status_code == 200:
                        for p in r.json().get('products', []):
                            p_id = p.get('id')
                            title = p.get('title', '')
                            handle = p.get('handle', '')
                            for v in p.get('variants', []):
                                price = v.get('price', '')
                                v_id = v.get('id')
                                self.precached_variants[title.lower().strip()] = v_id
                                
                                # STRICT $0.00 FREE ONLY
                                if price == '0.00' and p_id not in self.known_product_ids:
                                    self.known_product_ids.add(p_id)
                                    if not self.is_owned(title):
                                        self.action_dispatcher.execute_claim_sequence(title, variant_id=v_id, direct_url=f"/products/{handle}", price='0.00')
                except Exception:
                    pass
                time.sleep(1.0)
            time.sleep(1.5)

    def scan_sitemap_channel(self):
        """Channel 4: Shopify Sitemap XML Live Ingest."""
        while True:
            try:
                r = self.session.get(SITEMAP_URL, timeout=5.0)
                if r.status_code == 200:
                    root = ET.fromstring(r.content)
                    for elem in root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                        loc = elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                        if loc is not None and loc.text:
                            url = loc.text.strip()
                            if url not in self.known_sitemap_urls:
                                self.known_sitemap_urls.add(url)
                                if '/products/' in url:
                                    handle = url.split('/products/')[-1]
                                    try:
                                        r_p = self.session.get(f"https://cymatics.fm/products/{handle}.json", timeout=2.5)
                                        if r_p.status_code == 200:
                                            prod = r_p.json().get('product', {})
                                            t = prod.get('title', handle)
                                            for v in prod.get('variants', []):
                                                if v.get('price') == '0.00':
                                                    if not self.is_owned(t):
                                                        self.action_dispatcher.execute_claim_sequence(t, variant_id=v.get('id'), direct_url=f"/products/{handle}", price='0.00')
                                    except Exception:
                                        pass
            except Exception:
                pass
            time.sleep(10.0)

    def probe_variant_channel(self):
        """Channel 5: Upcoming Handle Availability Prober."""
        while True:
            for h in UPCOMING_TARGET_HANDLES:
                try:
                    r = self.session.get(f"https://cymatics.fm/products/{h}.json", timeout=3.0)
                    if r.status_code == 200:
                        prod = r.json().get('product', {})
                        t = prod.get('title', h)
                        for v in prod.get('variants', []):
                            if v.get('price') == '0.00' and v.get('available') is True:
                                if not self.is_owned(t):
                                    self.action_dispatcher.execute_claim_sequence(f"{t} (LIVE UNLOCKED)", variant_id=v.get('id'), direct_url=f"/products/{h}", price='0.00')
                except Exception:
                    pass
                time.sleep(0.5)
    def scan_youtube_channel(self):
        """Channel 6: YouTube Live Stream Chat & Description Sniffer."""
        yt_urls = [
            "https://www.youtube.com/watch?v=xZ9FOZ2g878",
            "https://www.youtube.com/live_chat?v=xZ9FOZ2g878"
        ]
        while True:
            for url in yt_urls:
                try:
                    r = self.session.get(url, timeout=5.0)
                    if r.status_code == 200:
                        text = r.text
                        for pattern in DOWNLOAD_PATTERNS:
                            for m in re.findall(pattern, text, re.IGNORECASE):
                                if m not in self.known_direct_links:
                                    self.known_direct_links.add(m)
                                    self.action_dispatcher.execute_claim_sequence(
                                        f"YouTube Live Drop: {m.split('/')[-1]}",
                                        direct_url=m,
                                        price='0.00'
                                    )
                        # Check for custom checkout links dropped in chat
                        cymatics_drops = re.findall(r'https?://cymatics\.fm/[^\s"\'<>]+', text, re.IGNORECASE)
                        for cd in cymatics_drops:
                            cd_clean = cd.rstrip('",;\\)}]>')
                            if cd_clean not in self.known_direct_links:
                                self.known_direct_links.add(cd_clean)
                                if 'cart' in cd_clean or 'products' in cd_clean or 'pages' in cd_clean:
                                    self.action_dispatcher.execute_claim_sequence(
                                        f"YouTube Live Link: {cd_clean}",
                                        direct_url=cd_clean,
                                        price='0.00'
                                    )
                except Exception:
                    pass
                time.sleep(2.0)
            time.sleep(3.0)
