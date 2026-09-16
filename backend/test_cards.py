import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

cards = soup.find_all(class_=lambda c: c and 'dl-card' in c)
print(f'Total cards on page: {len(cards)}')

for i, card in enumerate(cards):
    img = card.find('img')
    alt = img.get('alt', '') if img else ''
    classes = card.get('class', [])
    is_locked = any('locked' in c.lower() for c in classes)
    
    btn = card.find(['button', 'a'])
    btn_text = btn.get_text(strip=True) if btn else ''
    btn_style = btn.get('style', '') if btn else ''
    variant_id = btn.get('data-variant-id') if btn else ''
    card_num = card.get('data-card-num', '')
    
    if not is_locked or any(name in alt for name in ['Destiny', 'Trinity', 'MIDI', 'Evolution', 'Ripple', 'BOOM', 'Phalanx', 'Octagon']):
        print(f'Card #{card_num} [{alt}]: Locked={is_locked} | Btn: "{btn_text}" | Style: {btn_style} | Variant: {variant_id}')
