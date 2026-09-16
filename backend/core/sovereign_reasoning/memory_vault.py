import os
import sqlite3
import datetime

class SovereignMemoryVault:
    """
    Unified Memory-Mapped NVMe Retrieval & Historical Fact Engine.
    Combines:
    1. Chronological Master Archives (Stehouwer Historical Context)
    2. Lexicon Vault contextual vocabulary expansion
    3. FTS5 full-text fast search with PRAGMA mmap_size
    """

    MASTER_DB = r"C:\AI-BS\database\LLM_CrossCheck_Ledger.db"
    MASTER_ARCHIVE_MD = r"C:\AI-BS\STEHOUWER_OMNI_CHRONOLOGICAL_MASTER_ARCHIVE.md"

    @classmethod
    def get_unified_context(cls, prompt: str) -> str:
        context_blocks = []

        # 1. Historical Stehouwer Archive Facts
        try:
            from core.stehouwer_history_retriever import get_stehouwer_historical_context
            hist = get_stehouwer_historical_context(prompt)
            if hist:
                context_blocks.append(hist)
        except Exception:
            pass

        # 2. Lexicon Vocabulary Expansion
        try:
            from core.lexicon_service import LexiconService
            lexicon_expansion = LexiconService.bulk_expand(prompt)
            if lexicon_expansion:
                lex_text = "Contextual Lexicon Vector Enhancements:\n" + "\n".join([f"- {k}: {', '.join(v)}" for k,v in lexicon_expansion.items()])
                context_blocks.append(lex_text)
        except Exception:
            pass

        # 3. Omni-Space Multi-Database Context (11 SQLite Spaces)
        try:
            from core.omni_space_manager import omni_space_manager
            if len(prompt.strip()) < 250:
                space_res = omni_space_manager.search_all_spaces(prompt, limit_per_space=2)
                if space_res.get("total_matches", 0) > 0:
                    snippets = []
                    for s_key, s_data in space_res.get("matches_by_space", {}).items():
                        for rec in s_data.get("records", [])[:2]:
                            tbl = rec.get("table")
                            d = rec.get("data", {})
                            items_str = ", ".join([f"{k}: {v}" for k, v in list(d.items())[:4]])
                            snippets.append(f"[{s_key}::{tbl}] {items_str}")
                    if snippets:
                        context_blocks.append("Live Multi-Space Database Records:\n" + "\n".join(snippets[:5]))
        except Exception:
            pass

        return "\n\n".join(context_blocks)


    @classmethod
    def log_inference_telemetry(cls, model: str, prompt: str, response: str, score: float = 98.5):
        try:
            os.makedirs(os.path.dirname(cls.MASTER_DB), exist_ok=True)
            conn = sqlite3.connect(cls.MASTER_DB)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA mmap_size=268435456;") # 256MB mmap
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS crosscheck_ledger 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, model TEXT, prompt TEXT, response TEXT, score REAL)''')
            ts = datetime.datetime.now().isoformat()
            c.execute("INSERT INTO crosscheck_ledger (timestamp, model, prompt, response, score) VALUES (?, ?, ?, ?, ?)",
                      (ts, model, prompt[:500], response[:1500], score))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[MemoryVault] Telemetry log error: {e}")
