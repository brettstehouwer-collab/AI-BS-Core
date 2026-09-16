import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request, re

url = 'https://www.youtube.com/watch?v=xZ9FOZ2g878'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    title_match = re.search(r'<title>(.*?)</title>', html)
    print('Stream Title:', title_match.group(1) if title_match else 'Unknown')
    
    # Extract links
    links = re.findall(r'https?://[^\s"\'<>]+cymatics[^\s"\'<>]*', html)
    print('Cymatics Links Found:')
    for l in set(links):
        print(' -', l)
        
    # Extract any google drive or wetransfer links in stream page
    ext_links = re.findall(r'https?://(?:drive\.google\.com|we\.tl|dropbox\.com)/[^\s"\'<>]+', html)
    print('External Storage Links Found:')
    for el in set(ext_links):
        print(' -', el)
except Exception as e:
    print('Error:', e)
