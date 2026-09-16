import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

cards = soup.find_all(class_=lambda c: c and 'dl-card' in c)
unlocked = []
locked = []

for card in cards:
    img = card.find('img')
    alt = img.get('alt', 'Unnamed') if img else 'Unnamed'
    classes = card.get('class', [])
    is_locked = any('locked' in c.lower() for c in classes)
    btn = card.find(['button', 'a'])
    btn_style = btn.get('style', '') if btn else ''
    btn_disabled = btn.has_attr('disabled') if btn else True
    variant_id = btn.get('data-variant-id') if btn else None
    
    # Check unlock
    if not is_locked or variant_id or ('display:none' not in btn_style.replace(' ', '') and not btn_disabled):
        unlocked.append({'title': alt, 'variant': variant_id, 'btn_style': btn_style})
    else:
        locked.append(alt)

print(f'=== LIVE CYMATICS STATUS ===')
print(f'Total Cards: {len(cards)}')
print(f'Unlocked ({len(unlocked)}):')
for u in unlocked[:15]:
    print(f' - {u["title"]} (Variant: {u["variant"]})')
print(f'Locked Remaining: {len(locked)}')
print(f'First 10 Locked: {locked[:10]}')
