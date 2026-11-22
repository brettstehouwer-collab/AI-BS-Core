import os
import sys

sys.path.append("C:\\AI-BS")
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg): print(msg)

import chromadb
from chromadb.config import Settings

RESOURCE_DIR = "E:\\AI_BS_Resources"
CHROMA_DIR = os.path.join(RESOURCE_DIR, "ChromaDB")
os.makedirs(CHROMA_DIR, exist_ok=True)

# Using the exact same 70 industry keys as the previous scripts
industry_keys = [
    "real_estate", "legal", "medical", "retail", "finance", "education", 
    "manufacturing", "agriculture", "entertainment", "cybersecurity", "hr", 
    "customer_support", "logistics", "insurance", "construction", "automotive", 
    "travel", "gaming", "ngo", "journalism", "wellness", "events", "gov", 
    "energy", "telecom", "mining", "aerospace", "pharma", "fashion", "foodbev", 
    "audio", "video", "photography", "animation", "translation", "writing",
    "seo", "socialmedia", "pr", "sports", "landscaping", "realestatedev", 
    "hvac", "plumbing", "electrical", "cleaning", "security", "pestcontrol", 
    "wastemgmt", "delivery", "datacenter", "devops", "cloudfinops", "quantum", 
    "robotics", "cv", "blockchain", "syntheticbio", "materials", "nlpresearch",
    "edgeiot", "observability", "embedded", "gamearch", "pentesting", "autovehicles", 
    "ardev", "semiconductors", "nanotech", "deepspace"
]

def main():
    print(f"Initializing ChromaDB Client at {CHROMA_DIR}")
    # Initialize a single ChromaDB client using PersistentClient for standard usage
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    print("Creating 70 dedicated vector collections...")
    for key in industry_keys:
        collection_name = f"rag_{key}"
        try:
            # We get or create to ensure idempotency
            collection = client.get_or_create_collection(name=collection_name)
            
            # Seed with one dummy document so it's not empty
            # Using basic embedding generation handled automatically by Chroma's default EF
            collection.add(
                documents=[f"Welcome to the {key} knowledge base. This contains specialized enterprise manuals."],
                metadatas=[{"source": "system_init", "industry": key, "client_id": "stehouwer_publishing"}],
                ids=[f"init_{key}_01"]
            )
            print(f" [+] Initialized collection: {collection_name}")
        except Exception as e:
            print(f" [!] Failed on {collection_name}: {e}")
            
    print("ChromaDB Initialization Complete.")
    send_discord_update(f"Phase 12 Complete: 70 Local ChromaDB vector collections initialized in {CHROMA_DIR}")

if __name__ == "__main__":
    main()
