import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request, re, json

url = 'https://www.youtube.com/live_chat?v=xZ9FOZ2g878'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    html = urllib.request.urlopen(req, timeout=8).read().decode('utf-8', errors='ignore')
    print('Live chat page fetched. Length:', len(html))
    
    # Extract links in chat
    links = re.findall(r'https?://[^\s"\'<>]+', html)
    special_links = [l for l in set(links) if any(k in l.lower() for k in ['cymatics', 'drive', 'we.tl', 'dropbox', 'cart', 'checkout'])]
    print(f'Found {len(special_links)} relevant links in chat state:')
    for sl in special_links:
        print(' -', sl)
except Exception as e:
    print('Error:', e)
