import sys
import requests
from bs4 import BeautifulSoup
import json

sys.stdout.reconfigure(encoding='utf-8')

url = "https://cymatics.fm/pages/cymatics-c86v"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

# Let's find all cards inside the stream / drop grid
grids = soup.find_all(class_=lambda x: x and ('grid' in x or 'drops' in x or 'cards' in x or 'stream' in x))
print(f"Grids found: {len(grids)}")

# Look specifically for the main drop container
main_cards = soup.select('.dl-card')
print(f"Total .dl-card: {len(main_cards)}")

# Let's inspect the first 10 cards and any cards with 'locked' or 'unlocked'
valid_cards = []
for i, card in enumerate(main_cards):
    text = card.get_text(separator=" | ", strip=True)
    classes = card.get('class', [])
    data_num = card.get('data-card-num')
    
    # If it has content or data_num
    if data_num or len(text) > 0:
        valid_cards.append((i, data_num, classes, text, str(card)[:400]))

print(f"Valid cards with content/data_num: {len(valid_cards)}")

for i, num, cls, text, raw in valid_cards[:25]:
    print(f"--- CARD #{num or i} (Classes: {cls}) ---")
    print(f"Text: {text}")
    print(f"Raw snippet: {raw}\n")
