import requests
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = "https://stehouwer-publishing.com/assets/index-CUnfVHWn.js"
r = requests.get(url)
print(f"Bundle HTTP {r.status_code} | Size: {len(r.content)} bytes")

# Extract readable string snippets
strings = re.findall(r'"([^"\\]{4,60})"', r.text)
interesting = [s for s in strings if any(w in s.lower() for w in ['book', 'script', 'audio', 'stem', 'sample', 'manuscript', 'stehouwer', 'library', 'author', 'film', 'music'])]

print(f"\nExtracted {len(interesting)} content strings from live bundle:")
for s in interesting[:30]:
    print("  *", s)
