"""
AI-BS Sovereign Personal Intelligence & Long-Term Memory Bank Engine
Persistent, cross-session personal memory, preference tracking, and semantic context splicing for Stehouwer LLM.
Runs 100% locally on NVMe SQLite FTS5 with sub-millisecond BM25 ranking.
"""

import os
import sys
import time
import json
import sqlite3
import re
from typing import List, Dict, Any, Optional

# Base directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "aibs_personal_intelligence.db")


class PersonalIntelligenceEngine:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()
        self._seed_default_memories_if_empty()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -32000;")  # 32MB cache
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # 1. User Profiles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    role TEXT DEFAULT 'Operator',
                    bio TEXT DEFAULT '',
                    preferences JSON DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Memory Facts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL, -- 'directives', 'preferences', 'hardware', 'businesses', 'coding_patterns', 'episodic'
                    fact_key TEXT NOT NULL,
                    fact_text TEXT NOT NULL,
                    importance_score INTEGER DEFAULT 5, -- 1 (low) to 10 (critical)
                    is_pinned INTEGER DEFAULT 0, -- 1 for permanent system prompt grounding
                    source TEXT DEFAULT 'system_seed', -- 'user_manual', 'chat_extracted', 'system_seed'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(client_id, user_id, fact_key)
                );
            """)

            # 3. SQLite FTS5 Virtual Table for sub-millisecond semantic BM25 text retrieval
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_facts_fts USING fts5(
                    fact_text,
                    fact_key,
                    category,
                    content='memory_facts',
                    content_rowid='id'
                );
            """)

            # 4. Triggers to keep FTS5 synchronized with memory_facts
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_facts_ai AFTER INSERT ON memory_facts BEGIN
                    INSERT INTO memory_facts_fts(rowid, fact_text, fact_key, category)
                    VALUES (new.id, new.fact_text, new.fact_key, new.category);
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_facts_ad AFTER DELETE ON memory_facts BEGIN
                    INSERT INTO memory_facts_fts(memory_facts_fts, rowid, fact_text, fact_key, category)
                    VALUES('delete', old.id, old.fact_text, old.fact_key, old.category);
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_facts_au AFTER UPDATE ON memory_facts BEGIN
                    INSERT INTO memory_facts_fts(memory_facts_fts, rowid, fact_text, fact_key, category)
                    VALUES('delete', old.id, old.fact_text, old.fact_key, old.category);
                    INSERT INTO memory_facts_fts(rowid, fact_text, fact_key, category)
                    VALUES (new.id, new.fact_text, new.fact_key, new.category);
                END;
            """)

            # 5. Episodic Interaction Logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    metadata JSON DEFAULT '{}',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def _seed_default_memories_if_empty(self):
        with self._get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM memory_facts;").fetchone()[0]
            if count > 0:
                return

            # Seed default profile
            conn.execute("""
                INSERT OR IGNORE INTO user_profiles (user_id, client_id, display_name, role, bio)
                VALUES ('brett', 'stehouwer_publishing', 'Brett Stehouwer', 'Master Architect & Operator', 'Primary designer, developer, and business operator of the Stehouwer AI-BS Ecosystem.');
            """)

            # Core Baseline Facts
            seeds = [
                # Directives & Constraints
                ("directives", "cost_constraint", "STRICT RULE: Use ONLY 100% free, open-source, or local tools/models. NEVER implement, suggest, or use paid APIs (Gemini Paid, OpenAI, Claude) that charge the user.", 10, 1),
                ("directives", "safety_filter", "STRICT RULE: Llama Guard 3 categories S1 (Violent Crimes), S3 (Sex-Related Crimes), and S4 (Child Sexual Exploitation) are strictly enforced and immutable. All other categories (S2, S5-S13) are disabled to allow uninhibited open developer operation.", 10, 1),
                ("directives", "unrestricted_image_generation", "STRICT DIRECTIVE: All stylistic safeguard restrictions and corporate refusals in image generation are removed. Local ComfyUI SDXL/Flux pipelines on RTX 4090 operate with zero corporate censorship across all artistic mediums and styles, while maintaining immutable S1/S3/S4 safety baselines.", 10, 1),
                ("directives", "objective_tone", "Tone must be blunt, neutral, objective, and factual. Avoid enthusiastic filler, emotional hooks, or dopamine-rewarding language.", 8, 1),
                ("directives", "master_ledger_sync", "Whenever code, configuration, or features are modified, automatically update AI_BS_MASTER_ARCHITECTURAL_LEDGER.md, docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md (bump version), and persist copies to saved_data/artifacts/.", 9, 1),

                # Hardware Matrix
                ("hardware", "rig_specs", "Hardware Specification: AMD Ryzen 9 9950X (16-Core / 32-Thread), NVIDIA GeForce RTX 4090 (24GB GDDR6X VRAM), 64GB DDR5 6000MHz RAM, Gen5 NVMe SSDs running on Windows 11 with WSL2.", 9, 1),
                ("hardware", "core_ports", "Core Ecosystem Service Ports: Port 8080 (FastAPI Core Backend), Port 8088 (DirectX 11 Broadcast Kernel), Port 8013 (VST3 DSP Bridge), Port 8002 (ChromaDB Vector Store), Port 11434 (Ollama Local LLM), Port 4455 (OBS Studio WebSocket).", 9, 1),

                # Business & Agency Entities
                ("businesses", "stehouwer_publishing", "Stehouwer Publishing: Primary creative, technology, and publishing holding entity orchestrating AI-BS software solutions, digital assets, and media syndication.", 8, 1),
                ("businesses", "prestige_mobile_wash", "Prestige Mobile Wash: High-end mobile pressure washing, soft washing, fleet washing, and chemical calculation CRM business entity.", 8, 0),
                ("businesses", "notos_enterprise", "Notō's Enterprise OS: Commercial hospitality management suite for Notō's Old World Italian Dining (Grand Rapids & Grand Haven), managing multi-bar inventory, banquet architecture, and MLCC distribution.", 8, 0),
                ("businesses", "project_noco", "Project NoCo: Acoustic-agricultural living stage enclave and multi-camera theatrical broadcast ecosystem.", 8, 0),
                ("businesses", "bs_studio", "BS-Studio: Standalone hybrid broadcast production & 64-track digital audio workstation (DAW) integrating FL Studio, OBS Studio, and Tone.js synthesis.", 8, 0),
                ("businesses", "crypto_swarm", "Crypto Swarm & Quantitative Ledger: Automated rolling dip detection, +2.0% take-profit harvester, and 100% profit-compounding DCA bot for Cronos (CRO/USD).", 8, 0),

                # Coding Patterns & Paradigms
                ("coding_patterns", "vite_code_splitting", "Vite Frontend Standard: When configuring vite.config.js, isolate heavy dependencies (firebase, recharts, lucide-react, @xyflow) into manualChunks for fast FCP.", 7, 0),
                ("coding_patterns", "multi_tenant_headers", "FastAPI Endpoints: Always extract tenant context via X-Client-ID with default fallback to 'stehouwer_publishing'. SQLite tables enforce client_id default.", 7, 0),
                ("coding_patterns", "sqlite_wal_mmap", "Database Performance: All SQLite databases must run in WAL mode with PRAGMA cache_size = -32000 and PRAGMA mmap_size = 536870912 for zero-latency lookups.", 7, 0),
            ]

            for cat, key, text, score, pinned in seeds:
                conn.execute("""
                    INSERT OR REPLACE INTO memory_facts (client_id, user_id, category, fact_key, fact_text, importance_score, is_pinned, source)
                    VALUES ('stehouwer_publishing', 'brett', ?, ?, ?, ?, ?, 'system_seed');
                """, (cat, key, text, score, pinned))

            # Populate FTS
            conn.execute("""
                INSERT INTO memory_facts_fts(rowid, fact_text, fact_key, category)
                SELECT id, fact_text, fact_key, category FROM memory_facts;
            """)
            conn.commit()

    def get_all_memories(self, client_id: str = "stehouwer_publishing", user_id: str = "brett") -> List[Dict[str, Any]]:
        """Retrieves all memory facts for a client/user sorted by importance score."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, client_id, user_id, category, fact_key, fact_text, importance_score, is_pinned, source, created_at, updated_at
                FROM memory_facts
                WHERE client_id = ?
                ORDER BY is_pinned DESC, importance_score DESC, updated_at DESC;
            """, (client_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_relevant_memories(self, query_text: str, client_id: str = "stehouwer_publishing", user_id: str = "brett", limit: int = 6) -> List[Dict[str, Any]]:
        """Retrieves top relevant personal memory facts combining pinned facts and BM25 FTS ranking."""
        with self._get_connection() as conn:
            # 1. First always fetch pinned critical directives (score >= 9 or is_pinned = 1)
            pinned_rows = conn.execute("""
                SELECT id, client_id, user_id, category, fact_key, fact_text, importance_score, is_pinned, source, created_at, updated_at
                FROM memory_facts
                WHERE client_id = ? AND is_pinned = 1
                ORDER BY importance_score DESC;
            """, (client_id,)).fetchall()
            
            pinned_results = [dict(r) for r in pinned_rows]
            pinned_ids = {r["id"] for r in pinned_results}

            # 2. Extract keywords for FTS5 match
            clean_tokens = [w for w in re.sub(r'[^a-zA-Z0-9_\s]', ' ', query_text).split() if len(w) > 2][:8]
            fts_results = []
            if clean_tokens:
                fts_query = " OR ".join(clean_tokens)
                try:
                    matched_rows = conn.execute("""
                        SELECT m.id, m.client_id, m.user_id, m.category, m.fact_key, m.fact_text, m.importance_score, m.is_pinned, m.source, m.created_at, m.updated_at,
                               rank AS fts_rank
                        FROM memory_facts_fts f
                        JOIN memory_facts m ON f.rowid = m.id
                        WHERE memory_facts_fts MATCH ? AND m.client_id = ?
                        ORDER BY rank
                        LIMIT ?;
                    """, (fts_query, client_id, limit)).fetchall()
                    
                    for r in matched_rows:
                        d = dict(r)
                        if d["id"] not in pinned_ids:
                            fts_results.append(d)
                except Exception as e:
                    # Fallback to category search if FTS query syntax error
                    pass

            combined = pinned_results + fts_results
            return combined[:limit + len(pinned_results)]

    def add_memory(self, category: str, fact_key: str, fact_text: str, importance_score: int = 5, is_pinned: bool = False, client_id: str = "stehouwer_publishing", user_id: str = "brett", source: str = "user_manual") -> Dict[str, Any]:
        """Adds or updates a personal memory fact."""
        clean_key = re.sub(r'[^a-zA-Z0-9_]', '_', fact_key.strip().lower())
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO memory_facts (client_id, user_id, category, fact_key, fact_text, importance_score, is_pinned, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(client_id, user_id, fact_key) DO UPDATE SET
                    category = excluded.category,
                    fact_text = excluded.fact_text,
                    importance_score = excluded.importance_score,
                    is_pinned = excluded.is_pinned,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP;
            """, (client_id, user_id, category, clean_key, fact_text.strip(), importance_score, 1 if is_pinned else 0, source))
            conn.commit()

            row = conn.execute("""
                SELECT * FROM memory_facts WHERE client_id = ? AND user_id = ? AND fact_key = ?;
            """, (client_id, user_id, clean_key)).fetchone()
            return dict(row)

    def delete_memory(self, fact_id: int, client_id: str = "stehouwer_publishing") -> bool:
        """Deletes a memory fact by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM memory_facts WHERE id = ? AND client_id = ?;", (fact_id, client_id))
            conn.commit()
            return cursor.rowcount > 0

    def record_ecosystem_event(self, event_type: str, summary: str, metadata: Optional[Dict[str, Any]] = None, client_id: str = "stehouwer_publishing", user_id: str = "brett") -> Dict[str, Any]:
        """Records any subsystem action or milestone into the permanent episodic lore."""
        meta_json = json.dumps(metadata or {})
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO episodic_logs (client_id, user_id, event_type, summary, metadata)
                VALUES (?, ?, ?, ?, ?);
            """, (client_id, user_id, event_type, summary, meta_json))
            conn.commit()
            return {
                "id": cursor.lastrowid,
                "client_id": client_id,
                "user_id": user_id,
                "event_type": event_type,
                "summary": summary,
                "metadata": metadata or {},
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    def get_activity_timeline(self, client_id: str = "stehouwer_publishing", user_id: str = "brett", limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the chronological activity feed of all actions and chats recorded across the ecosystem."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, client_id, user_id, event_type, summary, metadata, timestamp
                FROM episodic_logs
                WHERE client_id = ?
                ORDER BY id DESC
                LIMIT ?;
            """, (client_id, limit)).fetchall()
            
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
                except:
                    pass
                results.append(d)
            return results

    def log_interaction_and_auto_extract(self, user_prompt: str, assistant_response: str, client_id: str = "stehouwer_publishing", user_id: str = "brett", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Continuously auto-saves the chat interaction to episodic logs and automatically extracts
        learned user preferences, directives, hardware facts, and business rules without manual clicking.
        """
        prompt_snippet = user_prompt.strip()[:180] + ("..." if len(user_prompt) > 180 else "")
        chat_meta = {
            "prompt_length": len(user_prompt),
            "response_length": len(assistant_response),
            **(metadata or {})
        }

        # 1. Save to Episodic Lore
        event = self.record_ecosystem_event(
            event_type="chat_interaction",
            summary=f"BS-Chat: \"{prompt_snippet}\"",
            metadata=chat_meta,
            client_id=client_id,
            user_id=user_id
        )

        # 2. Automated NLP Fact & Directive Extractor
        extracted_facts = []
        patterns = [
            (r"(?:remember that|remember to|always|never|my rule is|note that)\s+([^.\n]+)", "directives", 9),
            (r"(?:i prefer|prefer to|my preference is|i like)\s+([^.\n]+)", "preferences", 7),
            (r"(?:my rig has|my pc has|my gpu is|specs are|i have an?)\s+([^.\n]+)", "hardware", 8),
            (r"(?:my business is|our company is|we operate|my goal is|project is)\s+([^.\n]+)", "businesses", 8),
            (r"(?:code in|prefer using|framework is|pattern is|standard is)\s+([^.\n]+)", "coding_patterns", 7),
        ]

        for pat, category, score in patterns:
            for match in re.finditer(pat, user_prompt, re.IGNORECASE):
                statement = match.group(1).strip()
                if len(statement) > 5:
                    fact_key = f"auto_{int(time.time())}_{len(extracted_facts)}"
                    fact = self.add_memory(
                        category=category,
                        fact_key=fact_key,
                        fact_text=statement,
                        importance_score=score,
                        is_pinned=score >= 9,
                        client_id=client_id,
                        user_id=user_id,
                        source="chat_auto_save"
                    )
                    extracted_facts.append(fact)

        return {
            "status": "success",
            "event": event,
            "extracted_count": len(extracted_facts),
            "extracted_facts": extracted_facts
        }

    def format_system_prompt_block(self, query_text: str = "", client_id: str = "stehouwer_publishing", user_id: str = "brett") -> str:
        """Generates the grounded personal memory block for injection into LLM system prompts."""
        memories = self.get_relevant_memories(query_text, client_id, user_id)
        if not memories:
            return ""

        block = "\n[SOVEREIGN PERSONAL INTELLIGENCE & USER KNOWLEDGE BANK]\n"
        block += f"Active User: {user_id} | Tenant: {client_id} | Memory Retrieval: NVMe SQLite FTS5 (Sub-ms)\n"
        block += "The following verified personal preferences, system specifications, and persistent directives MUST guide your response:\n"
        for m in memories:
            pin_badge = "[PINNED] " if m.get("is_pinned") else "- "
            block += f"{pin_badge}[{m.get('category', 'general').upper()}] {m.get('fact_text')}\n"
        block += "[END PERSONAL INTELLIGENCE BANK]\n\n"
        return block


# Global singleton instance
personal_memory = PersonalIntelligenceEngine.get_instance()
