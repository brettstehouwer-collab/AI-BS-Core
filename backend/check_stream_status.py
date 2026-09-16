import sys
import requests
import re

sys.stdout.reconfigure(encoding='utf-8')

# Check previous stream URL: xZ9FOZ2g878
url = "https://www.youtube.com/watch?v=xZ9FOZ2g878"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get(url, headers=headers)
print("YouTube stream status code:", r.status_code)
if "isLive" in r.text or "LIVE" in r.text:
    print("Live markers found in HTML.")
if "Streamed live" in r.text or "Stream ended" in r.text or "Premieres" in r.text:
    print("Stream might have ended or is archived.")

# Search for liveBroadcastDetails
match = re.search(r'"status":"([^"]+)"', r.text)
if match:
    print("Broadcast status:", match.group(1))

# Check title
title_match = re.search(r'<title>(.*?)</title>', r.text)
if title_match:
    print("Title:", title_match.group(1))

# Check if Cymatics channel has an active live stream
chan_url = "https://www.youtube.com/@CymaticsFM/live"
r_chan = requests.get(chan_url, headers=headers)
print("\nCymatics @CymaticsFM/live:")
print("Status code:", r_chan.status_code)
print("URL:", r_chan.url)
chan_title = re.search(r'<title>(.*?)</title>', r_chan.text)
if chan_title:
    print("Live Title:", chan_title.group(1))
if "isLive" in r_chan.text:
    print("Live streaming marker present.")
else:
    print("No active live streaming marker.")
