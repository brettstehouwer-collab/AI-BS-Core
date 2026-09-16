import os
import sqlite3

RESOURCE_DIR = "E:\\AI_BS_Resources"
DB_DIR = os.path.join(RESOURCE_DIR, "Databases")

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

def upgrade_schemas():
    print("Upgrading schemas for 70 databases...")
    count = 0
    for db in db_names:
        db_path = os.path.join(RESOURCE_DIR, db)
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS industry_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    title TEXT,
                    content TEXT,
                    url TEXT,
                    published_at TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            count += 1
        except Exception as e:
            print(f"Failed on {db}: {e}")
            
    print(f"Successfully upgraded {count} databases.")

if __name__ == "__main__":
    upgrade_schemas()
