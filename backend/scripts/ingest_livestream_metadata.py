import os
import sys
import time
import sqlite3
import chromadb
from typing import Dict, Any

RESOURCE_DIR = "E:\\AI_BS_Resources"
CHROMA_DIR = os.path.join(RESOURCE_DIR, "ChromaDB")
SQLITE_DB = "C:/AI-BS/backend/stehouwer_vault.db"

def ingest_livestream():
    stream_data = {
        "id": "youtube_livestream_xZ9FOZ2g878",
        "title": "YouTube Live Stream Feed (xZ9FOZ2g878)",
        "source": "YouTube Live",
        "url": "https://www.youtube.com/live/xZ9FOZ2g878",
        "embed_url": "https://www.youtube.com/embed/xZ9FOZ2g878",
        "content_type": "live_stream_video",
        "author": "Brett Stehouwer / AI-BS",
        "shoutout_note": "Shout out to the live stream! These guys are great!",
        "tags": "livestream, youtube, scoring, daw_sync, broadcast_studio, reflex",
        "timestamp": time.time(),
        "client_id": "stehouwer_publishing"
    }

    doc_text = f"""Title: {stream_data['title']}
Source: {stream_data['source']}
URL: {stream_data['url']}
Embed URL: {stream_data['embed_url']}
Author: {stream_data['author']}
Note: {stream_data['shoutout_note']}
Tags: {stream_data['tags']}
Client ID: {stream_data['client_id']}
Description: Active live stream broadcast feed ingested for real-time video scoring in DAW VideoPreviewMonitor, theatrical teleprompter cues, and autonomous OBS stream reflex lower-thirds."""

    # 1. Ingest into ChromaDB
    try:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = chroma_client.get_or_create_collection(
            name="aibs_media_vault",
            metadata={"description": "AI-BS Media Vault and Broadcast Feeds"}
        )
        collection.upsert(
            ids=[stream_data["id"]],
            documents=[doc_text],
            metadatas=[{
                "title": stream_data["title"],
                "url": stream_data["url"],
                "source": stream_data["source"],
                "content_type": stream_data["content_type"],
                "client_id": stream_data["client_id"],
                "timestamp": stream_data["timestamp"]
            }]
        )
        print(f"[SUCCESS] ChromaDB: Ingested {stream_data['id']} into collection 'aibs_media_vault'")
    except Exception as e:
        print(f"[WARNING] ChromaDB Ingestion notice: {e}")

    # 2. Ingest into SQLite stehouwer_vault.db
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_vault (
                id TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                embed_url TEXT,
                source TEXT,
                content_type TEXT,
                shoutout_note TEXT,
                tags TEXT,
                client_id TEXT DEFAULT 'stehouwer_publishing',
                created_at REAL
            )
        """)
        cursor.execute("""
            INSERT OR REPLACE INTO media_vault (id, title, url, embed_url, source, content_type, shoutout_note, tags, client_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stream_data["id"],
            stream_data["title"],
            stream_data["url"],
            stream_data["embed_url"],
            stream_data["source"],
            stream_data["content_type"],
            stream_data["shoutout_note"],
            stream_data["tags"],
            stream_data["client_id"],
            stream_data["timestamp"]
        ))
        conn.commit()
        conn.close()
        print(f"[SUCCESS] SQLite: Persisted {stream_data['id']} to stehouwer_vault.db -> media_vault")
    except Exception as e:
        print(f"[WARNING] SQLite Ingestion error: {e}")

if __name__ == "__main__":
    ingest_livestream()
