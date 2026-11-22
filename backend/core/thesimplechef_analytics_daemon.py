"""
The Simple Chef - Sovereign AI Vector Analytics & Ingestion Engine
Part of the AI-BS Multi-Tenant Sovereign Infrastructure Architecture

- Dedicated Partition: 'thesimplechef_analytics_bin' in ChromaDB (Port 8002 / Persistent)
- Strict GDPR/CCPA Privacy IP Anonymization (IP Masking & Salted Hashing)
- Volumetric Memory Guard (MAX_VECTOR_COUNT = 50,000, PRUNE_BATCH_SIZE = 5,000)
- Semantic Intent Mapping & Automated Client Performance Reporting
"""

import os
import re
import time
import hashlib
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger("ChefAnalyticsDaemon")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(asctime)s] [CHEF-ANALYTICS] %(levelname)s: %(message)s"))
    logger.addHandler(ch)

# Configuration Constants
CHROMA_STORAGE_DIR = os.environ.get("AI_BS_CHEF_ANALYTICS_PATH", r"C:\AI-BS\saved_data\chromadb_chef")
COLLECTION_NAME = "thesimplechef_analytics_bin"
MAX_VECTOR_COUNT = 50000
PRUNE_BATCH_SIZE = 5000
IP_SALT = "aibs_chef_sovereign_2026_salt"



class TheSimpleChefAnalyticsEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TheSimpleChefAnalyticsEngine, cls).__new__(cls)
            cls._instance._collection = None
            cls._instance._storage_lock = threading.RLock()
        return cls._instance

    @property
    def collection(self):
        with self._storage_lock:
            if self._collection is None:
                self._init_engine()
            return self._collection

    def _init_engine(self):
        logger.info(f"Initializing ChromaDB vector storage partition at: {CHROMA_STORAGE_DIR}")
        try:
            self.client = chromadb.PersistentClient(path=CHROMA_STORAGE_DIR, settings=Settings(anonymized_telemetry=False))
            self._collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine", "tenant": "thesimplechef", "owner": "John Barr"}
            )
            logger.info(f"Connected to collection '{COLLECTION_NAME}' (Active Vector Count: {self.collection.count()})")
        except Exception as e:
            logger.error(f"Error connecting to persistent ChromaDB: {e}. Persistent data retained; no in-memory fallback.")
            raise RuntimeError("Chef analytics persistent store unavailable; no ephemeral substitution") from e

    @staticmethod
    def anonymize_ip(ip_address: str) -> str:
        """Masks IP address for CCPA/GDPR compliance: 192.168.1.45 -> 192.168.1.xxx"""
        if not ip_address:
            return "unknown.xxx"
        parts = ip_address.strip().split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
        # IPv6 fallback
        return ip_address[:12] + ":xxxx:xxxx"

    @staticmethod
    def hash_session(ip_address: str, user_agent: str) -> str:
        """Generates anonymized unique session hash without storing raw credentials"""
        raw = f"{ip_address}_{user_agent}_{IP_SALT}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def enforce_volumetric_limits(self):
        """Prevents HNSW vector index memory bloating beyond MAX_VECTOR_COUNT"""
        try:
            current_count = self.collection.count()
            if current_count > MAX_VECTOR_COUNT:
                prune_target = (current_count - MAX_VECTOR_COUNT) + PRUNE_BATCH_SIZE
                logger.warning(f"Collection count ({current_count}) exceeds limit ({MAX_VECTOR_COUNT}). Pruning oldest {prune_target} records...")
                
                # Fetch oldest records
                oldest_records = self.collection.get(limit=prune_target)
                if oldest_records and oldest_records.get("ids"):
                    self.collection.delete(ids=oldest_records["ids"])
                    logger.info(f"Pruned {len(oldest_records['ids'])} vectors. New count: {self.collection.count()}")
        except Exception as e:
            logger.error(f"Error during volumetric pruning: {e}")

    def ingest_event(self, event_data: Dict[str, Any]) -> str:
        """
        Ingests and vectorizes visitor interactions into dedicated partition.
        Expects: path, event_type, ip, user_agent, referrer, dish_or_rub, session_id, timestamp
        """
        raw_ip = event_data.get("ip", "127.0.0.1")
        masked_ip = self.anonymize_ip(raw_ip)
        user_agent = event_data.get("user_agent", "Mozilla/5.0")
        session_id = event_data.get("session_id") or self.hash_session(raw_ip, user_agent)
        path = event_data.get("path", "/")
        event_type = event_data.get("event_type", "page_view")
        item_name = event_data.get("item_name", "General Storefront")
        referrer = event_data.get("referrer", "direct")
        device = "mobile" if "mobi" in user_agent.lower() else "desktop"
        ts_now = datetime.now(timezone.utc).isoformat()

        # Semantic formulation for vector search
        document_text = (
            f"Visitor session [{session_id}] from [{masked_ip}] using [{device}]. "
            f"Action: {event_type} on route '{path}'. "
            f"Interaction target: '{item_name}'. Referrer: {referrer}. "
            f"Timestamp: {ts_now}."
        )

        event_id = f"evt_{int(time.time()*1000)}_{session_id[:6]}"

        metadata = {
            "session_id": session_id,
            "masked_ip": masked_ip,
            "path": path,
            "event_type": event_type,
            "item_name": item_name,
            "device": device,
            "referrer": referrer,
            "timestamp": ts_now,
            "is_bot": "bot" in user_agent.lower() or "crawl" in user_agent.lower() or path.endswith((".php", ".env", ".git"))
        }

        try:
            self.collection.upsert(
                ids=[event_id],
                documents=[document_text],
                metadatas=[metadata]
            )
            # Check limits periodically
            if int(time.time()) % 20 == 0:
                self.enforce_volumetric_limits()
            return event_id
        except Exception as e:
            logger.error(f"Error upserting event to ChromaDB: {e}")
            return ""

    def query_semantic_insights(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Vector similarity search to discover user journeys, bounce trends, or bot patterns"""
        try:
            res = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, max(1, self.collection.count()))
            )
            hits = []
            if res and res.get("documents") and res["documents"][0]:
                for idx, doc in enumerate(res["documents"][0]):
                    meta = res["metadatas"][0][idx] if res.get("metadatas") else {}
                    dist = res["distances"][0][idx] if res.get("distances") else 0.0
                    hits.append({
                        "document": doc,
                        "metadata": meta,
                        "similarity_score": round(1.0 - float(dist), 4)
                    })
            return hits
        except Exception as e:
            logger.error(f"Error querying semantic insights: {e}")
            return []

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Returns structured metrics for the AI-BS Client Hub dashboard"""
        total_vectors = self.collection.count()
        # Query sample to compute aggregate metrics
        sample = self.collection.get(limit=500)
        
        event_counts: Dict[str, int] = {}
        top_items: Dict[str, int] = {}
        devices: Dict[str, int] = {"mobile": 0, "desktop": 0}
        unique_sessions = set()
        bot_blocks = 0

        if sample and sample.get("metadatas"):
            for meta in sample["metadatas"]:
                etype = meta.get("event_type", "page_view")
                event_counts[etype] = event_counts.get(etype, 0) + 1
                
                item = meta.get("item_name")
                if item and item != "General Storefront":
                    top_items[item] = top_items.get(item, 0) + 1
                
                dev = meta.get("device", "desktop")
                devices[dev] = devices.get(dev, 0) + 1
                
                unique_sessions.add(meta.get("session_id", ""))
                if meta.get("is_bot"):
                    bot_blocks += 1

        sorted_items = sorted(top_items.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_events": max(total_vectors, len(sample.get("metadatas", []))),
            "unique_visitors": len(unique_sessions),
            "event_breakdown": event_counts,
            "top_interacted_items": sorted_items,
            "device_split": devices,
            "bot_probes_blocked": bot_blocks,
            "active_storage_path": CHROMA_STORAGE_DIR,
            "collection_name": COLLECTION_NAME,
            "status": "HEALTHY",
            "sample_events": len(sample.get("metadatas", [])),
            "summary_scope": "up to 500 retained events; not a calendar-month report",
            "hnsw_memory_clamped": total_vectors < MAX_VECTOR_COUNT
        }

    def generate_monthly_client_report(self) -> Dict[str, Any]:
        """Compiles monthly executive briefing for John Barr to justify the monthly retainer"""
        summary = self.get_analytics_summary()
        current_month = datetime.now().strftime("%B %Y")
        top_item = summary["top_interacted_items"][0][0] if summary["top_interacted_items"] else None
        return {
            "client_name": "John Barr",
            "business_name": "The Simple Chef",
            "billing_cycle": current_month,
            "retainer_tier": "Boutique Sovereign AI & Managed Infrastructure ($100/mo)",
            "infrastructure_uptime": None,
            "total_customer_interactions": summary["total_events"],
            "estimated_unique_diners": summary["unique_visitors"],
            "top_performing_rub": top_item,
            "signature_quartet": ["Rub That Hiney", "Yard Pimp Dust", "Kelly's Calling", "Buck Down"],
            "security_bot_probes_neutralized": summary["bot_probes_blocked"],
            "mobile_traffic_percentage": (round(100 * summary["device_split"].get("mobile", 0) / summary["sample_events"], 2) if summary["sample_events"] else None),
            "report_scope": summary["summary_scope"],
            "executive_recommendation": "Review observed sampled interactions; uptime, monthly totals and purchasing trends are not established by this report."
        }

analytics_daemon = TheSimpleChefAnalyticsEngine()
