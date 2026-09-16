import sys
import requests
from bs4 import BeautifulSoup
import json
import os

sys.stdout.reconfigure(encoding='utf-8')

url = "https://cymatics.fm/pages/cymatics-c86v"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

cards = soup.find_all(class_=lambda x: x and 'dl-card' in x)
print(f"Total dl-cards found: {len(cards)}")

unlocked_cards = []
locked_cards = []

for idx, card in enumerate(cards):
    num = card.get('data-card-num', str(idx+1))
    classes = card.get('class', [])
    
    # Title
    title_elem = card.find(class_=lambda x: x and ('title' in x.lower() or 'name' in x.lower() or 'heading' in x.lower()))
    if not title_elem:
        title_elem = card.find(['h2', 'h3', 'h4', 'h5', 'strong', 'p'])
    title = title_elem.get_text(strip=True) if title_elem else 'Unknown Title'
    
    # Button / CTA
    cta = card.find(class_=lambda x: x and 'cta' in x.lower()) or card.find('button') or card.find('a')
    cta_text = cta.get_text(strip=True) if cta else 'No CTA'
    cta_href = cta.get('href', '') if cta and cta.name == 'a' else ''
    
    # Check is locked
    is_locked = 'locked' in ' '.join(classes).lower() or 'dl-card--locked' in classes or 'locked' in cta_text.lower()
    
    variant_id = card.get('data-variant-id') or (cta.get('data-variant-id') if cta else '') or ''
    if not variant_id:
        # Check inside data attributes or inner buttons
        for btn in card.find_all(['button', 'a', 'input']):
            if btn.get('data-variant-id'):
                variant_id = btn.get('data-variant-id')
                break
            if btn.get('value') and btn.get('name') == 'id':
                variant_id = btn.get('value')
                break

    card_info = {
        'num': num,
        'title': title,
        'cta_text': cta_text,
        'cta_href': cta_href,
        'classes': ' '.join(classes),
        'variant_id': variant_id,
        'is_locked': is_locked
    }
    
    if is_locked:
        locked_cards.append(card_info)
    else:
        unlocked_cards.append(card_info)

print(f"Unlocked Cards: {len(unlocked_cards)}")
print(f"Locked Cards: {len(locked_cards)}")

print("\n=== ALL UNLOCKED CARDS ===")
for u in unlocked_cards:
    print(f"Card #{u['num']}: \"{u['title']}\" | CTA: {u['cta_text']} | Variant ID: {u['variant_id']}")

print(f"\nTotal Unlocked Count: {len(unlocked_cards)}")
