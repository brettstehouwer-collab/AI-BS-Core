import sqlite3
import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/industry", tags=["Industry Suites"])

RESOURCE_DIR = "E:\\AI_BS_Resources"

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

@router.get("/real_estate")
def get_real_estate():
    data = fetch_telemetry("real_estate.db")
    data["module"] = "Real_estate OS"
    return data

@router.get("/legal")
def get_legal():
    data = fetch_telemetry("legal_contracts.db")
    data["module"] = "Legal OS"
    return data

@router.get("/medical")
def get_medical():
    data = fetch_telemetry("medical_fhir.db")
    data["module"] = "Medical OS"
    return data

@router.get("/retail")
def get_retail():
    data = fetch_telemetry("retail_products.db")
    data["module"] = "Retail OS"
    return data

@router.get("/finance")
def get_finance():
    data = fetch_telemetry("finance_ledger.db")
    data["module"] = "Finance OS"
    return data

@router.get("/education")
def get_education():
    data = fetch_telemetry("education_lms.db")
    data["module"] = "Education OS"
    return data

@router.get("/manufacturing")
def get_manufacturing():
    data = fetch_telemetry("mfg_supply.db")
    data["module"] = "Manufacturing OS"
    return data

@router.get("/agriculture")
def get_agriculture():
    data = fetch_telemetry("ag_yields.db")
    data["module"] = "Agriculture OS"
    return data

@router.get("/entertainment")
def get_entertainment():
    data = fetch_telemetry("entertainment_media.db")
    data["module"] = "Entertainment OS"
    return data

@router.get("/cybersecurity")
def get_cybersecurity():
    data = fetch_telemetry("cyber_threats.db")
    data["module"] = "Cybersecurity OS"
    return data

@router.get("/hr")
def get_hr():
    data = fetch_telemetry("hr_talent.db")
    data["module"] = "Hr OS"
    return data

@router.get("/customer_support")
def get_customer_support():
    data = fetch_telemetry("support_tickets.db")
    data["module"] = "Customer_support OS"
    return data

@router.get("/logistics")
def get_logistics():
    data = fetch_telemetry("logistics_routes.db")
    data["module"] = "Logistics OS"
    return data

@router.get("/insurance")
def get_insurance():
    data = fetch_telemetry("insurance_claims.db")
    data["module"] = "Insurance OS"
    return data

@router.get("/construction")
def get_construction():
    data = fetch_telemetry("construction_blueprints.db")
    data["module"] = "Construction OS"
    return data

@router.get("/automotive")
def get_automotive():
    data = fetch_telemetry("automotive_inventory.db")
    data["module"] = "Automotive OS"
    return data

@router.get("/travel")
def get_travel():
    data = fetch_telemetry("travel_itineraries.db")
    data["module"] = "Travel OS"
    return data

@router.get("/gaming")
def get_gaming():
    data = fetch_telemetry("gaming_assets.db")
    data["module"] = "Gaming OS"
    return data

@router.get("/ngo")
def get_ngo():
    data = fetch_telemetry("ngo_grants.db")
    data["module"] = "Ngo OS"
    return data

@router.get("/journalism")
def get_journalism():
    data = fetch_telemetry("journalism_archives.db")
    data["module"] = "Journalism OS"
    return data

@router.get("/wellness")
def get_wellness():
    data = fetch_telemetry("wellness_metrics.db")
    data["module"] = "Wellness OS"
    return data

@router.get("/events")
def get_events():
    data = fetch_telemetry("events_ticketing.db")
    data["module"] = "Events OS"
    return data

@router.get("/gov")
def get_gov():
    data = fetch_telemetry("gov_policies.db")
    data["module"] = "Gov OS"
    return data

@router.get("/energy")
def get_energy():
    data = fetch_telemetry("energy_grid.db")
    data["module"] = "Energy OS"
    return data

@router.get("/telecom")
def get_telecom():
    data = fetch_telemetry("telecom_network.db")
    data["module"] = "Telecom OS"
    return data

@router.get("/mining")
def get_mining():
    data = fetch_telemetry("mining_surveys.db")
    data["module"] = "Mining OS"
    return data

@router.get("/aerospace")
def get_aerospace():
    data = fetch_telemetry("aerospace_telemetry.db")
    data["module"] = "Aerospace OS"
    return data

@router.get("/pharma")
def get_pharma():
    data = fetch_telemetry("pharma_trials.db")
    data["module"] = "Pharma OS"
    return data

@router.get("/fashion")
def get_fashion():
    data = fetch_telemetry("fashion_trends.db")
    data["module"] = "Fashion OS"
    return data

@router.get("/foodbev")
def get_foodbev():
    data = fetch_telemetry("foodbev_inventory.db")
    data["module"] = "Foodbev OS"
    return data

@router.get("/audio")
def get_audio():
    data = fetch_telemetry("audio_stems.db")
    data["module"] = "Audio OS"
    return data

@router.get("/video")
def get_video():
    data = fetch_telemetry("video_broadcast.db")
    data["module"] = "Video OS"
    return data

@router.get("/photography")
def get_photography():
    data = fetch_telemetry("photography_assets.db")
    data["module"] = "Photography OS"
    return data

@router.get("/animation")
def get_animation():
    data = fetch_telemetry("animation_vfx.db")
    data["module"] = "Animation OS"
    return data

@router.get("/translation")
def get_translation():
    data = fetch_telemetry("translation_corpus.db")
    data["module"] = "Translation OS"
    return data

@router.get("/writing")
def get_writing():
    data = fetch_telemetry("writing_manuscripts.db")
    data["module"] = "Writing OS"
    return data

@router.get("/seo")
def get_seo():
    data = fetch_telemetry("seo_analytics.db")
    data["module"] = "Seo OS"
    return data

@router.get("/socialmedia")
def get_socialmedia():
    data = fetch_telemetry("social_metrics.db")
    data["module"] = "Socialmedia OS"
    return data

@router.get("/pr")
def get_pr():
    data = fetch_telemetry("pr_campaigns.db")
    data["module"] = "Pr OS"
    return data

@router.get("/sports")
def get_sports():
    data = fetch_telemetry("sports_analytics.db")
    data["module"] = "Sports OS"
    return data

@router.get("/landscaping")
def get_landscaping():
    data = fetch_telemetry("landscaping.db")
    data["module"] = "Landscaping OS"
    return data

@router.get("/realestatedev")
def get_realestatedev():
    data = fetch_telemetry("real_estate_dev.db")
    data["module"] = "Realestatedev OS"
    return data

@router.get("/hvac")
def get_hvac():
    data = fetch_telemetry("hvac.db")
    data["module"] = "Hvac OS"
    return data

@router.get("/plumbing")
def get_plumbing():
    data = fetch_telemetry("plumbing.db")
    data["module"] = "Plumbing OS"
    return data

@router.get("/electrical")
def get_electrical():
    data = fetch_telemetry("electrical.db")
    data["module"] = "Electrical OS"
    return data

@router.get("/cleaning")
def get_cleaning():
    data = fetch_telemetry("cleaning.db")
    data["module"] = "Cleaning OS"
    return data

@router.get("/security")
def get_security():
    data = fetch_telemetry("security.db")
    data["module"] = "Security OS"
    return data

@router.get("/pestcontrol")
def get_pestcontrol():
    data = fetch_telemetry("pestcontrol.db")
    data["module"] = "Pestcontrol OS"
    return data

@router.get("/wastemgmt")
def get_wastemgmt():
    data = fetch_telemetry("wastemgmt.db")
    data["module"] = "Wastemgmt OS"
    return data

@router.get("/delivery")
def get_delivery():
    data = fetch_telemetry("delivery.db")
    data["module"] = "Delivery OS"
    return data

@router.get("/datacenter")
def get_datacenter():
    data = fetch_telemetry("datacenter.db")
    data["module"] = "Datacenter OS"
    return data

@router.get("/devops")
def get_devops():
    data = fetch_telemetry("devops.db")
    data["module"] = "Devops OS"
    return data

@router.get("/cloudfinops")
def get_cloudfinops():
    data = fetch_telemetry("cloudfinops.db")
    data["module"] = "Cloudfinops OS"
    return data

@router.get("/quantum")
def get_quantum():
    data = fetch_telemetry("quantum.db")
    data["module"] = "Quantum OS"
    return data

@router.get("/robotics")
def get_robotics():
    data = fetch_telemetry("robotics.db")
    data["module"] = "Robotics OS"
    return data

@router.get("/cv")
def get_cv():
    data = fetch_telemetry("cv.db")
    data["module"] = "Cv OS"
    return data

@router.get("/blockchain")
def get_blockchain():
    data = fetch_telemetry("blockchain.db")
    data["module"] = "Blockchain OS"
    return data

@router.get("/syntheticbio")
def get_syntheticbio():
    data = fetch_telemetry("syntheticbio.db")
    data["module"] = "Syntheticbio OS"
    return data

@router.get("/materials")
def get_materials():
    data = fetch_telemetry("materials.db")
    data["module"] = "Materials OS"
    return data

@router.get("/nlpresearch")
def get_nlpresearch():
    data = fetch_telemetry("nlpresearch.db")
    data["module"] = "Nlpresearch OS"
    return data

@router.get("/edgeiot")
def get_edgeiot():
    data = fetch_telemetry("edgeiot.db")
    data["module"] = "Edgeiot OS"
    return data

@router.get("/observability")
def get_observability():
    data = fetch_telemetry("observability.db")
    data["module"] = "Observability OS"
    return data

@router.get("/embedded")
def get_embedded():
    data = fetch_telemetry("embedded.db")
    data["module"] = "Embedded OS"
    return data

@router.get("/gamearch")
def get_gamearch():
    data = fetch_telemetry("gamearch.db")
    data["module"] = "Gamearch OS"
    return data

@router.get("/pentesting")
def get_pentesting():
    data = fetch_telemetry("pentesting.db")
    data["module"] = "Pentesting OS"
    return data

@router.get("/autovehicles")
def get_autovehicles():
    data = fetch_telemetry("autovehicles.db")
    data["module"] = "Autovehicles OS"
    return data

@router.get("/ardev")
def get_ardev():
    data = fetch_telemetry("ardev.db")
    data["module"] = "Ardev OS"
    return data

@router.get("/semiconductors")
def get_semiconductors():
    data = fetch_telemetry("semiconductors.db")
    data["module"] = "Semiconductors OS"
    return data

@router.get("/nanotech")
def get_nanotech():
    data = fetch_telemetry("nanotech.db")
    data["module"] = "Nanotech OS"
    return data

@router.get("/deepspace")
def get_deepspace():
    data = fetch_telemetry("deepspace.db")
    data["module"] = "Deepspace OS"
    return data

