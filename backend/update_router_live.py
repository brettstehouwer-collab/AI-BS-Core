import os
import sys

sys.path.append("C:\\AI-BS")
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg): print(msg)

# We use the same exact router structure, but we inject a dynamic DB fetcher.
content = """import sqlite3
import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/industry", tags=["Industry Suites"])

RESOURCE_DIR = "E:\\\\AI_BS_Resources"

def fetch_telemetry(db_name):
    db_path = os.path.join(RESOURCE_DIR, db_name)
    if not os.path.exists(db_path):
        return {"status": "inactive", "metrics": []}
    try:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        c = conn.cursor()
        c.execute("SELECT metric_name, metric_value, status, timestamp FROM system_telemetry ORDER BY id DESC LIMIT 15")
        rows = c.fetchall()
        conn.close()
        
        metrics = []
        for r in rows:
            metrics.append({"name": r[0], "value": r[1], "status": r[2], "timestamp": r[3]})
        return {"status": "active", "metrics": metrics[::-1]} # reverse to chronological
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/status")
def get_status():
    return {"status": "Enterprise Industry OS backend is online and serving live telemetry from 70 SQLite databases."}

"""

db_names = [
    ("real_estate", "real_estate.db"), ("legal", "legal_contracts.db"), ("medical", "medical_fhir.db"), 
    ("retail", "retail_products.db"), ("finance", "finance_ledger.db"), ("education", "education_lms.db"), 
    ("manufacturing", "mfg_supply.db"), ("agriculture", "ag_yields.db"), ("entertainment", "entertainment_media.db"), 
    ("cybersecurity", "cyber_threats.db"), ("hr", "hr_talent.db"), ("customer_support", "support_tickets.db"),
    ("logistics", "logistics_routes.db"), ("insurance", "insurance_claims.db"), ("construction", "construction_blueprints.db"), 
    ("automotive", "automotive_inventory.db"), ("travel", "travel_itineraries.db"), ("gaming", "gaming_assets.db"), 
    ("ngo", "ngo_grants.db"), ("journalism", "journalism_archives.db"), ("wellness", "wellness_metrics.db"), 
    ("events", "events_ticketing.db"), ("gov", "gov_policies.db"), ("energy", "energy_grid.db"),
    ("telecom", "telecom_network.db"), ("mining", "mining_surveys.db"), ("aerospace", "aerospace_telemetry.db"), 
    ("pharma", "pharma_trials.db"), ("fashion", "fashion_trends.db"), ("foodbev", "foodbev_inventory.db"), 
    ("audio", "audio_stems.db"), ("video", "video_broadcast.db"), ("photography", "photography_assets.db"), 
    ("animation", "animation_vfx.db"), ("translation", "translation_corpus.db"), ("writing", "writing_manuscripts.db"),
    ("seo", "seo_analytics.db"), ("socialmedia", "social_metrics.db"), ("pr", "pr_campaigns.db"), 
    ("sports", "sports_analytics.db"), ("landscaping", "landscaping.db"), ("realestatedev", "real_estate_dev.db"), 
    ("hvac", "hvac.db"), ("plumbing", "plumbing.db"), ("electrical", "electrical.db"),
    ("cleaning", "cleaning.db"), ("security", "security.db"), ("pestcontrol", "pestcontrol.db"), 
    ("wastemgmt", "wastemgmt.db"), ("delivery", "delivery.db"), ("datacenter", "datacenter.db"), 
    ("devops", "devops.db"), ("cloudfinops", "cloudfinops.db"), ("quantum", "quantum.db"), 
    ("robotics", "robotics.db"), ("cv", "cv.db"), ("blockchain", "blockchain.db"), 
    ("syntheticbio", "syntheticbio.db"), ("materials", "materials.db"), ("nlpresearch", "nlpresearch.db"),
    ("edgeiot", "edgeiot.db"), ("observability", "observability.db"), ("embedded", "embedded.db"), 
    ("gamearch", "gamearch.db"), ("pentesting", "pentesting.db"), ("autovehicles", "autovehicles.db"), 
    ("ardev", "ardev.db"), ("semiconductors", "semiconductors.db"), ("nanotech", "nanotech.db"), 
    ("deepspace", "deepspace.db")
]

for endpoint, db_file in db_names:
    content += f"""@router.get("/{endpoint}")
def get_{endpoint}():
    data = fetch_telemetry("{db_file}")
    data["module"] = "{endpoint.capitalize()} OS"
    return data

"""

with open("C:/AI-BS/backend/routers/demo_industry_suites.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated demo_industry_suites.py with Live SQLite telemetry fetching for ALL 70 endpoints.")
send_discord_update("Phase 11 Backend Complete: The 70 FastAPI routes are now wired directly to the live SQLite Telemetry databases.")
