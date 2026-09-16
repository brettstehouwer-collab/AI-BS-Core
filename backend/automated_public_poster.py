import requests
import xmlrpc.client
from concurrent.futures import ThreadPoolExecutor
import sys

sys.stdout.reconfigure(encoding='utf-8')

SITE_NAME = "Stehouwer Publishing L.L.C."
SITE_URL = "https://stehouwer-publishing.com"
FEED_URL = "https://stehouwer-publishing.com/library"
PROMO_MSG = "Stehouwer-Publishing.com — Independent Audio Engineering, Sound Suites & Literary Publishing"

print("="*80)
print(f"🚀 AUTOMATED PUBLIC WEB POSTING TOOL")
print(f"Target: {SITE_URL}")
print("="*80)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': '*/*'
}

results = []

# 1. XML-RPC Weblog & Aggregator Nodes
xml_rpc_nodes = [
    ("Ping-O-Matic Aggregator (Weblogs/FeedBurner/Spinn3r)", "http://rpc.pingomatic.com"),
    ("Blo.gs Global Web Ping Network", "http://ping.blo.gs/"),
    ("Twingly Blog & Content Indexer", "http://rpc.twingly.com/"),
    ("Feedster Feed Ping Node", "http://api.feedster.com/ping")
]

for name, endpoint in xml_rpc_nodes:
    try:
        server = xmlrpc.client.ServerProxy(endpoint, allow_none=True)
        res = server.weblogUpdates.ping(SITE_NAME, SITE_URL, FEED_URL)
        results.append((name, "SUCCESS", str(res)[:60]))
    except Exception as e:
        results.append((name, "SKIPPED/UNREACHABLE", str(e)[:60]))

# 2. Public Hubs & Real-time WebSub / PubSubHubbub Endpoints
websub_hubs = [
    ("Google PubSubHubbub Public Hub", "https://pubsubhubbub.appspot.com/publish", {"hub.mode": "publish", "hub.url": SITE_URL}),
    ("Superfeedr Public Push Hub", "https://superfeedr.com/hubbub", {"hub.mode": "publish", "hub.url": SITE_URL})
]

for name, endpoint, payload in websub_hubs:
    try:
        r = requests.post(endpoint, data=payload, headers=headers, timeout=6)
        status = f"HTTP {r.status_code}"
        results.append((name, "POSTED" if r.status_code in [200, 202, 204] else f"HTTP {r.status_code}", r.text[:60].strip().replace('\n', ' ')))
    except Exception as e:
        results.append((name, "FAILED", str(e)[:60]))

# 3. Open Web Directory & IndexNow Pings
directory_pings = [
    ("IndexNow Bing/Yandex API", f"https://api.indexnow.org/indexnow?url={SITE_URL}&key=stehouwer_pub"),
    ("Pingomatic REST Ping", f"http://pingomatic.com/ping/?title={SITE_NAME}&blogurl={SITE_URL}&rssurl={FEED_URL}&chk_weblogscom=on&chk_blogs=on&chk_feedburner=on&chk_syndic8=on"),
    ("MyPagerank Public Domain Pinger", f"https://mypagerank.net/service_pingservice_index?url={SITE_URL}")
]

for name, url in directory_pings:
    try:
        r = requests.get(url, headers=headers, timeout=6)
        results.append((name, f"HTTP {r.status_code}", "Payload Broadcasted" if r.status_code in [200, 302, 202] else r.text[:50].strip().replace('\n', ' ')))
    except Exception as e:
        results.append((name, "TIMEOUT", str(e)[:50]))

print("\n--- BROADCAST & POSTING EXECUTION LOG ---")
for target, status, note in results:
    print(f"[{status:10}] {target:<50} -> {note}")

print("="*80)
print(f"Finished posting to {len(results)} automated public targets.")
print("="*80)
