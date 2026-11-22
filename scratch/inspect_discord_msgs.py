import sys, json, requests
sys.path.append("C:/AI-BS/backend")
from discord_bot_daemon import DISCORD_BOT_TOKEN

headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
channel_id = "1526361931399827466"
message_ids = ["1546723158449455126", "1546723424137904199"]

for mid in message_ids:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{mid}"
    r = requests.get(url, headers=headers)
    print(f"=== MESSAGE {mid} (Status: {r.status_code}) ===")
    if r.status_code == 200:
        d = r.json()
        print(f"Author: {d.get('author', {}).get('username')}")
        print(f"Content: {d.get('content')}")
        embeds = d.get('embeds', [])
        print(f"Embeds count: {len(embeds)}")
        for idx, e in enumerate(embeds):
            print(f"--- Embed {idx+1} ---")
            print(f"Title: {e.get('title')}")
            print(f"Description: {e.get('description')}")
            for f in e.get('fields', []):
                name = f.get('name')
                val = f.get('value')
                print(f"  Field [{name}]: {val}")
    else:
        print(r.text)
