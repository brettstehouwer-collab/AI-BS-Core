"""
AI-BS Manuscript & Screenplay ChromaDB Ingestion Runner
Parses Final Draft (.fdx), Fountain (.fountain), and Manuscript Book Chunks (.json/.txt)
across all projects and indexes them into project-specific ChromaDB vector collections.
"""

import os
import sys
import asyncio
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from core.project_rag import (
    SCREENPLAY_ROOT,
    sync_project_screenplay,
    get_project_stats,
    get_project_collection_name
)

async def ingest_all_projects():
    print("=" * 70)
    print("      AI-BS VECTORIZED RAG: MANUSCRIPT & FDX SCREENPLAY INGESTION")
    print("=" * 70)
    
    if not SCREENPLAY_ROOT.exists():
        print(f"[ERROR] Screenplay root directory not found: {SCREENPLAY_ROOT}")
        return

    projects = [p for p in SCREENPLAY_ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")]
    print(f"Found {len(projects)} projects in {SCREENPLAY_ROOT}\n")

    summary_results = []
    for project_dir in projects:
        project_name = project_dir.name
        print(f"📁 Processing Project: '{project_name}'...")
        
        try:
            res = await sync_project_screenplay(project_name)
            stats = get_project_stats(project_name)
            print(f"   ✅ Indexed: {res.get('indexed_docs', 0)} docs | Total Collection Count: {stats.get('total_docs', 0)}")
            print(f"   📊 FDX Scenes: {stats.get('fdx_scenes', 0)} | Fountain Scenes: {stats.get('script_scenes', 0)} | Book Chunks: {stats.get('book_chunks', 0)}")
            summary_results.append({
                "project": project_name,
                "status": "SUCCESS",
                "stats": stats
            })
        except Exception as e:
            print(f"   ❌ Ingestion error on {project_name}: {e}")
            summary_results.append({
                "project": project_name,
                "status": "ERROR",
                "error": str(e)
            })
        print("-" * 50)

    print("\n" + "=" * 70)
    print("                      INGESTION COMPLETE SUMMARY")
    print("=" * 70)
    for s in summary_results:
        print(f"  • {s['project']}: {s['status']} (Total Vector Docs: {s.get('stats', {}).get('total_docs', 0)})")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(ingest_all_projects())
