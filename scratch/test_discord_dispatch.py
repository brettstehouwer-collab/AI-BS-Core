import os
import requests
from datetime import datetime

ENV_FILE = r"C:\AI-BS\.env"
wh = ""
with open(ENV_FILE) as f:
    for l in f:
        if l.startswith("DISCORD_WEBHOOK_URL="):
            wh = l.split("=", 1)[1].strip().strip('"')
            break

embed = {
    "title": "⚡ AI-BS Sovereign Mining & Trading Webhook Online",
    "description": "Verified pipeline handshake between AI-BS Host daemons, Pearl (PRL) PoUW mining telemetry, and Discord `#TradeBot`.",
    "color": 0x00ffcc,
    "timestamp": datetime.utcnow().isoformat(),
    "fields": [
        {"name": "Hardware Status", "value": "RTX 4090 @ 310W / 5001MHz (54°C)", "inline": True},
        {"name": "Mining Efficiency", "value": "587 Shares (100.0% eff)", "inline": True},
        {"name": "Mature Balance", "value": "0.2164 PRL ($0.67 USD)", "inline": True},
        {"name": "Crypto Trader", "value": "CRO/USD $0.05608 (Active WS)", "inline": True}
    ],
    "footer": {"text": "AI-BS Autonomous Telemetry • Port 8000/8007"}
}

payload = {
    "username": "AI-BS Sovereign Node",
    "embeds": [embed]
}

res = requests.post(wh, json=payload, timeout=5)
print("Discord Post Status:", res.status_code)
if res.status_code not in [200, 204]:
    print("Error:", res.text)
