import requests
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

r = requests.get('https://www.youtube.com/watch?v=xZ9FOZ2g878', headers=headers)
html = r.text

# Extract video title
title_match = re.search(r'<title>(.*?)</title>', html)
title = title_match.group(1) if title_match else "Unknown"
print("Live Stream Title:", title)

# Extract description links
urls = re.findall(r'https?://[^\s"\'<>]+', html)
clean_urls = set()
for u in urls:
    if any(k in u.lower() for k in ['cymatics', 'dropbox', 'drive.google', 'we.tl', 'wetransfer', 'cart', 'checkout', 'mediafire']):
        # Clean trailing chars
        u_clean = u.rstrip('",;\\)}]>')
        clean_urls.add(u_clean)

print("\nExtracted Stream & Description Links:")
for cu in sorted(list(clean_urls)):
    print("  ->", cu)

# Look for live chat continuation token or initial data
initial_data_match = re.search(r'ytInitialData\s*=\s*({.+?});</script>', html)
if initial_data_match:
    print("\nytInitialData extracted successfully.")
    try:
        data = json.loads(initial_data_match.group(1))
        # Find live chat renderer
        contents = data.get('contents', {})
        print("Keys in ytInitialData contents:", list(contents.keys()))
    except Exception as e:
        print("JSON parse error on ytInitialData:", e)
