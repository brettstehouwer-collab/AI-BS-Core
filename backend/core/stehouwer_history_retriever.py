import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import chromadb
from typing import List, Dict, Any

DB_PATH = "C:/AI-BS/database/stehouwer_chronology.db"
LOCAL_CHROMA = "C:/AI-BS/database/ChromaDB_local"
E_CHROMA = "E:/AI_BS_Resources/ChromaDB"

def search_chronology_fts(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Executes sub-2ms SQLite FTS5 search across all ecosystem eras and versions."""
    results = []
    if not os.path.exists(DB_PATH):
        return results
    
    clean_query = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
    if not clean_query:
        return results
        
    terms = clean_query.split()[:12]
    if not terms:
        return results
    fts_query = " OR ".join(f'"{t}"*' for t in terms)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA mmap_size = 2147483648;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA cache_size = -64000;")
        cursor = conn.cursor()
        sql = """
        SELECT era, date, version, title, content, rank
        FROM chronology_fts
        WHERE chronology_fts MATCH ?
        ORDER BY rank
        LIMIT ?;
        """
        cursor.execute(sql, (fts_query, limit))
        rows = cursor.fetchall()
        for r in rows:
            results.append({
                "era": r[0],
                "date": r[1],
                "version": r[2],
                "title": r[3],
                "content": r[4]
            })
        conn.close()
    except Exception as e:
        print(f"[History Retriever FTS Error]: {e}")
    return results

def search_chronology_vector(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Executes semantic vector retrieval from ChromaDB."""
    results = []
    target_dir = E_CHROMA if os.path.exists(E_CHROMA) else LOCAL_CHROMA
    try:
        client = chromadb.PersistentClient(path=target_dir)
        coll = client.get_collection(name="stehouwer_master_chronology")
        res = coll.query(query_texts=[query], n_results=limit)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        for d, m in zip(docs, metas):
            results.append({
                "title": m.get("title", ""),
                "date": m.get("date", ""),
                "version": m.get("version", ""),
                "era": m.get("era", ""),
                "content": d
            })
    except Exception as e:
        print(f"[History Retriever Vector Notice]: {e}")
    return results

def get_stehouwer_historical_context(query: str) -> str:
    """Combines FTS5 and Vector semantic search to return exact factual grounding."""
    # First try FTS5
    fts_res = search_chronology_fts(query, limit=2)
    # Then try Vector
    vec_res = search_chronology_vector(query, limit=2)
    
    combined = []
    seen = set()
    for item in fts_res + vec_res:
        uid = f"{item.get('date')}_{item.get('title')}"
        if uid not in seen:
            seen.add(uid)
            combined.append(item)
            
    if not combined:
        return ""
        
    brief = ["### [Stehouwer Autonomous Memory & Historical Grounding]:"]
    for c in combined[:2]:
        brief.append(f"**Era/Date:** {c.get('era')} ({c.get('date')}) | **Version:** {c.get('version')}")
        brief.append(f"**Title:** {c.get('title')}")
        brief.append(f"**Record:** {c.get('content')[:600]}...\n")
        
    return "\n".join(brief)

if __name__ == "__main__":
    test_queries = [
        "when was our first vercel upload?",
        "what is the 90 day accumulation matrix?",
        "what is our silicon hardware chassis?",
        "what was updated in version 5.152.0?"
    ]
    for q in test_queries:
        print(f"\n==================== QUERY: {q} ====================")
        ctx = get_stehouwer_historical_context(q)
        print(ctx)
