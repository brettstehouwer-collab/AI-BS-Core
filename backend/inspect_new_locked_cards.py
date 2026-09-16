import sys, io, requests, json
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

r = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=6)
soup = BeautifulSoup(r.text, 'html.parser')

cards = soup.find_all(class_=lambda c: c and 'dl-card' in c)
print(f"Total Cards on Drop Page: {len(cards)}")

results = []
for idx, c in enumerate(cards):
    img = c.find('img')
    alt = img.get('alt', '') if img else ''
    real_img = img.get('data-real-img', '') if img else ''
    src = img.get('src', '') if img else ''
    card_num = c.get('data-card-num', str(idx))
    classes = c.get('class', [])
    is_locked = any('locked' in cl.lower() for cl in classes)
    
    timer = c.find(class_=lambda cl: cl and 'timer' in cl)
    timer_text = timer.get_text(strip=True) if timer else ''
    
    btn = c.find(['button', 'a'])
    btn_style = btn.get('style', '') if btn else ''
    btn_disabled = btn.has_attr('disabled') if btn else True
    variant_id = btn.get('data-variant-id') if btn else None
    
    results.append({
        'index': idx,
        'card_num': card_num,
        'title': alt or 'Mystery Drop',
        'is_locked': is_locked,
        'real_img': real_img,
        'timer': timer_text,
        'variant_id': variant_id
    })

# Filter for locked cards
locked_cards = [r for r in results if r['is_locked']]
print(f"Total Locked Cards Pending Unlock: {len(locked_cards)}")

print("\n--- FIRST 20 LOCKED CARDS PENDING UNLOCK ---")
for lc in locked_cards[:20]:
    title = lc['title']
    img_name = lc['real_img'].split('/')[-1].split('?')[0] if lc['real_img'] else 'unknown'
    print(f"Card #{lc['card_num']:<4} | Title: {title:<35} | Target Img: {img_name}")

with open("C:/AI-BS/saved_data/cymatics_locked_cards_live.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
