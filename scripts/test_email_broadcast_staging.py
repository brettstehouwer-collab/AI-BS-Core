import urllib.request
import json
import ssl

ctx = ssl.create_default_context()

payload = {
    "athlete_ids": None,
    "custom_phone_numbers": None,
    "message_text": """Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.

Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.

We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.

If playing college sports is your goal, don’t wait for coaches to find you.

📱 Call or text: 616-291-5227
✅ Register FREE: RecDebut.com
📧 dbell002@sbcglobal.net

Let’s get you recruited!

Dennis Bell
Former New York Knicks
President, Recreational Debut""",
    "campaign_type": "email",
    "subject_line": "Dennis Bell (Former New York Knick) - Recreational Debut Recruitment Opportunity",
    "caller_id_email": "dbell002@sbcglobal.net",
    "caller_id_phone": "+1-616-291-5227",
    "caller_id_name": "Dennis Bell (+1-616-291-5227)",
    "dry_run": True,
    "batch_limit": 303,
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

try:
    with urllib.request.urlopen(req, context=ctx, timeout=30.0) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("Dry Run Direct Email Staging:")
        print("Success:", res.get("success"))
        print("Ready Athletes Count:", res.get("ready_athletes_count"))
        print("Campaign Type:", res.get("campaign_type"))
        print("Caller ID:", res.get("caller_id"))
        if res.get("preview_recipients"):
            print("First 3 preview recipients:")
            for p in res["preview_recipients"][:3]:
                print(f" - {p['name']} <{p['email']}> ({p['phone']})")
except Exception as e:
    print("Error staging email broadcast:", e)
