import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

site_url = "https://stehouwer-publishing.com"
sitemap_url = "https://stehouwer-publishing.com/sitemap.xml"

ping_endpoints = [
    f"https://www.google.com/ping?sitemap={sitemap_url}",
    f"https://www.bing.com/ping?sitemap={sitemap_url}",
    f"https://api.indexnow.org/indexnow?url={site_url}&key=stehouwer_pub",
    f"https://rpc.pingomatic.com/",
    f"http://blogsearch.google.com/ping/RPC2"
]

print(f"=== PINGING GLOBAL SEARCH ENGINES & DIRECTORIES FOR: {site_url} ===")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for endpoint in ping_endpoints:
    try:
        r = requests.get(endpoint, headers=headers, timeout=5)
        print(f"Pinged: {endpoint[:60]}... -> HTTP {r.status_code}")
    except Exception as e:
        print(f"Error pinging {endpoint[:40]}: {e}")

print("\nSearch engine notification & crawler ping sequence completed.")
