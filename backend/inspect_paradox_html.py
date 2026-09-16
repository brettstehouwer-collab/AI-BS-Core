import sys
from bs4 import BeautifulSoup
import re

sys.stdout.reconfigure(encoding='utf-8')

filepath = r"C:\Users\footb\.gemini\antigravity-ide\brain\417997f0-319d-4495-916f-af3a4d4ba4e9\.system_generated\steps\196\content.md"
with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Get text sections
headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'span'])
print("Headings and Key Text:")
for h in headings:
    txt = h.get_text(strip=True)
    if any(k in txt.lower() for k in ['paradox', 'bonus', 'free', 'price', '$', 'pack', 'edition', 'license', 'beta']):
        print(f"  -> {txt[:120]}")

# Look for links and buttons
print("\nAll Links:")
for a in soup.find_all('a'):
    href = a.get('href', '')
    txt = a.get_text(strip=True)
    if href and not href.startswith('#'):
        print(f"  [{txt}] -> {href}")
