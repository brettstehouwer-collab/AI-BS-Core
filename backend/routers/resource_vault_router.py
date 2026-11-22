"""
AI-BS Multi-Vault SQLite Catalog Router
Mounts 50+ domain databases located in E:\AI_BS_Resources\ in-place.
Enforces read-only WAL mode with zero-copy to Drive C.
Integrates with ChromaDB on Port 8001 for schema routing.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/vaults", tags=["Resource Vaults"])

VAULT_ROOT = Path(r"E:\AI_BS_Resources")

class QueryRequest(BaseModel):
    vault_name: str
    query: str
    limit: Optional[int] = 50

def get_vault_path(vault_name: str) -> Path:
    # Ensure no path traversal
    safe_name = os.path.basename(vault_name)
    if not safe_name.endswith((".db", ".sqlite", ".sqlite3")):
        safe_name += ".db"
        
    target = VAULT_ROOT / safe_name
    if not target.exists():
        # Check subfolder Databases
        sub_target = VAULT_ROOT / "Databases" / safe_name
        if sub_target.exists():
            return sub_target
        raise HTTPException(status_code=404, detail=f"Vault database '{safe_name}' not found on {VAULT_ROOT}")
    return target

@router.get("/list")
async def list_vaults():
    """Lists all available domain databases in E:\\AI_BS_Resources with sizes and table counts."""
    if not VAULT_ROOT.exists():
        return {"status": "offline", "message": f"Vault root {VAULT_ROOT} not accessible", "vaults": []}

    vaults = []
    # Search root and Databases subfolder
    db_files = list(VAULT_ROOT.glob("*.db")) + list((VAULT_ROOT / "Databases").glob("*.db"))
    
    for db_path in sorted(set(db_files)):
        try:
            size_mb = round(db_path.stat().st_size / (1024 * 1024), 2)
            # Count tables quickly
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            table_count = cursor.fetchone()[0]
            conn.close()
            
            vaults.append({
                "vault_name": db_path.name,
                "relative_path": str(db_path.relative_to(VAULT_ROOT)),
                "size_mb": size_mb,
                "table_count": table_count,
                "status": "online"
            })
        except Exception as e:
            vaults.append({
                "vault_name": db_path.name,
                "relative_path": str(db_path.relative_to(VAULT_ROOT)),
                "size_mb": round(db_path.stat().st_size / (1024 * 1024), 2) if db_path.exists() else 0,
                "table_count": 0,
                "status": f"error: {str(e)}"
            })
            
    return {
        "status": "online",
        "total_vaults": len(vaults),
        "root": str(VAULT_ROOT),
        "vaults": vaults
    }

@router.get("/schema/{vault_name}")
async def get_vault_schema(vault_name: str):
    """Returns the DDL structure and tables for a specific vault database."""
    db_path = get_vault_path(vault_name)
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%';")
        tables = [{"name": row[0], "sql": row[1]} for row in cursor.fetchall()]
        conn.close()
        return {"vault_name": db_path.name, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read schema from {vault_name}: {e}")

@router.post("/query")
async def execute_vault_query(req: QueryRequest):
    """Executes a read-only SELECT query against the specified vault database."""
    db_path = get_vault_path(req.vault_name)
    clean_query = req.query.strip()
    
    # Strictly enforce read-only
    upper_query = clean_query.upper()
    if not upper_query.startswith("SELECT") and not upper_query.startswith("PRAGMA") and not upper_query.startswith("EXPLAIN"):
        raise HTTPException(status_code=400, detail="Only SELECT or read-only PRAGMA queries are permitted.")
        
    for forbidden in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "ATTACH", "DETACH"]:
        if forbidden in upper_query.split():
            raise HTTPException(status_code=400, detail=f"Mutation statement '{forbidden}' forbidden in read-only vault query.")
            
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = ON;")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        limit = min(req.limit or 50, 200)
        cursor.execute(clean_query)
        rows = cursor.fetchmany(limit)
        
        result_rows = [dict(row) for row in rows]
        columns = [col[0] for col in cursor.description] if cursor.description else []
        conn.close()
        
        return {
            "vault_name": db_path.name,
            "columns": columns,
            "row_count": len(result_rows),
            "rows": result_rows
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vault query error: {e}")

@router.post("/index-schemas")
async def index_vault_schemas_to_chroma():
    """Extracts all table schemas from all 50+ vault DBs and upserts them into ChromaDB Port 8001."""
    import chromadb
    client = chromadb.HttpClient(host="127.0.0.1", port=8001)
    coll = client.get_or_create_collection(
        name="ai_bs_domain_vaults",
        metadata={"description": "Table schemas and metadata across all 50+ AI-BS domain databases in E:\\AI_BS_Resources"}
    )
    
    db_files = list(VAULT_ROOT.glob("*.db")) + list((VAULT_ROOT / "Databases").glob("*.db"))
    indexed_count = 0
    docs, ids, metas = [], [], []
    
    for db_path in sorted(set(db_files)):
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            rows = cursor.fetchall()
            conn.close()
            
            schema_summary = f"Database: {db_path.name}\n"
            table_names = []
            for t_name, sql in rows:
                table_names.append(t_name)
                schema_summary += f"\nTable: {t_name}\nSchema:\n{sql}\n"
                
            if rows:
                rel_id = str(db_path.relative_to(VAULT_ROOT)).replace("\\", "_").replace("/", "_").replace(".", "_")
                doc_id = f"vault_schema_{rel_id}"
                docs.append(schema_summary[:4000])
                ids.append(doc_id)
                metas.append({
                    "vault_name": db_path.name,
                    "relative_path": str(db_path.relative_to(VAULT_ROOT)),
                    "tables": ", ".join(table_names),
                    "size_mb": round(db_path.stat().st_size / (1024 * 1024), 2)
                })
                indexed_count += 1
        except Exception as e:
            print(f"Skipping {db_path.name}: {e}")
            
    if docs:
        coll.upsert(documents=docs, ids=ids, metadatas=metas)
        
    return {
        "status": "success",
        "databases_indexed": indexed_count,
        "collection": "ai_bs_domain_vaults"
    }
