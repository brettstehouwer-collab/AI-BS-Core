import urllib.request
import json
import time
import sys

prompt = """Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.

Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.

We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.

If playing college sports is your goal, don’t wait for coaches to find you.

📱 Call or text: +1-616-291-5227
✅ Register FREE: RecDebut.com
📧 dbell002@sbcglobal.net

Let’s get you recruited!

Dennis Bell
Former New York Knicks
President, Recreational Debut"""

payload = {
    "message_text": prompt,
    "campaign_type": "email",
    "subject_line": "Dennis Bell (Former New York Knick) - Recreational Debut",
    "caller_id_email": "dbell002@sbcglobal.net",
    "caller_id_phone": "+1-616-291-5227",
    "caller_id_name": "Dennis Bell (+1-616-291-5227)",
    "batch_limit": 400,
    "dry_run": False,
    "use_swarm": True
}

broadcast_url = "http://127.0.0.1:8080/api/v1/recdebut/broadcast"
status_url = "http://127.0.0.1:8080/api/v1/recdebut/broadcast/status"

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(broadcast_url, data=data, headers={"Content-Type": "application/json"})

print("[DISPATCH] Sending broadcast trigger request to backend...")
try:
    res = urllib.request.urlopen(req, timeout=10)
    init_resp = json.loads(res.read().decode())
    print("[DISPATCH INIT]", json.dumps(init_resp, indent=2))
except Exception as e:
    print("[DISPATCH ERROR]", e)
    sys.exit(1)

print("\n[MONITORING] Tracking live broadcast progress...")
time.sleep(2)

while True:
    try:
        s_req = urllib.request.urlopen(status_url, timeout=5)
        st = json.loads(s_req.read().decode())
        total = st.get("total", 0)
        sent = st.get("sent", 0)
        failed = st.get("failed", 0)
        progress = st.get("progress_pct", 0)
        status = st.get("status", "UNKNOWN")
        curr_athlete = st.get("current_athlete", "")

        print(f"Status: {status} | Sent: {sent}/{total} ({progress}%) | Failed: {failed} | Current: {curr_athlete}")

        if status in ("COMPLETED", "PAUSED_QUOTA", "CANCELLED", "ERROR"):
            print(f"\n[BROADCAST FINISHED] Terminal Status: {status}")
            print(f"Final Count: {sent} Successfully Delivered, {failed} Failed.")
            break
        elif not st.get("active") and status != "RUNNING":
            print(f"\n[BROADCAST INACTIVE] Final Status: {status}")
            break
    except Exception as e:
        print("[MONITOR WARNING]", e)

    time.sleep(5)
