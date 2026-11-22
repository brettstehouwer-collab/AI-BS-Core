"""
AI-BS Master Document & Vault Ingestion Script
Consolidates desktop documents, competitive prompts, training playlists, and indexes them into ChromaDB.
Zero external paid API cost (100% local).
"""

import os
import shutil
import json
import glob
from pathlib import Path

WORKSPACE = Path(r"C:\AI-BS")
DOCS_VAULT = WORKSPACE / "docs" / "archive_vault"
PROMPTS_VAULT = WORKSPACE / "backend" / "core" / "sovereign_reasoning" / "prompts"
TRAINING_VAULT = WORKSPACE / "docs" / "training"

DOCS_VAULT.mkdir(parents=True, exist_ok=True)
PROMPTS_VAULT.mkdir(parents=True, exist_ok=True)
TRAINING_VAULT.mkdir(parents=True, exist_ok=True)

print("=== 1. INGESTING DESKTOP ARCHIVE FOLDERS ===")
ingest_folder = Path(r"C:\Users\footb\OneDrive\Desktop\ingest folder")
if ingest_folder.exists():
    for f in ingest_folder.rglob("*.*"):
        if f.is_file() and f.suffix in [".md", ".txt", ".json", ".csv"]:
            target = DOCS_VAULT / f.name
            shutil.copy2(f, target)
            print(f"Ingested from ingest folder: {f.name}")

new_folder = Path(r"C:\Users\footb\OneDrive\Desktop\New folder")
if new_folder.exists():
    for f in new_folder.glob("*.*"):
        if f.is_file():
            if f.suffix in [".md", ".txt", ".pdf"]:
                shutil.copy2(f, DOCS_VAULT / f.name)
                print(f"Ingested from New folder: {f.name}")
            elif f.name == "leads_store.json":
                # Merge into lead harvesting store
                leads_target = WORKSPACE / "saved_data" / "leads_store.json"
                shutil.copy2(f, leads_target)
                print(f"Synced leads store: {leads_target}")

print("\n=== 2. INGESTING COMPETITION PROMPTS & REASONING BLUEPRINTS ===")
comp_folder = Path(r"C:\Users\footb\Documents\Compitition Data")
if comp_folder.exists():
    for f in comp_folder.glob("*.*"):
        if f.is_file():
            shutil.copy2(f, PROMPTS_VAULT / f.name)
            print(f"Ingested prompt blueprint: {f.name}")

print("\n=== 3. INGESTING TRAINING PLAYLISTS & FINE-TUNING GUIDES ===")
training_json = Path(r"C:\Users\footb\OneDrive\Desktop\Training videos.json")
if training_json.exists():
    shutil.copy2(training_json, TRAINING_VAULT / "training_videos_playlist_vault.json")
    print("Ingested: training_videos_playlist_vault.json")

training_md = Path(r"C:\Users\footb\OneDrive\Desktop\AI programing training.md")
if training_md.exists():
    shutil.copy2(training_md, TRAINING_VAULT / "sovereign_llm_finetuning_guide.md")
    print("Ingested: sovereign_llm_finetuning_guide.md")

print("\n=== 4. INDEXING INGESTED DOCUMENTS INTO CHROMADB PORT 8001 ===")
try:
    import chromadb
    client = chromadb.HttpClient(host="127.0.0.1", port=8001)
    coll = client.get_or_create_collection(
        name="ai_bs_master_history",
        metadata={"description": "AI-BS Historical Architecture, Master Ledgers, Monetization & Prompt Vault"}
    )
    
    docs_to_index = []
    ids_to_index = []
    metas_to_index = []
    
    for f in DOCS_VAULT.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                # Take chunks up to 4000 chars
                chunk = content[:4000]
                doc_id = f"doc_{f.stem}"
                docs_to_index.append(chunk)
                ids_to_index.append(doc_id)
                metas_to_index.append({"filename": f.name, "category": "architecture_history", "source": "archive_vault"})
        except Exception as e:
            print(f"Error reading {f.name}: {e}")
            
    for f in PROMPTS_VAULT.glob("*.*"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                chunk = content[:4000]
                doc_id = f"prompt_{f.stem}"
                docs_to_index.append(chunk)
                ids_to_index.append(doc_id)
                metas_to_index.append({"filename": f.name, "category": "competition_prompt", "source": "prompt_vault"})
        except Exception as e:
            print(f"Error reading {f.name}: {e}")

    if docs_to_index:
        coll.upsert(
            documents=docs_to_index,
            ids=ids_to_index,
            metadatas=metas_to_index
        )
        print(f"Successfully upserted {len(docs_to_index)} documents into ChromaDB 'ai_bs_master_history' (Port 8001)!")
except Exception as e:
    print(f"Notice: ChromaDB indexing deferred or handled offline: {e}")

print("\nIngestion Complete!")
