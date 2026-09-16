import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

stream_cards = []
for card in soup.find_all(class_=lambda c: c and 'dl-card' in c):
    text = card.get_text()
    img = card.find('img')
    alt = img.get('alt', 'Unknown') if img else 'Unknown'
    real_img = img.get('data-real-img', '') if img else ''
    btn = card.find(['button', 'a'])
    btn_style = btn.get('style', '') if btn else ''
    is_locked = 'dl-card--locked' in card.get('class', []) or 'Unlocks during' in text
    
    if is_locked or 'Trinity' in alt or 'Destiny' in alt or 'Evolution' in alt or 'MIDI' in alt:
        stream_cards.append({
            'title': alt,
            'locked': is_locked,
            'btn_style': btn_style,
            'real_img': real_img
        })

print(f'Found {len(stream_cards)} stream cards.')
for sc in stream_cards[:20]:
    lock_status = "🔒 LOCKED" if sc['locked'] else "✅ UNLOCKED"
    print(f"{lock_status} | {sc['title']}")
