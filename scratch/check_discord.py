import sys, requests
sys.path.append('C:/AI-BS/backend')
from discord_bot_daemon import DISCORD_BOT_TOKEN
headers = {'Authorization': 'Bot ' + DISCORD_BOT_TOKEN}
r = requests.get('https://discord.com/api/v10/channels/1526361931399827466/messages?limit=6', headers=headers)
for m in r.json():
    print(m['id'], m.get('author',{}).get('username'), m['timestamp'])
