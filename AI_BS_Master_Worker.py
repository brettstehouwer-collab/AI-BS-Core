import os
import sqlite3
import datetime
import time
import random
import sys
import psutil
import requests
import asyncio

sys.path.append("C:\\AI-BS")
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg): print(msg)

RESOURCE_DIR = "E:\\AI_BS_Resources"
DB_DIR = os.path.join(RESOURCE_DIR, "Databases")

# We use the list generated from phase 9
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

def get_real_crypto_price(symbol="BTCUSDT"):
    try:
        response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=2)
        if response.status_code == 200:
            return float(response.json()["price"])
    except Exception:
        pass
    return None

last_crypto_fetch_time = 0
cached_btc_price = None

def get_cached_btc_price():
    global last_crypto_fetch_time, cached_btc_price
    current_time = time.time()
    # Cache for 15 seconds to avoid API bans
    if current_time - last_crypto_fetch_time > 15 or cached_btc_price is None:
        price = get_real_crypto_price("BTCUSDT")
        if price:
            cached_btc_price = price
            last_crypto_fetch_time = current_time
    return cached_btc_price

def get_real_system_metrics():
    net_io = psutil.net_io_counters()
    cpu_usage = psutil.cpu_percent(interval=None)
    ram_usage = psutil.virtual_memory().percent
    network_rx_mb = round(net_io.bytes_recv / 1048576, 2)
    network_tx_mb = round(net_io.bytes_sent / 1048576, 2)

    return {
        "cpu_usage": round(cpu_usage, 2),
        "ram_usage": round(ram_usage, 2),
        "network_rx_mb": network_rx_mb,
        "network_tx_mb": network_tx_mb
    }

def inject_telemetry():
    target_dbs = random.sample(db_names, k=random.randint(5, 15))
    metrics = get_real_system_metrics()
    btc_price = get_cached_btc_price()
    if btc_price:
        metrics["btc_price_usd"] = btc_price

    for db in target_dbs:
        db_path = os.path.join(RESOURCE_DIR, db)
        if not os.path.exists(db_path):
            continue
            
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            for metric, value in metrics.items():
                status = "OK"
                if metric in ("cpu_usage", "ram_usage") and value > 90.0:
                    status = "WARNING"
                
                c.execute(
                    "INSERT INTO system_telemetry (metric_name, metric_value, status) VALUES (?, ?, ?)",
                    (metric, value, status)
                )
                
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error injecting into {db}: {e}")

async def run_worker_loop():
    psutil.cpu_percent(interval=None) # warmup
    print("AI_BS_Master_Worker initialized. Injecting real telemetry into 70 vertical databases...")
    send_discord_update("Phase 10: AI_BS_Master_Worker started. Real data injection has begun.")
    
    tick_count = 0
    try:
        while True:
            await asyncio.to_thread(inject_telemetry)
            tick_count += 1
            if tick_count % 10 == 0:
                print(f"[{datetime.datetime.now()}] Worker Tick {tick_count}: Injected real telemetry batch.")
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        print("Worker stopped.")
        send_discord_update("AI_BS_Master_Worker stopped.")

def run_worker():
    try:
        asyncio.run(run_worker_loop())
    except KeyboardInterrupt:
        print("Worker stopped.")

if __name__ == "__main__":
    run_worker()
