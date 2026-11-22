import urllib.request
import xml.etree.ElementTree as ET
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scratch/caption_url.txt', 'r', encoding='utf-8') as f:
    caption_url = f.read().strip()

print("Fetching captions from:", caption_url[:80], "...")

req = urllib.request.Request(caption_url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    content = urllib.request.urlopen(req).read().decode('utf-8', 'ignore')
    root = ET.fromstring(content)
    lines = []
    for elem in root.findall('.//text'):
        start = elem.get('start', '0')
        dur = elem.get('dur', '0')
        text = elem.text or ''
        text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
        lines.append(f"[{float(start):.1f}s]: {text}")
    
    full_text = "\n".join(lines)
    with open('scratch/transcript_full.txt', 'w', encoding='utf-8') as out_f:
        out_f.write(full_text)
    print(f"Success! Saved {len(lines)} caption segments to scratch/transcript_full.txt")
except Exception as e:
    print("Error fetching/parsing captions:", e)

# Also fix the description dump
import re
with open('scratch/extract_yt.py', 'r', encoding='utf-8') as f:
    pass

try:
    req2 = urllib.request.Request('https://www.youtube.com/watch?v=zc-dsSauYGM', headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req2).read().decode('utf-8', 'ignore')
    desc_match = re.search(r'"shortDescription":"(.*?)"', html)
    if desc_match:
        raw_desc = desc_match.group(1).encode('utf-8').decode('unicode_escape')
        with open('scratch/yt_desc.txt', 'w', encoding='utf-8') as df:
            df.write(raw_desc)
        print("Successfully saved description to scratch/yt_desc.txt")
except Exception as e:
    print("Error saving description:", e)
