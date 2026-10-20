import sqlite3

def init_audio_vocal_db():
    con = sqlite3.connect(r'C:\AI-BS\backend\stehouwer_vault.db')
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS audio_vocal_projects (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file TEXT,
            stems_path TEXT,
            vocal_prompt TEXT,
            duration_seconds REAL,
            sample_rate INTEGER,
            status TEXT,
            metadata_json TEXT
        )
    ''')
    con.commit()
    con.close()
    print("audio_vocal_projects table initialized successfully.")

if __name__ == "__main__":
    init_audio_vocal_db()
