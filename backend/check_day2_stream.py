import sys
import requests
import re
import json

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
r = requests.get("https://www.youtube.com/@CymaticsFM/live", headers=headers)

print("Final URL:", r.url)
# Extract video ID
video_id_match = re.search(r'v=([a-zA-Z0-9_-]+)', r.url)
if not video_id_match:
    video_id_match = re.search(r'"videoId":"([a-zA-Z0-9_-]+)"', r.text)

if video_id_match:
    video_id = video_id_match.group(1)
    print(f"Active Video ID: {video_id}")
    print(f"Direct link: https://www.youtube.com/watch?v={video_id}")

# Extract description links
links = re.findall(r'https?://[^\s"\'<>]+', r.text)
cymatics_links = set([l for l in links if 'cymatics' in l])
print("\nLinks in Stream:")
for l in cymatics_links:
    print("  ->", l)

# Check if isLiveBroadcast
is_live = '"isLiveBroadcast":true' in r.text or '"isLive":true' in r.text
print(f"\nIs Currently Live: {is_live}")
