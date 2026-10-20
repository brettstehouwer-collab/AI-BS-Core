import urllib.request
import json
import ssl
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()

message_script = """Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.

Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.

We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.

If playing college sports is your goal, don’t wait for coaches to find you.

📱 Call or text: 616-291-5227
✅ Register FREE: RecDebut.com
📧 dbell002@sbcglobal.net

Let’s get you recruited!

Dennis Bell
Former New York Knicks
President, Recreational Debut"""

payload = {
    "athlete_ids": None,
    "custom_phone_numbers": None,
    "message_text": message_script,
    "campaign_type": "sms",
    "subject_line": "Dennis Bell (+1-616-291-5227) - Recreational Debut",
    "caller_id_email": "dbell002@sbcglobal.net",
    "caller_id_phone": "+1-616-291-5227",
    "caller_id_name": "Dennis Bell (+1-616-291-5227)",
    "dry_run": False,
    "batch_limit": 554,
    "use_swarm": True
}

req_data = json.dumps(payload).encode("utf-8")
url = "https://api.brettstehouwer.live/api/v1/recdebut/broadcast"
req = urllib.request.Request(
    url,
    data=req_data,
    headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
)

print("🚀 Dispatching Next Batch (554 Athletes) via Cloudflare Edge Tunnel...")
print(f"Target URL: {url}")
print(f"Caller Name: {payload['caller_id_name']}")
print(f"Caller Email: {payload['caller_id_email']}")
print(f"Caller Phone: {payload['caller_id_phone']}")

try:
    with urllib.request.urlopen(req, context=ctx, timeout=30.0) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("\n✅ Broadcast Trigger Response:")
        print(json.dumps(res, indent=2))
except Exception as e:
    print(f"\n❌ Error launching broadcast via Cloudflare: {e}")
    sys.exit(1)
