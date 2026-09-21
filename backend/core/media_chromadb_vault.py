"""
AI-BS Dedicated Media ChromaDB & SQLite Vector Vault
---------------------------------------------------
Collection: 'stehouwer_media_memory'
Persists to: C:\\AI-BS\\chroma_db (when chromadb is installed)
and C:\\AI-BS\\backend\\stehouwer_vault.db (table: media_memory_vault) for resilient fallback.
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MediaChromaDBVault")

CHROMA_PERSIST_DIR = r"C:\AI-BS\chroma_db"
COLLECTION_NAME = "stehouwer_media_memory"
SQLITE_VAULT_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"

class MediaChromaDBVault:
    _instance = None
    _client = None
    _collection = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MediaChromaDBVault()
        return cls._instance

    def __init__(self):
        self._init_sqlite()
        self._init_chroma()

    def _init_sqlite(self):
        try:
            conn = sqlite3.connect(SQLITE_VAULT_PATH, timeout=5.0)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS media_memory_vault (
                    media_id TEXT PRIMARY KEY,
                    media_type TEXT,
                    title TEXT,
                    description TEXT,
                    file_path TEXT,
                    metadata_json TEXT,
                    created_at REAL
                );
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite media memory vault: {e}")

    def _init_chroma(self):
        try:
            import chromadb
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Dedicated Media ChromaDB for AI-BS BV-Media Creator & BsMedia-Chat"}
            )
            logger.info(f"MediaChromaDBVault connected to collection '{COLLECTION_NAME}'.")
        except Exception as e:
            logger.warning(f"ChromaDB native client fallback to SQLite vault: {e}")
            self._collection = None

    def add_media_asset(
        self,
        media_id: str,
        media_type: str,
        title: str,
        description: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Indexes a media asset into both ChromaDB and SQLite fallback."""
        meta = metadata or {}
        meta.update({
            "media_id": media_id,
            "media_type": media_type,
            "title": title,
            "file_path": file_path,
            "timestamp": time.time()
        })
        doc_text = f"[{media_type.upper()}] {title} | {description} | Path: {file_path}"

        # 1. Store in SQLite Vault
        try:
            conn = sqlite3.connect(SQLITE_VAULT_PATH, timeout=5.0)
            conn.execute("""
                INSERT OR REPLACE INTO media_memory_vault 
                (media_id, media_type, title, description, file_path, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (media_id, media_type, title, description, file_path, json.dumps(meta), time.time()))
            conn.commit()
            total_items = conn.execute("SELECT count(*) FROM media_memory_vault;").fetchone()[0]
            conn.close()
        except Exception as e:
            logger.error(f"SQLite media insert error: {e}")
            total_items = 0

        # 2. Store in ChromaDB if available
        if self._collection:
            sanitized_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    sanitized_meta[k] = v
                else:
                    sanitized_meta[k] = json.dumps(v)
            try:
                self._collection.upsert(
                    ids=[media_id],
                    documents=[doc_text],
                    metadatas=[sanitized_meta]
                )
            except Exception as ex:
                logger.warning(f"ChromaDB sync exception: {ex}")

        return {
            "status": "success",
            "media_id": media_id,
            "collection": COLLECTION_NAME,
            "total_items": total_items
        }

    def search_media_memory(self, query: str, top_k: int = 5, media_type: Optional[str] = None) -> Dict[str, Any]:
        """Semantic search across ChromaDB or SQLite LIKE search."""
        if self._collection:
            where_filter = {"media_type": media_type} if media_type else None
            try:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where_filter
                )
                formatted = []
                if results and results.get("ids") and results["ids"][0]:
                    for i in range(len(results["ids"][0])):
                        formatted.append({
                            "id": results["ids"][0][i],
                            "document": results["documents"][0][i] if results.get("documents") else "",
                            "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                            "distance": results["distances"][0][i] if results.get("distances") else 0.0
                        })
                return {
                    "status": "success",
                    "query": query,
                    "count": len(formatted),
                    "results": formatted,
                    "engine": "ChromaDB"
                }
            except Exception as e:
                logger.warning(f"Chroma query fallback to SQLite: {e}")

        # SQLite Fallback Search
        try:
            conn = sqlite3.connect(SQLITE_VAULT_PATH, timeout=5.0)
            cur = conn.cursor()
            sql = "SELECT media_id, media_type, title, description, file_path, metadata_json FROM media_memory_vault"
            params = []
            words = [w.strip() for w in query.strip().split() if w.strip()]
            if words:
                where_clauses = []
                for w in words:
                    where_clauses.append("(title LIKE ? OR description LIKE ?)")
                    term = f"%{w}%"
                    params.extend([term, term])
                sql += " WHERE " + " OR ".join(where_clauses)
            sql += f" LIMIT {top_k};"
            rows = cur.execute(sql, params).fetchall()
            conn.close()

            formatted = []
            for r in rows:
                formatted.append({
                    "id": r[0],
                    "document": f"[{r[1].upper()}] {r[2]} | {r[3]}",
                    "metadata": json.loads(r[5]) if r[5] else {},
                    "distance": 0.0
                })
            return {
                "status": "success",
                "query": query,
                "count": len(formatted),
                "results": formatted,
                "engine": "SQLite Vault Fallback"
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "results": []}

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics on media memory count."""
        try:
            conn = sqlite3.connect(SQLITE_VAULT_PATH, timeout=5.0)
            count = conn.execute("SELECT count(*) FROM media_memory_vault;").fetchone()[0]
            conn.close()
        except Exception:
            count = 0
        return {
            "collection_name": COLLECTION_NAME,
            "count": count,
            "persist_dir": CHROMA_PERSIST_DIR,
            "status": "online"
        }

media_chroma_vault = MediaChromaDBVault.get_instance()
