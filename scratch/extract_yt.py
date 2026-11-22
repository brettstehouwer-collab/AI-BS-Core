import urllib.request
import re
import json

req = urllib.request.Request('https://www.youtube.com/watch?v=zc-dsSauYGM', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
html = urllib.request.urlopen(req).read().decode('utf-8', 'ignore')

# Extract title
title_match = re.search(r'<title>(.*?)</title>', html)
print('Title:', title_match.group(1) if title_match else 'None')

# Look for caption tracks
caption_match = re.search(r'"captionTracks":(\[.*?\])', html)
if caption_match:
    tracks = json.loads(caption_match.group(1))
    for t in tracks:
        print('Found track language:', t.get('name', {}).get('simpleText'), t.get('languageCode'))
        track_url = t.get('baseUrl')
        if track_url:
            with open('scratch/caption_url.txt', 'w', encoding='utf-8') as f:
                f.write(track_url)
            print('Saved caption url to scratch/caption_url.txt')
            break
else:
    print('No caption tracks found in raw HTML')

# Find description
desc_match = re.search(r'"shortDescription":"(.*?)"', html)
if desc_match:
    raw_desc = desc_match.group(1).encode('utf-8').decode('unicode_escape')
    print('\n--- Video Description ---')
    print(raw_desc)
    with open('scratch/yt_desc.txt', 'w', encoding='utf-8') as f:
        f.write(raw_desc)
