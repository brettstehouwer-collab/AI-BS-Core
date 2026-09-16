import requests
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}

r_yt = requests.get('https://www.youtube.com/watch?v=rq2LZe3hcUU', headers=headers)
links_yt = re.findall(r'https?://[^\s"\'<>]+', r_yt.text)
for l in set(links_yt):
    if any(k in l.lower() for k in ['giveaway', 'gleam', 'form', 'gear', 'win', 'contest', 'rsvp', 'instagram']):
        print('YouTube Link:', l)

r_page = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers=headers)
links_page = re.findall(r'https?://[^\s"\'<>]+', r_page.text)
for l in set(links_page):
    if any(k in l.lower() for k in ['giveaway', 'gleam', 'form', 'gear', 'win', 'contest', 'rsvp', 'instagram']):
        print('Cymatics Page Link:', l)
