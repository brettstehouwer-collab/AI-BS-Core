import sqlite3
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

db_path = Path(r"C:\AI-BS\saved_data\rec_debut.db")
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=" * 70)
print(" RECREATIONAL DEBUT - COMPREHENSIVE LINK CLICK TELEMETRY AUDIT")
print("=" * 70)

# Get all click events
c.execute("""
    SELECT t.id, t.campaign_id, t.athlete_id, t.event_type, t.target_url, t.ip_address, t.created_at,
           a.name, a.phone, a.email, a.sport, a.high_school, a.city_state, a.grad_year
    FROM rec_debut_tracking_events t
    LEFT JOIN rec_debut_athletes a ON t.athlete_id = a.id
    WHERE UPPER(t.event_type) = 'CLICK'
    ORDER BY t.created_at ASC
""")
rows = [dict(r) for r in c.fetchall()]

total_clicks = len(rows)
unique_athlete_ids = set(r["athlete_id"] for r in rows if r["athlete_id"] is not None)

print(f"\nTotal Link Click Events Recorded: {total_clicks}")
print(f"Total Unique Athlete IDs Clicked: {len(unique_athlete_ids)}")

# Classify into Test/Internal vs Real Leads
test_athlete_ids = {1, 99999}  # 1 = Keonte Jenkins (test template #1), 99999 = Brett Stehouwer
# Also check IPs
local_ips = {"127.0.0.1", "127.0.0.1, 127.0.0.1"}

real_clicks = []
test_clicks = []

for r in rows:
    aid = r["athlete_id"]
    ip = r["ip_address"] or ""
    # Check if internal test
    if aid in test_athlete_ids or ip in local_ips or "38.131.234.4" in ip:  # 38.131.234.4 is the operator's host IP
        test_clicks.append(r)
    else:
        real_clicks.append(r)

print(f"\n--- BREAKDOWN ---")
print(f"Verified External/Recruit Link Clicks: {len(real_clicks)}")
print(f"Internal / Operator Test Clicks:       {len(test_clicks)}")

# Unique real athletes
real_unique_athletes = {}
for r in real_clicks:
    aid = r["athlete_id"]
    if aid not in real_unique_athletes:
        real_unique_athletes[aid] = {
            "athlete_id": aid,
            "name": r["name"] or f"Athlete #{aid}",
            "phone": r["phone"],
            "email": r["email"],
            "sport": r["sport"],
            "high_school": r["high_school"],
            "city_state": r["city_state"],
            "grad_year": r["grad_year"],
            "clicks": 0,
            "first_click": r["created_at"],
            "last_click": r["created_at"],
            "ips": set(),
            "campaigns": set()
        }
    real_unique_athletes[aid]["clicks"] += 1
    real_unique_athletes[aid]["last_click"] = max(real_unique_athletes[aid]["last_click"], r["created_at"])
    real_unique_athletes[aid]["ips"].add(r["ip_address"])
    real_unique_athletes[aid]["campaigns"].add(r["campaign_id"])

print(f"\nTotal Unique Real Recruits Who Clicked: {len(real_unique_athletes)}")
print("-" * 70)

for aid, info in sorted(real_unique_athletes.items(), key=lambda x: x[1]["last_click"], reverse=True):
    last_dt = datetime.fromtimestamp(info["last_click"]).strftime("%Y-%m-%d %I:%M:%S %p")
    first_dt = datetime.fromtimestamp(info["first_click"]).strftime("%Y-%m-%d %I:%M:%S %p")
    hs = f" | {info['high_school']}" if info['high_school'] else ""
    loc = f" ({info['city_state']})" if info['city_state'] else ""
    grad = f" (Class of {info['grad_year']})" if info['grad_year'] else ""
    camps = ", ".join(info["campaigns"])
    ips = ", ".join(info["ips"])
    print(f"🏀 ID #{aid}: {info['name']}{grad}")
    print(f"   School/Sport: {info['sport']}{hs}{loc}")
    print(f"   Phone:        {info['phone']}")
    print(f"   Clicks:       {info['clicks']} click(s)")
    print(f"   Last Clicked: {last_dt} (First: {first_dt})")
    print(f"   Campaign:     {camps} | IP: {ips}")
    print()

# Now also check recent Class of 2027 campaign specifically
print("=" * 70)
print(" CLASS OF 2027 SMS CAMPAIGN RECRUITS SPECIFICALLY (Recent Run)")
print("=" * 70)
c27_real = [r for r in real_clicks if r["campaign_id"] in ("sms", "sms_shortlink")]
c27_unique = set(r["athlete_id"] for r in c27_real)
print(f"Class of 2027 SMS Clicks: {len(c27_real)} click events across {len(c27_unique)} unique student-athletes:")

for aid in sorted(c27_unique):
    info = real_unique_athletes[aid]
    last_dt = datetime.fromtimestamp(info["last_click"]).strftime("%Y-%m-%d %I:%M:%S %p")
    print(f"  • {info['name']} (ID {aid}) - {info['phone']} - {info['clicks']} click(s) - Last at {last_dt}")

conn.close()
