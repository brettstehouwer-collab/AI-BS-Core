import os
import sys
import uuid
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import chromadb
from chromadb.config import Settings

# Add workspace to path to allow discord_notifier import
sys.path.append("C:\\AI-BS")
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg): print(msg)

RESOURCE_DIR = "E:\\AI_BS_Resources"
CHROMA_DIR = os.path.join(RESOURCE_DIR, "ChromaDB")

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

DOCS_PER_INDUSTRY = 50

# Mock document templates to simulate complex domain knowledge
DOCUMENT_TEMPLATES = [
    "Standard Operating Procedure: {industry} protocol {id}. Ensure compliance with regulatory standard {rand1}. Monitor threshold {rand2}%.",
    "Technical Manual for {industry} subsystem. When encountering error code {rand1}, verify the load balance is below {rand2}%.",
    "Compliance Ledger: {industry} sector audit. Validated {rand1} instances. Found anomalies in sector block {rand2}.",
    "Emergency Action Plan for {industry}. If telemetry metric {rand1} spikes, engage failsafe override sequence {rand2}.",
    "Performance Optimization Guide: {industry}. Reducing friction by {rand1}% increases overall throughput by {rand2}x."
]

print(f"Initializing Persistent ChromaDB Client at {CHROMA_DIR}")
client = chromadb.PersistentClient(path=CHROMA_DIR)

def seed_industry(key):
    collection_name = f"rag_{key}"
    try:
        collection = client.get_or_create_collection(name=collection_name)
        
        docs = []
        metas = []
        ids = []
        
        for i in range(DOCS_PER_INDUSTRY):
            template = random.choice(DOCUMENT_TEMPLATES)
            doc_text = template.format(
                industry=key.upper(), 
                id=i, 
                rand1=random.randint(100, 9999), 
                rand2=random.randint(10, 99)
            )
            
            docs.append(doc_text)
            metas.append({
                "source": "autonomous_seeder", 
                "industry": key, 
                "client_id": "stehouwer_publishing",
                "doc_type": "sop_manual",
                "importance": random.choice(["high", "medium", "low"])
            })
            ids.append(f"doc_{key}_{uuid.uuid4().hex[:8]}")
            
        # Add to collection (this calculates embeddings natively if using default embedding function)
        collection.add(
            documents=docs,
            metadatas=metas,
            ids=ids
        )
        return f"Successfully seeded {DOCS_PER_INDUSTRY} documents into {collection_name}"
    except Exception as e:
        return f"Error seeding {collection_name}: {str(e)}"

def main():
    print(f"Starting Multi-Threaded Vector Seeder for {len(industry_keys)} collections...")
    send_discord_update(f"AI-BS Phase 15: Initiated Deep Vector Data Ingestion for {len(industry_keys)} industries ({DOCS_PER_INDUSTRY} docs/each).")
    
    success_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(seed_industry, key): key for key in industry_keys}
        for future in as_completed(futures):
            key = futures[future]
            try:
                result = future.result()
                print(result)
                if "Successfully" in result:
                    success_count += 1
            except Exception as exc:
                print(f"Collection {key} generated an exception: {exc}")
                
    print(f"Vector Seeding Complete. {success_count}/{len(industry_keys)} collections populated.")
    send_discord_update(f"AI-BS Phase 15 Complete: Ingested {success_count * DOCS_PER_INDUSTRY} total vector documents into ChromaDB.")

if __name__ == "__main__":
    main()
