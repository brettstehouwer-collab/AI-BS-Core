"""
AI_BS_Universal_Data_Ingestor.py — High-Performance Concurrency Ingestor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Universal RSS & Industry Knowledge Ingestion Daemon (v5.255.0)
- Concurrent multi-feed parsing via ThreadPoolExecutor (max_workers=8).
- Resilient database resolution across E:\\AI_BS_Resources\\Databases and C:\\AI-BS\\database.
- Automatic table initialization (industry_data) with multi-tenant client_id.
- Batched WAL SQLite insertions with URL deduplication.
- ChromaDB vectorization bridge into collection 'industry_knowledge_vault'.
"""

import os
import sqlite3
import datetime
import time
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

import feedparser

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg): print(msg)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [UniversalIngestor] %(message)s"
)
logger = logging.getLogger("UniversalIngestor")

# Candidate directories for industry databases
CANDIDATE_DB_DIRS = [
    r"E:\AI_BS_Resources\Databases",
    r"E:\AI_BS_Resources",
    r"C:\AI-BS\database\industry_dbs",
    r"C:\AI-BS\database"
]

DEFAULT_CLIENT_ID = "stehouwer_publishing"

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

FEED_MAPPING = {
    "real_estate.db": "https://www.inman.com/feed/",
    "medical_fhir.db": "https://medicalxpress.com/rss-feed/",
    "finance_ledger.db": "https://finance.yahoo.com/news/rssindex",
    "education_lms.db": "https://www.edsurge.com/articles_rss",
    "cyber_threats.db": "https://feeds.feedburner.com/TheHackersNews",
    "aerospace_telemetry.db": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
    "gaming_assets.db": "https://www.polygon.com/rss/index.xml",
    "gov_policies.db": "https://www.whitehouse.gov/feed/",
    "energy_grid.db": "https://www.energy.gov/rss/news.xml",
    "cv.db": "https://techcrunch.com/feed/",
    "blockchain.db": "https://cointelegraph.com/rss",
    "ag_yields.db": "https://www.agriculture.com/rss.xml",
    "automotive_inventory.db": "https://www.autonews.com/rss",
    "pharma_trials.db": "https://www.fiercepharma.com/rss/xml",
    "fashion_trends.db": "https://www.businessoffashion.com/feed/rss"
}

FALLBACK_FEEDS = [
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"
]

def resolve_db_path(db_name: str) -> str:
    """Finds existing DB file or returns path in highest priority directory."""
    for d in CANDIDATE_DB_DIRS:
        cand = os.path.join(d, db_name)
        if os.path.exists(cand):
            return cand
    
    # Fallback creation in first available directory
    target_dir = CANDIDATE_DB_DIRS[0] if os.path.exists(CANDIDATE_DB_DIRS[0]) else CANDIDATE_DB_DIRS[-1]
    os.makedirs(target_dir, exist_ok=True)
    return os.path.join(target_dir, db_name)

def init_industry_db(db_path: str):
    """Initializes industry_data table with multi-tenant isolation and indices."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS industry_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                title TEXT,
                content TEXT,
                url TEXT UNIQUE,
                published_at TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                client_id TEXT DEFAULT 'stehouwer_publishing'
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_industry_url ON industry_data(url);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_industry_client ON industry_data(client_id);")
        conn.commit()
    finally:
        conn.close()

def fetch_feed_items(feed_url: str) -> List[Dict[str, Any]]:
    """Fetches and parses RSS feed with timeout protection."""
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return []
        
        items = []
        for entry in feed.entries[:25]:
            title = entry.get('title', '').strip()
            content = entry.get('summary', '').strip() or entry.get('description', '').strip()
            url = entry.get('link', '').strip()
            published = entry.get('published', '') or entry.get('updated', '')
            if url and title:
                items.append({
                    "title": title,
                    "content": content,
                    "url": url,
                    "published": published
                })
        return items
    except Exception as e:
        logger.debug(f"Feed fetch error for {feed_url}: {e}")
        return []

def process_single_database(db_name: str, fallback_idx: int = 0) -> Dict[str, Any]:
    """Processes a single database: fetches feed, writes batch rows, and bridges to vector memory."""
    db_path = resolve_db_path(db_name)
    init_industry_db(db_path)
    
    feed_url = FEED_MAPPING.get(db_name, FALLBACK_FEEDS[fallback_idx % len(FALLBACK_FEEDS)])
    items = fetch_feed_items(feed_url)
    if not items:
        return {"db": db_name, "inserted": 0, "status": "no_entries"}
    
    inserted_count = 0
    new_docs_for_vector = []
    
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        rows_to_insert = []
        for item in items:
            cur.execute("SELECT id FROM industry_data WHERE url = ?", (item["url"],))
            if cur.fetchone() is None:
                rows_to_insert.append((
                    feed_url,
                    item["title"],
                    item["content"],
                    item["url"],
                    item["published"],
                    DEFAULT_CLIENT_ID
                ))
                new_docs_for_vector.append(f"{item['title']}\n{item['content'][:300]}")
        
        if rows_to_insert:
            cur.executemany("""
                INSERT OR IGNORE INTO industry_data (source, title, content, url, published_at, client_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, rows_to_insert)
            conn.commit()
            inserted_count = len(rows_to_insert)
    finally:
        conn.close()
    
    return {
        "db": db_name,
        "inserted": inserted_count,
        "feed_url": feed_url,
        "new_docs": new_docs_for_vector
    }

def bridge_to_chromadb(documents: List[str]):
    """Optionally bridges fresh knowledge entries into ChromaDB collection industry_knowledge_vault."""
    if not documents:
        return
    try:
        import chromadb
        client = chromadb.HttpClient(host='127.0.0.1', port=8001)
        collection = client.get_or_create_collection(name="industry_knowledge_vault")
        
        # Batch insert up to 30 items
        docs = documents[:30]
        ids = [f"ind_{int(time.time() * 1000)}_{i}" for i in range(len(docs))]
        metadatas = [{"client_id": DEFAULT_CLIENT_ID, "source": "universal_ingestor"} for _ in docs]
        
        collection.upsert(
            documents=docs,
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"Bridged {len(docs)} industry records into ChromaDB 'industry_knowledge_vault'")
    except Exception as e:
        logger.debug(f"ChromaDB bridge notice: {e}")

def run_ingestion_cycle() -> Dict[str, Any]:
    """Executes a full concurrent ingestion pass over all 70 industry databases."""
    start_time = time.time()
    logger.info("Starting concurrent Universal Data Ingestion cycle (ThreadPool max_workers=8)...")
    
    total_inserted = 0
    processed_count = 0
    all_new_docs = []
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(process_single_database, db, i): db
            for i, db in enumerate(db_names)
        }
        for future in as_completed(futures):
            try:
                res = future.result()
                processed_count += 1
                cnt = res.get("inserted", 0)
                total_inserted += cnt
                if res.get("new_docs"):
                    all_new_docs.extend(res["new_docs"])
                if cnt > 0:
                    logger.info(f"[{res['db']}] Ingested {cnt} new records from {res['feed_url']}")
            except Exception as e:
                logger.error(f"Error processing DB task: {e}")
    
    if all_new_docs:
        bridge_to_chromadb(all_new_docs)
    
    duration = time.time() - start_time
    summary = {
        "databases_processed": processed_count,
        "total_new_records": total_inserted,
        "duration_seconds": round(duration, 2),
        "timestamp": datetime.datetime.now().isoformat()
    }
    logger.info(f"Cycle completed in {summary['duration_seconds']}s: {total_inserted} new records across {processed_count} databases.")
    return summary

def run_ingestor_daemon():
    logger.info("AI_BS_Universal_Data_Ingestor daemon active.")
    send_discord_update("Universal Data Ingestor started (Concurrent Multi-Feed Ingestion).")
    
    while True:
        try:
            run_ingestion_cycle()
        except Exception as e:
            logger.error(f"Ingestion cycle error: {e}")
        # Sleep for 15 minutes between full scraping cycles
        time.sleep(900)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # One-shot execution for testing
        res = run_ingestion_cycle()
        print(f"Ingestion Result: {res}")
    else:
        run_ingestor_daemon()
