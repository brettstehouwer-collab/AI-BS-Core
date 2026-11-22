import sys, requests
sys.path.append("C:/AI-BS/backend")
from discord_bot_daemon import DISCORD_BOT_TOKEN

headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
r = requests.get("https://discord.com/api/v10/channels/1526361931399827466/messages?limit=15", headers=headers)
for m in r.json():
    mid = m.get("id")
    author = m.get("author", {}).get("username")
    embeds = len(m.get("embeds", []))
    title = m.get("embeds", [{}])[0].get("title") if embeds > 0 else ""
    ts = m.get("timestamp")
    print(f"ID: {mid} | {ts} | {author} | Embeds: {embeds} | Title: {title}")
