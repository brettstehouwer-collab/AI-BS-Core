import sys
import requests
from bs4 import BeautifulSoup
import json

sys.stdout.reconfigure(encoding='utf-8')

url = "https://cymatics.fm/pages/cymatics-c86v"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

cards = soup.find_all(class_=lambda x: x and 'dl-card' in x and 'data-card-num' in getattr(x, 'attrs', {}))
if not cards:
    cards = soup.select('.dl-card[data-card-num]')

print(f"Total Stream Cards with data-card-num: {len(cards)}")

unlocked = []
locked = []

for card in cards:
    num_str = card.get('data-card-num')
    try:
        num = int(num_str)
    except:
        num = num_str
        
    classes = card.get('class', [])
    
    # Title from img alt or text
    img = card.find('img', class_='dl-card__img')
    img_alt = img.get('alt', '') if img else ''
    real_img = img.get('data-real-img', '') if img else ''
    src_img = img.get('src', '') if img else ''
    
    title_elem = card.find(class_='dl-card__title')
    title_text = title_elem.get_text(strip=True) if title_elem else ''
    title = title_text or img_alt or f"Card #{num}"
    
    # CTA & Buttons
    cta_btn = card.find(class_='dl-card__cta') or card.find('button') or card.find('a')
    cta_text = cta_btn.get_text(strip=True) if cta_btn else 'No CTA'
    
    # Check if locked
    is_locked = 'dl-card--locked' in classes or 'locked' in ' '.join(classes).lower()
    
    # Check variant id or buy links
    variant_id = card.get('data-variant-id', '')
    if not variant_id and cta_btn:
        variant_id = cta_btn.get('data-variant-id', '')
    
    # Check form
    form = card.find('form')
    if form:
        inp = form.find('input', {'name': 'id'})
        if inp:
            variant_id = inp.get('value', variant_id)

    item = {
        'num': num,
        'title': title,
        'is_locked': is_locked,
        'cta_text': cta_text,
        'variant_id': variant_id,
        'classes': classes,
        'real_img': real_img
    }
    
    if is_locked:
        locked.append(item)
    else:
        unlocked.append(item)

# Sort by card num
unlocked.sort(key=lambda x: x['num'] if isinstance(x['num'], int) else 999)
locked.sort(key=lambda x: x['num'] if isinstance(x['num'], int) else 999)

print(f"\n=======================================================")
print(f"SUMMARY: {len(unlocked)} UNLOCKED / {len(locked)} LOCKED (Total: {len(cards)})")
print(f"=======================================================\n")

print(f"--- UNLOCKED CARDS ({len(unlocked)}) ---")
for u in unlocked:
    print(f"Card #{u['num']:3}: {u['title']:<45} | CTA: {u['cta_text']:<15} | Variant: {u['variant_id']}")

print(f"\n--- LOCKED CARDS COUNT: {len(locked)} ---")
if locked:
    print("First 10 locked cards:")
    for l in locked[:10]:
        print(f"Card #{l['num']:3}: {l['title']:<45} | CTA: {l['cta_text']}")
    print(f"... and {len(locked) - 10} more locked cards.")
