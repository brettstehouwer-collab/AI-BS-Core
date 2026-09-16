import sqlite3
import os
import json
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "lexicon_vault.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA mmap_size = 2147483648;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -64000;")
    conn.row_factory = sqlite3.Row
    return conn

class LexiconService:
    @staticmethod
    def get_synonyms(word: str, limit: int = 10) -> list:
        """
        Looks up synonyms for a specific word using FTS5.
        Returns a list of synonym strings.
        """
        conn = get_db_connection()
        try:
            # Query the FTS5 virtual table for speed
            cursor = conn.cursor()
            cursor.execute('''
                SELECT synonyms 
                FROM dictionary_fts 
                WHERE dictionary_fts MATCH ?
                LIMIT ?
            ''', (word, limit))
            
            results = []
            for row in cursor.fetchall():
                if row['synonyms']:
                    # Assuming synonyms are comma separated in the DB
                    syns = [s.strip() for s in row['synonyms'].split(',') if s.strip()]
                    results.extend(syns)
                    
            # Return unique synonyms, preserving order mostly
            seen = set()
            unique_results = []
            for s in results:
                if s.lower() not in seen and s.lower() != word.lower():
                    seen.add(s.lower())
                    unique_results.append(s)
            
            return unique_results[:limit]
        finally:
            conn.close()

    @staticmethod
    def hybrid_tool_lookup(word: str) -> str:
        """
        Designed to be called directly by the LLM as a tool.
        Returns a JSON string containing the word, part of speech, definition, and synonyms.
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT word, part_of_speech, definition, synonyms, source
                FROM dictionary
                WHERE word = ? COLLATE NOCASE
                LIMIT 3
            ''', (word,))
            
            rows = cursor.fetchall()
            if not rows:
                return json.dumps({"error": f"No entry found for '{word}'."})
                
            entries = []
            for row in rows:
                entries.append({
                    "word": row["word"],
                    "part_of_speech": row["part_of_speech"],
                    "definition": row["definition"],
                    "synonyms": [s.strip() for s in row["synonyms"].split(',')] if row["synonyms"] else [],
                    "source": row["source"]
                })
                
            return json.dumps({"results": entries})
        finally:
            conn.close()

    @staticmethod
    def bulk_expand(text: str, max_words: int = 15) -> dict:
        """
        Takes a block of text, identifies significant words, and returns a dictionary 
        mapping those words to their top synonyms. Fast single-connection query capped at max_words.
        """
        if not text:
            return {}
        # Sample the first 1000 chars to avoid processing multi-megabyte payloads
        sample_text = text[:1000]
        words = list(dict.fromkeys(re.findall(r'\b[a-zA-Z]{4,}\b', sample_text)))[:max_words]
        
        expansion_map = {}
        try:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                for w in words:
                    cursor.execute('''
                        SELECT synonyms 
                        FROM dictionary_fts 
                        WHERE dictionary_fts MATCH ?
                        LIMIT 3
                    ''', (w,))
                    results = []
                    for row in cursor.fetchall():
                        if row['synonyms']:
                            syns = [s.strip() for s in row['synonyms'].split(',') if s.strip()]
                            results.extend(syns)
                    seen = set()
                    unique_results = []
                    for s in results:
                        if s.lower() not in seen and s.lower() != w.lower():
                            seen.add(s.lower())
                            unique_results.append(s)
                    if unique_results:
                        expansion_map[w] = unique_results[:3]
            finally:
                conn.close()
        except Exception:
            pass
            
        return expansion_map
