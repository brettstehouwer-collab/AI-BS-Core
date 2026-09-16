"""
AI-BS YouTube Live Chat & Stream Crawler Daemon
Monitors YouTube stream xZ9FOZ2g878 for secret links, codes, and download links.
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request
import re
import time
import json
import os

STREAM_URL = "https://www.youtube.com/live_chat?v=xZ9FOZ2g878"
OUTPUT_FILE = r"C:\AI-BS\saved_data\stream_live_links.txt"
seen_links = set()

def poll_stream_chat():
    print(f"[{time.strftime('%H:%M:%S')}] Stream Chat Crawler Active for xZ9FOZ2g878...")
    while True:
        try:
            req = urllib.request.Request(
                STREAM_URL, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8', errors='ignore')
            
            # Find URLs
            urls = re.findall(r'https?://[^\s"\'<>\\)]+', html)
            for u in urls:
                if u not in seen_links and any(k in u.lower() for k in ['cymatics', 'drive.google', 'we.tl', 'dropbox', 'mediafire', 'mega.nz']):
                    seen_links.add(u)
                    print(f"\n🚨 [STREAM LINK DETECTED]: {u}")
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {u}\n")
        except Exception:
            pass
        time.sleep(2.0)

if __name__ == "__main__":
    poll_stream_chat()
