import os
import sqlite3
import datetime
import sys

sys.path.append("C:\\AI-BS")
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg): print(msg)

RESOURCE_DIR = "E:\\AI_BS_Resources"
DB_DIR = os.path.join(RESOURCE_DIR, "Databases")

os.makedirs(DB_DIR, exist_ok=True)

db_names = [
    "real_estate.db", "legal_contracts.db", "medical_fhir.db", "retail_products.db",
    "finance_ledger.db", "education_lms.db", "mfg_supply.db", "ag_yields.db",
    "entertainment_media.db", "cyber_threats.db", "hr_talent.db", "support_tickets.db",
    "logistics_routes.db", "insurance_claims.db", "construction_blueprints.db", "automotive_inventory.db",
    "travel_itineraries.db", "gaming_assets.db", "ngo_grants.db", "journalism_archives.db",
    "wellness_metrics.db", "events_ticketing.db", "gov_policies.db", "energy_grid.db",
    "telecom_network.db", "mining_surveys.db", "aerospace_telemetry.db", "pharma_trials.db",
    "fashion_trends.db", "foodbev_inventory.db", "audio_stems.db", "video_broadcast.db",
    "photography_assets.db", "animation_vfx.db", "translation_corpus.db", "writing_manuscripts.db",
    "seo_analytics.db", "social_metrics.db", "pr_campaigns.db", "sports_analytics.db",
    "landscaping.db", "real_estate_dev.db", "hvac.db", "plumbing.db", "electrical.db",
    "cleaning.db", "security.db", "pestcontrol.db", "wastemgmt.db", "delivery.db",
    "datacenter.db", "devops.db", "cloudfinops.db", "quantum.db", "robotics.db",
    "cv.db", "blockchain.db", "syntheticbio.db", "materials.db", "nlpresearch.db",
    "edgeiot.db", "observability.db", "embedded.db", "gamearch.db", "pentesting.db",
    "autovehicles.db", "ardev.db", "semiconductors.db", "nanotech.db", "deepspace.db"
]

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    c = conn.cursor()
    # Create generic schema for telemetry and metrics (useful for the dashboards)
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            status TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS active_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            task TEXT,
            last_ping DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def main():
    print(f"Initializing {len(db_names)} SQLite databases in {DB_DIR}...")
    for db in db_names:
        db_path = os.path.join(DB_DIR, db)
        init_db(db_path)
        
        # We need to also create a symlink or put them where demo_industry_suites.py expects them,
        # which is directly in E:\AI_BS_Resources\ (based on demo_industry_suites.py paths).
        # Ah, the plan said "E:\AI_BS_Resources\Databases" but demo_industry_suites.py points to "E:\\AI_BS_Resources\real_estate.db"
        # I will create them in E:\AI_BS_Resources directly to avoid breaking the router.
        direct_path = os.path.join(RESOURCE_DIR, db)
        init_db(direct_path)
        
    print("Database Generation Complete.")
    send_discord_update(f"Phase 9 Complete: Generated 70 SQLite databases in {RESOURCE_DIR}")

if __name__ == "__main__":
    main()
