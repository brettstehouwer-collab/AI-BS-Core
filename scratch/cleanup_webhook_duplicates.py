import sys, time, requests
sys.path.append("C:/AI-BS/backend")
from discord_bot_daemon import DISCORD_BOT_TOKEN, DISCORD_WEBHOOK_URL

headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
wh_url = DISCORD_WEBHOOK_URL.rstrip('/')
channel_id = "1526361931399827466"

print("Fetching recent messages from #trade-signals...")
r = requests.get(f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100", headers=headers)
if r.status_code != 200:
    print("Failed to fetch messages:", r.text)
    sys.exit(1)

messages = r.json()
print(f"Total messages fetched: {len(messages)}")

deleted = 0
for m in messages:
    author = m.get("author", {}).get("username", "")
    mid = m.get("id")
    # Only delete messages sent by the webhook (AI-BS Matrix Node)
    if author == "AI-BS Matrix Node":
        del_r = requests.delete(f"{wh_url}/messages/{mid}")
        if del_r.status_code in [200, 204]:
            print(f"Deleted duplicate webhook message {mid}")
            deleted += 1
            time.sleep(0.3)  # Respect rate limits
        else:
            print(f"Failed to delete {mid}: HTTP {del_r.status_code} - {del_r.text}")

print(f"Cleanup finished. Deleted {deleted} duplicate webhook messages.")
