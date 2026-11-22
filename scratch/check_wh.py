import requests
from pathlib import Path

SCRIPT_DIR = Path('C:/AI-BS/backend')
ENV_FILE = SCRIPT_DIR.parent / '.env'

wh = ""
with open(ENV_FILE) as f:
    for line in f:
        if line.startswith('DISCORD_WEBHOOK_URL='):
            wh = line.split('=', 1)[1].strip().strip('"')
            break

print("Testing GET on Discord webhook URL...")
try:
    r = requests.get(wh, timeout=5)
    print("Webhook HTTP status:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        print("Webhook Name:", data.get("name"))
        print("Channel ID:", data.get("channel_id"))
        print("Guild ID:", data.get("guild_id"))
    else:
        print("Response:", r.text)
except Exception as e:
    print("Request failed:", e)
