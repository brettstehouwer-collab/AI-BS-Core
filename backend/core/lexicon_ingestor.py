import os
import json
import sqlite3
import glob

DB_PATH = r"C:\AI-BS\backend\lexicon_vault.db"
WORDSET_DIR = r"C:\AI-BS\docs\wordset-dictionary-master\data"
MOBY_PATH = r"C:\AI-BS\backend\node_modules\moby\words.txt"

def init_db():
    print(f"Initializing Lexicon Vault at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create tables
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            part_of_speech TEXT,
            definition TEXT,
            example TEXT,
            synonyms TEXT,
            source TEXT
        )
    ''')
    
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_word ON dictionary(word)
    ''')
    
    # FTS5 Virtual Table for fast semantic-like lexical searching
    cur.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS dictionary_fts USING fts5(
            word, part_of_speech, definition, example, synonyms, source, content='dictionary', content_rowid='id'
        )
    ''')
    
    # Trigger to keep FTS updated
    cur.execute('''
        CREATE TRIGGER IF NOT EXISTS dictionary_ai AFTER INSERT ON dictionary BEGIN
            INSERT INTO dictionary_fts(rowid, word, part_of_speech, definition, example, synonyms, source)
            VALUES (new.id, new.word, new.part_of_speech, new.definition, new.example, new.synonyms, new.source);
        END;
    ''')
    
    # Clear existing data for fresh ingestion
    cur.execute("DELETE FROM dictionary")
    cur.execute("DELETE FROM dictionary_fts")
    
    conn.commit()
    return conn

def ingest_moby(conn):
    print("Ingesting Moby Thesaurus...")
    if not os.path.exists(MOBY_PATH):
        print(f"Moby path {MOBY_PATH} not found. Skipping.")
        return
        
    cur = conn.cursor()
    count = 0
    with open(MOBY_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = [p.strip() for p in line.split(',')]
            if not parts:
                continue
            word = parts[0]
            synonyms = ", ".join(parts[1:])
            if not word or not synonyms:
                continue
                
            cur.execute('''
                INSERT INTO dictionary (word, part_of_speech, definition, example, synonyms, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (word, "", "Synonym cluster", "", synonyms, "moby_thesaurus"))
            count += 1
            if count % 10000 == 0:
                conn.commit()
                
    conn.commit()
    print(f"Ingested {count} root synonym clusters from Moby.")

def ingest_wordset(conn):
    print("Ingesting Wordset Dictionary...")
    if not os.path.exists(WORDSET_DIR):
        print(f"Wordset dir {WORDSET_DIR} not found. Skipping.")
        return
        
    cur = conn.cursor()
    count = 0
    json_files = glob.glob(os.path.join(WORDSET_DIR, "*.json"))
    
    for jf in json_files:
        print(f"Processing {os.path.basename(jf)}...")
        with open(jf, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Failed to parse {jf}: {e}")
                continue
                
            for word_key, word_data in data.items():
                word = word_data.get("word", word_key)
                meanings = word_data.get("meanings", [])
                
                for meaning in meanings:
                    definition = meaning.get("def", "")
                    speech_part = meaning.get("speech_part", "")
                    example = meaning.get("example", "")
                    syns = meaning.get("synonyms", [])
                    syns_str = ", ".join([str(s) for s in syns if s is not None]) if syns else ""
                    
                    cur.execute('''
                        INSERT INTO dictionary (word, part_of_speech, definition, example, synonyms, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (word, speech_part, definition, example, syns_str, "wordset_dictionary"))
                    count += 1
                    
        conn.commit()
        
    print(f"Ingested {count} meanings from Wordset Dictionary.")

def main():
    conn = init_db()
    ingest_moby(conn)
    ingest_wordset(conn)
    
    # Analyze and optimize
    print("Optimizing SQLite database...")
    conn.execute("PRAGMA optimize;")
    conn.execute("VACUUM;")
    conn.close()
    print("Ingestion complete. Lexicon Vault is ready for LLM Lexicographical Augmentation.")

if __name__ == "__main__":
    main()
