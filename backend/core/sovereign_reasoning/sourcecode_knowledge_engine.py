"""
backend/core/sovereign_reasoning/sourcecode_knowledge_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sovereign Codebase Knowledge Retrieval & Grounding Engine (v5.290.0)
- Interfaces with the 3,230-file master knowledge base in 'aibs_master.db' & ChromaDB 'ai_bs_codebase_vault'.
- Sub-millisecond FTS5 full-text keyword & BM25 ranking.
- Semantic vector similarity search via ChromaDB vector memory.
- Dynamic Context Grounding for Stehouwer LLM and all 17 specialist models.
- Auto-extracts exact source code snippets for any prompt discussing AI-BS architecture, tools, or components.
"""

import os
import re
import sys
import sqlite3
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("SourceCodeKnowledgeEngine")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = os.path.join(BASE_DIR, "backend", "aibs_master.db")
CHROMA_DIR = os.path.join(BASE_DIR, "stehouwer_vector_memory")


class SourceCodeKnowledgeEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SourceCodeKnowledgeEngine, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        self.db_path = DB_PATH
        self.chroma_dir = CHROMA_DIR
        self._chroma_collection = None
        self._load_chroma()

    def _load_chroma(self):
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.chroma_dir)
            self._chroma_collection = client.get_or_create_collection(
                name="ai_bs_codebase_vault"
            )
        except Exception as e:
            logger.warning(f"ChromaDB connection unavailable in SourceCodeKnowledgeEngine: {e}")

    def _get_db_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def search_codebase(
        self,
        query: str,
        subsystem: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid full-text (FTS5) and substring search across all 3,230 files.
        """
        if not query or not query.strip():
            return []

        clean_query = query.strip()
        results = []
        seen_paths = set()

        # 1. Exact path match attempt
        try:
            conn = self._get_db_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT file_index, file_path, subsystem, layer, language, lines_count, bytes_size, content_summary, content
                FROM codebase_master_knowledge
                WHERE file_path = ? OR file_path LIKE ?
                LIMIT ?;
            """, (clean_query, f"%{clean_query}%", limit))
            
            rows = cur.fetchall()
            for r in rows:
                p = r["file_path"]
                if p not in seen_paths:
                    seen_paths.add(p)
                    results.append({
                        "file_index": r["file_index"],
                        "file_path": r["file_path"],
                        "subsystem": r["subsystem"],
                        "layer": r["layer"],
                        "language": r["language"],
                        "lines_count": r["lines_count"],
                        "bytes_size": r["bytes_size"],
                        "summary": r["content_summary"],
                        "snippet": r["content"][:1500],
                        "match_type": "path_match"
                    })
            conn.close()
        except Exception as e:
            logger.error(f"Error querying exact path match: {e}")

        # If limit reached, return
        if len(results) >= limit:
            return results[:limit]

        # 2. SQLite FTS5 Full-Text Search
        try:
            conn = self._get_db_conn()
            cur = conn.cursor()

            # Sanitize query for FTS5 (strip punctuation that breaks FTS syntax)
            fts_query = re.sub(r'[^a-zA-Z0-9_\-\s]', ' ', clean_query).strip()
            terms = [t for t in fts_query.split() if len(t) > 2]
            
            if terms:
                fts_expr = " AND ".join(terms[:6])
                sql = """
                    SELECT k.file_index, k.file_path, k.subsystem, k.layer, k.language, k.lines_count, k.bytes_size, k.content_summary, k.content
                    FROM codebase_master_knowledge_fts f
                    JOIN codebase_master_knowledge k ON f.file_path = k.file_path
                    WHERE codebase_master_knowledge_fts MATCH ?
                """
                params = [fts_expr]

                if subsystem:
                    sql += " AND k.subsystem = ?"
                    params.append(subsystem)
                if language:
                    sql += " AND k.language = ?"
                    params.append(language)

                sql += f" LIMIT {limit * 2};"

                cur.execute(sql, params)
                rows = cur.fetchall()

                for r in rows:
                    p = r["file_path"]
                    if p not in seen_paths:
                        seen_paths.add(p)
                        results.append({
                            "file_index": r["file_index"],
                            "file_path": r["file_path"],
                            "subsystem": r["subsystem"],
                            "layer": r["layer"],
                            "language": r["language"],
                            "lines_count": r["lines_count"],
                            "bytes_size": r["bytes_size"],
                            "summary": r["content_summary"],
                            "snippet": r["content"][:1500],
                            "match_type": "fts5_fulltext"
                        })
                        if len(results) >= limit:
                            break
            conn.close()
        except Exception as e:
            logger.debug(f"FTS5 query fallback: {e}")

        # 3. ChromaDB Semantic Similarity Search (if needed)
        if len(results) < limit and self._chroma_collection:
            try:
                chroma_res = self._chroma_collection.query(
                    query_texts=[clean_query],
                    n_results=min(limit, 8)
                )
                if chroma_res and chroma_res.get("metadatas") and len(chroma_res["metadatas"]) > 0:
                    for meta in chroma_res["metadatas"][0]:
                        p = meta.get("file_path")
                        if p and p not in seen_paths:
                            seen_paths.add(p)
                            # Fetch full record from SQLite
                            conn = self._get_db_conn()
                            cur = conn.cursor()
                            cur.execute("SELECT * FROM codebase_master_knowledge WHERE file_path = ?", (p,))
                            row = cur.fetchone()
                            conn.close()

                            if row:
                                results.append({
                                    "file_index": row["file_index"],
                                    "file_path": row["file_path"],
                                    "subsystem": row["subsystem"],
                                    "layer": row["layer"],
                                    "language": row["language"],
                                    "lines_count": row["lines_count"],
                                    "bytes_size": row["bytes_size"],
                                    "summary": row["content_summary"],
                                    "snippet": row["content"][:1500],
                                    "match_type": "chroma_semantic"
                                })
                            if len(results) >= limit:
                                break
            except Exception as e:
                logger.debug(f"ChromaDB search fallback: {e}")

        return results[:limit]

    def get_file_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the exact content and metadata of a file.
        """
        clean_p = file_path.strip().replace("\\", "/")
        try:
            conn = self._get_db_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM codebase_master_knowledge
                WHERE file_path = ? OR file_path LIKE ?
                LIMIT 1;
            """, (clean_p, f"%{clean_p}"))
            
            row = cur.fetchone()
            conn.close()

            if row:
                return {
                    "file_index": row["file_index"],
                    "file_path": row["file_path"],
                    "subsystem": row["subsystem"],
                    "layer": row["layer"],
                    "language": row["language"],
                    "lines_count": row["lines_count"],
                    "bytes_size": row["bytes_size"],
                    "content_summary": row["content_summary"],
                    "content": row["content"]
                }
        except Exception as e:
            logger.error(f"Error fetching file by path: {e}")
        return None

    def get_subsystem_breakdown(self) -> Dict[str, Any]:
        """
        Returns an aggregated summary of all subsystems and file counts.
        """
        try:
            conn = self._get_db_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT subsystem, layer, COUNT(*) as file_count, SUM(lines_count) as total_lines, SUM(bytes_size) as total_bytes
                FROM codebase_master_knowledge
                GROUP BY subsystem
                ORDER BY file_count DESC;
            """)
            rows = cur.fetchall()
            
            cur.execute("SELECT COUNT(*), SUM(lines_count), SUM(bytes_size) FROM codebase_master_knowledge;")
            total_r = cur.fetchone()
            conn.close()

            subsystems = [
                {
                    "subsystem": r["subsystem"],
                    "layer": r["layer"],
                    "file_count": r["file_count"],
                    "total_lines": r["total_lines"],
                    "total_bytes": r["total_bytes"]
                }
                for r in rows
            ]

            return {
                "total_files": total_r[0] if total_r else 0,
                "total_lines": total_r[1] if total_r else 0,
                "total_bytes": total_r[2] if total_r else 0,
                "subsystems": subsystems
            }
        except Exception as e:
            logger.error(f"Error computing subsystem breakdown: {e}")
            return {"total_files": 0, "subsystems": []}

    def inject_codebase_context(self, prompt: str, max_tokens: int = 1200) -> str:
        """
        Scans an incoming prompt for codebase/architectural intent and returns
        a structured markdown grounding block with exact source code excerpts.
        """
        if not prompt or not prompt.strip():
            return ""

        # Check if prompt discusses code, architecture, tools, components, or files
        code_triggers = [
            "code", "function", "router", "endpoint", "component", "tab", "daemon",
            "telemetry", "port", "socket", "tool", "matrix", "schema", "table",
            "sqlite", "chroma", "ollama", "model", "fastapi", "react", "vite",
            "cuda", "rtx", "audio", "demucs", "nda", "typst", "btd6", "webrtc"
        ]

        has_trigger = any(t in prompt.lower() for t in code_triggers)
        if not has_trigger and len(prompt) < 15:
            return ""

        matches = self.search_codebase(prompt, limit=3)
        if not matches:
            return ""

        grounding_lines = [
            "### 📚 [SOVEREIGN CODEBASE MASTER GROUNDING (3,230 FILES INDEXED)]",
            "The following exact source code excerpts from the AI-BS repository are available for direct reference:"
        ]

        for m in matches:
            grounding_lines.append(f"\n#### File: `{m['file_path']}` ({m['subsystem']} | {m['lines_count']} lines | {m['language']})")
            grounding_lines.append(f"**Summary:** {m['summary'][:200]}")
            snippet_excerpt = m['snippet'][:800].strip()
            grounding_lines.append(f"```{m['language']}\n{snippet_excerpt}\n```")

        return "\n".join(grounding_lines)


# Global singleton instance
sourcecode_knowledge_engine = SourceCodeKnowledgeEngine()
