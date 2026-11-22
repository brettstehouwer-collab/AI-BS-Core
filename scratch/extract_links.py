import urllib.parse
from bs4 import BeautifulSoup

soup = BeautifulSoup(open('C:/AI-BS/scratch/youtube_stuff_extracted/Untitleddocument.html', encoding='utf-8').read(), 'html.parser')
with open('C:/AI-BS/scratch/extracted_links.txt', 'w', encoding='utf-8') as f:
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if href:
            text = a.get_text(strip=True)
            # unwrap google redirect if present
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('q', [href])[0]
            f.write(f"{text} ===> {target}\n")
print("Done extracting links.")
