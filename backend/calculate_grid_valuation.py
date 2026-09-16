import requests
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
r = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

cards = soup.select('.dl-card[data-card-num]')

total_grid_val = 0
categories = {
    'Full Suites & Large Collections ($147 - $297)': {'count': 0, 'val': 0},
    'VST3 Audio Plugins & DSP FX ($35 - $67)': {'count': 0, 'val': 0},
    'Melody & Vocal Sample Packs ($35 - $50)': {'count': 0, 'val': 0},
    'Drum Kits & 808 Frameworks ($25 - $40)': {'count': 0, 'val': 0},
    'MIDI Collections & Mini Packs ($20 - $30)': {'count': 0, 'val': 0},
    'Exclusive Sitewide Gift Cards & Deals ($50 - $100)': {'count': 0, 'val': 0}
}

for c in cards:
    num = c.get('data-card-num')
    img = c.find('img', class_='dl-card__img')
    title = (img.get('alt') if img else '') or f'Card #{num}'
    title_l = title.lower()
    
    if any(k in title_l for k in ['suite', 'collection', 'anniversary', 'edition', 'apocalypse', 'destiny', 'zodiac', 'sessions', 'generations', 'paradox']):
        categories['Full Suites & Large Collections ($147 - $297)']['count'] += 1
        categories['Full Suites & Large Collections ($147 - $297)']['val'] += 147
        total_grid_val += 147
    elif any(k in title_l for k in ['plugin', 'engine', 'shifter', 'nc-73', 'phantom', 'corrosion', 'plinko', 'chili', 'pulse', 'lotus', 'space', 'origin', 'diablo', 'memory', 'deja']):
        categories['VST3 Audio Plugins & DSP FX ($35 - $67)']['count'] += 1
        categories['VST3 Audio Plugins & DSP FX ($35 - $67)']['val'] += 49
        total_grid_val += 49
    elif any(k in title_l for k in ['discount', 'gift card', 'coupon', '50% off']):
        categories['Exclusive Sitewide Gift Cards & Deals ($50 - $100)']['count'] += 1
        categories['Exclusive Sitewide Gift Cards & Deals ($50 - $100)']['val'] += 50
        total_grid_val += 50
    elif any(k in title_l for k in ['drum', '808', 'rattle', 'percussion', 'hihat', 'snare', 'claps']):
        categories['Drum Kits & 808 Frameworks ($25 - $40)']['count'] += 1
        categories['Drum Kits & 808 Frameworks ($25 - $40)']['val'] += 30
        total_grid_val += 30
    elif any(k in title_l for k in ['midi', 'preset', 'chords']):
        categories['MIDI Collections & Mini Packs ($20 - $30)']['count'] += 1
        categories['MIDI Collections & Mini Packs ($20 - $30)']['val'] += 20
        total_grid_val += 20
    else:
        categories['Melody & Vocal Sample Packs ($35 - $50)']['count'] += 1
        categories['Melody & Vocal Sample Packs ($35 - $50)']['val'] += 35
        total_grid_val += 35

print(f"Total Stream Cards on Grid: {len(cards)}")
print("\n=== 194 STREAM GRID CARDS VALUATION BREAKDOWN ===")
for cat, data in categories.items():
    c_num = data['count']
    v_num = data['val']
    print(f"{cat:<52} | {c_num:>3} items | USD {v_num:,}")

print("\n" + "="*70)
print(f"TOTAL RETAIL VALUE OF ALL 194 STREAM DOWNLOADS: USD {total_grid_val:,}")
print("="*70)
