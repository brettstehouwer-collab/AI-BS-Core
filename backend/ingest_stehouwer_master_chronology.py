import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
import sqlite3
import chromadb
import uuid

CHRONO_MD = "C:/AI-BS/STEHOUWER_OMNI_CHRONOLOGICAL_MASTER_ARCHIVE.md"
DB_PATH = "C:/AI-BS/database/stehouwer_chronology.db"
LOCAL_CHROMA = "C:/AI-BS/database/ChromaDB_local"
E_CHROMA = "E:/AI_BS_Resources/ChromaDB"

os.makedirs("C:/AI-BS/database", exist_ok=True)
os.makedirs(LOCAL_CHROMA, exist_ok=True)

# 1. Parse markdown file into discrete chronological units
with open(CHRONO_MD, "r", encoding="utf-8") as f:
    text = f.read()

# Split by headers (## or | 2026-)
sections = re.split(r'\n(?=## |\n\| \d{4}-\d{2}-\d{2} \|)', text)

parsed_records = []

for sec in sections:
    sec = sec.strip()
    if not sec:
        continue
    
    # Extract date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', sec)
    date_str = date_match.group(1) if date_match else "2026-08-31"
    
    # Extract version
    ver_match = re.search(r'\[?(v?\d+\.\d+(\.\d+)?)\]?', sec)
    ver_str = ver_match.group(1) if ver_match else "General"
    
    # Extract title / summary
    first_line = sec.split("\n")[0].replace("#", "").replace("|", "").strip()
    title_str = first_line[:120]
    
    # Extract era
    era_str = "Ecosystem Evolution"
    if "Era 0" in sec or "2024" in sec:
        era_str = "Era 0: Fiscal & Tax Genesis"
    elif "Era 1" in sec or "90-Day" in sec or "Accumulation Matrix" in sec:
        era_str = "Era 1: Algorithmic Priming"
    elif "Era 2" in sec or "Capitalization" in sec or "Silicon" in sec:
        era_str = "Era 2: Capitalization Vectors & Silicon"
    elif "Era 3" in sec or "Vercel" in sec or "Genesis" in sec:
        era_str = "Era 3: AI-BS Genesis & Vercel Push"
    elif "Era 4" in sec:
        era_str = "Era 4: Multi-Modal Studio"
    elif "Era 5" in sec or "Theatrical" in sec or "Broadcast" in sec:
        era_str = "Era 5: Live Broadcast & DAW"
    elif "Era 6" in sec or "Pure VRAM" in sec or "BS-Studio" in sec:
        era_str = "Era 6: Neural Audio & Standalone Studio"
    elif "Era 7" in sec or "v5.152.0" in sec:
        era_str = "Era 7: Matrix Parity & Rust Cryptography"
        
    parsed_records.append({
        "era": era_str,
        "date": date_str,
        "version": ver_str,
        "title": title_str,
        "content": sec
    })

print(f"Extracted {len(parsed_records)} chronological knowledge units.")

# 2. Ingest into SQLite FTS5 Database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS chronology_fts;")
cursor.execute("DROP TABLE IF EXISTS chronology_meta;")

cursor.execute("""
CREATE VIRTUAL TABLE chronology_fts USING fts5(
    era,
    date,
    version,
    title,
    content,
    tokenize='porter unicode61'
);
""")

cursor.execute("""
CREATE TABLE chronology_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    era TEXT,
    date TEXT,
    version TEXT,
    title TEXT,
    content TEXT
);
""")

for r in parsed_records:
    cursor.execute("""
    INSERT INTO chronology_fts (era, date, version, title, content)
    VALUES (?, ?, ?, ?, ?);
    """, (r["era"], r["date"], r["version"], r["title"], r["content"]))
    
    cursor.execute("""
    INSERT INTO chronology_meta (era, date, version, title, content)
    VALUES (?, ?, ?, ?, ?);
    """, (r["era"], r["date"], r["version"], r["title"], r["content"]))

conn.commit()
conn.close()
print(f"SQLite FTS5 database written to {DB_PATH} (WAL mode).")

# 3. Ingest into ChromaDB Vector Stores (Local & E-Drive if present)
chroma_targets = [LOCAL_CHROMA]
if os.path.exists("E:/AI_BS_Resources"):
    os.makedirs(E_CHROMA, exist_ok=True)
    chroma_targets.append(E_CHROMA)

for target_dir in chroma_targets:
    try:
        client = chromadb.PersistentClient(path=target_dir)
        coll = client.get_or_create_collection(name="stehouwer_master_chronology")
        
        docs = []
        metas = []
        ids = []
        
        for idx, r in enumerate(parsed_records):
            doc_text = f"Title: {r['title']}\nDate: {r['date']}\nVersion: {r['version']}\nEra: {r['era']}\n\n{r['content']}"
            docs.append(doc_text)
            metas.append({
                "date": r["date"],
                "version": r["version"],
                "era": r["era"],
                "title": r["title"]
            })
            ids.append(f"chrono_{idx}_{r['date']}")
            
        coll.upsert(documents=docs, metadatas=metas, ids=ids)
        print(f"Ingested {len(docs)} documents into ChromaDB at {target_dir}")
    except Exception as e:
        print(f"Notice during ChromaDB ingestion at {target_dir}: {e}")

print("Ingestion complete!")
