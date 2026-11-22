import sys, requests
sys.path.append('C:/AI-BS/backend')
from discord_bot_daemon import DISCORD_BOT_TOKEN
headers = {'Authorization': 'Bot ' + DISCORD_BOT_TOKEN}
# Let's check message 1546724309563740263
r = requests.get('https://discord.com/api/v10/channels/1526361931399827466/messages/1546724309563740263', headers=headers)
print('Fetch status:', r.status_code)
